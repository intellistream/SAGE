#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from pathlib import Path
from typing import Any

from sage.workloads.large_scale_analysis import run_large_scale_analysis_workload

DEFAULT_SIZES = "50000:16:12,100000:32:16"
DEFAULT_SEEDS = "7,11,13"
DEFAULT_REDUCERS = "map-only,window-aggregate,deterministic,llm-stub"
DEFAULT_MAP_POLICIES = "tail-aware"


def _parse_sizes(raw_value: str) -> list[tuple[int, int, int]]:
    sizes: list[tuple[int, int, int]] = []
    for item in raw_value.split(","):
        fields = item.strip().split(":")
        if len(fields) != 3:
            raise ValueError(
                f"Invalid size spec {item!r}; expected events:shards:top_k."
            )
        events, shards, top_k = (int(field) for field in fields)
        sizes.append((events, shards, top_k))
    if not sizes:
        raise ValueError("At least one size spec is required.")
    return sizes


def _parse_csv_list(raw_value: str) -> list[str]:
    values = [item.strip() for item in raw_value.split(",") if item.strip()]
    if not values:
        raise ValueError("At least one value is required.")
    return values


def _mean(values: list[float]) -> float:
    return round(statistics.fmean(values), 4)


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_reducer: dict[str, list[dict[str, Any]]] = {}
    by_policy_reducer: dict[str, list[dict[str, Any]]] = {}
    by_size: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_reducer.setdefault(str(row["reducer"]), []).append(row)
        map_policy = str(row.get("map_policy", "tail-aware"))
        by_policy_reducer.setdefault(f"{map_policy}/{row['reducer']}", []).append(row)
        size_key = f"{row['events']}:{row['shards']}:{row['top_k']}:{map_policy}"
        by_size.setdefault(size_key, []).append(row)

    def summarize(groups: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        return {
            name: {
                metric: {
                    "mean": _mean([float(row[metric]) for row in group_rows]),
                    "min": min(float(row[metric]) for row in group_rows),
                    "max": max(float(row[metric]) for row in group_rows),
                }
                for metric in ("precision", "recall", "f1")
            }
            for name, group_rows in sorted(groups.items())
        }

    reducer_summary = summarize(by_reducer)
    policy_reducer_summary = summarize(by_policy_reducer)

    size_summary = {}
    for size_key, size_rows in sorted(by_size.items()):
        deterministic_rows = [
            row for row in size_rows if row["reducer"] == "deterministic"
        ]
        if not deterministic_rows:
            continue
        size_summary[size_key] = {
            metric: {
                "mean": _mean([float(row[metric]) for row in deterministic_rows]),
                "values": [float(row[metric]) for row in deterministic_rows],
            }
            for metric in ("precision", "recall", "f1")
        }

    return {
        "row_count": len(rows),
        "by_reducer": reducer_summary,
        "by_map_policy_reducer": policy_reducer_summary,
        "deterministic_by_size": size_summary,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a matrix of SAGE large-scale analysis workload experiments."
    )
    parser.add_argument(
        "--sizes",
        default=DEFAULT_SIZES,
        help=(
            "Comma-separated events:shards:top_k specs. "
            f"Default: {DEFAULT_SIZES}"
        ),
    )
    parser.add_argument(
        "--seeds",
        default=DEFAULT_SEEDS,
        help=f"Comma-separated random seeds. Default: {DEFAULT_SEEDS}",
    )
    parser.add_argument(
        "--reducers",
        default=DEFAULT_REDUCERS,
        help=f"Comma-separated reducer names. Default: {DEFAULT_REDUCERS}",
    )
    parser.add_argument(
        "--map-policies",
        default=DEFAULT_MAP_POLICIES,
        help=(
            "Comma-separated MapEvidence policies. "
            f"Default: {DEFAULT_MAP_POLICIES}"
        ),
    )
    parser.add_argument(
        "--output-root",
        default=".sage/benchmarks/large_scale_analysis",
        help="Directory under which timestamped run artifacts are written.",
    )
    parser.add_argument(
        "--run-id",
        help="Optional run id. Defaults to a UTC timestamp.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    sizes = _parse_sizes(args.sizes)
    seeds = [int(value) for value in _parse_csv_list(args.seeds)]
    reducers = _parse_csv_list(args.reducers)
    map_policies = _parse_csv_list(args.map_policies)

    run_id = args.run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    outdir = Path(args.output_root) / run_id
    outdir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for events, shards, top_k in sizes:
        for seed in seeds:
            for map_policy in map_policies:
                for reducer in reducers:
                    started = time.perf_counter()
                    report = run_large_scale_analysis_workload(
                        event_count=events,
                        shard_count=shards,
                        seed=seed,
                        top_k=top_k,
                        reducer=reducer,
                        map_policy=map_policy,
                    )
                    payload = report.to_dict()
                    payload["wall_duration_ms"] = round(
                        (time.perf_counter() - started) * 1000,
                        2,
                    )
                    artifact_name = (
                        f"events{events}_shards{shards}_seed{seed}_"
                        f"{map_policy}_{reducer}.json"
                    ).replace("-", "_")
                    (outdir / artifact_name).write_text(
                        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    row = {
                        "events": events,
                        "shards": shards,
                        "top_k": top_k,
                        "seed": seed,
                        "map_policy": map_policy,
                        "reducer": reducer,
                        "precision": payload["precision"],
                        "recall": payload["recall"],
                        "f1": payload["f1"],
                        "throughput_events_per_s": payload["throughput_events_per_s"],
                        "map_duration_ms": payload["map_duration_ms"],
                        "reduce_duration_ms": payload["reduce_duration_ms"],
                        "total_duration_ms": payload["total_duration_ms"],
                        "detected_incident_count": payload["detected_incident_count"],
                        "matched_incident_count": payload["matched_incident_count"],
                        "missed_incident_ids": ";".join(
                            item["incident_id"] for item in payload["missed_incidents"]
                        ),
                    }
                    rows.append(row)
                    print(
                        f"done events={events} shards={shards} seed={seed} "
                        f"map_policy={map_policy} reducer={reducer} "
                        f"precision={payload['precision']} recall={payload['recall']} "
                        f"f1={payload['f1']}"
                    )

    summary_path = outdir / "summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
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
