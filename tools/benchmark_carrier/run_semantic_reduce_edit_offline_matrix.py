#!/usr/bin/env python3
"""Run the frozen fair bounded-Edit v2 offline matrix (no NPU/model endpoint)."""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from sage.workloads.semantic_reduce_edit_evaluation import evaluate_workload
from sage.workloads.semantic_reduce_heldout import (
    HELDOUT_FAMILIES,
    generate_heldout_workload,
)

CONFIG_PATH = Path("experiments/semantic_mapreduce/heldout_v2_config.json")
DEFAULT_OUTPUT_ROOT = Path(".sage/benchmarks/semantic_reduce_edit_v2")


def _git(args: list[str], *, path: str | None = None) -> str:
    command = ["git"]
    if path:
        command += ["-C", path]
    try:
        return subprocess.check_output(
            [*command, *args], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _environment_name() -> str:
    configured = os.environ.get("CONDA_DEFAULT_ENV", "").strip()
    if configured:
        return configured
    prefix = Path(sys.prefix)
    return prefix.name if prefix.parent.name == "envs" else ""


def _submodule(path: str) -> dict[str, Any]:
    return {
        "path": path,
        "commit": _git(["rev-parse", "HEAD"], path=path),
        "branch": _git(["branch", "--show-current"], path=path),
        "dirty": bool(_git(["status", "--porcelain"], path=path)),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("development", "heldout"), default="heldout")
    parser.add_argument("--families", default=",".join(HELDOUT_FAMILIES))
    parser.add_argument("--seeds")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id")
    parser.add_argument("--allow-dirty", action="store_true")
    return parser.parse_args()


def _aggregate(rows: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    error_rows = [row for row in rows if row["proposal_coverage"]["h0_error"]]
    repairable = [
        row for row in error_rows if row["proposal_coverage"]["oracle_improves_h0"]
    ]
    score_balanced = [row["field_separability"]["score_balanced_accuracy"] for row in rows]
    hint_proxy = [
        row["field_separability"]["hint_coverage_times_correctness"] for row in rows
    ]
    gate = config["success_gates_frozen_before_heldout_matrix"]
    summary = {
        "unit_count": len(rows),
        "erroneous_h0_unit_count": len(error_rows),
        "oracle_repairable_unit_count": len(repairable),
        "oracle_repairable_fraction_of_erroneous_h0": round(
            len(repairable) / max(1, len(error_rows)), 6
        ),
        "improving_merge_unit_count": sum(
            row["proposal_coverage"]["improving_merge_proposal_exists"] for row in rows
        ),
        "improving_split_unit_count": sum(
            row["proposal_coverage"]["improving_split_proposal_exists"] for row in rows
        ),
        "aggregate_score_threshold_balanced_accuracy": round(
            sum(score_balanced) / max(1, len(score_balanced)), 6
        ),
        "aggregate_hint_coverage_times_correctness": round(
            sum(hint_proxy) / max(1, len(hint_proxy)), 6
        ),
        "shared_catalog_digest_match": all(
            row["shared_catalog_digest_match"] for row in rows
        ),
    }
    summary["offline_gates"] = {
        "oracle_coverage": summary[
            "oracle_repairable_fraction_of_erroneous_h0"
        ]
        >= gate["oracle_repairable_fraction_of_erroneous_h0_min"],
        "merge_coverage": summary["improving_merge_unit_count"]
        >= gate["improving_merge_unit_count_min"],
        "split_coverage": summary["improving_split_unit_count"]
        >= gate["improving_split_unit_count_min"],
        "score_proxy_reduced": summary[
            "aggregate_score_threshold_balanced_accuracy"
        ]
        <= gate["aggregate_score_threshold_balanced_accuracy_max"],
        "hint_proxy_reduced": summary[
            "aggregate_hint_coverage_times_correctness"
        ]
        <= gate["aggregate_hint_coverage_times_correctness_max"],
        "shared_catalog": summary["shared_catalog_digest_match"],
    }
    summary["online_readiness"] = "BLOCKED" if not all(summary["offline_gates"].values()) else "OFFLINE_GATES_ONLY"
    summary["online_execution_performed"] = False
    return summary


def main() -> int:
    args = _parse_args()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if not args.allow_dirty and _git(["status", "--porcelain"]):
        raise SystemExit("refusing clean matrix from dirty parent; commit first")
    if _environment_name() != "esage-vllm-hust-dev":
        raise SystemExit("run with the esage-vllm-hust-dev environment")
    families = tuple(value for value in args.families.split(",") if value)
    unknown = sorted(set(families) - set(HELDOUT_FAMILIES))
    if unknown:
        raise SystemExit(f"unknown families: {unknown}")
    seed_key = f"{args.split}_seeds"
    seeds = (
        [int(value) for value in args.seeds.split(",") if value]
        if args.seeds
        else [int(value) for value in config[seed_key]]
    )
    run_id = args.run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    outdir = args.output_root / run_id
    if outdir.exists():
        raise SystemExit(f"refusing to overwrite existing output: {outdir}")
    outdir.mkdir(parents=True)
    command_line = " ".join(shlex.quote(value) for value in sys.argv)
    manifest = {
        "run_id": run_id,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "command": command_line,
        "evidence_label": "simulation/model",
        "derived_outputs_label": "derived-artifact",
        "parent": {
            "commit": _git(["rev-parse", "HEAD"]),
            "branch": _git(["branch", "--show-current"]),
            "dirty": bool(_git(["status", "--porcelain"])),
        },
        "python": {"executable": sys.executable, "version": platform.python_version()},
        "conda_env": _environment_name(),
        "workload_source": {
            "kind": "repo-local",
            "path": "src/sage/workloads/semantic_reduce_heldout.py",
            "config_path": str(CONFIG_PATH),
            "config_digest": __import__("hashlib").sha256(CONFIG_PATH.read_bytes()).hexdigest(),
        },
        "split": args.split,
        "seeds": seeds,
        "families": list(families),
        "h0_reducer": "semantic-graph",
        "proposal_generators": [
            "candidate-pair",
            "conflicting-upstream-hints",
            "temporal-gap",
            "topology-disconnected",
        ],
        "selectors": [
            "proposal-oracle (diagnostic)",
            "deterministic-proposal-selector",
            "mock-model-proposal-selector (no endpoint/model invocation)",
        ],
        "constrained_reference_permission": "full-evidence global reclustering",
        "frozen_parameters": config["parameters"],
        "frozen_success_gates": config["success_gates_frozen_before_heldout_matrix"],
        "submodules": {
            path: _submodule(path)
            for path in (
                "external/vllm-hust",
                "external/vllm-ascend-hust",
                "external/triton-ascend-hust",
                "external/vllm-hust-dev-hub",
                "third_party/ascend-runtime-manager",
                "third_party/llm-serving-workloads",
            )
        },
        "hardware": {"used": False, "accelerator": None},
        "online_endpoint": {"used": False, "model": None, "credentials": False},
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    rows = []
    for family in families:
        for seed in seeds:
            workload = generate_heldout_workload(
                family, seed=seed, split=args.split
            )
            row = evaluate_workload(
                workload,
                oracle_max_edits=int(config["parameters"]["oracle_max_edits"]),
            )
            rows.append(row)
            (outdir / f"{family}_seed{seed}.json").write_text(
                json.dumps(row, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
    (outdir / "rows.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    flat_rows = []
    for row in rows:
        flat_rows.append(
            {
                "family": row["family"],
                "seed": row["seed"],
                "split": row["split"],
                "h0_f1": row["policies"]["h0"]["f1"],
                "oracle_f1": row["policies"]["proposal_oracle"]["f1"],
                "deterministic_f1": row["policies"]["deterministic_selector"]["f1"],
                "mock_model_f1": row["policies"]["mock_model_selector"]["f1"],
                "constrained_reference_f1": row["policies"]["constrained_reference"]["f1"],
                "merge_proposal_recall": row["proposal_coverage"]["merge_proposal_recall"],
                "split_proposal_recall": row["proposal_coverage"]["split_proposal_recall"],
                "catalog_truncated": sum(row["catalog_truncation_by_action"].values()),
                "deterministic_accepted_edits": row["policies"]["deterministic_selector"]["accepted_edit_count"],
                "mock_model_accepted_edits": row["policies"]["mock_model_selector"]["accepted_edit_count"],
                "evidence_conserved": row["policies"]["deterministic_selector"]["evidence_conserved"]
                and row["policies"]["mock_model_selector"]["evidence_conserved"],
                "failure_taxonomy": ";".join(
                    value
                    for value in (
                        row["policies"]["deterministic_selector"]["validator_reason_code"],
                        row["policies"]["mock_model_selector"]["validator_reason_code"],
                    )
                    if value
                ),
            }
        )
    with (outdir / "summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0]))
        writer.writeheader()
        writer.writerows(flat_rows)
    aggregate = _aggregate(rows, config)
    (outdir / "aggregate.json").write_text(
        json.dumps(aggregate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"RESULT_DIR={outdir}")
    print(json.dumps(aggregate, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
