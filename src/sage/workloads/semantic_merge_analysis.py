"""Hard semantic-merge workload for Semantic MapReduce experiments.

This workload complements ``large_scale_analysis``.  The earlier workload asks
whether a reducer can recover single-service incidents from shard evidence.  In
contrast, this workload makes the ground truth an incident *group*: one root
cause produces symptoms in multiple dependent services.  Alert-style reducers
therefore tend to emit fragments, while a semantic reducer must merge evidence
objects into a single hypothesis with provenance.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import time
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Protocol

from sage.workloads.large_scale_analysis import (
    _api_key_from_env_or_file,
    _extract_json_payload,
)


SERVICES = ("router", "scheduler", "prefill", "decode", "kv-cache", "embedding")
REGIONS = ("npu-a", "npu-b", "npu-c")
DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "router": ("scheduler", "prefill", "decode"),
    "scheduler": ("prefill", "decode"),
    "kv-cache": ("decode",),
    "embedding": ("router",),
}
SCENARIOS = (
    "single-service",
    "cascade",
    "shared-bottleneck",
    "concurrent",
    "false-correlation",
    "partial-evidence",
    "ambiguous-overmerge",
    "ambiguous-disconnected-merge",
    "ambiguous-temporal-split",
)


@dataclass(frozen=True)
class MergeIncident:
    incident_id: str
    root_service: str
    region: str
    start_minute: int
    end_minute: int
    kind: str
    affected_services: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceObject:
    evidence_id: str
    shard_id: int
    service: str
    region: str
    start_minute: int
    end_minute: int
    signals: tuple[str, ...]
    score: float
    p95_latency_ms: float
    error_rate: float
    queue_depth: float
    npu_util: float
    upstream_hint: str | None = None
    source_incident_id: str | None = None


@dataclass
class MergeDataset:
    evidence: list[EvidenceObject]
    incidents: list[MergeIncident]
    scenario: str = "cascade"


@dataclass
class MergeReport:
    reducer_name: str
    scenario: str
    seed: int
    shard_count: int
    evidence_count: int
    injected_incident_count: int
    detected_incident_count: int
    matched_incident_count: int
    precision: float
    recall: float
    f1: float
    evidence_coverage: float
    root_evidence_coverage: float
    support_evidence_recall: float
    reduce_duration_ms: float
    injected_incidents: list[dict[str, Any]]
    detected_incidents: list[dict[str, Any]]
    missed_incidents: list[dict[str, Any]]
    false_positive_incidents: list[dict[str, Any]]
    reducer_trace: dict[str, Any] = field(default_factory=dict)
    cost_accounting: dict[str, Any] = field(default_factory=dict)
    workflow_trace: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reducer_name": self.reducer_name,
            "scenario": self.scenario,
            "seed": self.seed,
            "shard_count": self.shard_count,
            "evidence_count": self.evidence_count,
            "injected_incident_count": self.injected_incident_count,
            "detected_incident_count": self.detected_incident_count,
            "matched_incident_count": self.matched_incident_count,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "evidence_coverage": round(self.evidence_coverage, 4),
            "root_evidence_coverage": round(self.root_evidence_coverage, 4),
            "support_evidence_recall": round(self.support_evidence_recall, 4),
            "reduce_duration_ms": round(self.reduce_duration_ms, 2),
            "injected_incidents": self.injected_incidents,
            "detected_incidents": self.detected_incidents,
            "missed_incidents": self.missed_incidents,
            "false_positive_incidents": self.false_positive_incidents,
            "reducer_trace": self.reducer_trace,
            "cost_accounting": self.cost_accounting,
            "workflow_trace": self.workflow_trace,
        }


class MergeReducer(Protocol):
    name: str

    def reduce(self, evidence: list[EvidenceObject]) -> list[dict[str, Any]]:
        """Merge evidence objects into incident-group hypotheses."""


def incident_to_dict(incident: MergeIncident) -> dict[str, Any]:
    return {
        "incident_id": incident.incident_id,
        "root_service": incident.root_service,
        "region": incident.region,
        "start_minute": incident.start_minute,
        "end_minute": incident.end_minute,
        "kind": incident.kind,
        "affected_services": list(incident.affected_services),
    }


def evidence_to_dict(evidence: EvidenceObject) -> dict[str, Any]:
    return {
        "evidence_id": evidence.evidence_id,
        "shard_id": evidence.shard_id,
        "service": evidence.service,
        "region": evidence.region,
        "start_minute": evidence.start_minute,
        "end_minute": evidence.end_minute,
        "signals": list(evidence.signals),
        "score": evidence.score,
        "p95_latency_ms": evidence.p95_latency_ms,
        "error_rate": evidence.error_rate,
        "queue_depth": evidence.queue_depth,
        "npu_util": evidence.npu_util,
        "upstream_hint": evidence.upstream_hint,
        "source_incident_id": evidence.source_incident_id,
    }


def generate_semantic_merge_dataset(
    *,
    seed: int = 7,
    shard_count: int = 8,
    incident_count: int = 4,
    scenario: str = "cascade",
) -> MergeDataset:
    if scenario not in SCENARIOS:
        raise ValueError(
            f"Unknown semantic merge scenario {scenario!r}. "
            f"Expected one of {', '.join(SCENARIOS)}."
        )
    rng = random.Random(seed)
    if scenario == "ambiguous-overmerge":
        return _generate_ambiguous_overmerge_dataset(
            seed=seed,
            shard_count=shard_count,
            incident_count=incident_count,
        )
    if scenario == "ambiguous-disconnected-merge":
        return _generate_disconnected_merge_dataset(
            seed=seed,
            shard_count=shard_count,
            incident_count=incident_count,
        )
    if scenario == "ambiguous-temporal-split":
        return _generate_temporal_split_dataset(
            seed=seed,
            shard_count=shard_count,
            incident_count=incident_count,
        )
    templates = _scenario_templates(scenario)
    rng.shuffle(templates)

    incidents: list[MergeIncident] = []
    evidence: list[EvidenceObject] = []
    evidence_index = 0
    for idx, template in enumerate(templates[:incident_count], start=1):
        root, affected, kind = template
        if scenario == "concurrent":
            region = REGIONS[(idx + seed) % len(REGIONS)]
            start = 120 + (idx % 2) * 5 + (seed % 4)
            duration = rng.randint(34, 54)
        elif scenario == "shared-bottleneck":
            region = REGIONS[(seed + idx) % len(REGIONS)]
            start = 70 + idx * 70 + rng.randint(0, 14)
            duration = rng.randint(40, 62)
        elif scenario == "false-correlation":
            region = REGIONS[idx % len(REGIONS)]
            start = 90 + idx * 62 + rng.randint(0, 10)
            duration = rng.randint(22, 38)
        else:
            region = rng.choice(REGIONS)
            start = rng.randint(40, 420)
            duration = rng.randint(24, 48)
        omit_root = scenario == "partial-evidence" and idx % 2 == 0
        evidence_index = _append_incident(
            incidents=incidents,
            evidence=evidence,
            evidence_index=evidence_index,
            shard_count=shard_count,
            rng=rng,
            incident_id=f"{scenario}-incident-{idx}",
            root=root,
            affected=affected,
            kind=kind,
            region=region,
            start=start,
            duration=duration,
            omit_root=omit_root,
        )

    if scenario == "false-correlation":
        evidence_index = _append_false_correlation_distractors(
            evidence=evidence,
            evidence_index=evidence_index,
            shard_count=shard_count,
            rng=rng,
            groups=max(incident_count, 3),
        )
    else:
        evidence_index = _append_local_distractors(
            evidence=evidence,
            evidence_index=evidence_index,
            shard_count=shard_count,
            rng=rng,
            count=max(incident_count * 2, 6),
        )

    rng.shuffle(evidence)
    return MergeDataset(evidence=evidence, incidents=incidents, scenario=scenario)


def _scenario_templates(scenario: str) -> list[tuple[str, tuple[str, ...], str]]:
    if scenario == "single-service":
        return [
            ("router", ("router",), "local_router_latency"),
            ("decode", ("decode",), "local_decode_error"),
            ("kv-cache", ("kv-cache",), "local_cache_utilization"),
            ("embedding", ("embedding",), "local_embedding_ingest"),
        ]
    if scenario == "shared-bottleneck":
        return [
            ("kv-cache", ("kv-cache", "decode", "prefill"), "shared_cache_pressure"),
            ("scheduler", ("scheduler", "prefill", "decode", "router"), "shared_queue_backlog"),
            ("router", ("router", "scheduler", "decode"), "shared_routing_backpressure"),
            ("embedding", ("embedding", "router", "scheduler"), "shared_ingest_pressure"),
        ]
    if scenario == "concurrent":
        return [
            ("router", ("router", "scheduler", "decode"), "concurrent_routing_backpressure"),
            ("kv-cache", ("kv-cache", "decode"), "concurrent_cache_pressure"),
            ("embedding", ("embedding", "router"), "concurrent_embedding_ingest"),
            ("scheduler", ("scheduler", "prefill", "decode"), "concurrent_scheduler_backlog"),
        ]
    if scenario == "false-correlation":
        return [
            ("router", ("router", "scheduler"), "true_routing_backpressure"),
            ("kv-cache", ("kv-cache", "decode"), "true_cache_pressure"),
            ("embedding", ("embedding", "router"), "true_embedding_ingest"),
            ("scheduler", ("scheduler", "prefill"), "true_scheduler_backlog"),
        ]
    if scenario == "ambiguous-overmerge":
        return [
            ("scheduler", ("scheduler", "prefill"), "ambiguous_scheduler_queue"),
            ("kv-cache", ("kv-cache", "decode"), "ambiguous_cache_pressure"),
            ("router", ("router", "scheduler"), "ambiguous_router_backpressure"),
            ("embedding", ("embedding", "router"), "ambiguous_embedding_ingest"),
        ]
    if scenario == "ambiguous-disconnected-merge":
        return [
            ("scheduler", ("scheduler", "kv-cache", "embedding"), "disconnected_scheduler_pressure"),
            ("router", ("router", "kv-cache", "embedding"), "disconnected_router_pressure"),
        ]
    if scenario == "ambiguous-temporal-split":
        return [
            ("scheduler", ("scheduler", "prefill", "decode"), "temporal_scheduler_backlog"),
            ("kv-cache", ("kv-cache", "decode", "prefill"), "temporal_cache_pressure"),
        ]
    return [
        ("router", ("router", "scheduler", "decode"), "routing_backpressure"),
        ("kv-cache", ("kv-cache", "decode"), "cache_pressure"),
        ("embedding", ("embedding", "router"), "embedding_ingest"),
        ("scheduler", ("scheduler", "prefill", "decode"), "scheduler_backlog"),
    ]


def _generate_ambiguous_overmerge_dataset(
    *,
    seed: int,
    shard_count: int,
    incident_count: int,
) -> MergeDataset:
    rng = random.Random(seed)
    region = REGIONS[seed % len(REGIONS)]
    incidents: list[MergeIncident] = []
    evidence: list[EvidenceObject] = []
    evidence_index = 0
    pairs = [
        (
            ("scheduler", ("scheduler", "prefill"), "ambiguous_scheduler_queue"),
            ("kv-cache", ("kv-cache", "decode"), "ambiguous_cache_pressure"),
        ),
        (
            ("router", ("router", "scheduler"), "ambiguous_router_backpressure"),
            ("embedding", ("embedding", "router"), "ambiguous_embedding_ingest"),
        ),
    ]
    target_incidents = max(2, min(incident_count, 4))
    for pair_index, pair in enumerate(pairs):
        if len(incidents) >= target_incidents:
            break
        base_start = 100 + pair_index * 120 + rng.randint(0, 4)
        for root, affected, kind in pair:
            if len(incidents) >= target_incidents:
                break
            incident_id = f"ambiguous-overmerge-incident-{len(incidents) + 1}"
            incident = MergeIncident(
                incident_id=incident_id,
                root_service=root,
                region=region,
                start_minute=base_start + rng.randint(0, 3),
                end_minute=base_start + 42 + rng.randint(0, 4),
                kind=kind,
                affected_services=affected,
            )
            incidents.append(incident)
            for service_index, service in enumerate(affected):
                ev_start = incident.start_minute + service_index * rng.randint(2, 5)
                signals = ["latency"]
                if root == "scheduler":
                    signals.append("queue")
                if root == "kv-cache":
                    signals.append("npu")
                if root == "router":
                    signals.append("error")
                if root == "embedding":
                    signals.append("ingest")
                evidence.append(
                    EvidenceObject(
                        evidence_id=f"e{evidence_index}",
                        shard_id=evidence_index % shard_count,
                        service=service,
                        region=region,
                        start_minute=ev_start,
                        end_minute=ev_start + rng.randint(22, 30),
                        signals=tuple(sorted(set(signals))),
                        score=round(0.82 - service_index * 0.08 + rng.random() * 0.03, 4),
                        p95_latency_ms=round(rng.uniform(110, 260), 2),
                        error_rate=round(rng.uniform(0.02, 0.10), 4),
                        queue_depth=round(rng.uniform(10, 34), 2),
                        npu_util=round(rng.uniform(0.62, 0.98), 4),
                        upstream_hint=root,
                        source_incident_id=incident_id,
                    )
                )
                evidence_index += 1

    evidence_index = _append_local_distractors(
        evidence=evidence,
        evidence_index=evidence_index,
        shard_count=shard_count,
        rng=rng,
        count=max(4, target_incidents),
    )
    rng.shuffle(evidence)
    return MergeDataset(
        evidence=evidence,
        incidents=incidents,
        scenario="ambiguous-overmerge",
    )


def _generate_disconnected_merge_dataset(
    *,
    seed: int,
    shard_count: int,
    incident_count: int,
) -> MergeDataset:
    """Generate incidents whose evidence is semantically connected by hints.

    The evidence services are intentionally weakly connected in the static
    dependency graph, so graph/hybrid reducers emit fragments.  The source
    evidence is still sufficient: every fragment carries the same upstream
    root hint and source incident id.
    """

    rng = random.Random(seed)
    incidents: list[MergeIncident] = []
    evidence: list[EvidenceObject] = []
    evidence_index = 0
    templates = [
        (
            "scheduler",
            ("scheduler", "kv-cache", "embedding"),
            ("kv-cache", "embedding"),
            "disconnected_scheduler_pressure",
        ),
        (
            "router",
            ("router", "kv-cache", "embedding"),
            ("kv-cache", "embedding"),
            "disconnected_router_pressure",
        ),
        (
            "kv-cache",
            ("kv-cache", "router", "embedding"),
            ("router", "embedding"),
            "disconnected_cache_pressure",
        ),
        (
            "embedding",
            ("embedding", "scheduler", "kv-cache"),
            ("scheduler", "kv-cache"),
            "disconnected_ingest_pressure",
        ),
    ]
    rng.shuffle(templates)
    for idx, (root, affected, observed, kind) in enumerate(
        templates[:incident_count], start=1
    ):
        region = REGIONS[(seed + idx) % len(REGIONS)]
        start = 80 + idx * 82 + rng.randint(0, 8)
        duration = rng.randint(38, 52)
        incident_id = f"ambiguous-disconnected-merge-incident-{idx}"
        incident = MergeIncident(
            incident_id=incident_id,
            root_service=root,
            region=region,
            start_minute=start,
            end_minute=start + duration,
            kind=kind,
            affected_services=affected,
        )
        incidents.append(incident)
        for service_index, service in enumerate(observed):
            ev_start = start + service_index * rng.randint(3, 7)
            signals = ["latency"]
            if service == "kv-cache":
                signals.append("npu")
            if service == "embedding":
                signals.append("ingest")
            if service in {"router", "scheduler"}:
                signals.append("queue")
            evidence.append(
                EvidenceObject(
                    evidence_id=f"e{evidence_index}",
                    shard_id=evidence_index % shard_count,
                    service=service,
                    region=region,
                    start_minute=ev_start,
                    end_minute=ev_start + rng.randint(18, 26),
                    signals=tuple(sorted(set(signals))),
                    score=round(0.78 - service_index * 0.05 + rng.random() * 0.04, 4),
                    p95_latency_ms=round(rng.uniform(120, 280), 2),
                    error_rate=round(rng.uniform(0.02, 0.09), 4),
                    queue_depth=round(rng.uniform(12, 36), 2),
                    npu_util=round(rng.uniform(0.62, 0.98), 4),
                    upstream_hint=root,
                    source_incident_id=incident_id,
                )
            )
            evidence_index += 1

    evidence_index = _append_local_distractors(
        evidence=evidence,
        evidence_index=evidence_index,
        shard_count=shard_count,
        rng=rng,
        count=max(4, incident_count),
    )
    rng.shuffle(evidence)
    return MergeDataset(
        evidence=evidence,
        incidents=incidents,
        scenario="ambiguous-disconnected-merge",
    )


def _generate_temporal_split_dataset(
    *,
    seed: int,
    shard_count: int,
    incident_count: int,
) -> MergeDataset:
    """Generate one incident whose evidence appears as separated bursts."""

    rng = random.Random(seed)
    incidents: list[MergeIncident] = []
    evidence: list[EvidenceObject] = []
    evidence_index = 0
    templates = [
        ("scheduler", ("scheduler", "prefill", "decode"), "temporal_scheduler_backlog"),
        ("kv-cache", ("kv-cache", "decode", "prefill"), "temporal_cache_pressure"),
        ("router", ("router", "scheduler", "decode"), "temporal_router_backpressure"),
        ("embedding", ("embedding", "router", "scheduler"), "temporal_ingest_pressure"),
    ]
    rng.shuffle(templates)
    for idx, (root, affected, kind) in enumerate(templates[:incident_count], start=1):
        region = REGIONS[(seed + idx * 2) % len(REGIONS)]
        start = 70 + idx * 86 + rng.randint(0, 6)
        duration = rng.randint(52, 70)
        incident_id = f"ambiguous-temporal-split-incident-{idx}"
        incident = MergeIncident(
            incident_id=incident_id,
            root_service=root,
            region=region,
            start_minute=start,
            end_minute=start + duration,
            kind=kind,
            affected_services=affected,
        )
        incidents.append(incident)
        bursts = (
            (affected[0], start),
            (affected[1], start + 24 + rng.randint(0, 5)),
            (affected[-1], start + 47 + rng.randint(0, 5)),
        )
        for service_index, (service, ev_start) in enumerate(bursts):
            signals = ["latency"]
            if service in {"scheduler", "router"}:
                signals.append("queue")
            if service == "kv-cache":
                signals.append("npu")
            if service == "embedding":
                signals.append("ingest")
            evidence.append(
                EvidenceObject(
                    evidence_id=f"e{evidence_index}",
                    shard_id=evidence_index % shard_count,
                    service=service,
                    region=region,
                    start_minute=ev_start,
                    end_minute=ev_start + rng.randint(10, 14),
                    signals=tuple(sorted(set(signals))),
                    score=round(0.84 - service_index * 0.06 + rng.random() * 0.03, 4),
                    p95_latency_ms=round(rng.uniform(120, 290), 2),
                    error_rate=round(rng.uniform(0.02, 0.10), 4),
                    queue_depth=round(rng.uniform(12, 38), 2),
                    npu_util=round(rng.uniform(0.62, 0.98), 4),
                    upstream_hint=root,
                    source_incident_id=incident_id,
                )
            )
            evidence_index += 1

    evidence_index = _append_local_distractors(
        evidence=evidence,
        evidence_index=evidence_index,
        shard_count=shard_count,
        rng=rng,
        count=max(4, incident_count),
    )
    rng.shuffle(evidence)
    return MergeDataset(
        evidence=evidence,
        incidents=incidents,
        scenario="ambiguous-temporal-split",
    )


def _append_incident(
    *,
    incidents: list[MergeIncident],
    evidence: list[EvidenceObject],
    evidence_index: int,
    shard_count: int,
    rng: random.Random,
    incident_id: str,
    root: str,
    affected: tuple[str, ...],
    kind: str,
    region: str,
    start: int,
    duration: int,
    omit_root: bool = False,
) -> int:
    incident = MergeIncident(
        incident_id=incident_id,
        root_service=root,
        region=region,
        start_minute=start,
        end_minute=start + duration,
        kind=kind,
        affected_services=tuple(affected),
    )
    incidents.append(incident)
    for service_index, service in enumerate(affected):
        if omit_root and service == root:
            continue
        lag = service_index * rng.randint(4, 10)
        ev_start = start + lag
        ev_end = min(start + duration + lag, ev_start + rng.randint(18, 30))
        signals = ["latency"]
        if service != root:
            signals.append(rng.choice(("queue", "error")))
        if "cache" in kind and service == "kv-cache":
            signals.append("npu")
        score = round(rng.uniform(0.54, 0.92) - service_index * 0.06, 4)
        evidence.append(
            EvidenceObject(
                evidence_id=f"e{evidence_index}",
                shard_id=evidence_index % shard_count,
                service=service,
                region=region,
                start_minute=ev_start,
                end_minute=ev_end,
                signals=tuple(sorted(set(signals))),
                score=max(0.34, score),
                p95_latency_ms=round(rng.uniform(70, 240), 2),
                error_rate=round(rng.uniform(0.015, 0.12), 4),
                queue_depth=round(rng.uniform(6, 28), 2),
                npu_util=round(rng.uniform(0.55, 0.96), 4),
                upstream_hint=root if service != root and rng.random() < 0.8 else None,
                source_incident_id=incident.incident_id,
            )
        )
        evidence_index += 1
    return evidence_index


def _append_local_distractors(
    *,
    evidence: list[EvidenceObject],
    evidence_index: int,
    shard_count: int,
    rng: random.Random,
    count: int,
) -> int:
    for _ in range(count):
        service = rng.choice(SERVICES)
        region = rng.choice(REGIONS)
        start = rng.randint(20, 500)
        evidence.append(
            EvidenceObject(
                evidence_id=f"e{evidence_index}",
                shard_id=evidence_index % shard_count,
                service=service,
                region=region,
                start_minute=start,
                end_minute=start + rng.randint(8, 18),
                signals=(rng.choice(("latency", "queue", "error")),),
                score=round(rng.uniform(0.26, 0.48), 4),
                p95_latency_ms=round(rng.uniform(35, 120), 2),
                error_rate=round(rng.uniform(0.0, 0.04), 4),
                queue_depth=round(rng.uniform(2, 12), 2),
                npu_util=round(rng.uniform(0.35, 0.85), 4),
            )
        )
        evidence_index += 1
    return evidence_index


def _append_false_correlation_distractors(
    *,
    evidence: list[EvidenceObject],
    evidence_index: int,
    shard_count: int,
    rng: random.Random,
    groups: int,
) -> int:
    unrelated_pairs = (("router", "kv-cache"), ("embedding", "decode"), ("scheduler", "kv-cache"))
    for group_index in range(groups):
        region = REGIONS[group_index % len(REGIONS)]
        start = 110 + group_index * 58 + rng.randint(0, 8)
        for service in unrelated_pairs[group_index % len(unrelated_pairs)]:
            evidence.append(
                EvidenceObject(
                    evidence_id=f"e{evidence_index}",
                    shard_id=evidence_index % shard_count,
                    service=service,
                    region=region,
                    start_minute=start + rng.randint(0, 5),
                    end_minute=start + rng.randint(18, 30),
                    signals=(rng.choice(("latency", "queue", "error")),),
                    score=round(rng.uniform(0.36, 0.52), 4),
                    p95_latency_ms=round(rng.uniform(50, 150), 2),
                    error_rate=round(rng.uniform(0.005, 0.055), 4),
                    queue_depth=round(rng.uniform(3, 18), 2),
                    npu_util=round(rng.uniform(0.4, 0.88), 4),
                )
            )
            evidence_index += 1
    return _append_local_distractors(
        evidence=evidence,
        evidence_index=evidence_index,
        shard_count=shard_count,
        rng=rng,
        count=max(groups, 4),
    )


class MapOnlyMergeReducer:
    name = "map-only"

    def reduce(self, evidence: list[EvidenceObject]) -> list[dict[str, Any]]:
        return [
            _hypothesis_from_evidence_group([item], reducer=self.name)
            for item in sorted(evidence, key=lambda item: item.score, reverse=True)
            if item.score >= 0.34
        ]


class ServiceLocalMergeReducer:
    name = "service-local"

    def reduce(self, evidence: list[EvidenceObject]) -> list[dict[str, Any]]:
        groups: dict[tuple[str, str], list[EvidenceObject]] = defaultdict(list)
        for item in evidence:
            if item.score >= 0.34:
                groups[(item.service, item.region)].append(item)
        return _clusters_from_groups(groups, reducer=self.name)


class WindowAggregateMergeReducer:
    name = "window-aggregate"

    def reduce(self, evidence: list[EvidenceObject]) -> list[dict[str, Any]]:
        groups: dict[tuple[str, int], list[EvidenceObject]] = defaultdict(list)
        for item in evidence:
            if item.score >= 0.34:
                groups[(item.region, item.start_minute // 40)].append(item)
        hypotheses = [
            _hypothesis_from_evidence_group(items, reducer=self.name)
            for items in groups.values()
        ]
        return sorted(hypotheses, key=lambda item: item["score"], reverse=True)


class SemanticGraphMergeReducer:
    name = "semantic-graph"
    include_root_hint_in_affected = False

    def reduce(self, evidence: list[EvidenceObject]) -> list[dict[str, Any]]:
        groups = _semantic_graph_groups(evidence)
        hypotheses = [
            _hypothesis_from_evidence_group(
                group,
                reducer=self.name,
                include_root_hint_in_affected=self.include_root_hint_in_affected,
            )
            for group in groups
            if max(item.score for item in group) >= 0.5
        ]
        return sorted(hypotheses, key=lambda item: item["score"], reverse=True)


class HybridHintMergeReducer(SemanticGraphMergeReducer):
    name = "hybrid-hint"
    include_root_hint_in_affected = True

    def reduce(self, evidence: list[EvidenceObject]) -> list[dict[str, Any]]:
        return [
            {**item, "hybrid_rule": "include-upstream-root-hint"}
            for item in super().reduce(evidence)
        ]


class LLMStubMergeReducer(SemanticGraphMergeReducer):
    name = "llm-stub"

    def reduce(self, evidence: list[EvidenceObject]) -> list[dict[str, Any]]:
        return [
            {**item, "reducer": self.name, "llm_call": "stubbed"}
            for item in super().reduce(evidence)
        ]


class OpenAISemanticMergeReducer:
    name = "llm-openai"

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        max_evidence: int = 24,
        max_tokens: int = 512,
        timeout_sec: int = 180,
        structured_output: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.max_evidence = max_evidence
        self.max_tokens = max_tokens
        self.timeout_sec = timeout_sec
        self.structured_output = structured_output
        self.last_call: dict[str, Any] = {}

    def reduce(self, evidence: list[EvidenceObject]) -> list[dict[str, Any]]:
        selected = sorted(evidence, key=lambda item: item.score, reverse=True)[
            : self.max_evidence
        ]
        prompt = _build_llm_semantic_merge_prompt(selected)
        started = time.perf_counter()
        text = ""
        try:
            text = self._completion(prompt)
            payload = _extract_json_payload(text)
            hypotheses = _normalize_llm_merge_payload(payload, selected)
            json_valid = True
            schema_valid = True
            error_type = None
        except Exception as exc:
            hypotheses = []
            json_valid = False
            schema_valid = False
            error_type = type(exc).__name__
        latency_ms = (time.perf_counter() - started) * 1000
        self.last_call = {
            "model": self.model,
            "base_url": self.base_url,
            "structured_output": self.structured_output,
            "latency_ms": round(latency_ms, 2),
            "json_valid": json_valid,
            "schema_valid": schema_valid,
            "error_type": error_type,
            "prompt_chars": len(prompt),
            "response_chars": len(text),
            "response_preview": text[:500],
            "estimated_prompt_tokens": _estimate_tokens_from_chars(len(prompt)),
            "estimated_response_tokens": _estimate_tokens_from_chars(len(text)),
            "estimated_total_tokens": _estimate_tokens_from_chars(
                len(prompt) + len(text)
            ),
            "input_evidence_count": len(selected),
            "output_incident_count": len(hypotheses),
        }
        for item in hypotheses:
            item["reducer"] = self.name
            item["llm_model"] = self.model
            item["llm_latency_ms"] = round(latency_ms, 2)
        return hypotheses

    def _completion(self, prompt: str) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a strict JSON semantic incident reducer.",
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self.max_tokens,
            "temperature": 0.0,
        }
        if self.structured_output:
            payload["response_format"] = {"type": "json_object"}
        req = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"LLM semantic merge endpoint returned HTTP {exc.code}: {body[:300]}"
            ) from exc
        parsed = json.loads(body) if body else {}
        choices = parsed.get("choices") or []
        if not choices:
            raise RuntimeError("LLM semantic merge endpoint returned no choices.")
        message = choices[0].get("message") or {}
        return str(message.get("content") or "")


class OpenAIHybridMergeReducer:
    """LLM-assisted reducer that edits graph candidates instead of regrouping all evidence.

    The reducer makes the LLM call a semantic adjudication step over compact
    incident candidates. This keeps the evidence contract identical to
    ``semantic-graph`` while bounding prompt size and making the model's edits
    inspectable in the reducer trace.
    """

    name = "llm-hybrid"
    validated = False

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        max_candidates: int = 12,
        max_tokens: int = 384,
        timeout_sec: int = 180,
        structured_output: bool = False,
        allow_drop: bool = False,
        fallback_reducer: MergeReducer | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.max_candidates = max_candidates
        self.max_tokens = max_tokens
        self.timeout_sec = timeout_sec
        self.structured_output = structured_output
        self.allow_drop = allow_drop
        self.fallback_reducer = fallback_reducer
        self.last_call: dict[str, Any] = {}

    def reduce(self, evidence: list[EvidenceObject]) -> list[dict[str, Any]]:
        graph = SemanticGraphMergeReducer()
        fallback = self.fallback_reducer or graph
        hypotheses = graph.reduce(evidence)
        candidates = hypotheses[: self.max_candidates]
        evidence_by_id = _evidence_index_by_id(evidence)
        prompt = _build_llm_hybrid_merge_prompt(candidates, evidence_by_id)
        started = time.perf_counter()
        text = ""
        try:
            text = self._completion(prompt)
            payload = _extract_json_payload(text)
            edited, edit_trace = _apply_llm_hybrid_merge_payload(
                payload,
                candidates,
                evidence_by_id,
                allow_drop=self.allow_drop,
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            fallback_hypotheses = fallback.reduce(evidence)
            self.last_call = {
                "model": self.model,
                "base_url": self.base_url,
                "structured_output": self.structured_output,
                "latency_ms": round(latency_ms, 2),
                "json_valid": False,
                "schema_valid": False,
                "fallback_count": 1,
                "fallback_reason": type(exc).__name__,
                "error_message": str(exc)[:300],
                "response_preview": text[:500],
                "prompt_chars": len(prompt),
                "response_chars": len(text),
                "estimated_prompt_tokens": _estimate_tokens_from_chars(len(prompt)),
                "estimated_response_tokens": _estimate_tokens_from_chars(len(text)),
                "estimated_total_tokens": _estimate_tokens_from_chars(
                    len(prompt) + len(text)
                ),
                "input_evidence_count": len(evidence),
                "input_candidate_count": len(candidates),
                "output_incident_count": len(fallback_hypotheses),
                "edit_trace": [],
                "base_reducer": graph.name,
                "fallback_reducer": fallback.name,
                "allow_drop": self.allow_drop,
                "validated": self.validated,
            }
            return [
                {
                    **item,
                    "reducer": self.name,
                    "llm_model": self.model,
                    "llm_fallback": True,
                }
                for item in fallback_hypotheses
            ]
        latency_ms = (time.perf_counter() - started) * 1000
        validation_trace: dict[str, Any] = {
            "enabled": False,
            "repair_count": 0,
            "fallback_count": 0,
            "schema_valid": True,
        }
        if self.validated:
            edited, validation_trace = _validate_hybrid_edits(
                edited,
                candidates=candidates,
                evidence_by_id=evidence_by_id,
                fallback_hypotheses=fallback.reduce(evidence),
            )
        self.last_call = {
            "model": self.model,
            "base_url": self.base_url,
            "structured_output": self.structured_output,
            "latency_ms": round(latency_ms, 2),
            "json_valid": True,
            "schema_valid": bool(validation_trace.get("schema_valid", True)),
            "prompt_chars": len(prompt),
            "response_chars": len(text),
            "response_preview": text[:500],
            "estimated_prompt_tokens": _estimate_tokens_from_chars(len(prompt)),
            "estimated_response_tokens": _estimate_tokens_from_chars(len(text)),
            "estimated_total_tokens": _estimate_tokens_from_chars(
                len(prompt) + len(text)
            ),
            "input_evidence_count": len(evidence),
            "input_candidate_count": len(candidates),
            "output_incident_count": len(edited),
            "edit_trace": edit_trace,
            "validation_trace": validation_trace,
            "repair_count": int(validation_trace.get("repair_count", 0)),
            "fallback_count": int(validation_trace.get("fallback_count", 0)),
            "split_count": sum(
                1 for item in edit_trace if item.get("action") == "split"
            ),
            "merge_count": sum(
                1 for item in edit_trace if item.get("action") == "merge"
            ),
            "accepted_edit_count": sum(
                1
                for item in edit_trace
                if item.get("action") in {"edit", "split", "merge"}
            ),
            "base_reducer": graph.name,
            "fallback_reducer": fallback.name,
            "allow_drop": self.allow_drop,
            "validated": self.validated,
        }
        for item in edited:
            item["reducer"] = self.name
            item["llm_model"] = self.model
            item["llm_latency_ms"] = round(latency_ms, 2)
        return edited

    def _completion(self, prompt: str) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a strict JSON semantic incident adjudicator. "
                        "Edit only the provided candidate incident hypotheses. "
                        "You must return a JSON object with a required top-level "
                        "'edits' array; returning {} is invalid."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self.max_tokens,
            "temperature": 0.0,
        }
        if self.structured_output:
            payload["response_format"] = {"type": "json_object"}
        req = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"LLM hybrid merge endpoint returned HTTP {exc.code}: {body[:300]}"
            ) from exc
        parsed = json.loads(body) if body else {}
        choices = parsed.get("choices") or []
        if not choices:
            raise RuntimeError("LLM hybrid merge endpoint returned no choices.")
        message = choices[0].get("message") or {}
        return str(message.get("content") or "")


class OpenAIHybridValidatedMergeReducer(OpenAIHybridMergeReducer):
    """Candidate-level LLM reducer with validation and no-regression fallback."""

    name = "llm-hybrid-validated"
    validated = True

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("fallback_reducer", HybridHintMergeReducer())
        super().__init__(**kwargs)


class OpenAIPairwiseMergeReducer(OpenAIHybridMergeReducer):
    """LLM reducer with a constrained pairwise merge contract.

    Instead of asking the model to rewrite candidate hypotheses, this reducer
    gives it short candidate pairs and asks only whether each pair should merge.
    Accepted pair decisions are converted into evidence-preserving merge edits
    and then passed through the same validator used by candidate-level editing.
    """

    name = "llm-pairwise"
    validated = False

    def reduce(self, evidence: list[EvidenceObject]) -> list[dict[str, Any]]:
        graph = SemanticGraphMergeReducer()
        fallback = self.fallback_reducer or graph
        hypotheses = graph.reduce(evidence)
        candidates = hypotheses[: self.max_candidates]
        evidence_by_id = _evidence_index_by_id(evidence)
        pair_prompt, pairs = _build_llm_pairwise_merge_prompt(
            candidates, evidence_by_id
        )
        started = time.perf_counter()
        text = ""
        retry_count = 0
        try:
            attempts = 2 if self.validated else 1
            last_error: Exception | None = None
            for attempt in range(attempts):
                retry_count = attempt
                attempt_prompt = pair_prompt
                if attempt:
                    attempt_prompt = (
                        pair_prompt
                        + "\nRetry because the previous output was invalid. "
                        "Return exactly one JSON object with key decisions and "
                        "no extra keys, prose, code fences, or non-JSON text."
                    )
                try:
                    text = self._completion(attempt_prompt)
                    payload = _extract_json_payload(text)
                    edited, edit_trace, pair_trace = _apply_llm_pairwise_merge_payload(
                        payload,
                        candidates,
                        pairs,
                        evidence_by_id,
                    )
                    break
                except Exception as exc:
                    last_error = exc
                    if attempt + 1 >= attempts:
                        raise
            else:  # pragma: no cover - defensive; loop always breaks or raises.
                raise RuntimeError("pairwise reducer retry loop produced no result")
        except Exception as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            fallback_hypotheses = fallback.reduce(evidence)
            self.last_call = {
                "model": self.model,
                "base_url": self.base_url,
                "structured_output": self.structured_output,
                "latency_ms": round(latency_ms, 2),
                "json_valid": False,
                "schema_valid": False,
                "fallback_count": 1,
                "fallback_reason": type(exc).__name__,
                "error_message": str(exc)[:300],
                "response_preview": text[:500],
                "prompt_chars": len(pair_prompt),
                "response_chars": len(text),
                "estimated_prompt_tokens": _estimate_tokens_from_chars(
                    len(pair_prompt)
                ),
                "estimated_response_tokens": _estimate_tokens_from_chars(len(text)),
                "estimated_total_tokens": _estimate_tokens_from_chars(
                    len(pair_prompt) + len(text)
                ),
                "input_evidence_count": len(evidence),
                "input_candidate_count": len(candidates),
                "input_pair_count": len(pairs),
                "retry_count": retry_count,
                "output_incident_count": len(fallback_hypotheses),
                "edit_trace": [],
                "pair_trace": [],
                "base_reducer": graph.name,
                "fallback_reducer": fallback.name,
                "allow_drop": False,
                "validated": self.validated,
            }
            return [
                {
                    **item,
                    "reducer": self.name,
                    "llm_model": self.model,
                    "llm_fallback": True,
                }
                for item in fallback_hypotheses
            ]
        latency_ms = (time.perf_counter() - started) * 1000
        validation_trace: dict[str, Any] = {
            "enabled": False,
            "repair_count": 0,
            "fallback_count": 0,
            "schema_valid": True,
        }
        if self.validated:
            edited, validation_trace = _validate_hybrid_edits(
                edited,
                candidates=candidates,
                evidence_by_id=evidence_by_id,
                fallback_hypotheses=fallback.reduce(evidence),
            )
        self.last_call = {
            "model": self.model,
            "base_url": self.base_url,
            "structured_output": self.structured_output,
            "latency_ms": round(latency_ms, 2),
            "json_valid": True,
            "schema_valid": bool(validation_trace.get("schema_valid", True)),
            "prompt_chars": len(pair_prompt),
            "response_chars": len(text),
            "response_preview": text[:500],
            "estimated_prompt_tokens": _estimate_tokens_from_chars(len(pair_prompt)),
            "estimated_response_tokens": _estimate_tokens_from_chars(len(text)),
            "estimated_total_tokens": _estimate_tokens_from_chars(
                len(pair_prompt) + len(text)
            ),
            "input_evidence_count": len(evidence),
            "input_candidate_count": len(candidates),
            "input_pair_count": len(pairs),
            "retry_count": retry_count,
            "output_incident_count": len(edited),
            "edit_trace": edit_trace,
            "pair_trace": pair_trace,
            "validation_trace": validation_trace,
            "repair_count": int(validation_trace.get("repair_count", 0)),
            "fallback_count": int(validation_trace.get("fallback_count", 0)),
            "split_count": 0,
            "merge_count": sum(
                1 for item in edit_trace if item.get("action") == "merge"
            ),
            "accepted_edit_count": sum(
                1 for item in edit_trace if item.get("action") == "merge"
            ),
            "base_reducer": graph.name,
            "fallback_reducer": fallback.name,
            "allow_drop": False,
            "validated": self.validated,
        }
        for item in edited:
            item["reducer"] = self.name
            item["llm_model"] = self.model
            item["llm_latency_ms"] = round(latency_ms, 2)
        return edited

    def _completion(self, prompt: str) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a strict JSON pairwise incident merge judge. "
                        "Return only {\"decisions\":[...]} with one action per "
                        "provided pair. Do not write full hypotheses."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self.max_tokens,
            "temperature": 0.0,
        }
        if self.structured_output:
            payload["response_format"] = {"type": "json_object"}
        req = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"LLM pairwise merge endpoint returned HTTP {exc.code}: {body[:300]}"
            ) from exc
        parsed = json.loads(body) if body else {}
        choices = parsed.get("choices") or []
        if not choices:
            raise RuntimeError("LLM pairwise merge endpoint returned no choices.")
        message = choices[0].get("message") or {}
        return str(message.get("content") or "")


class OpenAIPairwiseValidatedMergeReducer(OpenAIPairwiseMergeReducer):
    """Pairwise merge reducer with validation and hybrid fallback."""

    name = "llm-pairwise-validated"
    validated = True

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("fallback_reducer", HybridHintMergeReducer())
        super().__init__(**kwargs)


class OpenAIPairwiseActionMergeReducer(OpenAIPairwiseMergeReducer):
    """Pairwise reducer that constrains the model to one enum action per pair."""

    name = "llm-pairwise-action"
    validated = False

    def reduce(self, evidence: list[EvidenceObject]) -> list[dict[str, Any]]:
        graph = SemanticGraphMergeReducer()
        fallback = self.fallback_reducer or graph
        hypotheses = graph.reduce(evidence)
        candidates = hypotheses[: self.max_candidates]
        evidence_by_id = _evidence_index_by_id(evidence)
        _, pairs = _build_llm_pairwise_merge_prompt(candidates, evidence_by_id)
        started = time.perf_counter()
        responses: list[dict[str, Any]] = []
        decisions: list[dict[str, Any]] = []
        prompt_chars = 0
        response_chars = 0
        invalid_action_count = 0
        try:
            for pair in pairs:
                prompt = _build_pair_action_prompt(pair)
                prompt_chars += len(prompt)
                text = self._completion_action(prompt)
                response_chars += len(text)
                action, action_valid = _parse_pair_action(text)
                if not action_valid:
                    invalid_action_count += 1
                responses.append(
                    {
                        "pair": int(pair["pair"]),
                        "raw": text[:120],
                        "action": action,
                        "valid": action_valid,
                    }
                )
                if action == "MERGE":
                    decisions.append(
                        {
                            "pair": int(pair["pair"]),
                            "action": "merge",
                            "evidence_ids": pair.get("evidence_ids", []),
                            "reason": "enum merge",
                        }
                    )
                else:
                    decisions.append(
                        {
                            "pair": int(pair["pair"]),
                            "action": "keep",
                            "evidence_ids": pair.get("evidence_ids", []),
                            "reason": action.lower(),
                        }
                    )
            edited, edit_trace, pair_trace = _apply_llm_pairwise_merge_payload(
                {"decisions": decisions},
                candidates,
                pairs,
                evidence_by_id,
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            fallback_hypotheses = fallback.reduce(evidence)
            self.last_call = {
                "model": self.model,
                "base_url": self.base_url,
                "structured_output": False,
                "latency_ms": round(latency_ms, 2),
                "json_valid": True,
                "schema_valid": False,
                "fallback_count": 1,
                "fallback_reason": type(exc).__name__,
                "error_message": str(exc)[:300],
                "response_preview": json.dumps(responses[:4], sort_keys=True)[:500],
                "prompt_chars": prompt_chars,
                "response_chars": response_chars,
                "estimated_prompt_tokens": _estimate_tokens_from_chars(prompt_chars),
                "estimated_response_tokens": _estimate_tokens_from_chars(
                    response_chars
                ),
                "estimated_total_tokens": _estimate_tokens_from_chars(
                    prompt_chars + response_chars
                ),
                "input_evidence_count": len(evidence),
                "input_candidate_count": len(candidates),
                "input_pair_count": len(pairs),
                "invalid_action_count": invalid_action_count,
                "retry_count": 0,
                "output_incident_count": len(fallback_hypotheses),
                "edit_trace": [],
                "pair_trace": [],
                "action_trace": responses,
                "base_reducer": graph.name,
                "fallback_reducer": fallback.name,
                "allow_drop": False,
                "validated": self.validated,
            }
            return [
                {
                    **item,
                    "reducer": self.name,
                    "llm_model": self.model,
                    "llm_fallback": True,
                }
                for item in fallback_hypotheses
            ]

        latency_ms = (time.perf_counter() - started) * 1000
        validation_trace: dict[str, Any] = {
            "enabled": False,
            "repair_count": 0,
            "fallback_count": 0,
            "schema_valid": True,
        }
        if self.validated:
            edited, validation_trace = _validate_hybrid_edits(
                edited,
                candidates=candidates,
                evidence_by_id=evidence_by_id,
                fallback_hypotheses=fallback.reduce(evidence),
            )
        self.last_call = {
            "model": self.model,
            "base_url": self.base_url,
            "structured_output": False,
            "latency_ms": round(latency_ms, 2),
            "json_valid": True,
            "schema_valid": bool(validation_trace.get("schema_valid", True)),
            "prompt_chars": prompt_chars,
            "response_chars": response_chars,
            "response_preview": json.dumps(responses[:4], sort_keys=True)[:500],
            "estimated_prompt_tokens": _estimate_tokens_from_chars(prompt_chars),
            "estimated_response_tokens": _estimate_tokens_from_chars(response_chars),
            "estimated_total_tokens": _estimate_tokens_from_chars(
                prompt_chars + response_chars
            ),
            "input_evidence_count": len(evidence),
            "input_candidate_count": len(candidates),
            "input_pair_count": len(pairs),
            "invalid_action_count": invalid_action_count,
            "retry_count": 0,
            "output_incident_count": len(edited),
            "edit_trace": edit_trace,
            "pair_trace": pair_trace,
            "action_trace": responses,
            "validation_trace": validation_trace,
            "repair_count": int(validation_trace.get("repair_count", 0)),
            "fallback_count": int(validation_trace.get("fallback_count", 0)),
            "validator_reject_reason": validation_trace.get("fallback_reason"),
            "split_count": 0,
            "merge_count": sum(
                1 for item in edit_trace if item.get("action") == "merge"
            ),
            "accepted_edit_count": sum(
                1 for item in edit_trace if item.get("action") == "merge"
            ),
            "base_reducer": graph.name,
            "fallback_reducer": fallback.name,
            "allow_drop": False,
            "validated": self.validated,
        }
        for item in edited:
            item["reducer"] = self.name
            item["llm_model"] = self.model
            item["llm_latency_ms"] = round(latency_ms, 2)
        return edited

    def _completion_action(self, prompt: str) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a pairwise incident classifier. Answer with "
                        "exactly one token: KEEP, MERGE, SPLIT, or ABSTAIN."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": min(self.max_tokens, 8),
            "temperature": 0.0,
        }
        req = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"LLM pairwise action endpoint returned HTTP {exc.code}: {body[:300]}"
            ) from exc
        parsed = json.loads(body) if body else {}
        choices = parsed.get("choices") or []
        if not choices:
            raise RuntimeError("LLM pairwise action endpoint returned no choices.")
        message = choices[0].get("message") or {}
        return str(message.get("content") or "")


class OpenAIPairwiseActionValidatedMergeReducer(OpenAIPairwiseActionMergeReducer):
    """Enum-action pairwise reducer with validation and hybrid fallback."""

    name = "llm-pairwise-action-validated"
    validated = True

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("fallback_reducer", HybridHintMergeReducer())
        super().__init__(**kwargs)


def resolve_merge_reducer(reducer: str | MergeReducer | None) -> MergeReducer:
    if reducer is None:
        return SemanticGraphMergeReducer()
    if not isinstance(reducer, str):
        return reducer
    normalized = reducer.strip().lower()
    if normalized == "map-only":
        return MapOnlyMergeReducer()
    if normalized in {"service-local", "service_local", "traditional"}:
        return ServiceLocalMergeReducer()
    if normalized in {"window-aggregate", "window"}:
        return WindowAggregateMergeReducer()
    if normalized in {"semantic-graph", "semantic", "sage"}:
        return SemanticGraphMergeReducer()
    if normalized in {"hybrid-hint", "hybrid", "hint-aware"}:
        return HybridHintMergeReducer()
    if normalized in {"llm-stub", "llm_stub"}:
        return LLMStubMergeReducer()
    if normalized in {"llm-hybrid", "llm_hybrid", "hybrid-openai"}:
        return OpenAIHybridMergeReducer(
            base_url=os.environ.get("SAGE_SMR_LLM_BASE_URL", "http://127.0.0.1:18383"),
            model=os.environ.get("SAGE_SMR_LLM_MODEL", "qwen25-7b-sage-realonline"),
            api_key=_api_key_from_env_or_file(
                os.environ.get("SAGE_SMR_LLM_API_KEY_ENV", "VLLM_HUST_API_KEY"),
                os.environ.get(
                    "SAGE_SMR_LLM_ENV_FILE",
                    "external/vllm-hust-dev-hub/.env",
                ),
            ),
            max_candidates=int(os.environ.get("SAGE_SMR_LLM_MAX_CANDIDATES", "12")),
            max_tokens=int(os.environ.get("SAGE_SMR_LLM_MAX_TOKENS", "384")),
            timeout_sec=int(os.environ.get("SAGE_SMR_LLM_TIMEOUT_SEC", "180")),
            structured_output=os.environ.get("SAGE_SMR_LLM_STRUCTURED_OUTPUT", "")
            .strip()
            .lower()
            in {"1", "true", "yes", "on"},
            allow_drop=os.environ.get("SAGE_SMR_LLM_ALLOW_DROP", "")
            .strip()
            .lower()
            in {"1", "true", "yes", "on"},
        )
    if normalized in {
        "llm-hybrid-validated",
        "llm_hybrid_validated",
        "validated-hybrid",
        "hybrid-validated",
    }:
        return OpenAIHybridValidatedMergeReducer(
            base_url=os.environ.get("SAGE_SMR_LLM_BASE_URL", "http://127.0.0.1:18383"),
            model=os.environ.get("SAGE_SMR_LLM_MODEL", "qwen25-7b-sage-realonline"),
            api_key=_api_key_from_env_or_file(
                os.environ.get("SAGE_SMR_LLM_API_KEY_ENV", "VLLM_HUST_API_KEY"),
                os.environ.get(
                    "SAGE_SMR_LLM_ENV_FILE",
                    "external/vllm-hust-dev-hub/.env",
                ),
            ),
            max_candidates=int(os.environ.get("SAGE_SMR_LLM_MAX_CANDIDATES", "12")),
            max_tokens=int(os.environ.get("SAGE_SMR_LLM_MAX_TOKENS", "384")),
            timeout_sec=int(os.environ.get("SAGE_SMR_LLM_TIMEOUT_SEC", "180")),
            structured_output=os.environ.get("SAGE_SMR_LLM_STRUCTURED_OUTPUT", "")
            .strip()
            .lower()
            in {"1", "true", "yes", "on"},
            allow_drop=os.environ.get("SAGE_SMR_LLM_ALLOW_DROP", "")
            .strip()
            .lower()
            in {"1", "true", "yes", "on"},
        )
    if normalized in {"llm-pairwise", "llm_pairwise", "pairwise-openai"}:
        return OpenAIPairwiseMergeReducer(
            base_url=os.environ.get("SAGE_SMR_LLM_BASE_URL", "http://127.0.0.1:18383"),
            model=os.environ.get("SAGE_SMR_LLM_MODEL", "qwen25-7b-sage-realonline"),
            api_key=_api_key_from_env_or_file(
                os.environ.get("SAGE_SMR_LLM_API_KEY_ENV", "VLLM_HUST_API_KEY"),
                os.environ.get(
                    "SAGE_SMR_LLM_ENV_FILE",
                    "external/vllm-hust-dev-hub/.env",
                ),
            ),
            max_candidates=int(os.environ.get("SAGE_SMR_LLM_MAX_CANDIDATES", "12")),
            max_tokens=int(os.environ.get("SAGE_SMR_LLM_MAX_TOKENS", "384")),
            timeout_sec=int(os.environ.get("SAGE_SMR_LLM_TIMEOUT_SEC", "180")),
            structured_output=os.environ.get("SAGE_SMR_LLM_STRUCTURED_OUTPUT", "")
            .strip()
            .lower()
            in {"1", "true", "yes", "on"},
        )
    if normalized in {
        "llm-pairwise-validated",
        "llm_pairwise_validated",
        "pairwise-validated",
    }:
        return OpenAIPairwiseValidatedMergeReducer(
            base_url=os.environ.get("SAGE_SMR_LLM_BASE_URL", "http://127.0.0.1:18383"),
            model=os.environ.get("SAGE_SMR_LLM_MODEL", "qwen25-7b-sage-realonline"),
            api_key=_api_key_from_env_or_file(
                os.environ.get("SAGE_SMR_LLM_API_KEY_ENV", "VLLM_HUST_API_KEY"),
                os.environ.get(
                    "SAGE_SMR_LLM_ENV_FILE",
                    "external/vllm-hust-dev-hub/.env",
                ),
            ),
            max_candidates=int(os.environ.get("SAGE_SMR_LLM_MAX_CANDIDATES", "12")),
            max_tokens=int(os.environ.get("SAGE_SMR_LLM_MAX_TOKENS", "384")),
            timeout_sec=int(os.environ.get("SAGE_SMR_LLM_TIMEOUT_SEC", "180")),
            structured_output=os.environ.get("SAGE_SMR_LLM_STRUCTURED_OUTPUT", "")
            .strip()
            .lower()
            in {"1", "true", "yes", "on"},
        )
    if normalized in {
        "llm-pairwise-action",
        "llm_pairwise_action",
        "pairwise-action",
    }:
        return OpenAIPairwiseActionMergeReducer(
            base_url=os.environ.get("SAGE_SMR_LLM_BASE_URL", "http://127.0.0.1:18383"),
            model=os.environ.get("SAGE_SMR_LLM_MODEL", "qwen25-7b-sage-realonline"),
            api_key=_api_key_from_env_or_file(
                os.environ.get("SAGE_SMR_LLM_API_KEY_ENV", "VLLM_HUST_API_KEY"),
                os.environ.get(
                    "SAGE_SMR_LLM_ENV_FILE",
                    "external/vllm-hust-dev-hub/.env",
                ),
            ),
            max_candidates=int(os.environ.get("SAGE_SMR_LLM_MAX_CANDIDATES", "12")),
            max_tokens=int(os.environ.get("SAGE_SMR_LLM_MAX_TOKENS", "8")),
            timeout_sec=int(os.environ.get("SAGE_SMR_LLM_TIMEOUT_SEC", "180")),
        )
    if normalized in {
        "llm-pairwise-action-validated",
        "llm_pairwise_action_validated",
        "pairwise-action-validated",
        "action-validated",
    }:
        return OpenAIPairwiseActionValidatedMergeReducer(
            base_url=os.environ.get("SAGE_SMR_LLM_BASE_URL", "http://127.0.0.1:18383"),
            model=os.environ.get("SAGE_SMR_LLM_MODEL", "qwen25-7b-sage-realonline"),
            api_key=_api_key_from_env_or_file(
                os.environ.get("SAGE_SMR_LLM_API_KEY_ENV", "VLLM_HUST_API_KEY"),
                os.environ.get(
                    "SAGE_SMR_LLM_ENV_FILE",
                    "external/vllm-hust-dev-hub/.env",
                ),
            ),
            max_candidates=int(os.environ.get("SAGE_SMR_LLM_MAX_CANDIDATES", "12")),
            max_tokens=int(os.environ.get("SAGE_SMR_LLM_MAX_TOKENS", "8")),
            timeout_sec=int(os.environ.get("SAGE_SMR_LLM_TIMEOUT_SEC", "180")),
        )
    if normalized in {"llm-openai", "llm_openai", "openai"}:
        return OpenAISemanticMergeReducer(
            base_url=os.environ.get("SAGE_SMR_LLM_BASE_URL", "http://127.0.0.1:18383"),
            model=os.environ.get("SAGE_SMR_LLM_MODEL", "qwen25-7b-sage-realonline"),
            api_key=_api_key_from_env_or_file(
                os.environ.get("SAGE_SMR_LLM_API_KEY_ENV", "VLLM_HUST_API_KEY"),
                os.environ.get(
                    "SAGE_SMR_LLM_ENV_FILE",
                    "external/vllm-hust-dev-hub/.env",
                ),
            ),
            max_evidence=int(os.environ.get("SAGE_SMR_LLM_MAX_EVIDENCE", "24")),
            max_tokens=int(os.environ.get("SAGE_SMR_LLM_MAX_TOKENS", "512")),
            timeout_sec=int(os.environ.get("SAGE_SMR_LLM_TIMEOUT_SEC", "180")),
            structured_output=os.environ.get("SAGE_SMR_LLM_STRUCTURED_OUTPUT", "")
            .strip()
            .lower()
            in {"1", "true", "yes", "on"},
        )
    raise ValueError(
        f"Unknown semantic merge reducer {reducer!r}. Expected map-only, "
        "service-local, window-aggregate, semantic-graph, hybrid-hint, "
        "llm-stub, llm-hybrid, llm-hybrid-validated, llm-pairwise, "
        "llm-pairwise-validated, llm-pairwise-action, "
        "llm-pairwise-action-validated, or llm-openai."
    )


def _build_llm_semantic_merge_prompt(evidence: list[EvidenceObject]) -> str:
    compact = []
    for idx, item in enumerate(evidence):
        compact.append(
            {
                "row": idx,
                "evidence_id": item.evidence_id,
                "service": item.service,
                "region": item.region,
                "start_minute": item.start_minute,
                "end_minute": item.end_minute,
                "signals": list(item.signals),
                "score": item.score,
                "upstream_hint": item.upstream_hint,
            }
        )
    return (
        "Group evidence rows into incident-level hypotheses. Use the dependency "
        "graph to merge downstream symptoms into one root-cause incident. "
        "The root_service must also appear in affected_services. "
        "Return ONLY JSON: {\"incidents\":[{\"root_service\":\"router\","
        "\"region\":\"npu-a\",\"evidence_rows\":[0,1],"
        "\"affected_services\":[\"router\",\"scheduler\"]}]}.\n"
        f"Dependency graph: {json.dumps(DEPENDENCIES, sort_keys=True)}\n"
        f"Evidence: {json.dumps(compact, sort_keys=True)}"
    )


def _build_llm_hybrid_merge_prompt(
    hypotheses: list[dict[str, Any]], evidence_by_id: dict[str, EvidenceObject]
) -> str:
    candidates: list[dict[str, Any]] = []
    candidate_hint_rows: list[dict[str, Any]] = []
    for idx, hypothesis in enumerate(hypotheses):
        evidence_rows = []
        for evidence_id in hypothesis.get("evidence_ids", []):
            evidence = evidence_by_id.get(str(evidence_id))
            if evidence is None:
                continue
            evidence_rows.append(
                {
                    "evidence_id": evidence.evidence_id,
                    "service": evidence.service,
                    "region": evidence.region,
                    "start_minute": evidence.start_minute,
                    "end_minute": evidence.end_minute,
                    "signals": list(evidence.signals),
                    "score": evidence.score,
                    "upstream_hint": evidence.upstream_hint,
                }
            )
        upstream_hints = [
            str(row["upstream_hint"])
            for row in evidence_rows
            if row.get("upstream_hint")
        ]
        dominant_hint = statistics.mode(upstream_hints) if upstream_hints else None
        candidates.append(
            {
                "candidate": idx,
                "root_service": hypothesis.get("root_service"),
                "region": hypothesis.get("region"),
                "start_minute": hypothesis.get("start_minute"),
                "end_minute": hypothesis.get("end_minute"),
                "affected_services": hypothesis.get("affected_services", []),
                "dominant_upstream_hint": dominant_hint,
                "evidence_services": sorted(
                    {
                        str(row["service"])
                        for row in evidence_rows
                        if isinstance(row.get("service"), str)
                    }
                ),
                "evidence": evidence_rows,
            }
        )
        candidate_hint_rows.append(
            {
                "candidate": idx,
                "region": hypothesis.get("region"),
                "start_minute": hypothesis.get("start_minute"),
                "end_minute": hypothesis.get("end_minute"),
                "dominant_upstream_hint": dominant_hint,
            }
        )
    merge_hints: list[dict[str, Any]] = []
    for left_index, left in enumerate(candidate_hint_rows):
        for right in candidate_hint_rows[left_index + 1 :]:
            if not left.get("dominant_upstream_hint"):
                continue
            if left.get("dominant_upstream_hint") != right.get("dominant_upstream_hint"):
                continue
            if left.get("region") != right.get("region"):
                continue
            left_end = int(left.get("end_minute", -1) or -1)
            right_start = int(right.get("start_minute", 10**9) or 10**9)
            right_end = int(right.get("end_minute", -1) or -1)
            left_start = int(left.get("start_minute", 10**9) or 10**9)
            gap = max(left_start, right_start) - min(left_end, right_end)
            if gap <= 40:
                merge_hints.append(
                    {
                        "candidates": [left["candidate"], right["candidate"]],
                        "root_service": left["dominant_upstream_hint"],
                        "reason": "same dominant_upstream_hint, region, and nearby time",
                    }
                )
    return (
        "You are given graph-produced incident candidates. Return a JSON object "
        "with a required top-level edits array. Never return an empty object. "
        "If no candidate needs semantic correction, return keep edits. "
        "Do not create new "
        "incidents from raw data. For each candidate, keep it unless all of its "
        "evidence is clearly unrelated low-confidence distractor evidence. Merge "
        "candidates only when their evidence supports the same root cause and "
        "the same incident. Split a candidate only when its evidence supports "
        "multiple independent root causes; each split part must cite evidence_ids "
        "from that candidate. Edit only root_service and affected_services using "
        "dependency hints. The root_service must also appear in affected_services. "
        "Return ONLY JSON "
        "with this "
        "shape: {\"edits\":[{\"candidate\":0,\"action\":\"keep\","
        "\"root_service\":\"router\",\"affected_services\":[\"router\","
        "\"scheduler\"]},{\"candidate\":1,\"action\":\"merge\","
        "\"candidates\":[1,2],\"root_service\":\"scheduler\","
        "\"affected_services\":[\"scheduler\",\"prefill\",\"decode\"]},"
        "{\"candidate\":3,\"action\":\"split\",\"parts\":["
        "{\"evidence_ids\":[\"e1\",\"e2\"],\"root_service\":\"scheduler\","
        "\"affected_services\":[\"scheduler\",\"prefill\"]}]}]}.\n"
        "Every edit must use one of these actions: keep, merge, split, edit, drop. "
        "Every merge must include a candidates array. Every split part must cite "
        "evidence_ids from the source candidate. Use only services and evidence "
        "ids shown below. Prefer merge edits for candidates listed in merge_hints "
        "when their evidence has the same root hint and region.\n"
        f"Valid services: {json.dumps(SERVICES)}\n"
        f"Dependency graph: {json.dumps(DEPENDENCIES, sort_keys=True)}\n"
        f"Merge hints: {json.dumps(merge_hints, sort_keys=True)}\n"
        f"Candidates: {json.dumps(candidates, sort_keys=True)}"
    )


def _build_llm_pairwise_merge_prompt(
    hypotheses: list[dict[str, Any]], evidence_by_id: dict[str, EvidenceObject]
) -> tuple[str, list[dict[str, Any]]]:
    candidate_rows: list[dict[str, Any]] = []
    for idx, hypothesis in enumerate(hypotheses):
        evidence_items = [
            evidence_by_id[str(evidence_id)]
            for evidence_id in hypothesis.get("evidence_ids", [])
            if str(evidence_id) in evidence_by_id
        ]
        hints = [item.upstream_hint for item in evidence_items if item.upstream_hint]
        dominant_hint = statistics.mode(hints) if hints else None
        candidate_rows.append(
            {
                "candidate": idx,
                "root_service": hypothesis.get("root_service"),
                "region": hypothesis.get("region"),
                "start_minute": hypothesis.get("start_minute"),
                "end_minute": hypothesis.get("end_minute"),
                "affected_services": hypothesis.get("affected_services", []),
                "dominant_upstream_hint": dominant_hint,
                "evidence_ids": [item.evidence_id for item in evidence_items],
                "services": sorted({item.service for item in evidence_items}),
                "signals": sorted(
                    {signal for item in evidence_items for signal in item.signals}
                ),
            }
        )

    pairs: list[dict[str, Any]] = []
    for left_index, left in enumerate(candidate_rows):
        for right in candidate_rows[left_index + 1 :]:
            if left.get("region") != right.get("region"):
                continue
            left_hint = left.get("dominant_upstream_hint")
            right_hint = right.get("dominant_upstream_hint")
            same_hint = bool(left_hint and left_hint == right_hint)
            related_services = any(
                _services_related(str(left_service), str(right_service))
                for left_service in left.get("services", [])
                for right_service in right.get("services", [])
            )
            left_start = int(left.get("start_minute", 0) or 0)
            left_end = int(left.get("end_minute", 0) or 0)
            right_start = int(right.get("start_minute", 0) or 0)
            right_end = int(right.get("end_minute", 0) or 0)
            gap = max(left_start, right_start) - min(left_end, right_end)
            nearby = gap <= 80
            if not (same_hint and nearby) and not (
                related_services and gap <= 20
            ):
                continue
            pair_id = len(pairs)
            pair_evidence_ids = list(
                dict.fromkeys(
                    [
                        *[str(item) for item in left.get("evidence_ids", [])],
                        *[str(item) for item in right.get("evidence_ids", [])],
                    ]
                )
            )
            pairs.append(
                {
                    "pair": pair_id,
                    "candidates": [left["candidate"], right["candidate"]],
                    "region": left.get("region"),
                    "gap_minutes": gap,
                    "same_upstream_hint": same_hint,
                    "dominant_upstream_hint": left_hint if same_hint else None,
                    "evidence_ids": pair_evidence_ids,
                    "left": {
                        "candidate": left["candidate"],
                        "window": [left_start, left_end],
                        "services": left.get("services", []),
                        "signals": left.get("signals", []),
                        "evidence_ids": left.get("evidence_ids", []),
                    },
                    "right": {
                        "candidate": right["candidate"],
                        "window": [right_start, right_end],
                        "services": right.get("services", []),
                        "signals": right.get("signals", []),
                        "evidence_ids": right.get("evidence_ids", []),
                    },
                }
            )
    pairs.sort(
        key=lambda item: (
            not bool(item.get("same_upstream_hint")),
            int(item.get("gap_minutes", 10**9) or 10**9),
            int(item.get("pair", 0) or 0),
        )
    )
    max_pairs = int(os.environ.get("SAGE_SMR_LLM_MAX_PAIRS", "6"))
    pairs = [
        {**pair, "pair": idx}
        for idx, pair in enumerate(pairs[: max(1, max_pairs)])
    ]

    return (
        "Return JSON only. Task: judge if each pair is the same incident. "
        "Do not write incident hypotheses. Schema: {\"decisions\":[{\"pair\":0,"
        "\"action\":\"merge\",\"evidence_ids\":[\"e1\",\"e2\"],"
        "\"reason\":\"same upstream\"}]}.\n"
        "Actions: merge, keep, split. Treat split as keep. Rule: if "
        "same_upstream_hint is true and gap_minutes <= 80, choose merge unless "
        "the two windows clearly contradict. Different services are expected "
        "downstream symptoms, not a reason to keep. evidence_ids must be copied "
        "from that pair's evidence_ids. reason <= 8 words. Return one decision "
        "for every pair.\n"
        f"Pairs: {json.dumps(pairs, sort_keys=True)}",
        pairs,
    )


def _build_pair_action_prompt(pair: dict[str, Any]) -> str:
    compact = {
        "pair": pair.get("pair"),
        "same_upstream_hint": pair.get("same_upstream_hint"),
        "dominant_upstream_hint": pair.get("dominant_upstream_hint"),
        "gap_minutes": pair.get("gap_minutes"),
        "region": pair.get("region"),
        "left": pair.get("left"),
        "right": pair.get("right"),
    }
    return (
        "Choose one token: MERGE, KEEP, SPLIT, or ABSTAIN.\n"
        "MERGE if same_upstream_hint is true and gap_minutes <= 80 unless the "
        "evidence clearly contradicts. Different services can be downstream "
        "symptoms and should not by itself force KEEP. ABSTAIN if uncertain.\n"
        f"Pair: {json.dumps(compact, sort_keys=True)}"
    )


def _parse_pair_action(text: str) -> tuple[str, bool]:
    normalized = text.strip().upper()
    for action in ("MERGE", "KEEP", "SPLIT", "ABSTAIN"):
        if normalized == action:
            return action, True
    tokens = [
        token.strip(" \t\r\n.,:;!?\"'`[]{}()<>")
        for token in normalized.replace("/", " ").split()
    ]
    for action in ("MERGE", "KEEP", "SPLIT", "ABSTAIN"):
        if action in tokens:
            return action, True
    return "ABSTAIN", False


def _normalize_llm_merge_payload(
    payload: dict[str, Any], evidence: list[EvidenceObject]
) -> list[dict[str, Any]]:
    raw_incidents = payload.get("incidents")
    if not isinstance(raw_incidents, list):
        raise RuntimeError("LLM semantic merge JSON must contain an incidents list.")
    used_rows: set[int] = set()
    hypotheses: list[dict[str, Any]] = []
    for raw in raw_incidents:
        if not isinstance(raw, dict):
            continue
        rows = [
            int(row)
            for row in raw.get("evidence_rows", raw.get("evidence_ids", []))
            if isinstance(row, int) or (isinstance(row, str) and row.isdigit())
        ]
        rows = [row for row in dict.fromkeys(rows) if 0 <= row < len(evidence)]
        rows = [row for row in rows if row not in used_rows]
        if not rows:
            continue
        used_rows.update(rows)
        selected = [evidence[row] for row in rows]
        hypothesis = _hypothesis_from_evidence_group(selected, reducer="llm-openai")
        root_service = raw.get("root_service")
        selected_services = {item.service for item in selected}
        hinted_services = {item.upstream_hint for item in selected if item.upstream_hint}
        if isinstance(root_service, str) and (
            root_service in selected_services or root_service in hinted_services
        ):
            hypothesis["root_service"] = root_service
        affected_services = raw.get("affected_services")
        if isinstance(affected_services, list):
            normalized = [
                str(service)
                for service in affected_services
                if isinstance(service, str) and service in SERVICES
            ]
            if normalized:
                affected = set(normalized)
                root = hypothesis.get("root_service")
                if isinstance(root, str) and root in SERVICES:
                    affected.add(root)
                hypothesis["affected_services"] = sorted(affected)
        hypotheses.append(hypothesis)
    return sorted(hypotheses, key=lambda item: item["score"], reverse=True)


def _apply_llm_hybrid_merge_payload(
    payload: dict[str, Any],
    hypotheses: list[dict[str, Any]],
    evidence_by_id: dict[str, EvidenceObject],
    *,
    allow_drop: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw_edits = payload.get("edits")
    if not isinstance(raw_edits, list):
        raise RuntimeError("LLM hybrid merge JSON must contain an edits list.")
    edits_by_index: dict[int, dict[str, Any]] = {}
    for raw in raw_edits:
        if not isinstance(raw, dict):
            continue
        candidate = raw.get("candidate")
        if isinstance(candidate, int) and 0 <= candidate < len(hypotheses):
            edits_by_index[candidate] = raw

    edited: list[dict[str, Any]] = []
    trace: list[dict[str, Any]] = []
    consumed_by_merge: set[int] = set()
    for idx, hypothesis in enumerate(hypotheses):
        if idx in consumed_by_merge:
            continue
        raw = edits_by_index.get(idx, {})
        action = str(raw.get("action", "keep")).strip().lower()
        if action == "drop":
            if not allow_drop:
                trace.append(
                    {
                        "candidate": idx,
                        "action": "drop-suppressed",
                        "reason": str(raw.get("reason", ""))[:160],
                    }
                )
                raw = {}
            else:
                trace.append(
                    {
                        "candidate": idx,
                        "action": "drop",
                        "reason": str(raw.get("reason", ""))[:160],
                    }
                )
                continue
        item = {**hypothesis}
        selected = [
            evidence_by_id[evidence_id]
            for evidence_id in item.get("evidence_ids", [])
            if evidence_id in evidence_by_id
        ]
        selected_services = {evidence.service for evidence in selected}
        hinted_services = {
            evidence.upstream_hint for evidence in selected if evidence.upstream_hint
        }
        allowed_root_services = selected_services | hinted_services
        if action == "split":
            parts = raw.get("parts")
            split_items: list[dict[str, Any]] = []
            candidate_evidence_ids = {
                str(evidence_id) for evidence_id in item.get("evidence_ids", [])
            }
            if isinstance(parts, list):
                for part in parts:
                    if not isinstance(part, dict):
                        continue
                    part_evidence_ids = [
                        str(evidence_id)
                        for evidence_id in part.get("evidence_ids", [])
                        if str(evidence_id) in candidate_evidence_ids
                        and str(evidence_id) in evidence_by_id
                    ]
                    part_evidence_ids = list(dict.fromkeys(part_evidence_ids))
                    if not part_evidence_ids:
                        continue
                    part_evidence = [
                        evidence_by_id[evidence_id]
                        for evidence_id in part_evidence_ids
                    ]
                    part_item = _hypothesis_from_evidence_group(
                        part_evidence,
                        reducer="llm-hybrid",
                        include_root_hint_in_affected=True,
                    )
                    part_services = {evidence.service for evidence in part_evidence}
                    part_hints = {
                        evidence.upstream_hint
                        for evidence in part_evidence
                        if evidence.upstream_hint
                    }
                    part_allowed = part_services | part_hints
                    root_service = part.get("root_service")
                    if (
                        isinstance(root_service, str)
                        and root_service in part_allowed
                    ):
                        part_item["root_service"] = root_service
                    affected_services = part.get("affected_services")
                    if isinstance(affected_services, list):
                        normalized = {
                            str(service)
                            for service in affected_services
                            if isinstance(service, str)
                            and service in SERVICES
                            and service in part_allowed
                        }
                        root = part_item.get("root_service")
                        if isinstance(root, str) and root in part_allowed:
                            normalized.add(root)
                        if normalized:
                            part_item["affected_services"] = sorted(normalized)
                    split_items.append(part_item)
            if split_items:
                trace.append(
                    {
                        "candidate": idx,
                        "action": "split",
                        "part_count": len(split_items),
                        "evidence_ids": sorted(candidate_evidence_ids),
                    }
                )
                edited.extend(split_items)
                continue
            trace.append(
                {
                    "candidate": idx,
                    "action": "split-invalid-keep-default",
                    "reason": "no_valid_evidence_parts",
                }
            )
            raw = {}
        if action == "merge":
            raw_merge_candidates = raw.get("candidates", [idx])
            if not isinstance(raw_merge_candidates, list):
                raw_merge_candidates = [idx]
            merge_indices = [
                int(candidate)
                for candidate in raw_merge_candidates
                if isinstance(candidate, int) or str(candidate).isdigit()
            ]
            merge_indices = [
                candidate
                for candidate in dict.fromkeys([idx, *merge_indices])
                if 0 <= candidate < len(hypotheses)
                and candidate not in consumed_by_merge
            ]
            merge_evidence_ids: list[str] = []
            for candidate in merge_indices:
                merge_evidence_ids.extend(
                    str(evidence_id)
                    for evidence_id in hypotheses[candidate].get("evidence_ids", [])
                    if str(evidence_id) in evidence_by_id
                )
            merge_evidence_ids = list(dict.fromkeys(merge_evidence_ids))
            if len(merge_indices) > 1 and merge_evidence_ids:
                merge_evidence = [
                    evidence_by_id[evidence_id] for evidence_id in merge_evidence_ids
                ]
                merge_item = _hypothesis_from_evidence_group(
                    merge_evidence,
                    reducer="llm-hybrid",
                    include_root_hint_in_affected=True,
                )
                allowed_services = {
                    evidence.service for evidence in merge_evidence
                } | {
                    evidence.upstream_hint
                    for evidence in merge_evidence
                    if evidence.upstream_hint
                }
                root_service = raw.get("root_service")
                if isinstance(root_service, str) and root_service in allowed_services:
                    merge_item["root_service"] = root_service
                affected_services = raw.get("affected_services")
                if isinstance(affected_services, list):
                    normalized = {
                        str(service)
                        for service in affected_services
                        if isinstance(service, str)
                        and service in SERVICES
                        and service in allowed_services
                    }
                    root = merge_item.get("root_service")
                    if isinstance(root, str) and root in allowed_services:
                        normalized.add(root)
                    if normalized:
                        merge_item["affected_services"] = sorted(normalized)
                merge_item["llm_edit_action"] = "merge"
                merge_item["merged_candidates"] = merge_indices
                consumed_by_merge.update(merge_indices)
                trace.append(
                    {
                        "candidate": idx,
                        "action": "merge",
                        "candidates": merge_indices,
                        "evidence_ids": merge_evidence_ids,
                    }
                )
                edited.append(merge_item)
                continue
            trace.append(
                {
                    "candidate": idx,
                    "action": "merge-invalid-keep-default",
                    "reason": "need_at_least_two_valid_candidates",
                }
            )
            raw = {}
        root_service = raw.get("root_service")
        if isinstance(root_service, str) and root_service in allowed_root_services:
            item["root_service"] = root_service
        affected_services = raw.get("affected_services")
        if isinstance(affected_services, list):
            allowed_affected = selected_services | hinted_services
            normalized = sorted(
                {
                    str(service)
                    for service in affected_services
                    if isinstance(service, str)
                    and service in SERVICES
                    and service in allowed_affected
                }
            )
            if normalized:
                affected = set(normalized)
                root = item.get("root_service")
                if isinstance(root, str) and root in allowed_affected:
                    affected.add(root)
                item["affected_services"] = sorted(affected)
        trace.append(
            {
                "candidate": idx,
                "action": "edit" if raw else "keep-default",
                "root_service": item.get("root_service"),
                "affected_services": item.get("affected_services", []),
            }
        )
        edited.append(item)
    return sorted(edited, key=lambda item: item["score"], reverse=True), trace


def _apply_llm_pairwise_merge_payload(
    payload: dict[str, Any],
    hypotheses: list[dict[str, Any]],
    pairs: list[dict[str, Any]],
    evidence_by_id: dict[str, EvidenceObject],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    raw_decisions = payload.get("decisions")
    if not isinstance(raw_decisions, list):
        raise RuntimeError("LLM pairwise merge JSON must contain a decisions list.")
    pair_by_id = {int(pair["pair"]): pair for pair in pairs}
    parent = list(range(len(hypotheses)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    pair_trace: list[dict[str, Any]] = []
    merge_decisions: list[dict[str, Any]] = []
    for raw in raw_decisions:
        if not isinstance(raw, dict):
            continue
        pair_id = raw.get("pair")
        if not (isinstance(pair_id, int) or str(pair_id).isdigit()):
            pair_trace.append({"action": "invalid", "reason": "missing_pair_id"})
            continue
        pair = pair_by_id.get(int(pair_id))
        if pair is None:
            pair_trace.append(
                {"pair": int(pair_id), "action": "invalid", "reason": "unknown_pair"}
            )
            continue
        action = str(raw.get("action", "keep")).strip().lower()
        reason = str(raw.get("reason", ""))[:160]
        candidate_indices = [
            int(candidate)
            for candidate in pair.get("candidates", [])
            if isinstance(candidate, int) or str(candidate).isdigit()
        ]
        if len(candidate_indices) != 2:
            pair_trace.append(
                {"pair": int(pair_id), "action": "invalid", "reason": "bad_pair"}
            )
            continue
        pair_evidence_ids = {
            str(evidence_id)
            for evidence_id in pair.get("evidence_ids", [])
            if str(evidence_id) in evidence_by_id
        }
        raw_evidence_ids = raw.get("evidence_ids", [])
        if not isinstance(raw_evidence_ids, list):
            raw_evidence_ids = []
        decision_evidence_ids = {
            str(evidence_id)
            for evidence_id in raw_evidence_ids
            if str(evidence_id) in pair_evidence_ids
        }
        if not decision_evidence_ids:
            decision_evidence_ids = set(pair_evidence_ids)
        if action != "merge":
            pair_trace.append(
                {
                    "pair": int(pair_id),
                    "action": action if action in {"keep", "split"} else "keep",
                    "reason": reason,
                    "evidence_ids": sorted(decision_evidence_ids),
                }
            )
            continue
        left, right = candidate_indices
        if not (0 <= left < len(hypotheses) and 0 <= right < len(hypotheses)):
            pair_trace.append(
                {
                    "pair": int(pair_id),
                    "action": "merge-rejected",
                    "reason": "candidate_out_of_range",
                }
            )
            continue
        left_evidence = {
            str(evidence_id)
            for evidence_id in hypotheses[left].get("evidence_ids", [])
            if str(evidence_id) in evidence_by_id
        }
        right_evidence = {
            str(evidence_id)
            for evidence_id in hypotheses[right].get("evidence_ids", [])
            if str(evidence_id) in evidence_by_id
        }
        if not (decision_evidence_ids & left_evidence) or not (
            decision_evidence_ids & right_evidence
        ):
            pair_trace.append(
                {
                    "pair": int(pair_id),
                    "action": "merge-rejected",
                    "reason": "evidence_not_from_both_candidates",
                    "evidence_ids": sorted(decision_evidence_ids),
                }
            )
            continue
        union(left, right)
        trace_item = {
            "pair": int(pair_id),
            "action": "merge",
            "candidates": [left, right],
            "evidence_ids": sorted(decision_evidence_ids),
            "reason": reason,
        }
        pair_trace.append(trace_item)
        merge_decisions.append(trace_item)

    grouped_candidates: dict[int, list[int]] = defaultdict(list)
    for index in range(len(hypotheses)):
        grouped_candidates[find(index)].append(index)

    edited: list[dict[str, Any]] = []
    edit_trace: list[dict[str, Any]] = []
    for group in grouped_candidates.values():
        if len(group) <= 1:
            edited.append({**hypotheses[group[0]]})
            edit_trace.append({"candidate": group[0], "action": "keep"})
            continue
        evidence_ids: list[str] = []
        for candidate in group:
            evidence_ids.extend(
                str(evidence_id)
                for evidence_id in hypotheses[candidate].get("evidence_ids", [])
                if str(evidence_id) in evidence_by_id
            )
        evidence_ids = list(dict.fromkeys(evidence_ids))
        evidence_items = [evidence_by_id[evidence_id] for evidence_id in evidence_ids]
        item = _hypothesis_from_evidence_group(
            evidence_items,
            reducer="llm-pairwise",
            include_root_hint_in_affected=True,
        )
        item["llm_edit_action"] = "merge"
        item["merged_candidates"] = sorted(group)
        edited.append(item)
        edit_trace.append(
            {
                "candidate": min(group),
                "action": "merge",
                "candidates": sorted(group),
                "evidence_ids": evidence_ids,
            }
        )
    return (
        sorted(edited, key=lambda item: item["score"], reverse=True),
        edit_trace,
        pair_trace,
    )


def _validate_hybrid_edits(
    hypotheses: list[dict[str, Any]],
    *,
    candidates: list[dict[str, Any]],
    evidence_by_id: dict[str, EvidenceObject],
    fallback_hypotheses: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    trace: dict[str, Any] = {
        "enabled": True,
        "repair_count": 0,
        "fallback_count": 0,
        "schema_valid": True,
        "candidate_count": len(candidates),
        "output_count_before_validation": len(hypotheses),
        "repairs": [],
    }
    candidate_evidence_ids = {
        str(evidence_id)
        for candidate in candidates
        for evidence_id in candidate.get("evidence_ids", [])
        if str(evidence_id) in evidence_by_id
    }
    output_evidence_ids = {
        str(evidence_id)
        for hypothesis in hypotheses
        for evidence_id in hypothesis.get("evidence_ids", [])
        if str(evidence_id) in evidence_by_id
    }
    missing_candidate_evidence = sorted(candidate_evidence_ids - output_evidence_ids)
    if missing_candidate_evidence:
        trace.update(
            {
                "schema_valid": False,
                "fallback_count": 1,
                "fallback_reason": "candidate_evidence_regression",
                "missing_evidence_ids": missing_candidate_evidence,
            }
        )
        return _mark_validated_fallback(fallback_hypotheses), trace
    trace["candidate_evidence_count"] = len(candidate_evidence_ids)
    trace["output_evidence_count"] = len(output_evidence_ids)

    validated: list[dict[str, Any]] = []
    for hypothesis in hypotheses:
        item = {**hypothesis}
        evidence_ids = [str(value) for value in item.get("evidence_ids", [])]
        evidence_items = [
            evidence_by_id[evidence_id]
            for evidence_id in evidence_ids
            if evidence_id in evidence_by_id
        ]
        if not evidence_items:
            trace.update(
                {
                    "schema_valid": False,
                    "fallback_count": 1,
                    "fallback_reason": "hypothesis_without_evidence",
                }
            )
            return _mark_validated_fallback(fallback_hypotheses), trace

        selected_services = {evidence.service for evidence in evidence_items}
        hinted_services = [
            evidence.upstream_hint for evidence in evidence_items if evidence.upstream_hint
        ]
        allowed_services = set(selected_services) | set(hinted_services)
        affected = {
            str(service)
            for service in item.get("affected_services", [])
            if isinstance(service, str) and service in allowed_services
        }
        root = item.get("root_service")
        dominant_hint = statistics.mode(hinted_services) if hinted_services else None
        repaired = False

        if isinstance(dominant_hint, str) and root != dominant_hint:
            root = dominant_hint
            repaired = True
        if not isinstance(root, str) or root not in allowed_services:
            root = _choose_root_service(evidence_items)
            repaired = True
        affected.add(root)
        for evidence in evidence_items:
            if evidence.score >= 0.5:
                affected.add(evidence.service)
        if not affected:
            trace.update(
                {
                    "schema_valid": False,
                    "fallback_count": 1,
                    "fallback_reason": "empty_affected_services",
                }
            )
            return _mark_validated_fallback(fallback_hypotheses), trace

        item["root_service"] = root
        item["affected_services"] = sorted(affected)
        item["validation"] = {
            "dominant_upstream_hint": dominant_hint,
            "allowed_services": sorted(allowed_services),
            "repaired": repaired,
        }
        if repaired:
            trace["repair_count"] += 1
            trace["repairs"].append(
                {
                    "evidence_ids": evidence_ids,
                    "root_service": root,
                    "affected_services": item["affected_services"],
                    "dominant_upstream_hint": dominant_hint,
                }
            )
        validated.append(item)

    trace["output_count_after_validation"] = len(validated)
    return sorted(validated, key=lambda item: item["score"], reverse=True), trace


def _mark_validated_fallback(
    fallback_hypotheses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            **item,
            "llm_fallback": True,
            "validation": {"fallback": True},
        }
        for item in fallback_hypotheses
    ]


def _clusters_from_groups(
    groups: dict[tuple[str, str], list[EvidenceObject]], *, reducer: str
) -> list[dict[str, Any]]:
    hypotheses: list[dict[str, Any]] = []
    for items in groups.values():
        items.sort(key=lambda item: item.start_minute)
        cluster: list[EvidenceObject] = []
        for item in items:
            if not cluster or item.start_minute <= max(ev.end_minute for ev in cluster) + 8:
                cluster.append(item)
                continue
            hypotheses.append(_hypothesis_from_evidence_group(cluster, reducer=reducer))
            cluster = [item]
        if cluster:
            hypotheses.append(_hypothesis_from_evidence_group(cluster, reducer=reducer))
    return sorted(hypotheses, key=lambda item: item["score"], reverse=True)


def _semantic_graph_groups(evidence: list[EvidenceObject]) -> list[list[EvidenceObject]]:
    candidates = [item for item in evidence if item.score >= 0.34]
    groups: list[list[EvidenceObject]] = []
    for item in sorted(candidates, key=lambda ev: ev.start_minute):
        target_group = None
        for group in groups:
            if _can_semantically_merge(item, group):
                target_group = group
                break
        if target_group is None:
            groups.append([item])
        else:
            target_group.append(item)
    return groups


def _can_semantically_merge(item: EvidenceObject, group: list[EvidenceObject]) -> bool:
    if item.region != group[0].region:
        return False
    overlaps = item.start_minute <= max(ev.end_minute for ev in group) + 12
    if not overlaps:
        return False
    services = {ev.service for ev in group}
    return any(_services_related(item.service, service) for service in services)


def _services_related(left: str, right: str) -> bool:
    if left == right:
        return True
    return right in _descendants(left) or left in _descendants(right)


def _descendants(service: str) -> set[str]:
    seen: set[str] = set()
    frontier = list(DEPENDENCIES.get(service, ()))
    while frontier:
        item = frontier.pop()
        if item in seen:
            continue
        seen.add(item)
        frontier.extend(DEPENDENCIES.get(item, ()))
    return seen


def _choose_root_service(items: list[EvidenceObject]) -> str:
    services = {item.service for item in items}
    hinted = [item.upstream_hint for item in items if item.upstream_hint in services]
    if hinted:
        return statistics.mode(hinted)
    external_hints = [item.upstream_hint for item in items if item.upstream_hint]
    if external_hints:
        return statistics.mode(external_hints)
    for service in services:
        descendants = _descendants(service)
        if len(services & descendants) >= max(1, len(services) - 1):
            return service
    return max(items, key=lambda item: item.score).service


def _hypothesis_from_evidence_group(
    items: list[EvidenceObject],
    *,
    reducer: str,
    include_root_hint_in_affected: bool = False,
) -> dict[str, Any]:
    root = _choose_root_service(items)
    affected_services = {item.service for item in items}
    if include_root_hint_in_affected and root in SERVICES:
        affected_services.add(root)
    affected = sorted(affected_services)
    signals = sorted({signal for item in items for signal in item.signals})
    return {
        "root_service": root,
        "region": items[0].region,
        "start_minute": min(item.start_minute for item in items),
        "end_minute": max(item.end_minute for item in items),
        "affected_services": affected,
        "signals": signals,
        "score": round(max(item.score for item in items), 4),
        "evidence_ids": [item.evidence_id for item in items],
        "summary": (
            f"{root} incident affecting {', '.join(affected)} "
            f"from {min(item.start_minute for item in items)} to "
            f"{max(item.end_minute for item in items)}."
        ),
        "reducer": reducer,
    }


def _matches(hypothesis: dict[str, Any], incident: MergeIncident) -> bool:
    if hypothesis["region"] != incident.region:
        return False
    if hypothesis["start_minute"] > incident.end_minute:
        return False
    if hypothesis["end_minute"] < incident.start_minute:
        return False
    predicted = set(hypothesis.get("affected_services", []))
    actual = set(incident.affected_services)
    jaccard = len(predicted & actual) / max(1, len(predicted | actual))
    root_ok = hypothesis.get("root_service") == incident.root_service
    return root_ok and jaccard >= 0.6


def score_merge_hypotheses(
    hypotheses: list[dict[str, Any]], incidents: list[MergeIncident]
) -> tuple[set[str], int, list[dict[str, Any]]]:
    matched_incidents: set[str] = set()
    matched_hypotheses = 0
    annotated: list[dict[str, Any]] = []
    for hypothesis in hypotheses:
        item = {**hypothesis, "matched_incident_id": None}
        for incident in incidents:
            if incident.incident_id in matched_incidents:
                continue
            if _matches(hypothesis, incident):
                matched_incidents.add(incident.incident_id)
                matched_hypotheses += 1
                item["matched_incident_id"] = incident.incident_id
                break
        annotated.append(item)
    return matched_incidents, matched_hypotheses, annotated


def _estimate_tokens_from_chars(chars: int) -> int:
    return max(1, (chars + 3) // 4) if chars else 0


def _cost_accounting_for_reducer(
    reducer: MergeReducer, *, reduce_ms: float
) -> dict[str, Any]:
    last_call = getattr(reducer, "last_call", None)
    if isinstance(last_call, dict) and last_call:
        return {
            "provider": "openai-compatible",
            "model": last_call.get("model"),
            "latency_ms": last_call.get("latency_ms", round(reduce_ms, 2)),
            "json_valid": bool(last_call.get("json_valid", False)),
            "schema_valid": last_call.get("schema_valid"),
            "fallback_count": int(last_call.get("fallback_count", 0)),
            "repair_count": int(last_call.get("repair_count", 0)),
            "split_count": int(last_call.get("split_count", 0)),
            "merge_count": int(last_call.get("merge_count", 0)),
            "accepted_edit_count": int(last_call.get("accepted_edit_count", 0)),
            "input_candidate_count": int(last_call.get("input_candidate_count", 0)),
            "input_pair_count": int(last_call.get("input_pair_count", 0)),
            "invalid_action_count": int(last_call.get("invalid_action_count", 0)),
            "validator_reject_reason": last_call.get("validator_reject_reason")
            or (
                last_call.get("validation_trace", {})
                if isinstance(last_call.get("validation_trace"), dict)
                else {}
            ).get("fallback_reason"),
            "retry_count": int(last_call.get("retry_count", 0)),
            "estimated_prompt_tokens": int(last_call.get("estimated_prompt_tokens", 0)),
            "estimated_response_tokens": int(
                last_call.get("estimated_response_tokens", 0)
            ),
            "estimated_total_tokens": int(last_call.get("estimated_total_tokens", 0)),
        }
    return {
        "provider": "offline",
        "model": None,
        "latency_ms": round(reduce_ms, 2),
        "json_valid": None,
        "estimated_prompt_tokens": 0,
        "estimated_response_tokens": 0,
        "estimated_total_tokens": 0,
    }


def _evidence_index_by_id(evidence: list[EvidenceObject]) -> dict[str, EvidenceObject]:
    return {item.evidence_id: item for item in evidence}


def _incident_evidence(
    evidence: list[EvidenceObject], incident: MergeIncident
) -> list[EvidenceObject]:
    return [item for item in evidence if item.source_incident_id == incident.incident_id]


def _overlaps_incident(hypothesis: dict[str, Any], incident: MergeIncident) -> bool:
    return (
        hypothesis.get("region") == incident.region
        and int(hypothesis.get("start_minute", 10**9)) <= incident.end_minute
        and int(hypothesis.get("end_minute", -1)) >= incident.start_minute
    )


def _jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / max(1, len(left | right))


def _classify_missed_incident(
    incident: MergeIncident,
    *,
    detected: list[dict[str, Any]],
    evidence: list[EvidenceObject],
) -> dict[str, Any]:
    source_evidence = _incident_evidence(evidence, incident)
    overlapping = [
        item for item in detected if _overlaps_incident(item, incident)
    ]
    result = {
        **incident_to_dict(incident),
        "failure_type": "unknown",
        "source_evidence_ids": [item.evidence_id for item in source_evidence],
        "overlapping_hypothesis_count": len(overlapping),
        "best_overlapping_hypothesis": None,
    }
    if not source_evidence:
        result["failure_type"] = "missing_map_evidence"
        return result
    if not overlapping:
        result["failure_type"] = "reducer_filtered_or_under_merged"
        return result

    actual = set(incident.affected_services)
    best = max(
        overlapping,
        key=lambda item: _jaccard(set(item.get("affected_services", [])), actual),
    )
    predicted = set(best.get("affected_services", []))
    root_ok = best.get("root_service") == incident.root_service
    affected_overlap = _jaccard(predicted, actual)
    best_summary = {
        "root_service": best.get("root_service"),
        "affected_services": sorted(predicted),
        "evidence_ids": best.get("evidence_ids", []),
        "affected_jaccard": round(affected_overlap, 4),
    }
    result["best_overlapping_hypothesis"] = best_summary
    if not root_ok:
        result["failure_type"] = "wrong_root"
    elif affected_overlap < 0.6:
        result["failure_type"] = "incomplete_affected_services"
    else:
        result["failure_type"] = "duplicate_or_matching_conflict"
    return result


def _classify_false_positive(
    hypothesis: dict[str, Any], evidence_by_id: dict[str, EvidenceObject]
) -> dict[str, Any]:
    evidence_ids = [str(item) for item in hypothesis.get("evidence_ids", [])]
    source_ids = sorted(
        {
            evidence_by_id[evidence_id].source_incident_id
            for evidence_id in evidence_ids
            if evidence_id in evidence_by_id
            and evidence_by_id[evidence_id].source_incident_id
        }
    )
    if not source_ids:
        failure_type = "distractor_evidence"
    elif len(source_ids) > 1:
        failure_type = "over_merged_incidents"
    else:
        failure_type = "unmatched_incident_fragment"
    return {
        **hypothesis,
        "failure_type": failure_type,
        "source_incident_ids": source_ids,
    }


def _evidence_coverage_metrics(
    *,
    evidence: list[EvidenceObject],
    incidents: list[MergeIncident],
    detected: list[dict[str, Any]],
) -> dict[str, float]:
    evidence_by_incident: dict[str, list[EvidenceObject]] = {
        incident.incident_id: _incident_evidence(evidence, incident)
        for incident in incidents
    }
    incident_count = len(incidents)
    evidence_covered = sum(1 for items in evidence_by_incident.values() if items)
    root_covered = 0
    source_evidence_ids: set[str] = set()
    for incident in incidents:
        items = evidence_by_incident[incident.incident_id]
        source_evidence_ids.update(item.evidence_id for item in items)
        if any(item.service == incident.root_service for item in items):
            root_covered += 1

    referenced_source_ids: set[str] = set()
    for hypothesis in detected:
        if not hypothesis.get("matched_incident_id"):
            continue
        referenced_source_ids.update(
            str(evidence_id)
            for evidence_id in hypothesis.get("evidence_ids", [])
            if str(evidence_id) in source_evidence_ids
        )

    return {
        "evidence_coverage": evidence_covered / incident_count
        if incident_count
        else 1.0,
        "root_evidence_coverage": root_covered / incident_count
        if incident_count
        else 1.0,
        "support_evidence_recall": len(referenced_source_ids)
        / max(1, len(source_evidence_ids)),
    }


def run_semantic_merge_workload(
    *,
    seed: int = 7,
    shard_count: int = 8,
    incident_count: int = 4,
    scenario: str = "cascade",
    reducer: str | MergeReducer | None = None,
) -> MergeReport:
    dataset = generate_semantic_merge_dataset(
        seed=seed,
        shard_count=shard_count,
        incident_count=incident_count,
        scenario=scenario,
    )
    merge_reducer = resolve_merge_reducer(reducer)
    started = time.perf_counter()
    hypotheses = merge_reducer.reduce(dataset.evidence)
    reduce_ms = (time.perf_counter() - started) * 1000
    matched_ids, matched_hypotheses, detected = score_merge_hypotheses(
        hypotheses, dataset.incidents
    )
    precision = matched_hypotheses / len(detected) if detected else 0.0
    recall = len(matched_ids) / len(dataset.incidents) if dataset.incidents else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    missed = [
        _classify_missed_incident(
            incident, detected=detected, evidence=dataset.evidence
        )
        for incident in dataset.incidents
        if incident.incident_id not in matched_ids
    ]
    evidence_by_id = _evidence_index_by_id(dataset.evidence)
    false_positives = [
        _classify_false_positive(item, evidence_by_id)
        for item in detected
        if item["matched_incident_id"] is None
    ]
    evidence_metrics = _evidence_coverage_metrics(
        evidence=dataset.evidence,
        incidents=dataset.incidents,
        detected=detected,
    )
    reducer_metadata = getattr(merge_reducer, "last_call", {})
    if not isinstance(reducer_metadata, dict):
        reducer_metadata = {}
    return MergeReport(
        reducer_name=merge_reducer.name,
        scenario=dataset.scenario,
        seed=seed,
        shard_count=shard_count,
        evidence_count=len(dataset.evidence),
        injected_incident_count=len(dataset.incidents),
        detected_incident_count=len(detected),
        matched_incident_count=len(matched_ids),
        precision=precision,
        recall=recall,
        f1=f1,
        evidence_coverage=evidence_metrics["evidence_coverage"],
        root_evidence_coverage=evidence_metrics["root_evidence_coverage"],
        support_evidence_recall=evidence_metrics["support_evidence_recall"],
        reduce_duration_ms=reduce_ms,
        injected_incidents=[incident_to_dict(incident) for incident in dataset.incidents],
        detected_incidents=detected,
        missed_incidents=missed,
        false_positive_incidents=false_positives,
        reducer_trace={
            "reducer_name": merge_reducer.name,
            "input_evidence_count": len(dataset.evidence),
            "output_hypothesis_count": len(hypotheses),
            "matched_hypothesis_count": matched_hypotheses,
            "reduce_duration_ms": round(reduce_ms, 2),
            "metadata": reducer_metadata,
        },
        cost_accounting=_cost_accounting_for_reducer(
            merge_reducer, reduce_ms=reduce_ms
        ),
        workflow_trace={
            "operators": [
                "Shard",
                "MapEvidence",
                "Normalize",
                "GroupEvidence",
                "SemanticReduce",
                "ReportTrace",
            ],
            "dependency_graph": DEPENDENCIES,
            "evidence": [evidence_to_dict(item) for item in dataset.evidence],
        },
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Semantic MapReduce hard semantic-merge workload."
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--shards", type=int, default=8)
    parser.add_argument("--incidents", type=int, default=4)
    parser.add_argument("--scenario", choices=SCENARIOS, default="cascade")
    parser.add_argument(
        "--reducer",
        choices=(
            "map-only",
            "service-local",
            "window-aggregate",
            "semantic-graph",
            "hybrid-hint",
            "llm-stub",
            "llm-hybrid",
            "llm-hybrid-validated",
            "llm-openai",
        ),
        default="semantic-graph",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = run_semantic_merge_workload(
        seed=args.seed,
        shard_count=args.shards,
        incident_count=args.incidents,
        scenario=args.scenario,
        reducer=args.reducer,
    )
    text = json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
