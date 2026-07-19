from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path


def _load_verifier():
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "tools" / "benchmark_carrier" / "verify_semantic_merge_artifact.py"
    spec = importlib.util.spec_from_file_location("semantic_merge_artifact_gate", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_publication_manifest_rejects_infrastructure_identifiers(tmp_path: Path) -> None:
    verifier = _load_verifier()
    package = tmp_path / "artifact"
    endpoint = package / "endpoint"
    endpoint.mkdir(parents=True)
    leak = endpoint / "npu-smi-before.txt"
    leak.write_text(
        "base_url=http://127.0.0.1:18383\ncontainer=PROJECT-smr-npu3\n"
        "| 0 | 0000:C1:00.0 |\n| 0 0 | 1067293 | engine | 28347 |\n",
        encoding="utf-8",
    )
    manifest = {
        "status": "PASS", "failures": [], "publication_anonymized": True,
        "files": {
            "endpoint/npu-smi-before.txt": {
                "packaged_sha256": hashlib.sha256(leak.read_bytes()).hexdigest()
            }
        },
    }
    (package / "ANONYMIZATION_MANIFEST.json").write_text(
        json.dumps(manifest) + "\n", encoding="utf-8"
    )
    failures: list[str] = []
    verifier._verify_publication_manifest(package, failures)
    assert any("endpoint/port leak" in item for item in failures)
    assert any("unit/container leak" in item for item in failures)
    assert any("PCI topology leak" in item for item in failures)
    assert any("process-ID leak" in item for item in failures)


def test_publication_manifest_rejects_all_anonymity_policy_classes(
    tmp_path: Path,
) -> None:
    verifier = _load_verifier()
    package = tmp_path / "artifact"
    endpoint = package / "endpoint"
    endpoint.mkdir(parents=True)
    leaks = {
        "endpoint/unallowlisted.log": "private log\n",
        "grant.json": '{"Authorization":"Bearer abcdefghijklmnop"}\n',
        "identity.txt": (
            "path=/home/reviewer/workspace/model host=private-host "
            "remote=git@github.com:private/repo.git author=user@example.com "
            "commit=0123456789abcdef0123456789abcdef01234567 "
            "version=faculty-twin-runtime-20260706-fix1-2-gREVISION_001\n"
        ),
    }
    files = {}
    for relative, text in leaks.items():
        path = package / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        files[relative] = {"packaged_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    manifest = {
        "status": "PASS", "failures": [], "publication_anonymized": True,
        "endpoint_allowlist": ["metadata.json"], "files": files,
    }
    (package / "ANONYMIZATION_MANIFEST.json").write_text(
        json.dumps(manifest) + "\n", encoding="utf-8"
    )
    failures: list[str] = []
    verifier._verify_publication_manifest(package, failures)
    for fragment in (
        "unallowlisted endpoint", "forbidden raw/control", "sensitive path",
        "hostname", "Git/email identity", "Git revision", "credential",
    ):
        assert any(fragment in item for item in failures), (fragment, failures)


def _write_complete_fixture(
    verifier,
    artifact: Path,
    manifest: dict,
    run: dict,
    endpoint_path: Path,
    endpoint: dict,
    rows: list[dict],
) -> None:
    matrix = artifact / "matrix"
    matrix.mkdir(parents=True, exist_ok=True)
    matrix_rows = []
    for row in rows:
        row.setdefault("precision", row["f1"])
        row.setdefault("recall", row["f1"])
        row.setdefault("invalid_json_count", 0)
        row["failure_taxonomy"] = {"missed": {}, "false_positive": {}}
        summary = {
            "scenario": row["scenario"],
            "seed": row["seed"],
            "sample_id": row["sample_id"],
            "reducer": row["reducer"],
            "precision": row["precision"],
            "recall": row["recall"],
            "f1": row["f1"],
            "support_evidence_recall": row["support_evidence_recall"],
        }
        matrix_rows.append(summary)
        cost = {
            "accepted_edit_count": row["accepted_edit_count"],
            "fallback_count": row["fallback_count"],
            "invalid_action_count": row["invalid_action_count"],
            "json_valid": row.get("json_valid"),
            "schema_valid": row.get("schema_valid"),
            "estimated_total_tokens": row["estimated_total_tokens"],
            "validator_reject_reason": row.get("validator_reject_reason"),
        }
        metadata = {}
        if row["reducer"] == verifier.TARGET:
            metadata = {
                "raw_response_retained": row["raw_response_retained"],
                "request_trace": [
                    {"status": "ok"} for _ in range(row["request_attempt_count"])
                ],
                "contract_trace": {
                    "validator_owned": row["validator_owned"],
                    "commit_outcome": row["commit_outcome"],
                    "replay_id": row["replay_id"],
                },
            }
        report = {
            **summary,
            "reducer_name": row["reducer"],
            "reduce_duration_ms": row["reduce_duration_ms"],
            "cost_accounting": cost,
            "reducer_trace": {"metadata": metadata},
            "missed_incidents": [],
            "false_positive_incidents": [],
        }
        stem = (
            f"{row['scenario']}_seed{row['seed']}_"
            f"{row['reducer'].replace('-', '_')}_sample{row['sample_id']}.json"
        )
        (matrix / stem).write_text(json.dumps(report), encoding="utf-8")

    by_reducer = {}
    comparison = []
    for reducer in (verifier.TARGET, verifier.BASELINE, verifier.NEGATIVE):
        group = [row for row in rows if row["reducer"] == reducer]
        mean = sum(row["f1"] for row in group) / len(group)
        by_reducer[reducer] = {"f1": {"mean": mean}}
        comparison.append({"reducer": reducer, "f1_mean": mean})
    files = {
        artifact / "run_metadata.json": run,
        artifact / "comparison_summary.json": comparison,
        artifact / "case_seed_summary.json": rows,
        matrix / "manifest.json": manifest,
        matrix / "summary.json": matrix_rows,
        matrix / "aggregate.json": {"row_count": len(rows), "by_reducer": by_reducer},
    }
    for path, payload in files.items():
        path.write_text(json.dumps(payload), encoding="utf-8")
    with (artifact / "case_seed_summary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    endpoint_path.write_text(json.dumps(endpoint), encoding="utf-8")


def _write_anonymization_manifest(package_root: Path) -> None:
    files = {}
    for path in package_root.rglob("*"):
        if path.is_file() and path.name != "ANONYMIZATION_MANIFEST.json":
            files[str(path.relative_to(package_root))] = {
                "packaged_sha256": hashlib.sha256(path.read_bytes()).hexdigest()
            }
    (package_root / "ANONYMIZATION_MANIFEST.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "failures": [],
                "publication_anonymized": True,
                "endpoint_allowlist": [],
                "files": files,
            }
        ),
        encoding="utf-8",
    )


