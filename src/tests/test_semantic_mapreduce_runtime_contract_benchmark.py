from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_benchmark_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "tools"
        / "benchmark_carrier"
        / "run_semantic_mapreduce_runtime_contract.py"
    )
    spec = importlib.util.spec_from_file_location("semantic_mapreduce_runtime_contract", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runtime_contract_matrix_preserves_state_and_replays() -> None:
    module = _load_benchmark_module()
    rows = module.run_contract_matrix()

    assert len(rows) == 27
    assert {row["scenario"] for row in rows} == set(module.SCENARIOS)
    assert all(row["valid_schema"] for row in rows)
    assert all(row["valid_state_changed"] for row in rows)
    assert all(row["baseline_digest"] != row["committed_digest"] for row in rows)
    assert all(row["invalid_schema_rejected"] for row in rows)
    assert all(row["invalid_preserved_baseline"] for row in rows)
    assert all(row["checkpoint_preserved_commit"] for row in rows)
    assert all(row["checkpoint_independent_of_failed_live_state"] for row in rows)
    assert all(row["checkpoint_source"] == "supplied-snapshot" for row in rows)
    assert all(row["replay_deterministic"] for row in rows)
    assert all(row["recovery_status"] == "checkpoint_restored" for row in rows)
