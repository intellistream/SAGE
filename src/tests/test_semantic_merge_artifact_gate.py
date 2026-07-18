from __future__ import annotations

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
    files = {
        artifact / "run_metadata.json": run,
        artifact / "comparison_summary.json": {},
        artifact / "case_seed_summary.json": rows,
        matrix / "manifest.json": manifest,
        matrix / "summary.json": {},
        matrix / "aggregate.json": {},
    }
    for path, payload in files.items():
        path.write_text(json.dumps(payload), encoding="utf-8")
    (artifact / "case_seed_summary.csv").write_text("header\n", encoding="utf-8")
    endpoint_path = tmp_path / "endpoint.json"
    endpoint_path.write_text(json.dumps(endpoint), encoding="utf-8")

    result = verifier.verify(
        artifact, endpoint_path, profile="full", min_samples=2
    )

    assert result["status"] == "PASS", result["failures"]
    assert result["samples"] == 2
