from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest


def _load_module(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "tools" / "benchmark_carrier" / "openai_replay_carrier.py"
    module_name = f"openai_replay_carrier_test_{tmp_path.name}"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_openai_replay_carrier_load_aware_delays_batch_requests_under_overload(
    tmp_path: Path,
) -> None:
    module = _load_module(tmp_path)

    policy = module._variant_policy_for("baseline", "load-aware")
    event = {
        "serving_context": {
            "deadline_class": "batch-standard",
            "priority": 20,
        }
    }
    decision = module._policy_dispatch_decision(
        policy,
        event,
        {
            "num_requests_running": 3.0,
            "num_requests_waiting": 1.0,
            "kv_cache_usage_perc": 0.08,
        },
    )

    assert decision["action"] == "delay"
    assert decision["reason"] == "load_threshold_exceeded"


def test_openai_replay_carrier_fifo_dispatches_under_same_overload(tmp_path: Path) -> None:
    module = _load_module(tmp_path)

    policy = module._variant_policy_for("baseline", "fifo")
    event = {
        "serving_context": {
            "deadline_class": "batch-standard",
            "priority": 20,
        }
    }
    decision = module._policy_dispatch_decision(
        policy,
        event,
        {
            "num_requests_running": 3.0,
            "num_requests_waiting": 1.0,
            "kv_cache_usage_perc": 0.08,
        },
    )

    assert decision["action"] == "dispatch"
    assert decision["reason"] == "fifo_order"


def test_openai_replay_carrier_interactive_priority_bypasses_load_delay(tmp_path: Path) -> None:
    module = _load_module(tmp_path)

    policy = module._variant_policy_for("baseline", "load-aware")
    event = {
        "serving_context": {
            "deadline_class": "interactive-high",
            "priority": 100,
        }
    }
    decision = module._policy_dispatch_decision(
        policy,
        event,
        {
            "num_requests_running": 5.0,
            "num_requests_waiting": 2.0,
            "kv_cache_usage_perc": 0.1,
        },
    )

    assert decision["action"] == "dispatch"
    assert decision["reason"] == "priority_bypass"


def test_openai_replay_carrier_no_memory_aware_ignores_pure_kv_pressure(tmp_path: Path) -> None:
    module = _load_module(tmp_path)

    policy = module._variant_policy_for("baseline", "no-memory-aware")
    event = {
        "serving_context": {
            "deadline_class": "batch-standard",
            "priority": 20,
        }
    }
    decision = module._policy_dispatch_decision(
        policy,
        event,
        {
            "num_requests_running": 1.0,
            "num_requests_waiting": 0.0,
            "kv_cache_usage_perc": 0.08,
        },
    )

    assert decision["action"] == "dispatch"
    assert decision["reason"] == "below_non_memory_thresholds"


def test_openai_replay_carrier_no_memory_aware_still_delays_on_running_pressure(
    tmp_path: Path,
) -> None:
    module = _load_module(tmp_path)

    policy = module._variant_policy_for("baseline", "no-memory-aware")
    event = {
        "serving_context": {
            "deadline_class": "batch-standard",
            "priority": 20,
        }
    }
    decision = module._policy_dispatch_decision(
        policy,
        event,
        {
            "num_requests_running": 3.0,
            "num_requests_waiting": 0.0,
            "kv_cache_usage_perc": 0.0,
        },
    )

    assert decision["action"] == "delay"
    assert decision["reason"] == "non_memory_load_threshold_exceeded"


def test_openai_replay_carrier_no_profiling_uses_static_pacing_for_batch(tmp_path: Path) -> None:
    module = _load_module(tmp_path)

    policy = module._variant_policy_for("ablation", "no-profiling")
    event = {
        "serving_context": {
            "deadline_class": "batch-standard",
            "priority": 20,
        }
    }
    decision = module._policy_dispatch_decision(
        policy,
        event,
        {
            "num_requests_running": 0.0,
            "num_requests_waiting": 0.0,
            "kv_cache_usage_perc": 0.0,
        },
        elapsed_delay_s=0.0,
    )

    assert decision["action"] == "delay"
    assert decision["reason"] == "profiling_disabled_static_pacing"
    assert decision["observed_load"] == {
        "num_requests_running": None,
        "num_requests_waiting": None,
        "kv_cache_usage_perc": None,
    }


def test_openai_replay_carrier_no_profiling_dispatches_after_static_pacing(tmp_path: Path) -> None:
    module = _load_module(tmp_path)

    policy = module._variant_policy_for("ablation", "no-profiling")
    event = {
        "serving_context": {
            "deadline_class": "batch-standard",
            "priority": 20,
        }
    }
    decision = module._policy_dispatch_decision(
        policy,
        event,
        {
            "num_requests_running": 10.0,
            "num_requests_waiting": 5.0,
            "kv_cache_usage_perc": 0.2,
        },
        elapsed_delay_s=1.0,
    )

    assert decision["action"] == "dispatch"
    assert decision["reason"] == "profiling_disabled_dispatch"


def test_openai_replay_carrier_no_profiling_runtime_path_waits_before_dispatch(
    tmp_path: Path,
) -> None:
    module = _load_module(tmp_path)

    async def _run() -> dict[str, object]:
        policy = module._variant_policy_for("ablation", "no-profiling")
        policy["defer_interval_sec"] = 0.01
        policy["max_deferral_sec"] = 0.02
        policy["static_batch_delay_sec"] = 0.01
        event = {
            "serving_context": {
                "deadline_class": "batch-standard",
                "priority": 20,
            }
        }
        current_load = {
            "http://example.test": {
                "num_requests_running": 99.0,
                "num_requests_waiting": 99.0,
                "kv_cache_usage_perc": 0.99,
            }
        }
        return await module._await_policy_dispatch_window(
            event,
            "http://example.test",
            policy,
            current_load,
        )

    result = asyncio.run(_run())

    assert result["policy_mode"] == "no-profiling"
    assert result["policy_reason"] == "profiling_disabled_dispatch"
    assert float(result["dispatch_delay_s"]) >= 0.01
    assert int(result["deferral_count"]) >= 1


def test_openai_replay_carrier_full_policy_rejects_after_bounded_deferral(
    tmp_path: Path,
) -> None:
    module = _load_module(tmp_path)

    async def _run() -> dict[str, object]:
        policy = module._variant_policy_for("baseline", "full-policy")
        policy["defer_interval_sec"] = 0.01
        policy["max_deferral_sec"] = 0.02
        event = {
            "serving_context": {
                "deadline_class": "batch-standard",
                "priority": 20,
            }
        }
        current_load = {
            "http://example.test": {
                "num_requests_running": 99.0,
                "num_requests_waiting": 99.0,
                "kv_cache_usage_perc": 0.99,
            }
        }
        return await module._await_policy_dispatch_window(
            event,
            "http://example.test",
            policy,
            current_load,
        )

    result = asyncio.run(_run())

    assert result["policy_action"] == "reject"
    assert result["policy_mode"] == "load-aware"
    assert result["policy_reason"] == "admission_control_reject"
    assert int(result["deferral_count"]) >= 1


def test_openai_replay_carrier_no_admission_control_dispatches_after_bounded_deferral(
    tmp_path: Path,
) -> None:
    module = _load_module(tmp_path)

    async def _run() -> dict[str, object]:
        policy = module._variant_policy_for("ablation", "no-admission-control")
        policy["defer_interval_sec"] = 0.01
        policy["max_deferral_sec"] = 0.02
        event = {
            "serving_context": {
                "deadline_class": "batch-standard",
                "priority": 20,
            }
        }
        current_load = {
            "http://example.test": {
                "num_requests_running": 99.0,
                "num_requests_waiting": 99.0,
                "kv_cache_usage_perc": 0.99,
            }
        }
        return await module._await_policy_dispatch_window(
            event,
            "http://example.test",
            policy,
            current_load,
        )

    result = asyncio.run(_run())

    assert result["policy_action"] == "dispatch"
    assert result["policy_mode"] == "load-aware"
    assert result["policy_reason"] == "max_deferral_elapsed"
    assert int(result["deferral_count"]) >= 1


def test_openai_replay_carrier_rejects_still_unsupported_variant(tmp_path: Path) -> None:
    module = _load_module(tmp_path)

    with pytest.raises(
        ValueError,
        match=(
            "baseline:fifo, baseline:load-aware, baseline:no-memory-aware, "
            "baseline:full-policy, ablation:no-admission-control, and ablation:no-profiling"
        ),
    ):
        module._validate_direct_endpoint_variant({"kind": "baseline", "name": "no-spillover"})