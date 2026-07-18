from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "tools"
        / "benchmark_carrier"
        / "run_aiops2020_public_replay.py"
    )
    spec = importlib.util.spec_from_file_location("aiops2020_public_replay", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_aiops_timestamp_matches_published_daily_epoch() -> None:
    module = _load_module()
    assert module._timestamp_ms("2020/5/29 3:41") == 1590694860000


def test_robust_shift_has_finite_floor_for_constant_baseline() -> None:
    module = _load_module()
    score = module._robust_shift([0.0] * 10, [2.0, 2.0, 2.0])
    assert score is not None
    assert score["robust_shift"] == 2.0
