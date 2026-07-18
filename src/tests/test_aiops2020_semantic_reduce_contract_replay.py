from __future__ import annotations

import importlib.util
from pathlib import Path


def _module():
    path = (
        Path(__file__).resolve().parents[2]
        / "tools"
        / "benchmark_carrier"
        / "run_aiops2020_semantic_reduce_contract_replay.py"
    )
    spec = importlib.util.spec_from_file_location("aiops_contract_replay", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_public_contract_rejects_missing_reference_and_replays() -> None:
    module = _module()
    rows = [
        {
            "evidence_id": "public-e1",
            "source_ref": "AIOps2020:window:1",
            "object_type": "docker",
            "object_id": "container-a",
            "fault_type": "cpu",
            "start_ms": 1,
            "max_robust_shift": 4.5,
            "expected_fault": True,
            "predicted_fault": True,
        },
        {
            "evidence_id": "public-negative",
            "source_ref": "AIOps2020:window:2",
            "object_type": "docker",
            "object_id": "container-b",
            "fault_type": "none",
            "start_ms": 2,
            "max_robust_shift": 0.2,
            "expected_fault": False,
            "predicted_fault": False,
        },
    ]

    result = module.run_contract(rows)

    assert result["status"] == "PASS"
    assert result["evidence_count"] == 1
    assert result["valid_commit"] is True
    assert result["invalid_reference_rejected"] is True
    assert result["baseline_preserved_after_rejection"] is True
    assert result["deterministic_replay"] is True
    assert "not" in result["boundary"].lower()
