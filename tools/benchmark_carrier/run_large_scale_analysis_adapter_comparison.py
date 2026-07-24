#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from pathlib import Path
from typing import Any, TypedDict

from sage.workloads.large_scale_analysis import (
    ShardSummary,
    WorkloadReport,
    generate_synthetic_events,
    incident_to_dict,
    map_shard,
    match_detections,
    operator_durations,
    partition_events,
    resolve_incident_reducer,
    run_large_scale_analysis_workload,
    score_detections,
)

DEFAULT_SIZES = "50000:16:12,100000:32:16"
DEFAULT_SEEDS = "7,11,13"
DEFAULT_ADAPTERS = "sage-local,ray-local,langgraph-local,llamaindex-docstore"


def _parse_sizes(raw_value: str) -> list[tuple[int, int, int]]:
    sizes: list[tuple[int, int, int]] = []
    for item in raw_value.split(","):
        fields = item.strip().split(":")
        if len(fields) != 3:
            raise ValueError(
                f"Invalid size spec {item!r}; expected events:shards:top_k."
            )
        sizes.append(tuple(int(field) for field in fields))
    return sizes


def _parse_csv(raw_value: str) -> list[str]:
    values = [item.strip() for item in raw_value.split(",") if item.strip()]
    if not values:
        raise ValueError("At least one value is required.")
    return values


def _report_from_parts(
    *,
    adapter: str,
    event_count: int,
    shard_count: int,
    seed: int,
    top_k: int,
    map_policy: str,
    reducer: str,
    dataset: Any,
    summaries: list[ShardSummary],
    map_duration_ms: float,
    reduce_duration_ms: float,
    total_duration_ms: float,
) -> WorkloadReport:
    incident_reducer = resolve_incident_reducer(reducer)
    detections = incident_reducer.reduce(summaries)[:top_k]
    matched, precision, recall, f1, coverage = score_detections(
        detections, dataset.incidents
    )
    matched_incident_ids, _ = match_detections(detections, dataset.incidents)
    missed_incidents = [
        incident_to_dict(incident)
        for incident in dataset.incidents
        if incident.incident_id not in matched_incident_ids
    ]
    report = WorkloadReport(
        event_count=event_count,
        shard_count=shard_count,
        seed=seed,
        top_k=top_k,
        map_policy=map_policy,
        reducer_name=incident_reducer.name,
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
        injected_incidents=[incident_to_dict(incident) for incident in dataset.incidents],
        missed_incidents=missed_incidents,
        detected_incidents=detections,
        operator_duration_ms=operator_durations(
            map_duration_ms=map_duration_ms,
            reduce_duration_ms=reduce_duration_ms,
        ),
    )
    for detection in report.detected_incidents:
        detection.setdefault("adapter", adapter)
    return report


def run_sage_local(
    *,
    event_count: int,
    shard_count: int,
    seed: int,
    top_k: int,
    map_policy: str,
    reducer: str,
) -> WorkloadReport:
    return run_large_scale_analysis_workload(
        event_count=event_count,
        shard_count=shard_count,
        seed=seed,
        top_k=top_k,
        reducer=reducer,
        map_policy=map_policy,
    )


def run_ray_local(
    *,
    event_count: int,
    shard_count: int,
    seed: int,
    top_k: int,
    map_policy: str,
    reducer: str,
) -> WorkloadReport:
    try:
        import ray
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(f"ray adapter unavailable: {exc}") from exc

    @ray.remote
    def _remote_map(shard_id: int, events: list[Any], policy: str) -> ShardSummary:
        return map_shard(shard_id, events, map_policy=policy)

    started = time.perf_counter()
    dataset = generate_synthetic_events(event_count=event_count, seed=seed)
    shards = partition_events(dataset.events, shard_count)

    if not ray.is_initialized():
        ray.init(
            ignore_reinit_error=True,
            include_dashboard=False,
            logging_level="ERROR",
            num_cpus=min(8, max(1, shard_count)),
        )

    map_started = time.perf_counter()
    summaries = ray.get(
        [
            _remote_map.remote(shard_id, shard, map_policy)
            for shard_id, shard in enumerate(shards)
        ]
    )
    map_duration_ms = (time.perf_counter() - map_started) * 1000

    reduce_started = time.perf_counter()
    report = _report_from_parts(
        adapter="ray-local",
        event_count=event_count,
        shard_count=shard_count,
        seed=seed,
        top_k=top_k,
        map_policy=map_policy,
        reducer=reducer,
        dataset=dataset,
        summaries=summaries,
        map_duration_ms=map_duration_ms,
        reduce_duration_ms=0.0,
        total_duration_ms=0.0,
    )
    report.reduce_duration_ms = (time.perf_counter() - reduce_started) * 1000
    report.total_duration_ms = (time.perf_counter() - started) * 1000
    report.throughput_events_per_s = event_count / max(
        report.total_duration_ms / 1000, 0.001
    )
    report.operator_duration_ms = operator_durations(
        map_duration_ms=map_duration_ms,
        reduce_duration_ms=report.reduce_duration_ms,
    )
    return report