def test_artifact_gate_rejects_missing_evidence(tmp_path: Path) -> None:
    verifier = _load_verifier()

    result = verifier.verify(tmp_path / "missing", tmp_path / "endpoint.json")

    assert result["status"] == "FAIL"
    assert any("missing required file" in item for item in result["failures"])
    assert any("missing endpoint metadata" in item for item in result["failures"])


def test_full_artifact_gate_accepts_repeated_contract_evidence(tmp_path: Path) -> None:
    verifier = _load_verifier()
    artifact = tmp_path / "artifact"
    matrix = artifact / "matrix"
    matrix.mkdir(parents=True)
    commit = "a" * 40
    reducers = [verifier.TARGET, verifier.BASELINE, verifier.NEGATIVE]
    manifest = {
        "evidence_label": "real-online",
        "seeds": [7, 11, 13],
        "scenarios": sorted(verifier.FULL_SCENARIOS),
        "reducers": reducers,
        "samples": 2,
    }
    run = {
        "evidence_label": "real-online",
        "conda_env": "esage-vllm-hust-dev",
        "hardware": {"npu_device": 3},
        "git": {"dirty": False, "commit": commit},
        "endpoint": {"model": "model-a"},
        "runtime_submodules": {"runtime": {"dirty": False}},
        "shared_workload_submodule": {"dirty": False},
    }
    endpoint = {
        "evidence_label": "real-online",
        "parent_repo_dirty": False,
        "parent_repo_commit": commit,
        "npu_device": 3,
        "conda_env": "esage-vllm-hust-dev",
        "served_model_name": "model-a",
    }
    rows = []
    for scenario in sorted(verifier.FULL_SCENARIOS):
        for seed in (7, 11, 13):
            for sample_id in (1, 2):
                for reducer in reducers:
                    row = {
                        "scenario": scenario,
                        "seed": seed,
                        "sample_id": sample_id,
                        "reducer": reducer,
                        "f1": 0.9 if reducer == verifier.TARGET else 0.7,
                        "support_evidence_recall": 1.0,
                        "accepted_edit_count": 1,
                        "fallback_count": 0,
                        "invalid_action_count": 0,
                        "invalid_schema_count": 0,
                        "estimated_total_tokens": 10,
                        "reduce_duration_ms": 1.0,
                        "failure_taxonomy": {},
                    }
                    if reducer == verifier.TARGET:
                        row.update(
                            validator_owned=True,
                            commit_outcome="committed",
                            replay_id=f"{scenario}-{seed}-{sample_id}",
                            raw_response_retained=True,
                            request_attempt_count=1,
                            request_failure_count=0,
                        )
                    rows.append(row)
    endpoint_path = tmp_path / "endpoint.json"
    _write_complete_fixture(
        verifier, artifact, manifest, run, endpoint_path, endpoint, rows
    )

    result = verifier.verify(
        artifact, endpoint_path, profile="full", min_samples=2
    )

    assert result["status"] == "PASS", result["failures"]
    assert result["samples"] == 2

    case_path = artifact / "case_seed_summary.json"
    original_cases = json.loads(case_path.read_text(encoding="utf-8"))
    case_path.write_text(
        json.dumps([*original_cases, original_cases[0]]), encoding="utf-8"
    )
    duplicate = verifier.verify(
        artifact, endpoint_path, profile="full", min_samples=2
    )
    assert duplicate["status"] == "FAIL"
    assert any("duplicate keys" in item for item in duplicate["failures"])
    case_path.write_text(json.dumps(original_cases), encoding="utf-8")

    raw_path = next((artifact / "matrix").glob("*_sample1.json"))
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    raw["f1"] = 0.123
    raw_path.write_text(json.dumps(raw), encoding="utf-8")
    tampered = verifier.verify(
        artifact, endpoint_path, profile="full", min_samples=2
    )
    assert tampered["status"] == "FAIL"
    assert any("raw/summary f1 mismatch" in item for item in tampered["failures"])


