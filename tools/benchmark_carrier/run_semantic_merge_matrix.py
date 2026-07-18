#!/usr/bin/env python3
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

from sage.workloads.semantic_merge_analysis import SCENARIOS, run_semantic_merge_workload

DEFAULT_SEEDS = "7,11,13,17,19,23,29,31,37,41"
DEFAULT_REDUCERS = "map-only,service-local,window-aggregate,semantic-graph,hybrid-hint,llm-stub"
DEFAULT_SCENARIOS = ",".join(SCENARIOS)


def _parse_csv(raw: str) -> list[str]:
    values = [item.strip() for item in raw.split(",") if item.strip()]
    if not values:
        raise ValueError("expected at least one comma-separated value")
    return values


def _mean(values: list[float]) -> float:
    return round(statistics.fmean(values), 4)


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_reducer: dict[str, list[dict[str, Any]]] = {}
    by_scenario_reducer: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_reducer.setdefault(str(row["reducer"]), []).append(row)
        key = f"{row['scenario']}:{row['reducer']}"
        by_scenario_reducer.setdefault(key, []).append(row)
    metrics = (
        "precision",
        "recall",
        "f1",
        "evidence_coverage",
        "root_evidence_coverage",
        "support_evidence_recall",
        "detected_incident_count",
        "reduce_duration_ms",
    )
    return {
        "row_count": len(rows),
        "by_reducer": {
            name: {
                metric: {
                    "mean": _mean([float(row[metric]) for row in group]),
                    "min": min(float(row[metric]) for row in group),
                    "max": max(float(row[metric]) for row in group),
                }
                for metric in metrics
            }
            for name, group in sorted(by_reducer.items())
        },
        "by_scenario_reducer": {
            name: {
                metric: {
                    "mean": _mean([float(row[metric]) for row in group]),
                    "min": min(float(row[metric]) for row in group),
                    "max": max(float(row[metric]) for row in group),
                }
                for metric in metrics
            }
            for name, group in sorted(by_scenario_reducer.items())
        },
    }


def _scenario_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((str(row["scenario"]), str(row["reducer"])), []).append(row)
    summary: list[dict[str, Any]] = []
    for (scenario, reducer), group in sorted(grouped.items()):
        summary.append(
            {
                "scenario": scenario,
                "reducer": reducer,
                "precision_mean": _mean([float(row["precision"]) for row in group]),
                "recall_mean": _mean([float(row["recall"]) for row in group]),
                "f1_mean": _mean([float(row["f1"]) for row in group]),
                "evidence_coverage_mean": _mean([float(row["evidence_coverage"]) for row in group]),
                "root_evidence_coverage_mean": _mean(
                    [float(row["root_evidence_coverage"]) for row in group]
                ),
                "support_evidence_recall_mean": _mean(
                    [float(row["support_evidence_recall"]) for row in group]
                ),
                "detected_incident_count_mean": _mean(
                    [float(row["detected_incident_count"]) for row in group]
                ),
                "reduce_duration_ms_mean": _mean(
                    [float(row["reduce_duration_ms"]) for row in group]
                ),
                "runs": len(group),
            }
        )
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Semantic MapReduce hard semantic-merge matrix."
    )
    parser.add_argument("--seeds", default=DEFAULT_SEEDS)
    parser.add_argument("--reducers", default=DEFAULT_REDUCERS)
    parser.add_argument("--scenarios", default=DEFAULT_SCENARIOS)
    parser.add_argument("--shards", type=int, default=8)
    parser.add_argument("--incidents", type=int, default=4)
    parser.add_argument(
        "--samples",
        type=int,
        default=1,
        help=(
            "Independent reducer invocations per scenario/seed/reducer. "
            "Use values >1 for real-online repeated-sampling stability."
        ),
    )
    parser.add_argument(
        "--output-root",
        default=".sage/benchmarks/semantic_merge_analysis",
    )
    parser.add_argument("--run-id")
    return parser.parse_args()


