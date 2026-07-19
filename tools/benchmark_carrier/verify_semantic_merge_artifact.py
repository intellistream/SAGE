#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any

TARGET = "llm-pairwise-action-validated"
BASELINE = "hybrid-hint"
NEGATIVE = "llm-pairwise-validated"
HARDCASE_SCENARIOS = {
    "ambiguous-disconnected-merge",
    "ambiguous-temporal-split",
    "ambiguous-overmerge",
}
FULL_SCENARIOS = {
    "single-service",
    "cascade",
    "shared-bottleneck",
    "concurrent",
    "false-correlation",
    "partial-evidence",
    *HARDCASE_SCENARIOS,
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
FULL_REQUIRED_CASE_FIELDS = REQUIRED_CASE_FIELDS | {"sample_id"}
TARGET_CONTRACT_FIELDS = {
    "validator_owned",
    "commit_outcome",
    "replay_id",
    "raw_response_retained",
    "request_attempt_count",
    "request_failure_count",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _case_key(row: dict[str, Any]) -> tuple[str, int, int, str]:
    return (
        str(row["scenario"]),
        int(row["seed"]),
        int(row.get("sample_id", 1)),
        str(row["reducer"]),
    )


def _raw_report_path(matrix_dir: Path, row: dict[str, Any]) -> Path:
    stem = (
        f"{row['scenario']}_seed{int(row['seed'])}_"
        f"{str(row['reducer']).replace('-', '_')}"
    )
    sampled = matrix_dir / f"{stem}_sample{int(row.get('sample_id', 1))}.json"
    return sampled if sampled.is_file() else matrix_dir / f"{stem}.json"


def _close(left: Any, right: Any, *, tolerance: float = 1e-6) -> bool:
    try:
        return abs(float(left) - float(right)) <= tolerance
    except (TypeError, ValueError):
        return left == right


def _failure_taxonomy(report: dict[str, Any]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for output_name, report_name in (
        ("missed", "missed_incidents"),
        ("false_positive", "false_positive_incidents"),
    ):
        counts: dict[str, int] = {}
        for item in report.get(report_name, []):
            failure_type = str(item.get("failure_type") or "unknown")
            counts[failure_type] = counts.get(failure_type, 0) + 1
        result[output_name] = dict(sorted(counts.items()))
    return result


def _verify_publication_manifest(package_root: Path, failures: list[str]) -> None:
    manifest_path = package_root / "ANONYMIZATION_MANIFEST.json"
    if not manifest_path.is_file():
        failures.append("publication-anonymized artifact lacks ANONYMIZATION_MANIFEST.json")
        return
    manifest = _load(manifest_path)
    if not isinstance(manifest, dict):
        failures.append("anonymization manifest is not an object")
        return
    if manifest.get("status") != "PASS" or manifest.get("failures") != []:
        failures.append("anonymization manifest does not report a clean PASS")
    if manifest.get("publication_anonymized") is not True:
        failures.append("anonymization manifest lacks publication_anonymized=true")
    listed = manifest.get("files")
    if not isinstance(listed, dict):
        failures.append("anonymization manifest lacks a file inventory")
        return
    actual = {
        str(path.relative_to(package_root))
        for path in package_root.rglob("*")
        if path.is_file() and path != manifest_path
    }
    if set(listed) != actual:
        missing = sorted(set(listed) - actual)
        extra = sorted(actual - set(listed))
        failures.append(
            f"anonymization inventory mismatch: missing={missing[:3]}, extra={extra[:3]}"
        )
    for relative, metadata in listed.items():
        path = package_root / relative
        if not path.is_file() or not isinstance(metadata, dict):
            continue
        expected = metadata.get("packaged_sha256")
        if not isinstance(expected, str) or _sha256(path) != expected:
            failures.append(f"anonymization hash mismatch: {relative}")


def verify(
    artifact_dir: Path,
    endpoint_metadata_path: Path,
    *,
    profile: str = "hardcase",
    min_samples: int = 1,
) -> dict[str, Any]:
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
    matrix_rows = _load(required["matrix_summary"])
    aggregate = _load(required["matrix_aggregate"])
    comparison = _load(required["comparison_summary"])
    endpoint = _load(endpoint_metadata_path)
    publication_anonymized = run.get("publication_anonymized") is True

    def expect(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    expect(isinstance(rows, list), "case_seed_summary is not a list")
    expect(isinstance(matrix_rows, list), "matrix summary is not a list")
    expect(isinstance(aggregate, dict), "matrix aggregate is not an object")
    expect(isinstance(comparison, list), "comparison summary is not a list")
    if not all(
        (
            isinstance(rows, list),
            isinstance(matrix_rows, list),
            isinstance(aggregate, dict),
            isinstance(comparison, list),
        )
    ):
        return {"status": "FAIL", "failures": failures}

    expect(run.get("evidence_label") == "real-online", "run is not real-online")
    expected_env = "project-specific-env" if publication_anonymized else "esage-vllm-hust-dev"
    expect(run.get("conda_env") == expected_env, "wrong Conda environment")
    expect(run.get("hardware", {}).get("npu_device") == 3, "run is not bound to NPU3")
    expect(run.get("git", {}).get("dirty") is False, "parent repository was dirty")
    expect(manifest.get("evidence_label") == "real-online", "matrix is not real-online")
    expect(set(manifest.get("seeds", [])) >= {7, 11, 13}, "required seeds 7/11/13 are absent")
    expected_scenarios = (
        HARDCASE_SCENARIOS if profile == "hardcase" else FULL_SCENARIOS
    )
    expect(
        set(manifest.get("scenarios", [])) == expected_scenarios,
        f"{profile} scenario set changed",
    )
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
    expect(
        bool(endpoint.get("publication_anonymized")) is publication_anonymized,
        "endpoint/run anonymization mode mismatch",
    )
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
    samples = int(manifest.get("samples", 1))
    expect(samples >= min_samples, f"samples={samples}, required at least {min_samples}")
    expected_rows = len(seeds) * len(expected_scenarios) * samples
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
            required_fields = REQUIRED_CASE_FIELDS
            if profile == "full":
                required_fields = FULL_REQUIRED_CASE_FIELDS
                if reducer == TARGET:
                    required_fields = required_fields | TARGET_CONTRACT_FIELDS
            missing = required_fields - set(row)
            expect(not missing, f"{reducer} row missing fields: {sorted(missing)}")

    expected_keys = {
        (scenario, seed, sample_id, reducer)
        for scenario in expected_scenarios
        for seed in seeds
        for sample_id in range(1, samples + 1)
        for reducer in (TARGET, BASELINE, NEGATIVE)
    }
    row_keys = [_case_key(row) for row in rows]
    matrix_keys = [_case_key(row) for row in matrix_rows]
    expect(len(row_keys) == len(set(row_keys)), "case_seed_summary has duplicate keys")
    expect(len(matrix_keys) == len(set(matrix_keys)), "matrix summary has duplicate keys")
    expect(set(row_keys) == expected_keys, "case_seed_summary key set is incomplete")
    expect(set(matrix_keys) == expected_keys, "matrix summary key set is incomplete")

    rows_by_key = {_case_key(row): row for row in rows}
    raw_reports: dict[tuple[str, int, int, str], dict[str, Any]] = {}
    expected_raw_paths: set[Path] = set()
    for summary in matrix_rows:
        key = _case_key(summary)
        raw_path = _raw_report_path(artifact_dir / "matrix", summary)
        expected_raw_paths.add(raw_path)
        if not raw_path.is_file():
            failures.append(f"missing raw report for {key}: {raw_path.name}")
            continue
        report = _load(raw_path)
        if not isinstance(report, dict):
            failures.append(f"raw report is not an object: {raw_path.name}")
            continue
        raw_reports[key] = report
        for name in ("scenario", "seed", "sample_id"):
            expect(
                str(report.get(name, 1 if name == "sample_id" else ""))
                == str(summary.get(name, 1 if name == "sample_id" else "")),
                f"raw/summary {name} mismatch for {key}",
            )
        expect(
            str(report.get("reducer_name")) == key[3],
            f"raw reducer mismatch for {key}",
        )
        for name in ("precision", "recall", "f1", "support_evidence_recall"):
            expect(
                _close(report.get(name), summary.get(name)),
                f"raw/summary {name} mismatch for {key}",
            )

        case = rows_by_key.get(key)
        if case is None:
            continue
        cost = report.get("cost_accounting", {}) or {}
        metadata = (report.get("reducer_trace") or {}).get("metadata") or {}
        contract = metadata.get("contract_trace") or {}
        request_trace = metadata.get("request_trace") or []
        derived = {
            "accepted_edit_count": int(cost.get("accepted_edit_count", 0) or 0),
            "fallback_count": int(cost.get("fallback_count", 0) or 0),
            "invalid_action_count": int(cost.get("invalid_action_count", 0) or 0),
            "invalid_json_count": int(cost.get("json_valid") is False),
            "invalid_schema_count": int(cost.get("schema_valid") is False),
            "estimated_total_tokens": int(cost.get("estimated_total_tokens", 0) or 0),
            "reduce_duration_ms": float(report["reduce_duration_ms"]),
            "validator_reject_reason": cost.get("validator_reject_reason"),
            "validator_owned": contract.get("validator_owned"),
            "commit_outcome": contract.get("commit_outcome"),
            "replay_id": contract.get("replay_id"),
            "raw_response_retained": metadata.get("raw_response_retained"),
            "request_attempt_count": len(request_trace),
            "request_failure_count": sum(
                item.get("status") != "ok" for item in request_trace
            ),
            "failure_taxonomy": _failure_taxonomy(report),
        }
        for name in ("precision", "recall", "f1", "support_evidence_recall"):
            expect(
                _close(case.get(name), summary.get(name)),
                f"case/summary {name} mismatch for {key}",
            )
        for name, value in derived.items():
            if name not in case:
                continue
            if name == "reduce_duration_ms":
                matches = _close(case.get(name), value)
            else:
                matches = case.get(name) == value
            expect(matches, f"case/raw {name} mismatch for {key}")

    expect(
        len(raw_reports) == len(expected_keys),
        f"raw report coverage is {len(raw_reports)}, expected {len(expected_keys)}",
    )
    report_files = {
        path
        for path in (artifact_dir / "matrix").glob("*.json")
        if path not in {
            required["matrix_manifest"],
            required["matrix_summary"],
            required["matrix_aggregate"],
            artifact_dir / "matrix" / "scenario_summary.json",
        }
    }
    expect(report_files == expected_raw_paths, "raw report file set has missing or extra rows")

    with required["case_seed_csv"].open(newline="", encoding="utf-8") as handle:
        csv_rows = list(csv.DictReader(handle))
    expect(len(csv_rows) == len(rows), "case_seed_summary.csv row count mismatch")
    csv_keys = {
        (
            str(row.get("scenario")),
            int(row.get("seed", 0)),
            int(row.get("sample_id", 1)),
            str(row.get("reducer")),
        )
        for row in csv_rows
    }
    expect(csv_keys == expected_keys, "case_seed_summary.csv key set mismatch")

    expect(aggregate.get("row_count") == len(matrix_rows), "aggregate row_count mismatch")
    aggregate_by_reducer = aggregate.get("by_reducer", {})
    comparison_by_reducer = {
        str(row.get("reducer")): row for row in comparison if isinstance(row, dict)
    }
    expect(
        set(comparison_by_reducer) >= {TARGET, BASELINE, NEGATIVE},
        "comparison summary reducer set is incomplete",
    )
    for reducer in (TARGET, BASELINE, NEGATIVE):
        group = groups[reducer]
        f1_mean = statistics.fmean(float(row["f1"]) for row in group)
        comp = comparison_by_reducer.get(reducer, {})
        expect(_close(comp.get("f1_mean"), f1_mean, tolerance=1e-4), f"comparison F1 mismatch for {reducer}")
        aggregate_f1 = (aggregate_by_reducer.get(reducer, {}).get("f1") or {}).get("mean")
        expect(_close(aggregate_f1, f1_mean, tolerance=1e-4), f"aggregate F1 mismatch for {reducer}")

    if publication_anonymized:
        _verify_publication_manifest(artifact_dir.parent, failures)

    target_rows = groups[TARGET]
    baseline_rows = groups[BASELINE]
    negative_rows = groups[NEGATIVE]
    target_by_case = {
        (row["scenario"], row["seed"], row.get("sample_id", 1)): row
        for row in target_rows
    }
    baseline_by_case = {
        (row["scenario"], row["seed"], row.get("sample_id", 1)): row
        for row in baseline_rows
    }
    if profile == "hardcase":
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
            all(
                row["fallback_count"] > 0 and row["invalid_schema_count"] > 0
                for row in negative_rows
            ),
            "free-form validated negative did not exercise schema fallback",
        )
    else:
        for row in target_rows:
            expect(
                row.get("validator_owned") is True,
                "target commit is not validator-owned",
            )
            expect(
                row.get("commit_outcome") in {"committed", "preserved-baseline"},
                "target commit outcome absent",
            )
            expect(bool(row.get("replay_id")), "target replay ID absent")
            expect(
                row.get("raw_response_retained") is True,
                "target raw response not retained",
            )

    target_f1 = statistics.fmean(row["f1"] for row in target_rows)
    baseline_f1 = statistics.fmean(row["f1"] for row in baseline_rows)
    expect(target_f1 > baseline_f1, "target mean F1 does not exceed hybrid-hint")
    if profile == "hardcase":
        for seed in seeds:
            for sample_id in range(1, samples + 1):
                disconnected = target_by_case[
                    ("ambiguous-disconnected-merge", seed, sample_id)
                ]
                expect(
                    disconnected["f1"] == 1.0,
                    f"seed {seed} sample {sample_id} disconnected merge is not F1 1.0",
                )
                expect(
                    disconnected["accepted_edit_count"] > 0,
                    f"seed {seed} sample {sample_id} has no accepted merge edit",
                )
                overmerge = target_by_case[("ambiguous-overmerge", seed, sample_id)]
                baseline = baseline_by_case[("ambiguous-overmerge", seed, sample_id)]
                expect(
                    overmerge["f1"] >= baseline["f1"],
                    f"seed {seed} sample {sample_id} regresses overmerge",
                )

    checksums = {name: _sha256(path) for name, path in required.items()}
    checksums["endpoint_metadata"] = _sha256(endpoint_metadata_path)
    return {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "evidence_label": run.get("evidence_label"),
        "publication_anonymized": publication_anonymized,
        "parent_commit": run_git.get("commit"),
        "seeds": seeds,
        "scenarios": sorted(expected_scenarios),
        "profile": profile,
        "samples": samples,
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
    parser.add_argument("--profile", choices=("hardcase", "full"), default="hardcase")
    parser.add_argument("--min-samples", type=int, default=1)
    args = parser.parse_args()
    result = verify(
        args.artifact_dir,
        args.endpoint_metadata,
        profile=args.profile,
        min_samples=args.min_samples,
    )
    if args.output:
        if args.output.exists():
            raise SystemExit("refusing to overwrite verifier output")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
