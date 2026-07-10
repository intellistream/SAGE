#!/usr/bin/env python3
"""Measure MapEvidence coverage before reducer comparisons.

This sweep answers a narrower question than the reducer matrix: for each
workload scale and MapEvidence policy, how many injected incidents are even
present in the shard-level evidence objects? Reducer quality comparisons are
only meaningful once this coverage is high enough.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from sage.workloads.large_scale_analysis import (
    InjectedIncident,
    generate_synthetic_events,
    map_shard,
    partition_events,
    resolve_incident_reducer,
    score_detections,
)


DEFAULT_SIZES = "2000:4:8,10000:8:12,50000:16:12,100000:32:16"
DEFAULT_SEEDS = "7,11,13"
DEFAULT_MAP_POLICIES = "tail-aware,baseline-aware"
DEFAULT_REDUCERS = "map-only,window-aggregate,deterministic,llm-stub"


def _parse_sizes(raw_value: str) -> list[tuple[int, int, int]]:
    sizes: list[tuple[int, int, int]] = []
    for item in raw_value.split(","):
        fields = item.strip().split(":")
        if len(fields) != 3:
            raise ValueError(
                f"Invalid size spec {item!r}; expected events:shards:top_k."
            )
        sizes.append(tuple(int(field) for field in fields))
    if not sizes:
        raise ValueError("At least one size spec is required.")
    return sizes


def _parse_csv_list(raw_value: str) -> list[str]:
    values = [item.strip() for item in raw_value.split(",") if item.strip()]
    if not values:
        raise ValueError("At least one value is required.")
    return values


def _git_output(args: list[str], *, cwd: Path | None = None) -> str:
    try:
        command = ["git"]
        if cwd is not None:
            command.extend(["-C", str(cwd)])
        command.extend(args)
        return subprocess.check_output(
            command, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _submodule_info(path: str) -> dict[str, Any]:
    module_path = Path(path)
    if not module_path.exists():
        return {"path": path, "present": False}
    return {
        "path": path,
        "present": True,
        "commit": _git_output(["rev-parse", "HEAD"], cwd=module_path),
        "branch": _git_output(["rev-parse", "--abbrev-ref", "HEAD"], cwd=module_path),
        "dirty": bool(_git_output(["status", "--porcelain"], cwd=module_path)),
    }


def _overlaps(candidate: dict[str, Any], incident: InjectedIncident) -> bool:
    return (
        candidate["service"] == incident.service
        and candidate["region"] == incident.region
        and candidate["start_minute"] <= incident.end_minute
        and candidate["end_minute"] >= incident.start_minute
    )


def _coverage_for_config(
    *,
    events: int,
    shards: int,
    seed: int,
    map_policy: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    dataset = generate_synthetic_events(event_count=events, seed=seed)
    shard_events = partition_events(dataset.events, shards)
    summaries = [
        map_shard(shard_id, shard, map_policy=map_policy)
        for shard_id, shard in enumerate(shard_events)
    ]
    candidates = [candidate for summary in summaries for candidate in summary.candidates]
    covered_incidents: list[dict[str, Any]] = []
    missed_incidents: list[dict[str, Any]] = []
    for incident in dataset.incidents:
        matches = [candidate for candidate in candidates if _overlaps(candidate, incident)]
        incident_row = {
            "incident_id": incident.incident_id,
            "service": incident.service,
            "region": incident.region,
            "kind": incident.kind,
            "start_minute": incident.start_minute,
            "end_minute": incident.end_minute,
            "overlapping_candidate_count": len(matches),
            "best_candidate_scores": sorted(
                (float(item["score"]) for item in matches), reverse=True
            )[:3],
        }
        if matches:
            covered_incidents.append(incident_row)
        else:
            missed_incidents.append(incident_row)

    duration_ms = (time.perf_counter() - started) * 1000
    return {
        "events": events,
        "shards": shards,
        "seed": seed,
        "map_policy": map_policy,
        "injected_incident_count": len(dataset.incidents),
        "candidate_count": len(candidates),
        "covered_incident_count": len(covered_incidents),
        "map_coverage": round(
            len(covered_incidents) / max(1, len(dataset.incidents)), 4
        ),
        "map_duration_ms": round(sum(summary.duration_ms for summary in summaries), 2),
        "total_duration_ms": round(duration_ms, 2),
        "covered_incidents": covered_incidents,
        "missed_incidents": missed_incidents,
        "summaries": summaries,
        "incidents": dataset.incidents,
        "shard_candidate_counts": [
            {
                "shard_id": summary.shard_id,
                "event_count": summary.event_count,
                "candidate_count": summary.candidate_count,
            }
            for summary in summaries
        ],
    }


def _mean(values: list[float]) -> float:
    return round(statistics.fmean(values), 4)


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = f"{row['events']}:{row['shards']}:{row['top_k']}:{row['map_policy']}"
        groups.setdefault(key, []).append(row)

    return {
        key: {
            "map_coverage": {
                "mean": _mean([float(row["map_coverage"]) for row in group]),
                "min": min(float(row["map_coverage"]) for row in group),
                "max": max(float(row["map_coverage"]) for row in group),
            },
            "candidate_count": {
                "mean": _mean([float(row["candidate_count"]) for row in group]),
                "min": min(int(row["candidate_count"]) for row in group),
                "max": max(int(row["candidate_count"]) for row in group),
            },
            "deterministic_f1": {
                "mean": _mean([float(row["deterministic_f1"]) for row in group]),
                "min": min(float(row["deterministic_f1"]) for row in group),
                "max": max(float(row["deterministic_f1"]) for row in group),
            },
            "best_reducer": max(
                group,
                key=lambda row: (
                    float(row["best_reducer_f1"]),
                    float(row["map_coverage"]),
                ),
            )["best_reducer"],
        }
        for key, group in sorted(groups.items())
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sweep MapEvidence coverage for large-scale analysis."
    )
    parser.add_argument("--sizes", default=DEFAULT_SIZES)
    parser.add_argument("--seeds", default=DEFAULT_SEEDS)
    parser.add_argument("--map-policies", default=DEFAULT_MAP_POLICIES)
    parser.add_argument("--reducers", default=DEFAULT_REDUCERS)
    parser.add_argument(
        "--output-root",
        default=".sage/benchmarks/large_scale_analysis_coverage",
    )
    parser.add_argument("--run-id")
    return parser.parse_args()


def _write_manifest(
    outdir: Path,
    *,
    args: argparse.Namespace,
    sizes: list[tuple[int, int, int]],
    seeds: list[int],
    map_policies: list[str],
    reducers: list[str],
) -> None:
    manifest = {
        "run_id": outdir.name,
        "created_unix": int(time.time()),
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "command_args": vars(args),
        "sizes": [
            {"events": events, "shards": shards, "top_k": top_k}
            for events, shards, top_k in sizes
        ],
        "seeds": seeds,
        "map_policies": map_policies,
        "reducers": reducers,
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
        },
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", ""),
        "git": {
            "commit": _git_output(["rev-parse", "HEAD"]),
            "branch": _git_output(["rev-parse", "--abbrev-ref", "HEAD"]),
            "dirty": bool(_git_output(["status", "--porcelain"])),
        },
        "evidence_label": "simulation/model",
        "workload_source": {
            "kind": "repo-local",
            "path": "src/sage/workloads/large_scale_analysis.py",
            "suite": "large_scale_analysis_coverage",
        },
        "shared_workload_submodule": _submodule_info(
            "third_party/llm-serving-workloads"
        ),
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = _parse_args()
    sizes = _parse_sizes(args.sizes)
    seeds = [int(value) for value in _parse_csv_list(args.seeds)]
    map_policies = _parse_csv_list(args.map_policies)
    reducers = _parse_csv_list(args.reducers)

    run_id = args.run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    outdir = Path(args.output_root) / run_id
    outdir.mkdir(parents=True, exist_ok=True)
    _write_manifest(
        outdir,
        args=args,
        sizes=sizes,
        seeds=seeds,
        map_policies=map_policies,
        reducers=reducers,
    )

    rows: list[dict[str, Any]] = []
    for events, shards, top_k in sizes:
        for seed in seeds:
            for map_policy in map_policies:
                coverage = _coverage_for_config(
                    events=events,
                    shards=shards,
                    seed=seed,
                    map_policy=map_policy,
                )
                reducer_scores: dict[str, dict[str, Any]] = {}
                for reducer in reducers:
                    reducer_impl = resolve_incident_reducer(reducer)
                    detections = reducer_impl.reduce(coverage["summaries"])[:top_k]
                    matched, precision, recall, f1, _ = score_detections(
                        detections, coverage["incidents"]
                    )
                    reducer_scores[reducer] = {
                        "precision": round(precision, 4),
                        "recall": round(recall, 4),
                        "f1": round(f1, 4),
                        "detected_incident_count": len(detections),
                        "matched_incident_count": matched,
                    }

                best_reducer, best_scores = max(
                    reducer_scores.items(),
                    key=lambda item: (
                        float(item[1]["f1"]),
                        float(item[1]["recall"]),
                        float(item[1]["precision"]),
                    ),
                )
                row = {
                    "events": events,
                    "shards": shards,
                    "top_k": top_k,
                    "seed": seed,
                    "map_policy": map_policy,
                    "candidate_count": coverage["candidate_count"],
                    "covered_incident_count": coverage["covered_incident_count"],
                    "injected_incident_count": coverage["injected_incident_count"],
                    "map_coverage": coverage["map_coverage"],
                    "map_duration_ms": coverage["map_duration_ms"],
                    "coverage_total_duration_ms": coverage["total_duration_ms"],
                    "deterministic_precision": reducer_scores["deterministic"][
                        "precision"
                    ],
                    "deterministic_recall": reducer_scores["deterministic"]["recall"],
                    "deterministic_f1": reducer_scores["deterministic"]["f1"],
                    "best_reducer": best_reducer,
                    "best_reducer_f1": best_scores["f1"],
                    "best_reducer_recall": best_scores["recall"],
                    "missed_incident_ids": ";".join(
                        item["incident_id"] for item in coverage["missed_incidents"]
                    ),
                }
                rows.append(row)

                detail_name = (
                    f"coverage_events{events}_shards{shards}_seed{seed}_"
                    f"{map_policy}.json"
                ).replace("-", "_")
                (outdir / detail_name).write_text(
                    json.dumps(
                        {
                            **{
                                key: value
                                for key, value in coverage.items()
                                if key not in {"summaries", "incidents"}
                            },
                            "top_k": top_k,
                            "reducer_scores": reducer_scores,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                print(
                    f"done events={events} shards={shards} seed={seed} "
                    f"map_policy={map_policy} map_coverage={row['map_coverage']} "
                    f"candidates={row['candidate_count']} best={best_reducer}:"
                    f"{best_scores['f1']}"
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