class _GraphState(TypedDict, total=False):
    event_count: int
    shard_count: int
    seed: int
    top_k: int
    map_policy: str
    reducer: str
    dataset: Any
    shards: list[list[Any]]
    summaries: list[ShardSummary]
    map_duration_ms: float
    reduce_duration_ms: float
    started: float
    report: WorkloadReport


def run_langgraph_local(
    *,
    event_count: int,
    shard_count: int,
    seed: int,
    top_k: int,
    map_policy: str,
    reducer: str,
) -> WorkloadReport:
    try:
        from langgraph.graph import END, StateGraph
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(f"langgraph adapter unavailable: {exc}") from exc

    def generate_node(state: _GraphState) -> dict[str, Any]:
        dataset = generate_synthetic_events(
            event_count=state["event_count"], seed=state["seed"]
        )
        return {
            "dataset": dataset,
            "shards": partition_events(dataset.events, state["shard_count"]),
        }

    def map_node(state: _GraphState) -> dict[str, Any]:
        map_started = time.perf_counter()
        summaries = [
            map_shard(shard_id, shard, map_policy=state["map_policy"])
            for shard_id, shard in enumerate(state["shards"])
        ]
        return {
            "summaries": summaries,
            "map_duration_ms": (time.perf_counter() - map_started) * 1000,
        }

    def reduce_node(state: _GraphState) -> dict[str, Any]:
        reduce_started = time.perf_counter()
        report = _report_from_parts(
            adapter="langgraph-local",
            event_count=state["event_count"],
            shard_count=state["shard_count"],
            seed=state["seed"],
            top_k=state["top_k"],
            map_policy=state["map_policy"],
            reducer=state["reducer"],
            dataset=state["dataset"],
            summaries=state["summaries"],
            map_duration_ms=state["map_duration_ms"],
            reduce_duration_ms=0.0,
            total_duration_ms=0.0,
        )
        report.reduce_duration_ms = (time.perf_counter() - reduce_started) * 1000
        report.total_duration_ms = (time.perf_counter() - state["started"]) * 1000
        report.throughput_events_per_s = state["event_count"] / max(
            report.total_duration_ms / 1000, 0.001
        )
        report.operator_duration_ms = operator_durations(
            map_duration_ms=state["map_duration_ms"],
            reduce_duration_ms=report.reduce_duration_ms,
        )
        return {"report": report}

    graph = StateGraph(_GraphState)
    graph.add_node("generate", generate_node)
    graph.add_node("map", map_node)
    graph.add_node("reduce", reduce_node)
    graph.set_entry_point("generate")
    graph.add_edge("generate", "map")
    graph.add_edge("map", "reduce")
    graph.add_edge("reduce", END)
    compiled = graph.compile()

    result = compiled.invoke(
        {
            "event_count": event_count,
            "shard_count": shard_count,
            "seed": seed,
            "top_k": top_k,
            "map_policy": map_policy,
            "reducer": reducer,
            "started": time.perf_counter(),
        }
    )
    return result["report"]


def run_llamaindex_docstore(
    *,
    event_count: int,
    shard_count: int,
    seed: int,
    top_k: int,
    map_policy: str,
    reducer: str,
) -> WorkloadReport:
    try:
        from llama_index.core.schema import Document
        from llama_index.core.storage.docstore import SimpleDocumentStore
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(f"llama-index-core adapter unavailable: {exc}") from exc

    started = time.perf_counter()
    dataset = generate_synthetic_events(event_count=event_count, seed=seed)
    shards = partition_events(dataset.events, shard_count)

    map_started = time.perf_counter()
    summaries = [
        map_shard(shard_id, shard, map_policy=map_policy)
        for shard_id, shard in enumerate(shards)
    ]
    docstore = SimpleDocumentStore()
    documents = []
    for summary in summaries:
        for idx, candidate in enumerate(summary.candidates):
            documents.append(
                Document(
                    text=json.dumps(candidate, sort_keys=True),
                    id_=f"shard-{summary.shard_id}-candidate-{idx}",
                    metadata={
                        "service": candidate["service"],
                        "region": candidate["region"],
                        "window": candidate["window"],
                        "score": candidate["score"],
                    },
                )
            )
    if documents:
        docstore.add_documents(documents)
    map_duration_ms = (time.perf_counter() - map_started) * 1000

    reduce_started = time.perf_counter()
    report = _report_from_parts(
        adapter="llamaindex-docstore",
        event_count=event_count,
        shard_count=shard_count,
        seed=seed,
        top_k=top_k,
        map_policy=map_policy,
        reducer=reducer,
        dataset=dataset,
        summaries=summaries,
        map_duration_ms=map_duration_ms,
        reduce_duration_ms=0.0,
        total_duration_ms=0.0,
    )
    report.reduce_duration_ms = (time.perf_counter() - reduce_started) * 1000
    report.total_duration_ms = (time.perf_counter() - started) * 1000
    report.throughput_events_per_s = event_count / max(
        report.total_duration_ms / 1000, 0.001
    )
    report.operator_duration_ms = operator_durations(
        map_duration_ms=map_duration_ms,
        reduce_duration_ms=report.reduce_duration_ms,
    )
    return report


