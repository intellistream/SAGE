from __future__ import annotations

import asyncio
import importlib.util
import json
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

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


def _run_fake_replay_with_response_metadata(
    module: object,
    tmp_path: Path,
    response_metadata: dict[str, str],
    *,
    variant_kind: str = "baseline",
    variant_name: str = "fifo",
    execution_priority_mode: str = "off",
    deadline_class_max_tokens: dict[str, int] | None = None,
    request_deadline_class: str = "interactive-high",
    request_max_tokens: int = 8,
    current_load_snapshot: dict[str, float | None] | None = None,
    policy_trace_override: dict[str, object] | None = None,
) -> tuple[dict[str, str], dict[str, object], dict[str, object], dict[str, object], list[object]]:
    replay_path = tmp_path / "replay.jsonl"
    run_plan_path = tmp_path / "run-plan.json"
    experiment_manifest_path = tmp_path / "experiment.json"
    summary_path = tmp_path / "summary.json"
    trace_path = tmp_path / "trace.jsonl"
    raw_log_path = tmp_path / "raw-log.jsonl"

    replay_path.write_text(
        json.dumps(
            {
                "request_id": "req-1",
                "metadata": {"phase": "overload-burst", "scheduled_at_s": 0.0},
                "serving_context": {
                    "model_id": "test-model",
                    "deadline_class": request_deadline_class,
                    "priority": 100,
                    "prefix_cache_key": "tenant-a:incident-summary:v1",
                    "max_tokens": request_max_tokens,
                    "prompt_len": 4,
                    "target_ttft_ms": 200,
                    "target_e2e_ms": 800,
                    "trace_tags": {"phase": "overload-burst"},
                },
                "payload": {"input_payload": {"prompt": "Hello"}},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    run_plan_path.write_text(
        json.dumps(
            {
                "experiment": {"name": "burst-overload-baseline-matrix"},
                "systems": {"engine": "vllm-hust"},
                "metrics": {"latency": ["ttft_p50_ms", "e2e_p95_ms"]},
                "variants": [{"kind": variant_kind, "name": variant_name}],
            }
        ),
        encoding="utf-8",
    )
    experiment_manifest_path.write_text(json.dumps({"name": "burst-overload"}), encoding="utf-8")

    async def _noop_wait_for_endpoint(base_url: str, model_id: str, timeout: int) -> None:
        return None

    async def _fake_discover_served_model(base_url: str, session: object) -> str:
        return "served-test-model"

    async def _noop_poll_metrics(
        base_urls: set[str],
        interval_sec: float,
        stop_event: asyncio.Event,
        peak_load: dict[str, float | None],
        current_load: dict[str, dict[str, float | None]],
    ) -> None:
        peak_load["running_requests"] = 1.0
        peak_load["waiting_requests"] = 0.0
        peak_load["kv_cache_usage_perc"] = 0.02
        if current_load_snapshot is not None:
            for base_url in base_urls:
                current_load[base_url].update(current_load_snapshot)
        return None

    async def _fake_await_policy_dispatch_window(
        event: dict[str, object],
        base_url: str,
        policy: dict[str, object],
        current_load: dict[str, dict[str, float | None]],
    ) -> dict[str, object]:
        assert event
        assert base_url
        assert policy
        assert current_load is not None
        return dict(policy_trace_override or {})

    captured_request_inputs: list[object] = []

    async def _fake_request(_request_input: object, _session: object) -> SimpleNamespace:
        captured_request_inputs.append(_request_input)
        return SimpleNamespace(
            success=True,
            ttft=0.012,
            latency=0.045,
            output_tokens=8,
            prompt_len=4,
            error="",
            start_time=1000.01,
            response_metadata=response_metadata,
        )

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(module, "_wait_for_endpoint", _noop_wait_for_endpoint)
    monkeypatch.setattr(module, "_discover_served_model", _fake_discover_served_model)
    monkeypatch.setattr(module, "_poll_metrics", _noop_poll_metrics)
    if policy_trace_override is not None:
        monkeypatch.setattr(
            module,
            "_await_policy_dispatch_window",
            _fake_await_policy_dispatch_window,
        )
    monkeypatch.setattr(module, "_git_commit", lambda _path: "deadbeef")
    monkeypatch.setattr(module.time, "perf_counter", lambda: 1000.0)
    monkeypatch.setattr(
        module,
        "_load_vllm_benchmark_deps",
        lambda: (
            module.aiohttp.ClientTimeout(total=5),
            lambda **kwargs: SimpleNamespace(**kwargs),
            _fake_request,
        ),
    )

    try:
        result = asyncio.run(
            module._run_replay(
                Namespace(
                    experiment_manifest=str(experiment_manifest_path),
                    run_plan=str(run_plan_path),
                    workload_replay=str(replay_path),
                    variant_kind=variant_kind,
                    variant_name=variant_name,
                    summary_output=str(summary_path),
                    trace_output=str(trace_path),
                    raw_log_output=str(raw_log_path),
                    seed=42,
                    endpoint_map=json.dumps({"test-model": "http://endpoint.test"}),
                    endpoint_map_file=None,
                    metrics_poll_interval_sec=0.01,
                    ready_timeout_sec=1,
                    execution_priority_mode=execution_priority_mode,
                    deadline_class_max_tokens=(
                        json.dumps(deadline_class_max_tokens)
                        if deadline_class_max_tokens is not None
                        else None
                    ),
                    output_root=None,
                )
            )
        )
    finally:
        monkeypatch.undo()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    raw_row = json.loads(raw_log_path.read_text(encoding="utf-8").strip())
    trace_row = json.loads(trace_path.read_text(encoding="utf-8").strip())
    return result, summary, raw_row, trace_row, captured_request_inputs


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


def test_openai_replay_carrier_no_spillover_dispatches_local_fifo_under_same_overload(
    tmp_path: Path,
) -> None:
    module = _load_module(tmp_path)

    module._validate_direct_endpoint_variant({"kind": "baseline", "name": "no-spillover"})
    policy = module._variant_policy_for("baseline", "no-spillover")
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

    assert policy["spillover_enabled"] is False
    assert decision["action"] == "dispatch"
    assert decision["reason"] == "fifo_order"


def test_openai_replay_carrier_prism_style_static_sharing_is_fixed_endpoint_fifo(
    tmp_path: Path,
) -> None:
    module = _load_module(tmp_path)

    module._validate_direct_endpoint_variant(
        {"kind": "baseline", "name": "prism-style-static-sharing"}
    )
    policy = module._variant_policy_for("baseline", "prism-style-static-sharing")
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

    assert policy["policy_family"] == "prism-style"
    assert policy["sharing_model"] == "static-per-model-endpoint"
    assert decision["action"] == "dispatch"
    assert decision["reason"] == "fifo_order"


def test_openai_replay_carrier_prism_style_elastic_sharing_defers_on_memory_pressure(
    tmp_path: Path,
) -> None:
    module = _load_module(tmp_path)

    module._validate_direct_endpoint_variant(
        {"kind": "baseline", "name": "prism-style-elastic-sharing"}
    )
    policy = module._variant_policy_for("baseline", "prism-style-elastic-sharing")
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

    assert policy["policy_family"] == "prism-style"
    assert policy["sharing_model"] == "elastic-load-and-memory-aware-deferral"
    assert decision["action"] == "delay"
    assert decision["reason"] == "load_threshold_exceeded"


def test_openai_replay_carrier_prism_style_two_level_scheduler_ignores_memory_pressure(
    tmp_path: Path,
) -> None:
    module = _load_module(tmp_path)

    module._validate_direct_endpoint_variant(
        {"kind": "baseline", "name": "prism-style-two-level-scheduler"}
    )
    policy = module._variant_policy_for("baseline", "prism-style-two-level-scheduler")
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

    assert policy["policy_family"] == "prism-style"
    assert policy["use_memory_signal"] is False
    assert policy["admission_control"] is True
    assert decision["action"] == "dispatch"
    assert decision["reason"] == "below_non_memory_thresholds"


def test_openai_replay_carrier_vamos_slo_feasibility_controller_shapes_deadline_caps(
    tmp_path: Path,
) -> None:
    module = _load_module(tmp_path)

    module._validate_direct_endpoint_variant(
        {"kind": "baseline", "name": "vamos-slo-feasibility-controller"}
    )
    policy = module._variant_policy_for("baseline", "vamos-slo-feasibility-controller")
    controller, source = module._resolve_deadline_class_max_tokens(
        Namespace(deadline_class_max_tokens=None),
        policy,
    )
    caps, profile = module._deadline_class_max_tokens_for_request(
        policy,
        controller,
        {
            "num_requests_running": 3.0,
            "num_requests_waiting": 0.0,
            "kv_cache_usage_perc": 0.08,
        },
    )

    assert policy["policy_family"] == "vamos"
    assert source == "variant_policy"
    assert profile == "static"
    assert caps["interactive-high"] == 16
    assert caps["batch-standard"] == 64
    assert caps["long-generation-standard"] == 64


def test_openai_replay_carrier_vamos_slo_rescue_no_reject_keeps_caps_without_admission_reject(
    tmp_path: Path,
) -> None:
    module = _load_module(tmp_path)

    module._validate_direct_endpoint_variant(
        {"kind": "baseline", "name": "vamos-slo-rescue-no-reject"}
    )
    policy = module._variant_policy_for("baseline", "vamos-slo-rescue-no-reject")
    controller, source = module._resolve_deadline_class_max_tokens(
        Namespace(deadline_class_max_tokens=None),
        policy,
    )
    caps, _ = module._deadline_class_max_tokens_for_request(
        policy,
        controller,
        {
            "num_requests_running": 3.0,
            "num_requests_waiting": 0.0,
            "kv_cache_usage_perc": 0.08,
        },
    )

    assert source == "variant_policy"
    assert caps["interactive-high"] == 16
    assert caps["batch-standard"] == 64
    assert policy["admission_control"] is False


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


def test_openai_replay_carrier_inverts_vamos_priority_for_vllm(tmp_path: Path) -> None:
    module = _load_module(tmp_path)

    assert module._map_execution_priority({"priority": 100}, "invert-vamos") == -100
    assert module._map_execution_priority({"priority": 20}, "invert-vamos") == -20
    assert module._map_execution_priority({"priority": 20}, "off") is None


def test_openai_replay_carrier_parses_prefix_cache_metrics_from_prometheus_snapshot(
    tmp_path: Path,
) -> None:
    module = _load_module(tmp_path)

    snapshot = module._parse_load_metrics_snapshot(
        "\n".join(
            [
                "vllm:num_requests_running{engine=\"0\"} 2",
                "vllm:num_requests_waiting{engine=\"0\"} 1",
                "vllm:kv_cache_usage_perc{engine=\"0\"} 0.25",
                "vllm:prefix_cache_queries_total{engine=\"0\"} 100",
                "vllm:prefix_cache_hits_total{engine=\"0\"} 40",
                "vllm:external_prefix_cache_queries_total{engine=\"0\"} 20",
                "vllm:external_prefix_cache_hits_total{engine=\"0\"} 5",
                "vllm:prefix_cache_queries_total{engine=\"1\"} 50",
                "vllm:prefix_cache_hits_total{engine=\"1\"} 15",
            ]
        )
    )

    assert snapshot == {
        "num_requests_running": 2.0,
        "num_requests_waiting": 1.0,
        "kv_cache_usage_perc": 0.25,
        "prefix_cache_queries": 150.0,
        "prefix_cache_hits": 55.0,
        "external_prefix_cache_queries": 20.0,
        "external_prefix_cache_hits": 5.0,
    }


def test_openai_replay_carrier_build_metrics_emits_prefix_cache_deltas_and_rates(
    tmp_path: Path,
) -> None:
    module = _load_module(tmp_path)

    metrics = module._build_metrics(
        {
            "metrics": {
                "cache": [
                    "prefix_cache_queries_delta",
                    "prefix_cache_hits_delta",
                    "prefix_cache_hit_rate",
                    "external_prefix_cache_queries_delta",
                    "external_prefix_cache_hits_delta",
                    "external_prefix_cache_hit_rate",
                ]
            }
        },
        [
            {
                "success": True,
                "ttft_ms": 100.0,
                "e2e_ms": 200.0,
                "slo_violated": False,
                "used_spillover": False,
                "scheduled_at_s": 0.0,
                "started_at_s": 0.0,
                "completed_at_s": 1.0,
            }
        ],
        {
            "running_requests": 1.0,
            "waiting_requests": 0.0,
            "kv_cache_usage_perc": 0.3,
            "prefix_cache_queries_start": 100.0,
            "prefix_cache_queries_end": 160.0,
            "prefix_cache_hits_start": 30.0,
            "prefix_cache_hits_end": 75.0,
            "external_prefix_cache_queries_start": 10.0,
            "external_prefix_cache_queries_end": 18.0,
            "external_prefix_cache_hits_start": 2.0,
            "external_prefix_cache_hits_end": 6.0,
        },
    )

    assert metrics["prefix_cache_queries_delta"] == 60.0
    assert metrics["prefix_cache_hits_delta"] == 45.0
    assert metrics["prefix_cache_hit_rate"] == 0.75
    assert metrics["external_prefix_cache_queries_delta"] == 8.0
    assert metrics["external_prefix_cache_hits_delta"] == 4.0
    assert metrics["external_prefix_cache_hit_rate"] == 0.5


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
            "baseline:fifo, baseline:balanced-operating-point, baseline:load-aware, baseline:no-spillover, baseline:no-memory-aware, baseline:full-policy, baseline:prism-style-static-sharing, baseline:prism-style-elastic-sharing, baseline:prism-style-two-level-scheduler, baseline:vamos-slo-feasibility-controller, baseline:vamos-slo-rescue-no-reject, ablation:aggressive-upper-bound, ablation:no-admission-control, ablation:no-profiling, and ablation:adaptive-controller"
        ),
    ):
        module._validate_direct_endpoint_variant({"kind": "ablation", "name": "no-prefix-cache-signal"})


def test_openai_replay_carrier_persists_response_metadata_in_raw_log_and_trace(
    tmp_path: Path,
) -> None:
    module = _load_module(tmp_path)
    result, summary, raw_row, trace_row, captured_request_inputs = _run_fake_replay_with_response_metadata(
        module,
        tmp_path,
        {
            "x-vllm-backend-id": "served-test-model",
            "x-vllm-endpoint-pool-id": "single-endpoint:served-test-model",
            "x-vllm-backend-scope": "local",
            "x-vllm-route-outcome": "local_only",
        },
        execution_priority_mode="invert-vamos",
    )

    assert result["raw_log_output"].endswith("raw-log.jsonl")
    assert summary["execution_metadata"]["execution_priority_mode"] == "invert-vamos"
    assert raw_row["response_metadata"] == {
        "x-vllm-backend-id": "served-test-model",
        "x-vllm-endpoint-pool-id": "single-endpoint:served-test-model",
        "x-vllm-backend-scope": "local",
        "x-vllm-route-outcome": "local_only",
    }
    assert raw_row["execution_priority"] == -100
    assert raw_row["used_spillover"] is False
    assert summary["metrics"]["spillover_rate"] == 0.0
    assert summary["request_mix"]["route_outcome_counts"] == {"local_only": 1}
    assert summary["request_mix"]["backend_scope_counts"] == {"local": 1}
    assert summary["request_mix"]["prefix_cache_key_counts"] == {
        "tenant-a:incident-summary:v1": 1
    }
    assert raw_row["prefix_cache_key"] == "tenant-a:incident-summary:v1"
    assert trace_row["decision_trace"]["execution_priority"] == -100
    assert trace_row["decision_trace"]["prefix_cache_key"] == "tenant-a:incident-summary:v1"
    assert trace_row["prefix_cache_key"] == "tenant-a:incident-summary:v1"
    assert trace_row["decision_trace"]["response_metadata"] == raw_row["response_metadata"]
    assert len(captured_request_inputs) == 1
    assert getattr(captured_request_inputs[0], "extra_body") == {
        "priority": -100,
        "cache_salt": "tenant-a:incident-summary:v1",
        "prefix_cache_key": "tenant-a:incident-summary:v1",
    }


def test_openai_replay_carrier_caps_deadline_class_max_tokens_before_dispatch(
    tmp_path: Path,
) -> None:
    module = _load_module(tmp_path)
    _, summary, raw_row, trace_row, captured_request_inputs = _run_fake_replay_with_response_metadata(
        module,
        tmp_path,
        {
            "x-vllm-backend-id": "served-test-model",
            "x-vllm-endpoint-pool-id": "single-endpoint:served-test-model",
            "x-vllm-backend-scope": "local",
            "x-vllm-route-outcome": "local_only",
        },
        deadline_class_max_tokens={"interactive-high": 4},
    )

    assert summary["execution_metadata"]["deadline_class_max_tokens"] == {"interactive-high": 4}
    assert raw_row["requested_max_tokens"] == 8
    assert raw_row["effective_max_tokens"] == 4
    assert trace_row["decision_trace"]["requested_max_tokens"] == 8
    assert trace_row["decision_trace"]["effective_max_tokens"] == 4
    assert len(captured_request_inputs) == 1
    assert getattr(captured_request_inputs[0], "output_len") == 4


def test_openai_replay_carrier_variant_policy_caps_deadline_class_max_tokens_before_dispatch(
    tmp_path: Path,
) -> None:
    module = _load_module(tmp_path)
    _, summary, raw_row, trace_row, captured_request_inputs = _run_fake_replay_with_response_metadata(
        module,
        tmp_path,
        {
            "x-vllm-backend-id": "served-test-model",
            "x-vllm-endpoint-pool-id": "single-endpoint:served-test-model",
            "x-vllm-backend-scope": "local",
            "x-vllm-route-outcome": "local_only",
        },
        variant_kind="baseline",
        variant_name="balanced-operating-point",
        request_deadline_class="batch-standard",
        request_max_tokens=512,
    )

    assert summary["execution_metadata"]["deadline_class_max_tokens"] == {
        "interactive-high": 384,
        "batch-standard": 256,
    }
    assert summary["execution_metadata"]["deadline_class_max_tokens_source"] == "variant_policy"
    assert raw_row["requested_max_tokens"] == 512
    assert raw_row["effective_max_tokens"] == 256
    assert trace_row["decision_trace"]["requested_max_tokens"] == 512
    assert trace_row["decision_trace"]["effective_max_tokens"] == 256
    assert len(captured_request_inputs) == 1
    assert getattr(captured_request_inputs[0], "output_len") == 256


def test_openai_replay_carrier_rejects_cli_caps_when_variant_policy_already_defines_them(
    tmp_path: Path,
) -> None:
    module = _load_module(tmp_path)

    with pytest.raises(
        ValueError,
        match="Variant policy already defines deadline class max token control",
    ):
        _run_fake_replay_with_response_metadata(
            module,
            tmp_path,
            {
                "x-vllm-backend-id": "served-test-model",
                "x-vllm-endpoint-pool-id": "single-endpoint:served-test-model",
                "x-vllm-backend-scope": "local",
                "x-vllm-route-outcome": "local_only",
            },
            variant_kind="baseline",
            variant_name="balanced-operating-point",
            deadline_class_max_tokens={"interactive-high": 4},
        )


def test_openai_replay_carrier_adaptive_controller_uses_default_cap_profile_below_thresholds(
    tmp_path: Path,
) -> None:
    module = _load_module(tmp_path)
    _, summary, raw_row, trace_row, captured_request_inputs = _run_fake_replay_with_response_metadata(
        module,
        tmp_path,
        {
            "x-vllm-backend-id": "served-test-model",
            "x-vllm-endpoint-pool-id": "single-endpoint:served-test-model",
            "x-vllm-backend-scope": "local",
            "x-vllm-route-outcome": "local_only",
        },
        variant_kind="ablation",
        variant_name="adaptive-controller",
        request_deadline_class="interactive-high",
        request_max_tokens=512,
        current_load_snapshot={
            "num_requests_running": 1.0,
            "num_requests_waiting": 0.0,
            "kv_cache_usage_perc": 0.01,
        },
    )

    assert summary["execution_metadata"]["adaptive_deadline_class_max_tokens"] == {
        "default": {"interactive-high": 384, "batch-standard": 256},
        "overload": {"interactive-high": 256, "batch-standard": 256},
    }
    assert summary["execution_metadata"]["deadline_class_max_tokens_source"] == "variant_policy"
    assert raw_row["deadline_class_cap_profile"] == "default"
    assert raw_row["deadline_class_cap_source"] == "variant_policy"
    assert raw_row["requested_max_tokens"] == 512
    assert raw_row["effective_max_tokens"] == 384
    assert trace_row["decision_trace"]["deadline_class_cap_profile"] == "default"
    assert trace_row["decision_trace"]["deadline_class_cap_source"] == "variant_policy"
    assert len(captured_request_inputs) == 1
    assert getattr(captured_request_inputs[0], "output_len") == 384


def test_openai_replay_carrier_adaptive_controller_uses_overload_cap_profile_under_load(
    tmp_path: Path,
) -> None:
    module = _load_module(tmp_path)
    _, summary, raw_row, trace_row, captured_request_inputs = _run_fake_replay_with_response_metadata(
        module,
        tmp_path,
        {
            "x-vllm-backend-id": "served-test-model",
            "x-vllm-endpoint-pool-id": "single-endpoint:served-test-model",
            "x-vllm-backend-scope": "local",
            "x-vllm-route-outcome": "local_only",
        },
        variant_kind="ablation",
        variant_name="adaptive-controller",
        request_deadline_class="interactive-high",
        request_max_tokens=512,
        current_load_snapshot={
            "num_requests_running": 3.0,
            "num_requests_waiting": 0.0,
            "kv_cache_usage_perc": 0.06,
        },
    )

    assert summary["execution_metadata"]["adaptive_deadline_class_max_tokens"] == {
        "default": {"interactive-high": 384, "batch-standard": 256},
        "overload": {"interactive-high": 256, "batch-standard": 256},
    }
    assert raw_row["deadline_class_cap_profile"] == "overload"
    assert raw_row["requested_max_tokens"] == 512
    assert raw_row["effective_max_tokens"] == 256
    assert trace_row["decision_trace"]["deadline_class_cap_profile"] == "overload"
    assert len(captured_request_inputs) == 1
    assert getattr(captured_request_inputs[0], "output_len") == 256


def test_openai_replay_carrier_adaptive_controller_recomputes_cap_profile_at_dispatch_time(
    tmp_path: Path,
) -> None:
    module = _load_module(tmp_path)
    _, summary, raw_row, trace_row, captured_request_inputs = _run_fake_replay_with_response_metadata(
        module,
        tmp_path,
        {
            "x-vllm-backend-id": "served-test-model",
            "x-vllm-endpoint-pool-id": "single-endpoint:served-test-model",
            "x-vllm-backend-scope": "local",
            "x-vllm-route-outcome": "local_only",
        },
        variant_kind="ablation",
        variant_name="adaptive-controller",
        request_deadline_class="interactive-high",
        request_max_tokens=512,
        current_load_snapshot={
            "num_requests_running": 0.0,
            "num_requests_waiting": 0.0,
            "kv_cache_usage_perc": 0.0,
        },
        policy_trace_override={
            "policy_action": "dispatch",
            "policy_mode": "fifo",
            "policy_reason": "fifo_order",
            "dispatch_delay_s": 0.0,
            "deferral_count": 0,
            "observed_load": {
                "num_requests_running": 4.0,
                "num_requests_waiting": 0.0,
                "kv_cache_usage_perc": 0.06,
            },
        },
    )

    assert summary["execution_metadata"]["adaptive_deadline_class_max_tokens"] == {
        "default": {"interactive-high": 384, "batch-standard": 256},
        "overload": {"interactive-high": 256, "batch-standard": 256},
    }
    assert raw_row["deadline_class_cap_profile"] == "overload"
    assert trace_row["decision_trace"]["deadline_class_cap_profile"] == "overload"
    assert raw_row["effective_max_tokens"] == 256
    assert len(captured_request_inputs) == 1
    assert getattr(captured_request_inputs[0], "output_len") == 256


def test_openai_replay_carrier_derives_spillover_rate_from_response_metadata(
    tmp_path: Path,
) -> None:
    module = _load_module(tmp_path)
    _, summary, raw_row, trace_row, _ = _run_fake_replay_with_response_metadata(
        module,
        tmp_path,
        {
            "x-vllm-backend-id": "served-remote-model",
            "x-vllm-endpoint-pool-id": "pool-b",
            "x-vllm-backend-scope": "remote",
            "x-vllm-route-outcome": "spillover_remote",
        },
    )

    assert raw_row["used_spillover"] is True
    assert trace_row["decision_trace"]["used_spillover"] is True
    assert summary["metrics"]["spillover_rate"] == 1.0
    assert summary["request_mix"]["route_outcome_counts"] == {"spillover_remote": 1}
    assert summary["request_mix"]["backend_scope_counts"] == {"remote": 1}