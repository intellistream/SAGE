"""Synthetic large-scale data analysis + LLM orchestration workload.

The workload models the kind of task SAGE is good at orchestrating:
large event streams are partitioned into shards, each shard is analyzed
locally, then the global reducer fuses evidence into incident hypotheses.
The default implementation is deterministic so it can run in CI without a
live LLM. A real LLM can later replace the reducer's explanation function.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class AnalysisEvent:
    event_id: int
    minute: int
    service: str
    tenant: str
    region: str
    latency_ms: float
    error: bool
    npu_util: float
    queue_depth: float


@dataclass(frozen=True)
class InjectedIncident:
    incident_id: str
    service: str
    region: str
    start_minute: int
    end_minute: int
    kind: str


@dataclass
class WorkloadDataset:
    events: list[AnalysisEvent]
    incidents: list[InjectedIncident]


@dataclass
class ShardSummary:
    shard_id: int
    event_count: int
    candidate_count: int
    candidates: list[dict[str, Any]] = field(default_factory=list)
    top_services: list[tuple[str, int]] = field(default_factory=list)
    duration_ms: float = 0.0


@dataclass
class WorkloadReport:
    event_count: int
    shard_count: int
    injected_incident_count: int
    detected_incident_count: int
    matched_incident_count: int
    precision: float
    recall: float
    f1: float
    evidence_coverage: float
    map_duration_ms: float
    reduce_duration_ms: float
    total_duration_ms: float
    throughput_events_per_s: float
    detected_incidents: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_count": self.event_count,
            "shard_count": self.shard_count,
            "injected_incident_count": self.injected_incident_count,
            "detected_incident_count": self.detected_incident_count,
            "matched_incident_count": self.matched_incident_count,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "evidence_coverage": round(self.evidence_coverage, 4),
            "map_duration_ms": round(self.map_duration_ms, 2),
            "reduce_duration_ms": round(self.reduce_duration_ms, 2),
            "total_duration_ms": round(self.total_duration_ms, 2),
            "throughput_events_per_s": round(self.throughput_events_per_s, 2),
            "detected_incidents": self.detected_incidents,
        }


SERVICES = ("prefill", "decode", "kv-cache", "scheduler", "router", "embedding")
TENANTS = tuple(f"tenant-{idx:03d}" for idx in range(64))
REGIONS = ("npu-a", "npu-b", "npu-c")


def generate_synthetic_events(
    *,
    event_count: int = 50_000,
    seed: int = 7,
    incident_count: int = 4,
) -> WorkloadDataset:
    rng = random.Random(seed)
    max_minute = max(240, event_count // 120)
    incidents: list[InjectedIncident] = []
    incident_services = rng.sample(list(SERVICES), k=min(incident_count, len(SERVICES)))
    for idx, service in enumerate(incident_services):
        start = rng.randint(30, max_minute - 45)
        duration = rng.randint(16, 38)
        incidents.append(
            InjectedIncident(
                incident_id=f"incident-{idx + 1}",
                service=service,
                region=rng.choice(REGIONS),
                start_minute=start,
                end_minute=start + duration,
                kind=rng.choice(("latency_spike", "npu_saturation", "queue_backlog")),
            )
        )

    events: list[AnalysisEvent] = []
    for event_id in range(event_count):
        service = rng.choice(SERVICES)
        region = rng.choice(REGIONS)
        tenant = rng.choice(TENANTS)
        minute = rng.randrange(max_minute)
        base_latency = {
            "prefill": 42,
            "decode": 65,
            "kv-cache": 18,
            "scheduler": 12,
            "router": 8,
            "embedding": 28,
        }[service]
        latency = max(1.0, rng.gauss(base_latency, base_latency * 0.18))
        queue_depth = max(0.0, rng.gauss(4.0, 1.6))
        npu_util = min(0.98, max(0.18, rng.gauss(0.58, 0.12)))
        error_rate = 0.006

        for incident in incidents:
            if (
                incident.service == service
                and incident.region == region
                and incident.start_minute <= minute <= incident.end_minute
            ):
                if incident.kind == "latency_spike":
                    latency *= rng.uniform(2.2, 3.5)
                    error_rate = 0.035
                elif incident.kind == "npu_saturation":
                    npu_util = min(0.995, rng.gauss(0.94, 0.035))
                    latency *= rng.uniform(1.5, 2.2)
                    error_rate = 0.02
                else:
                    queue_depth += rng.uniform(12, 25)
                    latency *= rng.uniform(1.7, 2.6)
                    error_rate = 0.028

        events.append(
            AnalysisEvent(
                event_id=event_id,
                minute=minute,
                service=service,
                tenant=tenant,
                region=region,
                latency_ms=latency,
                error=rng.random() < error_rate,
                npu_util=npu_util,
                queue_depth=queue_depth,
            )
        )

    return WorkloadDataset(events=events, incidents=incidents)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    pos = (len(ordered) - 1) * percentile
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return ordered[int(pos)]
    return ordered[low] * (high - pos) + ordered[high] * (pos - low)


def partition_events(events: list[AnalysisEvent], shard_count: int) -> list[list[AnalysisEvent]]:
    shards: list[list[AnalysisEvent]] = [[] for _ in range(shard_count)]
    for event in events:
        shards[event.event_id % shard_count].append(event)
    return shards


def map_shard(shard_id: int, events: list[AnalysisEvent]) -> ShardSummary:
    started = time.perf_counter()
    grouped: dict[tuple[str, str, int], list[AnalysisEvent]] = defaultdict(list)
    for event in events:
        window = event.minute // 20
        grouped[(event.service, event.region, window)].append(event)

    candidates: list[dict[str, Any]] = []
    for (service, region, window), bucket in grouped.items():
        if len(bucket) < 4:
            continue
        latencies = [item.latency_ms for item in bucket]
        queue_depths = [item.queue_depth for item in bucket]
        npu_utils = [item.npu_util for item in bucket]
        error_rate = sum(1 for item in bucket if item.error) / len(bucket)
        p95_latency = _percentile(latencies, 0.95)
        mean_latency = statistics.fmean(latencies)
        mean_queue = statistics.fmean(queue_depths)
        mean_npu = statistics.fmean(npu_utils)

        latency_anomaly = p95_latency > 135 or p95_latency > mean_latency * 1.9
        queue_anomaly = mean_queue > 10
        npu_anomaly = mean_npu > 0.84
        error_anomaly = error_rate > 0.018
        score = (
            int(latency_anomaly) * 0.34
            + int(queue_anomaly) * 0.22
            + int(npu_anomaly) * 0.22
            + int(error_anomaly) * 0.22
        )
        if score < 0.34:
            continue
        candidates.append(
            {
                "service": service,
                "region": region,
                "window": window,
                "start_minute": window * 20,
                "end_minute": window * 20 + 19,
                "event_count": len(bucket),
                "p95_latency_ms": round(p95_latency, 2),
                "mean_latency_ms": round(mean_latency, 2),
                "error_rate": round(error_rate, 4),
                "mean_npu_util": round(mean_npu, 4),
                "mean_queue_depth": round(mean_queue, 2),
                "score": round(score, 4),
                "signals": [
                    name
                    for name, active in (
                        ("latency", latency_anomaly),
                        ("queue", queue_anomaly),
                        ("npu", npu_anomaly),
                        ("error", error_anomaly),
                    )
                    if active
                ],
            }
        )

    top_services = Counter(event.service for event in events).most_common(3)
    return ShardSummary(
        shard_id=shard_id,
        event_count=len(events),
        candidate_count=len(candidates),
        candidates=candidates,
        top_services=top_services,
        duration_ms=(time.perf_counter() - started) * 1000,
    )


def _explain_candidate(candidate: dict[str, Any]) -> str:
    signals = ", ".join(candidate["signals"])
    return (
        f"{candidate['service']} in {candidate['region']} shows {signals}; "
        f"p95={candidate['p95_latency_ms']}ms, errors={candidate['error_rate']:.2%}, "
        f"npu={candidate['mean_npu_util']:.2f}, queue={candidate['mean_queue_depth']}."
    )


def reduce_summaries(summaries: list[ShardSummary]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for summary in summaries:
        for candidate in summary.candidates:
            key = (candidate["service"], candidate["region"], candidate["window"])
            merged[key].append(candidate)

    window_detections: list[dict[str, Any]] = []
    for (service, region, window), candidates in merged.items():
        evidence_count = sum(item["event_count"] for item in candidates)
        score = statistics.fmean(item["score"] for item in candidates)
        signals = sorted({signal for item in candidates for signal in item["signals"]})
        p95 = max(item["p95_latency_ms"] for item in candidates)
        error_rate = max(item["error_rate"] for item in candidates)
        mean_npu_util = max(item["mean_npu_util"] for item in candidates)
        mean_queue_depth = max(item["mean_queue_depth"] for item in candidates)
        window_detections.append(
            {
                "service": service,
                "region": region,
                "window": window,
                "start_minute": window * 20,
                "end_minute": window * 20 + 19,
                "score": round(score, 4),
                "evidence_count": evidence_count,
                "signals": signals,
                "p95_latency_ms": p95,
                "error_rate": error_rate,
                "mean_npu_util": mean_npu_util,
                "mean_queue_depth": mean_queue_depth,
                "summary": _explain_candidate(
                    {
                        **candidates[0],
                        "signals": signals,
                        "p95_latency_ms": p95,
                        "error_rate": error_rate,
                    }
                ),
            }
        )

    by_target: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for detection in window_detections:
        by_target[(detection["service"], detection["region"])].append(detection)

    incidents: list[dict[str, Any]] = []
    for (service, region), detections in by_target.items():
        detections.sort(key=lambda item: item["window"])
        cluster: list[dict[str, Any]] = []
        for detection in detections:
            if not cluster or detection["window"] <= cluster[-1]["window"] + 1:
                cluster.append(detection)
                continue
            incidents.append(_cluster_window_detections(service, region, cluster))
            cluster = [detection]
        if cluster:
            incidents.append(_cluster_window_detections(service, region, cluster))

    incidents.sort(key=lambda item: (item["score"], item["evidence_count"]), reverse=True)
    return incidents


def _cluster_window_detections(
    service: str, region: str, detections: list[dict[str, Any]]
) -> dict[str, Any]:
    signals = sorted({signal for item in detections for signal in item["signals"]})
    score = max(item["score"] for item in detections)
    evidence_count = sum(item["evidence_count"] for item in detections)
    p95 = max(item["p95_latency_ms"] for item in detections)
    error_rate = max(item["error_rate"] for item in detections)
    mean_npu_util = max(item["mean_npu_util"] for item in detections)
    mean_queue_depth = max(item["mean_queue_depth"] for item in detections)
    start_minute = min(item["start_minute"] for item in detections)
    end_minute = max(item["end_minute"] for item in detections)
    representative = max(detections, key=lambda item: (item["score"], item["evidence_count"]))
    return {
        "service": service,
        "region": region,
        "window": representative["window"],
        "start_minute": start_minute,
        "end_minute": end_minute,
        "score": round(score, 4),
        "evidence_count": evidence_count,
        "signals": signals,
        "p95_latency_ms": p95,
        "error_rate": error_rate,
        "mean_npu_util": mean_npu_util,
        "mean_queue_depth": mean_queue_depth,
        "summary": _explain_candidate(
            {
                **representative,
                "signals": signals,
                "p95_latency_ms": p95,
                "error_rate": error_rate,
                "mean_npu_util": mean_npu_util,
                "mean_queue_depth": mean_queue_depth,
            }
        ),
    }


def _matches_incident(detection: dict[str, Any], incident: InjectedIncident) -> bool:
    same_target = (
        detection["service"] == incident.service and detection["region"] == incident.region
    )
    overlaps_time = (
        detection["start_minute"] <= incident.end_minute
        and detection["end_minute"] >= incident.start_minute
    )
    return same_target and overlaps_time


def score_detections(
    detections: list[dict[str, Any]], incidents: list[InjectedIncident]
) -> tuple[int, float, float, float, float]:
    matched_incidents: set[str] = set()
    matched_detections = 0
    for detection in detections:
        for incident in incidents:
            if incident.incident_id in matched_incidents:
                continue
            if _matches_incident(detection, incident):
                matched_incidents.add(incident.incident_id)
                matched_detections += 1
                break
    precision = matched_detections / len(detections) if detections else 0.0
    recall = len(matched_incidents) / len(incidents) if incidents else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    evidence_coverage = (
        sum(detection["evidence_count"] for detection in detections) / max(1, len(detections))
    )
    return len(matched_incidents), precision, recall, f1, evidence_coverage


def run_large_scale_analysis_workload(
    *,
    event_count: int = 50_000,
    shard_count: int = 16,
    seed: int = 7,
    top_k: int = 12,
) -> WorkloadReport:
    started = time.perf_counter()
    dataset = generate_synthetic_events(event_count=event_count, seed=seed)
    shards = partition_events(dataset.events, shard_count)

    map_started = time.perf_counter()
    summaries = [map_shard(shard_id, shard) for shard_id, shard in enumerate(shards)]
    map_duration_ms = (time.perf_counter() - map_started) * 1000

    reduce_started = time.perf_counter()
    detections = reduce_summaries(summaries)[:top_k]
    reduce_duration_ms = (time.perf_counter() - reduce_started) * 1000

    matched, precision, recall, f1, coverage = score_detections(
        detections, dataset.incidents
    )
    total_duration_ms = (time.perf_counter() - started) * 1000
    return WorkloadReport(
        event_count=event_count,
        shard_count=shard_count,
        injected_incident_count=len(dataset.incidents),
        detected_incident_count=len(detections),
        matched_incident_count=matched,
        precision=precision,
        recall=recall,
        f1=f1,
        evidence_coverage=coverage,
        map_duration_ms=map_duration_ms,
        reduce_duration_ms=reduce_duration_ms,
        total_duration_ms=total_duration_ms,
        throughput_events_per_s=event_count / max(total_duration_ms / 1000, 0.001),
        detected_incidents=detections,
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the synthetic SAGE large-scale analysis workload."
    )
    parser.add_argument("--events", type=int, default=50_000)
    parser.add_argument("--shards", type=int, default=16)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--top-k", type=int, default=12)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = run_large_scale_analysis_workload(
        event_count=args.events,
        shard_count=args.shards,
        seed=args.seed,
        top_k=args.top_k,
    )
    payload = report.to_dict()
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
