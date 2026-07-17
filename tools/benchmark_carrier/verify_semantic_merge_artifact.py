#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any

TARGET = "llm-pairwise-action-validated"
BASELINE = "hybrid-hint"
NEGATIVE = "llm-pairwise-validated"
SCENARIOS = {
    "ambiguous-disconnected-merge",
    "ambiguous-temporal-split",
    "ambiguous-overmerge",
}
REQUIRED_CASE_FIELDS = {
    "scenario",
    "seed",
    "reducer",
    "f1",
    "support_evidence_recall",
    "accepted_edit_count",
    "fallback_count",
    "invalid_action_count",
    "invalid_schema_count",
    "estimated_total_tokens",
    "reduce_duration_ms",
    "failure_taxonomy",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(artifact_dir: Path, endpoint_metadata_path: Path) -> dict[str, Any]:
    required = {
        "run_metadata": artifact_dir / "run_metadata.json",
        "comparison_summary": artifact_dir / "comparison_summary.json",
        "case_seed_summary": artifact_dir / "case_seed_summary.json",
        "case_seed_csv": artifact_dir / "case_seed_summary.csv",
        "matrix_manifest": artifact_dir / "matrix" / "manifest.json",
        "matrix_summary": artifact_dir / "matrix" / "summary.json",
        "matrix_aggregate": artifact_dir / "matrix" / "aggregate.json",
    }
    failures = [
        f"missing required file: {path}" for path in required.values() if not path.is_file()
    ]
    if not endpoint_metadata_path.is_file():
        failures.append(f"missing endpoint metadata: {endpoint_metadata_path}")
    if failures:
        return {"status": "FAIL", "failures": failures}

    run = _load(required["run_metadata"])
    manifest = _load(required["matrix_manifest"])
    rows = _load(required["case_seed_summary"])
    endpoint = _load(endpoint_metadata_path)

    def expect(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    expect(run.get("evidence_label") == "real-online", "run is not real-online")
    expect(run.get("conda_env") == "esage-vllm-hust-dev", "wrong Conda environment")
    expect(run.get("hardware", {}).get("npu_device") == 3, "run is not bound to NPU3")
    expect(run.get("git", {}).get("dirty") is False, "parent repository was dirty")
    expect(manifest.get("evidence_label") == "real-online", "matrix is not real-online")
    expect(set(manifest.get("seeds", [])) >= {7, 11, 13}, "required seeds 7/11/13 are absent")
    expect(set(manifest.get("scenarios", [])) == SCENARIOS, "hardcase scenario set changed")
    expect(
        {TARGET, BASELINE, NEGATIVE}.issubset(manifest.get("reducers", [])),
        "target, strong baseline, or negative control is absent",
    )
    expect(
        all(not entry.get("dirty", True) for entry in run.get("runtime_submodules", {}).values()),
        "a runtime submodule was dirty",
    )
    expect(
        run.get("shared_workload_submodule", {}).get("dirty") is False,
        "shared workload submodule was dirty",
    )

    run_git = run.get("git", {})
    expect(endpoint.get("evidence_label") == "real-online", "endpoint is not real-online")
    expect(endpoint.get("parent_repo_dirty") is False, "endpoint parent was dirty")
    expect(
        endpoint.get("parent_repo_commit") == run_git.get("commit"), "endpoint/run commit mismatch"
    )
    expect(str(endpoint.get("npu_device")) == "3", "endpoint is not bound to NPU3")
    expect(endpoint.get("conda_env") == run.get("conda_env"), "endpoint/run env mismatch")
    expect(
        endpoint.get("served_model_name") == run.get("endpoint", {}).get("model"),
        "endpoint/run model mismatch",
    )

    seeds = sorted(set(manifest.get("seeds", [])))
    expected_rows = len(seeds) * len(SCENARIOS)
    groups = {
        reducer: [row for row in rows if row.get("reducer") == reducer]
        for reducer in (TARGET, BASELINE, NEGATIVE)
    }
    for reducer, group in groups.items():
        expect(
            len(group) == expected_rows,
            f"{reducer} has {len(group)} rows, expected {expected_rows}",
        )
        for row in group:
            missing = REQUIRED_CASE_FIELDS - set(row)
            expect(not missing, f"{reducer} row missing fields: {sorted(missing)}")

    target_rows = groups[TARGET]
    baseline_rows = groups[BASELINE]
    negative_rows = groups[NEGATIVE]
    target_by_case = {(row["scenario"], row["seed"]): row for row in target_rows}
    baseline_by_case = {(row["scenario"], row["seed"]): row for row in baseline_rows}
    expect(
        all(
            row["fallback_count"] == 0
            and row["invalid_action_count"] == 0
            and row["invalid_schema_count"] == 0
            for row in target_rows
        ),
        "target has fallback or invalid output",
    )
    expect(
        all(row["fallback_count"] > 0 and row["invalid_schema_count"] > 0 for row in negative_rows),
        "free-form validated negative did not exercise schema fallback",
    )

    target_f1 = statistics.fmean(row["f1"] for row in target_rows)
    baseline_f1 = statistics.fmean(row["f1"] for row in baseline_rows)
    expect(target_f1 > baseline_f1, "target mean F1 does not exceed hybrid-hint")
    for seed in seeds:
        disconnected = target_by_case[("ambiguous-disconnected-merge", seed)]
        expect(disconnected["f1"] == 1.0, f"seed {seed} disconnected merge is not F1 1.0")
        expect(disconnected["accepted_edit_count"] > 0, f"seed {seed} has no accepted merge edit")
        overmerge = target_by_case[("ambiguous-overmerge", seed)]
        baseline = baseline_by_case[("ambiguous-overmerge", seed)]
        expect(overmerge["f1"] >= baseline["f1"], f"seed {seed} regresses overmerge")

    checksums = {name: _sha256(path) for name, path in required.items()}
    checksums["endpoint_metadata"] = _sha256(endpoint_metadata_path)
    return {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "evidence_label": run.get("evidence_label"),
        "parent_commit": run_git.get("commit"),
        "seeds": seeds,
        "scenarios": sorted(SCENARIOS),
        "target_reducer": TARGET,
        "strong_baseline": BASELINE,
        "negative_control": NEGATIVE,
        "target_mean_f1": round(target_f1, 4),
        "baseline_mean_f1": round(baseline_f1, 4),
        "target_mean_support_recall": round(
            statistics.fmean(row["support_evidence_recall"] for row in target_rows), 4
        ),
        "target_mean_accepted_edits": round(
            statistics.fmean(row["accepted_edit_count"] for row in target_rows), 4
        ),
        "target_fallback_total": sum(row["fallback_count"] for row in target_rows),
        "target_invalid_action_total": sum(row["invalid_action_count"] for row in target_rows),
        "target_invalid_schema_total": sum(row["invalid_schema_count"] for row in target_rows),
        "checksums": checksums,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify a Semantic MapReduce real-online artifact."
    )
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument("--endpoint-metadata", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(args.artifact_dir, args.endpoint_metadata)
    output = args.output or args.artifact_dir / "artifact_gate.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