def test_full_artifact_gate_accepts_consistent_opaque_publication_provenance(
    tmp_path: Path,
) -> None:
    verifier = _load_verifier()
    artifact = tmp_path / "artifact"
    matrix = artifact / "matrix"
    matrix.mkdir(parents=True)
    reducers = [verifier.TARGET, verifier.BASELINE, verifier.NEGATIVE]
    manifest = {
        "evidence_label": "real-online",
        "publication_anonymized": True,
        "seeds": [7, 11, 13],
        "scenarios": sorted(verifier.FULL_SCENARIOS),
        "reducers": reducers,
        "samples": 1,
    }
    run = {
        "evidence_label": "real-online",
        "publication_anonymized": True,
        "conda_env": "project-specific-env",
        "hardware": {"npu_device": 3},
        "git": {"dirty": False, "commit": "REVISION_001"},
        "endpoint": {"model": "qwen2.5-7b-review-endpoint"},
        "runtime_submodules": {"runtime-a": {"dirty": False}},
        "shared_workload_submodule": {"dirty": False},
    }
    endpoint = {
        "evidence_label": "real-online",
        "publication_anonymized": True,
        "parent_repo_dirty": False,
        "parent_repo_commit": "REVISION_001",
        "npu_device": 3,
        "conda_env": "project-specific-env",
        "served_model_name": "qwen2.5-7b-review-endpoint",
    }
    rows = []
    for scenario in sorted(verifier.FULL_SCENARIOS):
        for seed in (7, 11, 13):
            for reducer in reducers:
                row = {
                    "scenario": scenario,
                    "seed": seed,
                    "sample_id": 1,
                    "reducer": reducer,
                    "f1": 0.9 if reducer == verifier.TARGET else 0.7,
                    "support_evidence_recall": 1.0,
                    "accepted_edit_count": 1,
                    "fallback_count": 0,
                    "invalid_action_count": 0,
                    "invalid_schema_count": 0,
                    "estimated_total_tokens": 10,
                    "reduce_duration_ms": 1.0,
                    "failure_taxonomy": {},
                }
                if reducer == verifier.TARGET:
                    row.update(
                        validator_owned=True,
                        commit_outcome="committed",
                        replay_id=f"{scenario}-{seed}",
                        raw_response_retained=True,
                        request_attempt_count=1,
                        request_failure_count=0,
                    )
                rows.append(row)
    endpoint_path = tmp_path / "endpoint.json"
    _write_complete_fixture(
        verifier, artifact, manifest, run, endpoint_path, endpoint, rows
    )
    _write_anonymization_manifest(tmp_path)

    result = verifier.verify(artifact, endpoint_path, profile="full")

    assert result["status"] == "PASS", result["failures"]
    assert result["publication_anonymized"] is True