ADAPTERS = {
    "sage-local": run_sage_local,
    "ray-local": run_ray_local,
    "langgraph-local": run_langgraph_local,
    "llamaindex-docstore": run_llamaindex_docstore,
}


def _mean(values: list[float]) -> float:
    return round(statistics.fmean(values), 4)


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_adapter: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("status") == "ok":
            by_adapter.setdefault(row["adapter"], []).append(row)

    return {
        adapter: {
            metric: {
                "mean": _mean([float(row[metric]) for row in adapter_rows]),
                "min": min(float(row[metric]) for row in adapter_rows),
                "max": max(float(row[metric]) for row in adapter_rows),
            }
            for metric in (
                "precision",
                "recall",
                "f1",
                "throughput_events_per_s",
                "map_duration_ms",
                "reduce_duration_ms",
                "total_duration_ms",
            )
        }
        for adapter, adapter_rows in sorted(by_adapter.items())
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare optional orchestration adapters for the large-scale "
            "analysis workload."
        )
    )
    parser.add_argument("--sizes", default=DEFAULT_SIZES)
    parser.add_argument("--seeds", default=DEFAULT_SEEDS)
    parser.add_argument("--adapters", default=DEFAULT_ADAPTERS)
    parser.add_argument("--reducer", default="deterministic")
    parser.add_argument(
        "--map-policy",
        choices=("tail-aware", "mean-only"),
        default="tail-aware",
    )
    parser.add_argument(
        "--output-root",
        default=".sage/benchmarks/large_scale_analysis_adapters",
    )
    parser.add_argument("--run-id")
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Record unavailable adapters as skipped instead of failing the run.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    sizes = _parse_sizes(args.sizes)
    seeds = [int(seed) for seed in _parse_csv(args.seeds)]
    adapters = _parse_csv(args.adapters)
    run_id = args.run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    outdir = Path(args.output_root) / run_id
    outdir.mkdir(parents=True, exist_ok=True)

    if "ray-local" in adapters:
        try:
            import ray

            if not ray.is_initialized():
                max_shards = max(shard_count for _, shard_count, _ in sizes)
                ray.init(
                    ignore_reinit_error=True,
                    include_dashboard=False,
                    logging_level="ERROR",
                    num_cpus=min(8, max(1, max_shards)),
                )
        except Exception:
            if not args.continue_on_error:
                raise

    rows: list[dict[str, Any]] = []
    for events, shards, top_k in sizes:
        for seed in seeds:
            for adapter_name in adapters:
                if adapter_name not in ADAPTERS:
                    raise ValueError(f"Unknown adapter {adapter_name!r}")
                started = time.perf_counter()
                try:
                    report = ADAPTERS[adapter_name](
                        event_count=events,
                        shard_count=shards,
                        seed=seed,
                        top_k=top_k,
                        map_policy=args.map_policy,
                        reducer=args.reducer,
                    )
                    payload = report.to_dict()
                    payload["adapter"] = adapter_name
                    payload["status"] = "ok"
                    error = ""
                except Exception as exc:
                    if not args.continue_on_error:
                        raise
                    payload = {
                        "adapter": adapter_name,
                        "event_count": events,
                        "shard_count": shards,
                        "seed": seed,
                        "top_k": top_k,
                        "map_policy": args.map_policy,
                        "reducer_name": args.reducer,
                        "status": "skipped",
                    }
                    error = f"{type(exc).__name__}: {exc}"
                    payload["error"] = error

                payload["wall_duration_ms"] = round(
                    (time.perf_counter() - started) * 1000,
                    2,
                )
                artifact_name = (
                    f"events{events}_shards{shards}_seed{seed}_{adapter_name}.json"
                    .replace("-", "_")
                )
                (outdir / artifact_name).write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                row = {
                    "events": events,
                    "shards": shards,
                    "top_k": top_k,
                    "seed": seed,
                    "map_policy": payload.get("map_policy", args.map_policy),
                    "adapter": adapter_name,
                    "reducer": payload.get("reducer_name", args.reducer),
                    "status": payload["status"],
                    "precision": payload.get("precision", ""),
                    "recall": payload.get("recall", ""),
                    "f1": payload.get("f1", ""),
                    "throughput_events_per_s": payload.get(
                        "throughput_events_per_s", ""
                    ),
                    "map_duration_ms": payload.get("map_duration_ms", ""),
                    "reduce_duration_ms": payload.get("reduce_duration_ms", ""),
                    "total_duration_ms": payload.get("total_duration_ms", ""),
                    "wall_duration_ms": payload["wall_duration_ms"],
                    "detected_incident_count": payload.get(
                        "detected_incident_count", ""
                    ),
                    "matched_incident_count": payload.get("matched_incident_count", ""),
                    "error": error,
                }
                rows.append(row)
                print(
                    f"done events={events} shards={shards} seed={seed} "
                    f"adapter={adapter_name} status={payload['status']} "
                    f"f1={payload.get('f1', '')}"
                )

    with (outdir / "summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    (outdir / "summary.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (outdir / "aggregate.json").write_text(
        json.dumps(_aggregate(rows), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"RESULT_DIR={outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
