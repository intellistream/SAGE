from __future__ import annotations

import importlib.util
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