def _git_output(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _environment_name() -> str:
    configured = os.environ.get("CONDA_DEFAULT_ENV", "").strip()
    if configured:
        return configured
    prefix = Path(sys.prefix)
    if prefix.parent.name == "envs":
        return prefix.name
    return ""


def _submodule_info(path: str) -> dict[str, Any]:
    module_path = Path(path)
    if not module_path.exists():
        return {"path": path, "present": False}

    def run(args: list[str]) -> str:
        try:
            return subprocess.check_output(
                ["git", "-C", path, *args], text=True, stderr=subprocess.DEVNULL
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "unknown"

    return {
        "path": path,
        "present": True,
        "commit": run(["rev-parse", "HEAD"]),
        "branch": run(["rev-parse", "--abbrev-ref", "HEAD"]),
        "dirty": bool(run(["status", "--porcelain"])),
    }


def _write_manifest(
    outdir: Path,
    *,
    args: argparse.Namespace,
    seeds: list[int],
    reducers: list[str],
    scenarios: list[str],
) -> None:
    manifest = {
        "run_id": outdir.name,
        "created_unix": int(time.time()),
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "command_args": vars(args),
        "seeds": seeds,
        "reducers": reducers,
        "scenarios": scenarios,
        "samples": args.samples,
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
        },
        "conda_env": _environment_name(),
        "git": {
            "commit": _git_output(["rev-parse", "HEAD"]),
            "branch": _git_output(["rev-parse", "--abbrev-ref", "HEAD"]),
            "dirty": bool(_git_output(["status", "--porcelain"])),
        },
        "evidence_label": "simulation/model",
        "workload_source": {
            "kind": "repo-local",
            "path": "src/sage/workloads/semantic_merge_analysis.py",
            "suite": "semantic_merge_analysis",
        },
        "shared_workload_submodule": _submodule_info("third_party/llm-serving-workloads"),
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = _parse_args()
    seeds = [int(seed) for seed in _parse_csv(args.seeds)]
    reducers = _parse_csv(args.reducers)
    scenarios = _parse_csv(args.scenarios)
    if args.samples < 1:
        raise ValueError("--samples must be at least 1")
    unknown_scenarios = sorted(set(scenarios) - set(SCENARIOS))
    if unknown_scenarios:
        raise ValueError(
            "Unknown scenarios: "
            + ", ".join(unknown_scenarios)
            + f". Expected one of {', '.join(SCENARIOS)}."
        )
    run_id = args.run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    outdir = Path(args.output_root) / run_id
    outdir.mkdir(parents=True, exist_ok=True)
    _write_manifest(
        outdir,
        args=args,
        seeds=seeds,
        reducers=reducers,
        scenarios=scenarios,
    )

    rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        for seed in seeds:
            for reducer in reducers:
                for sample_id in range(1, args.samples + 1):
                    report = run_semantic_merge_workload(
                        seed=seed,
                        shard_count=args.shards,
                        incident_count=args.incidents,
                        scenario=scenario,
                        reducer=reducer,
                    )
                    payload = report.to_dict()
                    payload["sample_id"] = sample_id
                    stem = f"{scenario}_seed{seed}_{reducer.replace('-', '_')}"
                    if args.samples > 1:
                        stem += f"_sample{sample_id}"
                    artifact = outdir / f"{stem}.json"
                    artifact.write_text(
                        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    row = {
                        "scenario": scenario,
                        "seed": seed,
                        "sample_id": sample_id,
                        "shards": args.shards,
                        "incidents": args.incidents,
                        "reducer": reducer,
                        "precision": payload["precision"],
                        "recall": payload["recall"],
                        "f1": payload["f1"],
                        "evidence_coverage": payload["evidence_coverage"],
                        "root_evidence_coverage": payload["root_evidence_coverage"],
                        "support_evidence_recall": payload["support_evidence_recall"],
                        "detected_incident_count": payload["detected_incident_count"],
                        "matched_incident_count": payload["matched_incident_count"],
                        "reduce_duration_ms": payload["reduce_duration_ms"],
                        "missed_incident_ids": ";".join(
                            item["incident_id"] for item in payload["missed_incidents"]
                        ),
                    }
                    rows.append(row)
                    print(
                        f"done scenario={scenario} seed={seed} sample={sample_id} "
                        f"reducer={reducer} precision={payload['precision']} "
                        f"recall={payload['recall']} f1={payload['f1']}"
                    )

    with (outdir / "summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    scenario_summary = _scenario_summary(rows)
    with (outdir / "scenario_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(scenario_summary[0].keys()))
        writer.writeheader()
        writer.writerows(scenario_summary)
    (outdir / "summary.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (outdir / "scenario_summary.json").write_text(
        json.dumps(scenario_summary, ensure_ascii=False, indent=2) + "\n",
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
