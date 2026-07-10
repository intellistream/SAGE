#!/usr/bin/env python3
"""Probe shared LLM-serving workloads from the pinned submodule.

This probe keeps shared serving workload evidence separate from SAGE's
repo-local Semantic MapReduce workloads. It validates that the pinned
`third_party/llm-serving-workloads` source can generate canonical shared cases
and records their request/anchor structure with reproducible provenance.
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


REPO_ROOT = Path(__file__).resolve().parents[2]
SHARED_WORKLOAD_PATH = REPO_ROOT / "third_party" / "llm-serving-workloads"
SHARED_WORKLOAD_SRC = SHARED_WORKLOAD_PATH / "src"
if str(SHARED_WORKLOAD_SRC) not in sys.path:
    sys.path.insert(0, str(SHARED_WORKLOAD_SRC))

from llm_serving_workloads.shared_workload_smoke import (  # noqa: E402
    build_shared_workload_report,
    render_markdown,
)


DEFAULT_OUTPUT_ROOT = ".sage/benchmarks/shared_llm_serving_workloads"
DEFAULT_SEEDS = "7,11,13"


def _parse_csv_ints(raw_value: str) -> list[int]:
    values = [int(item.strip()) for item in raw_value.split(",") if item.strip()]
    if not values:
        raise ValueError("At least one seed is required.")
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


def _submodule_info(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(REPO_ROOT)),
        "present": path.exists(),
        "commit": _git_output(["rev-parse", "HEAD"], cwd=path),
        "branch": _git_output(["rev-parse", "--abbrev-ref", "HEAD"], cwd=path),
        "dirty": bool(_git_output(["status", "--porcelain"], cwd=path)),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a provenance-recorded shared LLM-serving workload probe."
    )
    parser.add_argument("--seeds", default=DEFAULT_SEEDS)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id")
    parser.add_argument(
        "--skip-unsupported",
        action="store_true",
        help="Do not include public/boundary cases unsupported by the local generator.",
    )
    return parser.parse_args()


def _write_manifest(outdir: Path, args: argparse.Namespace, seeds: list[int]) -> None:
    manifest = {
        "run_id": outdir.name,
        "created_unix": int(time.time()),
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "command_args": vars(args),
        "seeds": seeds,
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
        },
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", ""),
        "git": {
            "commit": _git_output(["rev-parse", "HEAD"], cwd=REPO_ROOT),
            "branch": _git_output(["rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO_ROOT),
            "dirty": bool(_git_output(["status", "--porcelain"], cwd=REPO_ROOT)),
        },
        "evidence_label": "derived-artifact",
        "workload_source": {
            "kind": "shared-submodule",
            "path": "third_party/llm-serving-workloads",
            "module": "llm_serving_workloads.shared_workload_smoke",
        },
        "shared_workload_submodule": _submodule_info(SHARED_WORKLOAD_PATH),
        "boundary": (
            "This probe validates shared workload generation and structure. "
            "It does not measure Semantic MapReduce reducer quality."
        ),
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _flatten_case_rows(seed: int, report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in report["supported_cases"]:
        summary = case["summary"]
        rows.append(
            {
                "seed": seed,
                "case_id": case["case_id"],
                "label": case["label"],
                "dataset_name": case["dataset_name"],
                "dp_size": case["dp_size"],
                "request_count": summary["request_count"],
                "workload_family": summary["workload_family"],
                "primary_anchor_count": summary["primary_anchor_count"],
                "secondary_anchor_count": summary["secondary_anchor_count"],
                "anchor_rank_coverage": summary["anchor_rank_coverage"],
                "mean_prompt_len": case["mean_prompt_len"],
                "mean_output_len": case["mean_output_len"],
            }
        )
    return rows


def _aggregate(rows: list[dict[str, Any]], reports: list[dict[str, Any]]) -> dict[str, Any]:
    by_case: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_case.setdefault(str(row["case_id"]), []).append(row)

    return {
        "seed_count": len(reports),
        "supported_case_count": reports[0]["supported_case_count"] if reports else 0,
        "skipped_case_count": reports[0]["skipped_case_count"] if reports else 0,
        "total_supported_requests_per_seed": sum(
            int(row["request_count"]) for row in rows if row["seed"] == rows[0]["seed"]
        )
        if rows
        else 0,
        "by_case": {
            case_id: {
                "dataset_name": group[0]["dataset_name"],
                "request_count": group[0]["request_count"],
                "mean_prompt_len": round(
                    statistics.fmean(float(row["mean_prompt_len"]) for row in group), 3
                ),
                "mean_output_len": round(
                    statistics.fmean(float(row["mean_output_len"]) for row in group), 3
                ),
                "primary_anchor_count": group[0]["primary_anchor_count"],
                "secondary_anchor_count": group[0]["secondary_anchor_count"],
                "anchor_rank_coverage": group[0]["anchor_rank_coverage"],
            }
            for case_id, group in sorted(by_case.items())
        },
    }


def main() -> int:
    args = _parse_args()
    if not SHARED_WORKLOAD_PATH.exists():
        raise FileNotFoundError(f"missing submodule: {SHARED_WORKLOAD_PATH}")

    seeds = _parse_csv_ints(args.seeds)
    run_id = args.run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    outdir = Path(args.output_root) / run_id
    outdir.mkdir(parents=True, exist_ok=True)
    _write_manifest(outdir, args, seeds)

    reports: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for seed in seeds:
        report = build_shared_workload_report(
            seed=seed,
            include_unsupported=not args.skip_unsupported,
        )
        reports.append(report)
        rows.extend(_flatten_case_rows(seed, report))
        (outdir / f"shared_workload_seed{seed}.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (outdir / f"shared_workload_seed{seed}.md").write_text(
            render_markdown(report),
            encoding="utf-8",
        )
        print(
            f"done seed={seed} supported={report['supported_case_count']} "
            f"skipped={report['skipped_case_count']}"
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
        json.dumps(_aggregate(rows, reports), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"RESULT_DIR={outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
