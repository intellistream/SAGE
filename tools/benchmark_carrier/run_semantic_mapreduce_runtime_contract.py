#!/usr/bin/env python3
"""Exercise Semantic MapReduce commit/reject/recovery invariants.

This benchmark is deliberately model-free. It isolates the runtime contract:
validated hypotheses may commit, invalid edits preserve the valid baseline, a
checkpoint restore preserves the committed state, and the archived trace can
replay to the same digest. Results are derived-artifact evidence, not online
model quality measurements.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import subprocess
import sys
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

from sage.runtime.flownet.contracts.shared_state_contract import SharedStateServiceDescriptor
from sage.runtime.flownet.runtime.shared_state_registry import SharedStateServiceRegistry
from sage.workloads.semantic_merge_analysis import (
    SCENARIOS,
    HybridHintMergeReducer,
    SemanticGraphMergeReducer,
    _evidence_index_by_id,
    _stable_payload_digest,
    _validate_hybrid_edits,
    generate_semantic_merge_dataset,
)

DEFAULT_SEEDS = (7, 11, 13)


def _hypothesis_state_digest(hypotheses: list[dict[str, Any]]) -> str:
    """Digest semantic state while excluding runtime-only audit annotations."""

    canonical = []
    for hypothesis in hypotheses:
        item = deepcopy(hypothesis)
        item.pop("llm_fallback", None)
        item.pop("validation", None)
        canonical.append(item)
    return _stable_payload_digest(canonical)


class ReductionStateService:
    """Checkpointable state owned by the runtime, not by the model reducer."""

    def __init__(self) -> None:
        self.hypotheses: list[dict[str, Any]] = []
        self.trace: list[dict[str, Any]] = []

    def initialize(self, hypotheses: list[dict[str, Any]]) -> None:
        self.hypotheses = deepcopy(hypotheses)

    def commit(self, hypotheses: list[dict[str, Any]], trace: dict[str, Any]) -> None:
        self.hypotheses = deepcopy(hypotheses)
        self.trace.append(deepcopy(trace))

    def snapshot_state(self) -> dict[str, Any]:
        return {"hypotheses": deepcopy(self.hypotheses), "trace": deepcopy(self.trace)}

    def restore_state(self, snapshot: dict[str, Any]) -> None:
        self.hypotheses = deepcopy(snapshot.get("hypotheses", []))
        self.trace = deepcopy(snapshot.get("trace", []))


def _git_output(args: list[str]) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def run_contract_matrix(
    *, seeds: tuple[int, ...] = DEFAULT_SEEDS,
    scenarios: tuple[str, ...] = SCENARIOS,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        for seed in seeds:
            dataset = generate_semantic_merge_dataset(seed=seed, scenario=scenario)
            evidence_by_id = _evidence_index_by_id(dataset.evidence)
            candidates = SemanticGraphMergeReducer().reduce(dataset.evidence)
            baseline = HybridHintMergeReducer().reduce(dataset.evidence)

            valid_output, valid_trace = _validate_hybrid_edits(
                deepcopy(baseline),
                candidates=candidates,
                evidence_by_id=evidence_by_id,
                fallback_hypotheses=baseline,
            )
            invalid_output, invalid_trace = _validate_hybrid_edits(
                [],
                candidates=candidates,
                evidence_by_id=evidence_by_id,
                fallback_hypotheses=baseline,
            )

            registry = SharedStateServiceRegistry()
            descriptor = SharedStateServiceDescriptor(
                service_name=f"semantic-reduce-{scenario}-{seed}",
                namespace="sage.semantic-mapreduce",
                owner="benchmark",
                visibility="private",
                reuse_policy="flow",
                recovery_policy="checkpoint_restore",
            )
            record = registry.register_service(
                descriptor=descriptor,
                service_object=ReductionStateService(),
                factory=ReductionStateService,
            )
            state = record.service_object
            state.initialize(baseline)
            baseline_digest = _hypothesis_state_digest(state.hypotheses)

            state.commit(
                valid_output,
                {
                    "outcome": "committed",
                    "scenario": scenario,
                    "seed": seed,
                    "validation": valid_trace,
                },
            )
            committed_digest = _hypothesis_state_digest(state.hypotheses)
            recovered = registry.recover_service(
                descriptor, reason="semantic-reduce-checkpoint-injection"
            )
            recovered_digest = _hypothesis_state_digest(recovered.service_object.hypotheses)

            # Invalid edits are rejected before state.commit; the validator's
            # fallback output must equal the pre-edit baseline exactly.
            rejected_digest = _hypothesis_state_digest(invalid_output)
            replay_digest = _hypothesis_state_digest(
                json.loads(json.dumps(recovered.service_object.hypotheses, sort_keys=True))
            )
            rows.append(
                {
                    "scenario": scenario,
                    "seed": seed,
                    "baseline_digest": baseline_digest,
                    "committed_digest": committed_digest,
                    "recovered_digest": recovered_digest,
                    "replay_digest": replay_digest,
                    "rejected_fallback_digest": rejected_digest,
                    "valid_schema": bool(valid_trace["schema_valid"]),
                    "invalid_schema_rejected": not bool(invalid_trace["schema_valid"]),
                    "invalid_fallback_count": int(invalid_trace["fallback_count"]),
                    "invalid_preserved_baseline": rejected_digest == baseline_digest,
                    "checkpoint_preserved_commit": recovered_digest == committed_digest,
                    "replay_deterministic": replay_digest == committed_digest,
                    "recovery_status": recovered.recovery_summary.status,
                    "recovery_action": recovered.recovery_summary.last_action,
                    "service_revision": recovered.service_revision,
                }
            )
    return rows


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", default="7,11,13")
    parser.add_argument("--scenarios", default=",".join(SCENARIOS))
    parser.add_argument(
        "--output-root", default=".sage/benchmarks/semantic_mapreduce_runtime_contract"
    )
    parser.add_argument("--run-id")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    seeds = tuple(int(value) for value in args.seeds.split(",") if value.strip())
    scenarios = tuple(value.strip() for value in args.scenarios.split(",") if value.strip())
    unknown = sorted(set(scenarios) - set(SCENARIOS))
    if unknown:
        raise ValueError(f"unknown scenarios: {', '.join(unknown)}")
    rows = run_contract_matrix(seeds=seeds, scenarios=scenarios)
    run_id = args.run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    outdir = Path(args.output_root) / run_id
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_id": run_id,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "command_args": vars(args),
        "evidence_label": "derived-artifact",
        "workload_source": {
            "kind": "repo-local",
            "path": "src/sage/workloads/semantic_merge_analysis.py",
            "runtime_contract": "src/sage/runtime/flownet/runtime/shared_state_registry.py",
        },
        "python": {"version": platform.python_version(), "executable": sys.executable},
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", ""),
        "git": {
            "commit": _git_output(["rev-parse", "HEAD"]),
            "branch": _git_output(["rev-parse", "--abbrev-ref", "HEAD"]),
            "dirty": bool(_git_output(["status", "--porcelain"])),
        },
        "boundary": (
            "Model-free runtime-contract evidence. It tests commit/reject, checkpoint "
            "restore, and trace replay; it does not measure model quality or production FT."
        ),
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (outdir / "rows.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (outdir / "summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    aggregate = {
        "row_count": len(rows),
        "scenario_count": len(set(row["scenario"] for row in rows)),
        "seed_count": len(set(row["seed"] for row in rows)),
        "valid_commit_passes": sum(bool(row["valid_schema"]) for row in rows),
        "invalid_edit_rejections": sum(bool(row["invalid_schema_rejected"]) for row in rows),
        "baseline_preservation_passes": sum(bool(row["invalid_preserved_baseline"]) for row in rows),
        "checkpoint_restore_passes": sum(bool(row["checkpoint_preserved_commit"]) for row in rows),
        "deterministic_replay_passes": sum(bool(row["replay_deterministic"]) for row in rows),
    }
    (outdir / "aggregate.json").write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"RESULT_DIR={outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
