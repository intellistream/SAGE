from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import math
import platform
import socket
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp


SUPPORTED_DIRECT_ENDPOINT_VARIANTS = frozenset(
    {
        ("baseline", "fifo"),
        ("baseline", "balanced-operating-point"),
        ("baseline", "load-aware"),
        ("baseline", "no-spillover"),
        ("baseline", "no-memory-aware"),
        ("baseline", "full-policy"),
        ("baseline", "prism-style-static-sharing"),
        ("baseline", "prism-style-elastic-sharing"),
        ("baseline", "prism-style-two-level-scheduler"),
        ("baseline", "vamos-slo-feasibility-controller"),
        ("baseline", "vamos-slo-rescue-no-reject"),
        ("baseline", "wfq-token-budget"),
        ("baseline", "strict-priority-preempt"),
        ("ablation", "aggressive-upper-bound"),
        ("ablation", "no-admission-control"),
        ("ablation", "no-profiling"),
        ("ablation", "adaptive-controller"),
        ("ablation", "graduated-shaping"),
        ("ablation", "risk-aware-shaping"),
        ("ablation", "cap-sweep-24"),
        ("ablation", "cap-sweep-32"),
        ("ablation", "cap-sweep-48"),
    }
)
_VLLM_BENCHMARK_DEPS: tuple[Any, Any, Any] | None = None
_DIRECT_ENDPOINT_VARIANT_POLICIES: dict[tuple[str, str], dict[str, Any]] = {
    ("baseline", "fifo"): {
        "mode": "fifo",
    },
    ("baseline", "balanced-operating-point"): {
        "mode": "fifo",
        "deadline_class_max_tokens": {
            "interactive-high": 384,
            "batch-standard": 256,
        },
    },
    ("baseline", "no-spillover"): {
        "mode": "fifo",
        "spillover_enabled": False,
    },
    ("baseline", "load-aware"): {
        "mode": "load-aware",
        "defer_interval_sec": 0.5,
        "max_deferral_sec": 4.0,
        "running_threshold": 2.0,
        "waiting_threshold": 0.0,
        "kv_cache_threshold": 0.05,
        "priority_cutoff": 50,
    },
    ("baseline", "no-memory-aware"): {
        "mode": "load-aware",
        "defer_interval_sec": 0.5,
        "max_deferral_sec": 4.0,
        "running_threshold": 2.0,
        "waiting_threshold": 0.0,
        "priority_cutoff": 50,
        "use_memory_signal": False,
    },
    ("baseline", "full-policy"): {
        "mode": "load-aware",
        "defer_interval_sec": 0.5,
        "max_deferral_sec": 4.0,
        "running_threshold": 2.0,
        "waiting_threshold": 0.0,
        "kv_cache_threshold": 0.05,
        "priority_cutoff": 50,
        "admission_control": True,
    },
    ("baseline", "prism-style-static-sharing"): {
        "mode": "fifo",
        "spillover_enabled": False,
        "policy_family": "prism-style",
        "sharing_model": "static-per-model-endpoint",
    },
    ("baseline", "prism-style-elastic-sharing"): {
        "mode": "load-aware",
        "defer_interval_sec": 0.5,
        "max_deferral_sec": 4.0,
        "running_threshold": 2.0,
        "waiting_threshold": 0.0,
        "kv_cache_threshold": 0.05,
        "priority_cutoff": 50,
        "admission_control": False,
        "policy_family": "prism-style",
        "sharing_model": "elastic-load-and-memory-aware-deferral",
    },
    ("baseline", "prism-style-two-level-scheduler"): {
        "mode": "load-aware",
        "defer_interval_sec": 0.5,
        "max_deferral_sec": 4.0,
        "running_threshold": 2.0,
        "waiting_threshold": 0.0,
        "priority_cutoff": 50,
        "use_memory_signal": False,
        "admission_control": True,
        "policy_family": "prism-style",
        "sharing_model": "priority-admission-without-vram-signal",
    },
    ("baseline", "vamos-slo-feasibility-controller"): {
        "mode": "load-aware",
        "defer_interval_sec": 0.25,
        "max_deferral_sec": 2.0,
        "running_threshold": 2.0,
        "waiting_threshold": 0.0,
        "kv_cache_threshold": 0.05,
        "priority_cutoff": 50,
        "admission_control": True,
        "policy_family": "vamos",
        "control_objective": "slo-feasible-token-reshaping",
        "deadline_class_max_tokens": {
            "interactive-high": 16,
            "batch-standard": 64,
            "long-generation-standard": 64,
        },
    },
    ("baseline", "vamos-slo-rescue-no-reject"): {
        "mode": "load-aware",
        "defer_interval_sec": 0.25,
        "max_deferral_sec": 2.0,
        "running_threshold": 2.0,
        "waiting_threshold": 0.0,
        "kv_cache_threshold": 0.05,
        "priority_cutoff": 50,
        "admission_control": False,
        "policy_family": "vamos",
        "control_objective": "slo-feasible-token-reshaping-with-background-preservation",
        "deadline_class_max_tokens": {
            "interactive-high": 16,
            "batch-standard": 64,
            "long-generation-standard": 64,
        },
    },
    ("baseline", "wfq-token-budget"): {
        "mode": "wfq",
        "policy_family": "classical-qos",
        "control_objective": "weighted-fair-token-allocation",
        "wfq_class_weights": {
            "interactive-high": 0.70,
            "batch-standard": 0.20,
            "long-generation-standard": 0.10,
        },
        "wfq_window_sec": 5.0,
        "wfq_total_budget_per_window": 2048,
    },
    ("baseline", "strict-priority-preempt"): {
        "mode": "strict-priority",
        "policy_family": "classical-qos",
        "control_objective": "strict-priority-with-batch-preemption",
        "priority_cutoff": 50,
        "preempt_batch_to_current_tokens": True,
        "max_concurrent_batch": 2,
    },
    ("ablation", "no-admission-control"): {
        "mode": "load-aware",
        "defer_interval_sec": 0.5,
        "max_deferral_sec": 4.0,
        "running_threshold": 2.0,
        "waiting_threshold": 0.0,
        "kv_cache_threshold": 0.05,
        "priority_cutoff": 50,
        "admission_control": False,
    },
    ("ablation", "no-profiling"): {
        "mode": "no-profiling",
        "defer_interval_sec": 0.5,
        "max_deferral_sec": 1.0,
        "static_batch_delay_sec": 1.0,
        "priority_cutoff": 50,
    },
    ("ablation", "adaptive-controller"): {
        "mode": "fifo",
        "running_threshold": 2.0,
        "waiting_threshold": 0.0,
        "kv_cache_threshold": 0.05,
        "adaptive_deadline_class_max_tokens": {
            "default": {
                "interactive-high": 384,
                "batch-standard": 256,
            },
            "overload": {
                "interactive-high": 256,
                "batch-standard": 256,
            },
        },
    },
    ("ablation", "aggressive-upper-bound"): {
        "mode": "fifo",
        "deadline_class_max_tokens": {
            "interactive-high": 256,
            "batch-standard": 256,
        },
    },
    ("ablation", "graduated-shaping"): {
        "mode": "load-aware",
        "defer_interval_sec": 0.25,
        "max_deferral_sec": 2.0,
        "running_threshold": 2.0,
        "waiting_threshold": 0.0,
        "kv_cache_threshold": 0.05,
        "priority_cutoff": 50,
        "admission_control": False,
        "policy_family": "vamos",
        "control_objective": "graduated-load-proportional-shaping",
        "graduated_shaping": {
            "interactive-high": {"max_cap": 384, "min_cap": 16},
            "batch-standard": {"max_cap": 256, "min_cap": 64},
            "long-generation-standard": {"max_cap": 256, "min_cap": 64},
        },
    },
    ("ablation", "risk-aware-shaping"): {
        "mode": "load-aware",
        "defer_interval_sec": 0.25,
        "max_deferral_sec": 2.0,
        "running_threshold": 2.0,
        "waiting_threshold": 0.0,
        "kv_cache_threshold": 0.05,
        "priority_cutoff": 50,
        "admission_control": False,
        "policy_family": "vamos",
        "control_objective": "risk-aware-selective-shaping",
        "risk_aware_shaping": {
            "base_decode_ms_per_token": 25.0,
            "load_factor_per_running": 0.5,
            "base_ttft_ms": 150.0,
            "interactive-high": {"max_cap": 384, "min_cap": 16},
            "batch-standard": {"max_cap": 256, "min_cap": 64},
            "long-generation-standard": {"max_cap": 256, "min_cap": 64},
        },
    },
    ("ablation", "cap-sweep-24"): {
        "mode": "load-aware",
        "defer_interval_sec": 0.25,
        "max_deferral_sec": 2.0,
        "running_threshold": 2.0,
        "waiting_threshold": 0.0,
        "kv_cache_threshold": 0.05,
        "priority_cutoff": 50,
        "admission_control": False,
        "policy_family": "vamos",
        "control_objective": "slo-feasible-token-reshaping-with-background-preservation",
        "deadline_class_max_tokens": {
            "interactive-high": 24,
            "batch-standard": 64,
            "long-generation-standard": 64,
        },
    },
    ("ablation", "cap-sweep-32"): {
        "mode": "load-aware",
        "defer_interval_sec": 0.25,
        "max_deferral_sec": 2.0,
        "running_threshold": 2.0,
        "waiting_threshold": 0.0,
        "kv_cache_threshold": 0.05,
        "priority_cutoff": 50,
        "admission_control": False,
        "policy_family": "vamos",
        "control_objective": "slo-feasible-token-reshaping-with-background-preservation",
        "deadline_class_max_tokens": {
            "interactive-high": 32,
            "batch-standard": 64,
            "long-generation-standard": 64,
        },
    },
    ("ablation", "cap-sweep-48"): {
        "mode": "load-aware",
        "defer_interval_sec": 0.25,
        "max_deferral_sec": 2.0,
        "running_threshold": 2.0,
        "waiting_threshold": 0.0,
        "kv_cache_threshold": 0.05,
        "priority_cutoff": 50,
        "admission_control": False,
        "policy_family": "vamos",
        "control_objective": "slo-feasible-token-reshaping-with-background-preservation",
        "deadline_class_max_tokens": {
            "interactive-high": 48,
            "batch-standard": 64,
            "long-generation-standard": 64,
        },
    },
}

_EXECUTION_PRIORITY_MODES = ("off", "invert-vamos")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Replay a VAMOS burst-overload workload against real vllm-hust "
            "OpenAI-compatible endpoints and archive summary/log/trace artifacts."
        )
    )
    parser.add_argument("--experiment-manifest", required=True)
    parser.add_argument("--run-plan", required=True)
    parser.add_argument("--workload-replay", required=True)
    parser.add_argument("--variant-kind", required=True, choices=["baseline", "ablation"])
    parser.add_argument("--variant-name", required=True)
    parser.add_argument("--summary-output", required=True)
    parser.add_argument("--trace-output", required=True)
    parser.add_argument("--raw-log-output", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument(
        "--endpoint-map",
        help=(
            "JSON object mapping replay model_id values to base URLs, for example "
            "'{\"meta-llama/Llama-3.1-8B-Instruct\":\"http://127.0.0.1:8101\"}'."
        ),
    )
    parser.add_argument(
        "--endpoint-map-file",
        help="Path to a JSON file containing the model_id -> base_url endpoint map.",
    )
    parser.add_argument(
        "--metrics-poll-interval-sec",
        type=float,
        default=1.0,
        help="Polling interval for Prometheus /metrics sampling while the replay is running.",
    )
    parser.add_argument(
        "--ready-timeout-sec",
        type=int,
        default=900,
        help="Maximum time to wait for each configured endpoint to become ready.",
    )
    parser.add_argument(
        "--execution-priority-mode",
        choices=_EXECUTION_PRIORITY_MODES,
        default="off",
        help=(
            "How to propagate replay priority into the execution plane. "
            "'invert-vamos' maps larger VAMOS priority values to smaller vLLM "
            "priority values so endpoints started with --scheduling-policy priority "
            "can honor interactive requests earlier."
        ),
    )
    parser.add_argument(
        "--deadline-class-max-tokens",
        help=(
            "Optional JSON object mapping deadline_class values to explicit max_tokens caps, "
            "for example '{\"interactive-high\":512,\"batch-standard\":64}'. "
            "When set, the replay request budget is clamped to the smaller of the replay "
            "value and the configured class cap."
        ),
    )
    parser.add_argument(
        "--output-root",
        help=(
            "Optional sandbox root for emitted artifacts. When set, output paths are rewritten under this root "
            "using the path suffix that begins at results/."
        ),
    )
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _load_vllm_benchmark_deps() -> tuple[Any, Any, Any]:
    global _VLLM_BENCHMARK_DEPS
    if _VLLM_BENCHMARK_DEPS is None:
        from vllm.benchmarks.lib.endpoint_request_func import (
            AIOHTTP_TIMEOUT,
            RequestFuncInput,
            async_request_openai_completions,
        )

        _VLLM_BENCHMARK_DEPS = (
            AIOHTTP_TIMEOUT,
            RequestFuncInput,
            async_request_openai_completions,
        )
    return _VLLM_BENCHMARK_DEPS


def _load_endpoint_map(args: argparse.Namespace) -> dict[str, str]:
    raw_value = args.endpoint_map
    if args.endpoint_map_file:
        raw_value = Path(args.endpoint_map_file).read_text(encoding="utf-8")
    if raw_value is None:
        raw_value = Path(args.run_plan).resolve().parent.joinpath("burst-overload-endpoints.json")
        if Path(raw_value).exists():
            raw_value = Path(raw_value).read_text(encoding="utf-8")
        else:
            raw_value = None
    if raw_value is None:
        raise ValueError("Missing endpoint map. Use --endpoint-map or --endpoint-map-file.")
    endpoint_map = json.loads(raw_value)
    if not isinstance(endpoint_map, dict) or not endpoint_map:
        raise ValueError("Endpoint map must be a non-empty JSON object.")
    normalized: dict[str, str] = {}
    for model_id, base_url in endpoint_map.items():
        normalized[str(model_id)] = str(base_url).rstrip("/")
    return normalized


def _load_deadline_class_max_tokens(args: argparse.Namespace) -> dict[str, int]:
    raw_value = getattr(args, "deadline_class_max_tokens", None)
    if raw_value is None:
        return {}
    payload = json.loads(raw_value)
    if not isinstance(payload, dict):
        raise ValueError("--deadline-class-max-tokens must be a JSON object.")
    caps: dict[str, int] = {}
    for deadline_class, max_tokens in payload.items():
        cap_value = int(max_tokens)
        if cap_value <= 0:
            raise ValueError(
                "--deadline-class-max-tokens values must be positive integers; "
                f"got {max_tokens!r} for {deadline_class!r}."
            )
        caps[str(deadline_class)] = cap_value
    return caps


def _normalize_deadline_class_max_tokens(
    raw_value: Any,
    *,
    source_label: str,
) -> dict[str, int]:
    if raw_value is None:
        return {}
    if not isinstance(raw_value, dict):
        raise ValueError(f"{source_label} deadline_class_max_tokens must be a JSON object.")
    caps: dict[str, int] = {}
    for deadline_class, max_tokens in raw_value.items():
        cap_value = int(max_tokens)
        if cap_value <= 0:
            raise ValueError(
                f"{source_label} deadline_class_max_tokens values must be positive integers; "
                f"got {max_tokens!r} for {deadline_class!r}."
            )
        caps[str(deadline_class)] = cap_value
    return caps


def _normalize_adaptive_deadline_class_max_tokens(
    raw_value: Any,
    *,
    source_label: str,
) -> dict[str, dict[str, int]]:
    if raw_value is None:
        return {}
    if not isinstance(raw_value, dict):
        raise ValueError(f"{source_label} adaptive_deadline_class_max_tokens must be a JSON object.")
    profiles: dict[str, dict[str, int]] = {}
    for profile_name, max_tokens in raw_value.items():
        profiles[str(profile_name)] = _normalize_deadline_class_max_tokens(
            max_tokens,
            source_label=f"{source_label} adaptive_deadline_class_max_tokens[{profile_name!r}]",
        )
    if "default" not in profiles or "overload" not in profiles:
        raise ValueError(
            f"{source_label} adaptive_deadline_class_max_tokens must define both 'default' and 'overload' profiles."
        )
    return profiles


def _resolve_deadline_class_max_tokens(
    args: argparse.Namespace,
    variant_policy: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    cli_caps = _load_deadline_class_max_tokens(args)
    policy_caps = _normalize_deadline_class_max_tokens(
        variant_policy.get("deadline_class_max_tokens"),
        source_label="variant policy",
    )
    adaptive_policy_caps = _normalize_adaptive_deadline_class_max_tokens(
        variant_policy.get("adaptive_deadline_class_max_tokens"),
        source_label="variant policy",
    )
    if policy_caps and adaptive_policy_caps:
        raise ValueError(
            "Variant policy cannot define both deadline_class_max_tokens and adaptive_deadline_class_max_tokens."
        )
    if cli_caps and (policy_caps or adaptive_policy_caps):
        raise ValueError(
            "Variant policy already defines deadline class max token control; "
            "do not combine it with --deadline-class-max-tokens."
        )
    if cli_caps:
        return {"mode": "static", "profiles": {"static": cli_caps}}, "cli"
    if policy_caps:
        return {"mode": "static", "profiles": {"static": policy_caps}}, "variant_policy"
    if adaptive_policy_caps:
        return {"mode": "adaptive", "profiles": adaptive_policy_caps}, "variant_policy"
    if variant_policy.get("graduated_shaping"):
        return {"mode": "graduated", "profiles": {}}, "variant_policy"
    if variant_policy.get("risk_aware_shaping"):
        return {"mode": "risk-aware", "profiles": {}}, "variant_policy"
    return {"mode": "off", "profiles": {}}, "off"


def _policy_overload_state(
    policy: dict[str, Any],
    snapshot: dict[str, float | None],
) -> tuple[bool, str]:
    running = snapshot.get("num_requests_running")
    waiting = snapshot.get("num_requests_waiting")
    kv_cache = snapshot.get("kv_cache_usage_perc")
    running_overloaded = (
        running is not None and running >= float(policy.get("running_threshold") or 0.0)
    )
    waiting_overloaded = (
        waiting is not None and waiting > float(policy.get("waiting_threshold") or 0.0)
    )
    use_memory_signal = bool(policy.get("use_memory_signal", True))
    kv_threshold = policy.get("kv_cache_threshold")
    kv_overloaded = (
        use_memory_signal
        and kv_threshold is not None
        and kv_cache is not None
        and kv_cache >= float(kv_threshold)
    )
    overloaded = running_overloaded or waiting_overloaded or kv_overloaded
    reason = (
        "load_threshold_exceeded"
        if overloaded and use_memory_signal
        else "non_memory_load_threshold_exceeded"
        if overloaded
        else "below_thresholds"
        if use_memory_signal
        else "below_non_memory_thresholds"
    )
    return overloaded, reason


def _compute_pressure_ratio(
    policy: dict[str, Any],
    snapshot: dict[str, float | None],
) -> float:
    running = snapshot.get("num_requests_running") or 0.0
    kv_cache = snapshot.get("kv_cache_usage_perc") or 0.0
    running_threshold = float(policy.get("running_threshold") or 2.0)
    kv_threshold = float(policy.get("kv_cache_threshold") or 0.05)
    running_ratio = running / max(running_threshold, 0.01)
    kv_ratio = kv_cache / max(kv_threshold, 0.001)
    return min(1.0, max(running_ratio, kv_ratio))


def _graduated_shaping_caps(
    policy: dict[str, Any],
    snapshot: dict[str, float | None],
) -> tuple[dict[str, int], str | None]:
    graduated_config = policy.get("graduated_shaping")
    if not graduated_config:
        return {}, None
    pressure = _compute_pressure_ratio(policy, snapshot)
    caps: dict[str, int] = {}
    for class_name, bounds in graduated_config.items():
        if not isinstance(bounds, dict):
            continue
        max_cap = int(bounds.get("max_cap") or 384)
        min_cap = int(bounds.get("min_cap") or 16)
        cap = int(max_cap - (max_cap - min_cap) * pressure)
        caps[class_name] = max(min_cap, min(max_cap, cap))
    profile_name = f"graduated-p{int(pressure*100)}"
    return caps, profile_name


def _risk_aware_shaping_caps(
    policy: dict[str, Any],
    event: dict[str, Any],
    snapshot: dict[str, float | None],
) -> tuple[dict[str, int], str | None]:
    risk_config = policy.get("risk_aware_shaping")
    if not risk_config:
        return {}, None
    serving_context = dict(event.get("serving_context") or {})
    deadline_class = str(serving_context.get("deadline_class") or "unknown")
    target_e2e_ms = float(serving_context.get("target_e2e_ms") or 0.0)
    running = float((snapshot.get("num_requests_running") or 0.0))
    base_decode = float(risk_config.get("base_decode_ms_per_token") or 25.0)
    load_factor = float(risk_config.get("load_factor_per_running") or 0.5)
    base_ttft = float(risk_config.get("base_ttft_ms") or 150.0)
    decode_rate = base_decode * (1.0 + load_factor * running)
    class_config = risk_config.get(deadline_class)
    if not isinstance(class_config, dict) or target_e2e_ms <= 0:
        return {}, None
    max_cap = int(class_config.get("max_cap") or 384)
    min_cap = int(class_config.get("min_cap") or 16)
    available_decode_ms = target_e2e_ms - base_ttft
    if available_decode_ms <= 0:
        feasible_tokens = min_cap
    else:
        feasible_tokens = int(available_decode_ms / decode_rate)
    feasible_cap = max(min_cap, min(max_cap, feasible_tokens))
    caps: dict[str, int] = {}
    for class_name, bounds in risk_config.items():
        if not isinstance(bounds, dict):
            continue
        caps[class_name] = int(bounds.get("max_cap") or 256)
    caps[deadline_class] = feasible_cap
    profile_name = f"risk-cap{feasible_cap}"
    return caps, profile_name


def _deadline_class_max_tokens_for_request(
    policy: dict[str, Any],
    controller: dict[str, Any],
    snapshot: dict[str, float | None],
    event: dict[str, Any] | None = None,
) -> tuple[dict[str, int], str | None]:
    controller_mode = str(controller.get("mode") or "off")
    profiles = dict(controller.get("profiles") or {})
    if controller_mode == "static":
        return dict(profiles.get("static") or {}), "static"
    if controller_mode == "graduated":
        return _graduated_shaping_caps(policy, snapshot)
    if controller_mode == "risk-aware":
        return _risk_aware_shaping_caps(policy, event or {}, snapshot)
    if controller_mode != "adaptive":
        return {}, None
    overloaded, _ = _policy_overload_state(policy, snapshot)
    profile_name = "overload" if overloaded else "default"
    return dict(profiles.get(profile_name) or {}), profile_name


def _read_replay(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"Replay line {line_number} must be a JSON object.")
        rows.append(payload)
    return rows


def _resolve_output_path(path_str: str, output_root: Path | None) -> Path:
    path = Path(path_str)
    if output_root is None:
        return path
    if path.is_absolute():
        parts = list(path.parts)
        if "results" in parts:
            suffix = Path(*parts[parts.index("results") :])
            return output_root / suffix
        return output_root / path.name
    return output_root / path


def _load_run_plan(path: Path) -> dict[str, Any]:
    payload = _load_json(path)
    variants = payload.get("variants")
    metrics = payload.get("metrics")
    if not isinstance(variants, list) or not isinstance(metrics, dict):
        raise ValueError(f"Run plan missing variants/metrics in {path}")
    return payload


def _find_variant(run_plan: dict[str, Any], kind: str, name: str) -> dict[str, Any]:
    for item in run_plan.get("variants") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("kind") or "") == kind and str(item.get("name") or "") == name:
            return item
    raise ValueError(f"Variant {kind}:{name} not present in run plan")


def _validate_direct_endpoint_variant(variant: dict[str, Any]) -> None:
    kind = str(variant.get("kind") or "")
    name = str(variant.get("name") or "")
    if (kind, name) in SUPPORTED_DIRECT_ENDPOINT_VARIANTS:
        return
    raise ValueError(
        f"Variant {kind}:{name} is not executable with openai_replay_carrier. "
        "This carrier replays directly against fixed model endpoints and only supports "
        "baseline:fifo, baseline:balanced-operating-point, baseline:load-aware, baseline:no-spillover, baseline:no-memory-aware, baseline:full-policy, baseline:prism-style-static-sharing, baseline:prism-style-elastic-sharing, baseline:prism-style-two-level-scheduler, baseline:vamos-slo-feasibility-controller, baseline:vamos-slo-rescue-no-reject, ablation:aggressive-upper-bound, ablation:no-admission-control, ablation:no-profiling, and ablation:adaptive-controller. Remaining policy-distinct variants require "
        "a policy-aware control-plane executor."
    )


def _variant_policy_for(kind: str, name: str) -> dict[str, Any]:
    try:
        return dict(_DIRECT_ENDPOINT_VARIANT_POLICIES[(kind, name)])
    except KeyError as exc:
        raise ValueError(f"No direct-endpoint policy profile defined for {kind}:{name}") from exc


def _metric_names(run_plan: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for values in (run_plan.get("metrics") or {}).values():
        if isinstance(values, list):
            names.extend(str(item) for item in values)
    return names


def _quantile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * percentile / 100.0) - 1))
    return round(ordered[rank], 6)


def _normalize_response_metadata(raw_metadata: Any) -> dict[str, str]:
    if not isinstance(raw_metadata, dict):
        return {}
    normalized: dict[str, str] = {}
    for key, value in raw_metadata.items():
        if value is None:
            continue
        normalized[str(key)] = str(value)
    return normalized


def _response_metadata_uses_spillover(response_metadata: dict[str, str]) -> bool:
    backend_scope = str(response_metadata.get("x-vllm-backend-scope") or "").strip().lower()
    route_outcome = str(response_metadata.get("x-vllm-route-outcome") or "").strip().lower()
    if backend_scope and backend_scope not in {"local", "local_only", "local-only"}:
        return True
    return (
        "spillover" in route_outcome
        or route_outcome.startswith("remote")
        or route_outcome.endswith("remote")
        or "_remote" in route_outcome
    )


def _git_commit(repo_root: Path) -> str | None:
    if not repo_root.exists():
        return None
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _hardware_metadata() -> dict[str, Any]:
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }


def _extract_prometheus_metric_name(line: str) -> str | None:
    first_field = line.split(None, 1)[0].strip()
    if not first_field:
        return None
    return first_field.split("{", 1)[0]


def _parse_prometheus_metric_value(line: str) -> float | None:
    parts = line.split()
    if not parts:
        return None
    with contextlib.suppress(ValueError):
        return float(parts[-1])
    return None


def _aggregate_prometheus_samples(samples: list[float], *, aggregate: str) -> float | None:
    if not samples:
        return None
    if aggregate == "sum":
        return float(sum(samples))
    if aggregate == "max":
        return float(max(samples))
    raise ValueError(f"Unsupported aggregate '{aggregate}'")


def _parse_load_metrics_snapshot(text: str) -> dict[str, float | None] | None:
    tracked_metrics: dict[str, list[float]] = {
        "vllm:num_requests_running": [],
        "vllm:num_requests_waiting": [],
        "vllm:kv_cache_usage_perc": [],
        "vllm:prefix_cache_queries": [],
        "vllm:prefix_cache_hits": [],
        "vllm:external_prefix_cache_queries": [],
        "vllm:external_prefix_cache_hits": [],
    }
    metric_aliases = {
        "vllm:prefix_cache_queries_total": "vllm:prefix_cache_queries",
        "vllm:prefix_cache_hits_total": "vllm:prefix_cache_hits",
        "vllm:external_prefix_cache_queries_total": "vllm:external_prefix_cache_queries",
        "vllm:external_prefix_cache_hits_total": "vllm:external_prefix_cache_hits",
    }

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        metric_name = _extract_prometheus_metric_name(line)
        metric_name = metric_aliases.get(str(metric_name), metric_name)
        if metric_name not in tracked_metrics:
            continue
        value = _parse_prometheus_metric_value(line)
        if value is None:
            continue
        tracked_metrics[metric_name].append(value)

    if not any(tracked_metrics.values()):
        return None

    return {
        "num_requests_running": _aggregate_prometheus_samples(
            tracked_metrics["vllm:num_requests_running"],
            aggregate="sum",
        ),
        "num_requests_waiting": _aggregate_prometheus_samples(
            tracked_metrics["vllm:num_requests_waiting"],
            aggregate="sum",
        ),
        "kv_cache_usage_perc": _aggregate_prometheus_samples(
            tracked_metrics["vllm:kv_cache_usage_perc"],
            aggregate="max",
        ),
        "prefix_cache_queries": _aggregate_prometheus_samples(
            tracked_metrics["vllm:prefix_cache_queries"],
            aggregate="sum",
        ),
        "prefix_cache_hits": _aggregate_prometheus_samples(
            tracked_metrics["vllm:prefix_cache_hits"],
            aggregate="sum",
        ),
        "external_prefix_cache_queries": _aggregate_prometheus_samples(
            tracked_metrics["vllm:external_prefix_cache_queries"],
            aggregate="sum",
        ),
        "external_prefix_cache_hits": _aggregate_prometheus_samples(
            tracked_metrics["vllm:external_prefix_cache_hits"],
            aggregate="sum",
        ),
    }


async def _discover_served_model(base_url: str, session: aiohttp.ClientSession) -> str:
    async with session.get(f"{base_url}/v1/models") as response:
        response.raise_for_status()
        payload = await response.json()
    models = payload.get("data") or []
    if not models:
        raise ValueError(f"No served models found at {base_url}/v1/models")
    first = models[0]
    if not isinstance(first, dict) or not first.get("id"):
        raise ValueError(f"Invalid /v1/models payload from {base_url}")
    return str(first["id"])


async def _wait_for_endpoint(base_url: str, model_name: str, timeout_seconds: int) -> None:
    deadline = time.perf_counter() + timeout_seconds
    aiohttp_timeout, _, _ = _load_vllm_benchmark_deps()
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(timeout=aiohttp_timeout, connector=connector) as session:
        while time.perf_counter() < deadline:
            try:
                await _discover_served_model(base_url, session)
                return
            except Exception:
                await asyncio.sleep(5)
    raise TimeoutError(f"Endpoint {base_url} did not become ready for model {model_name}")


async def _fetch_metrics(base_url: str, session: aiohttp.ClientSession) -> dict[str, float | None]:
    try:
        async with session.get(f"{base_url}/metrics") as response:
            if response.status != 200:
                return {}
            text = await response.text()
    except Exception:
        return {}
    snapshot = _parse_load_metrics_snapshot(text)
    if snapshot is None:
        return {}
    return {
        "num_requests_running": snapshot["num_requests_running"],
        "num_requests_waiting": snapshot["num_requests_waiting"],
        "kv_cache_usage_perc": snapshot["kv_cache_usage_perc"],
        "prefix_cache_queries": snapshot["prefix_cache_queries"],
        "prefix_cache_hits": snapshot["prefix_cache_hits"],
        "external_prefix_cache_queries": snapshot["external_prefix_cache_queries"],
        "external_prefix_cache_hits": snapshot["external_prefix_cache_hits"],
    }


async def _poll_metrics(
    base_urls: set[str],
    interval_sec: float,
    stop_event: asyncio.Event,
    accumulator: dict[str, float | None],
    current_load: dict[str, dict[str, float | None]],
) -> None:
    aiohttp_timeout, _, _ = _load_vllm_benchmark_deps()
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(timeout=aiohttp_timeout, connector=connector) as session:
        while not stop_event.is_set():
            running_total = 0.0
            waiting_total = 0.0
            kv_max = None
            for base_url in base_urls:
                metrics = await _fetch_metrics(base_url, session)
                snapshot = current_load.setdefault(base_url, {})
                snapshot.clear()
                snapshot.update(
                    {
                        "num_requests_running": (
                            float(metrics["num_requests_running"])
                            if metrics.get("num_requests_running") is not None
                            else None
                        ),
                        "num_requests_waiting": (
                            float(metrics["num_requests_waiting"])
                            if metrics.get("num_requests_waiting") is not None
                            else None
                        ),
                        "kv_cache_usage_perc": (
                            float(metrics["kv_cache_usage_perc"])
                            if metrics.get("kv_cache_usage_perc") is not None
                            else None
                        ),
                        "prefix_cache_queries": (
                            float(metrics["prefix_cache_queries"])
                            if metrics.get("prefix_cache_queries") is not None
                            else None
                        ),
                        "prefix_cache_hits": (
                            float(metrics["prefix_cache_hits"])
                            if metrics.get("prefix_cache_hits") is not None
                            else None
                        ),
                        "external_prefix_cache_queries": (
                            float(metrics["external_prefix_cache_queries"])
                            if metrics.get("external_prefix_cache_queries") is not None
                            else None
                        ),
                        "external_prefix_cache_hits": (
                            float(metrics["external_prefix_cache_hits"])
                            if metrics.get("external_prefix_cache_hits") is not None
                            else None
                        ),
                    }
                )
                if metrics.get("num_requests_running") is not None:
                    running_total += float(metrics["num_requests_running"])
                if metrics.get("num_requests_waiting") is not None:
                    waiting_total += float(metrics["num_requests_waiting"])
                kv_value = metrics.get("kv_cache_usage_perc")
                if kv_value is not None:
                    kv_value = float(kv_value)
                    kv_max = kv_value if kv_max is None else max(kv_max, kv_value)

            accumulator["running_requests"] = max(
                float(accumulator.get("running_requests") or 0.0),
                running_total,
            )
            accumulator["waiting_requests"] = max(
                float(accumulator.get("waiting_requests") or 0.0),
                waiting_total,
            )
            if kv_max is not None:
                current_kv = accumulator.get("kv_cache_usage_perc")
                accumulator["kv_cache_usage_perc"] = (
                    kv_max if current_kv is None else max(float(current_kv), kv_max)
                )

            for metric_name in (
                "prefix_cache_queries",
                "prefix_cache_hits",
                "external_prefix_cache_queries",
                "external_prefix_cache_hits",
            ):
                observed_total = sum(
                    float(snapshot[metric_name])
                    for snapshot in current_load.values()
                    if snapshot.get(metric_name) is not None
                )
                if observed_total <= 0 and not any(
                    snapshot.get(metric_name) is not None for snapshot in current_load.values()
                ):
                    continue
                start_key = f"{metric_name}_start"
                end_key = f"{metric_name}_end"
                if accumulator.get(start_key) is None:
                    accumulator[start_key] = observed_total
                accumulator[end_key] = observed_total

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval_sec)
            except asyncio.TimeoutError:
                continue


def _counter_delta(metrics: dict[str, float | None], metric_name: str) -> float | None:
    start_value = metrics.get(f"{metric_name}_start")
    end_value = metrics.get(f"{metric_name}_end")
    if start_value is None or end_value is None:
        return None
    return round(float(end_value) - float(start_value), 6)


def _rate_or_none(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return round(float(numerator) / float(denominator), 6)


def _live_load_snapshot(
    current_load: dict[str, dict[str, float | None]], base_url: str
) -> dict[str, float | None]:
    snapshot = current_load.get(base_url) or {}
    return {
        "num_requests_running": (
            float(snapshot["num_requests_running"])
            if snapshot.get("num_requests_running") is not None
            else None
        ),
        "num_requests_waiting": (
            float(snapshot["num_requests_waiting"])
            if snapshot.get("num_requests_waiting") is not None
            else None
        ),
        "kv_cache_usage_perc": (
            float(snapshot["kv_cache_usage_perc"])
            if snapshot.get("kv_cache_usage_perc") is not None
            else None
        ),
    }


def _map_execution_priority(serving_context: dict[str, Any], mode: str) -> int | None:
    if mode == "off":
        return None
    priority = int(serving_context.get("priority") or 0)
    if mode == "invert-vamos":
        return -priority
    raise ValueError(f"Unsupported execution priority mode: {mode}")


def _effective_output_len(
    serving_context: dict[str, Any],
    deadline_class_max_tokens: dict[str, int],
) -> tuple[int, int]:
    requested_output_len = int(serving_context.get("max_tokens") or 0)
    if requested_output_len <= 0:
        raise ValueError("Replay event missing positive serving_context.max_tokens")
    deadline_class = str(serving_context.get("deadline_class") or "unknown")
    class_cap = deadline_class_max_tokens.get(deadline_class)
    if class_cap is None:
        return requested_output_len, requested_output_len
    return requested_output_len, min(requested_output_len, class_cap)


def _policy_dispatch_decision(
    policy: dict[str, Any],
    event: dict[str, Any],
    snapshot: dict[str, float | None],
    elapsed_delay_s: float = 0.0,
) -> dict[str, Any]:
    mode = str(policy.get("mode") or "fifo")
    serving_context = dict(event.get("serving_context") or {})
    deadline_class = str(serving_context.get("deadline_class") or "unknown")
    priority = int(serving_context.get("priority") or 0)
    if mode == "fifo":
        return {
            "action": "dispatch",
            "reason": "fifo_order",
            "mode": mode,
            "observed_load": snapshot,
        }

    if mode == "no-profiling":
        if deadline_class == "interactive-high" or priority >= int(policy.get("priority_cutoff") or 0):
            return {
                "action": "dispatch",
                "reason": "priority_bypass",
                "mode": mode,
                "observed_load": snapshot,
            }
        static_delay_s = float(policy.get("static_batch_delay_sec") or 0.0)
        if elapsed_delay_s < static_delay_s:
            return {
                "action": "delay",
                "reason": "profiling_disabled_static_pacing",
                "mode": mode,
                "observed_load": {
                    "num_requests_running": None,
                    "num_requests_waiting": None,
                    "kv_cache_usage_perc": None,
                },
            }
        return {
            "action": "dispatch",
            "reason": "profiling_disabled_dispatch",
            "mode": mode,
            "observed_load": {
                "num_requests_running": None,
                "num_requests_waiting": None,
                "kv_cache_usage_perc": None,
            },
        }

    if mode != "load-aware":
        if mode == "wfq":
            # Weighted Fair Queuing: allocate token budget proportional to class weight
            wfq_weights = dict(policy.get("wfq_class_weights") or {})
            class_weight = float(wfq_weights.get(deadline_class, 0.1))
            total_budget = int(policy.get("wfq_total_budget_per_window") or 2048)
            class_budget = int(total_budget * class_weight)
            return {
                "action": "dispatch",
                "reason": f"wfq_class_budget_{class_budget}",
                "mode": mode,
                "observed_load": snapshot,
                "wfq_class_budget": class_budget,
            }
        if mode == "strict-priority":
            # Strict priority: interactive always dispatches immediately,
            # batch requests are limited by max_concurrent_batch
            max_concurrent = int(policy.get("max_concurrent_batch") or 2)
            running = snapshot.get("num_requests_running")
            if deadline_class == "interactive-high" or priority >= int(policy.get("priority_cutoff") or 0):
                return {
                    "action": "dispatch",
                    "reason": "strict_priority_bypass",
                    "mode": mode,
                    "observed_load": snapshot,
                    "preempt_batch": bool(policy.get("preempt_batch_to_current_tokens")),
                }
            # Non-interactive: only dispatch if below max concurrent batch
            if running is not None and running >= max_concurrent:
                if elapsed_delay_s >= float(policy.get("max_deferral_sec") or 4.0):
                    return {
                        "action": "dispatch",
                        "reason": "strict_priority_max_wait_elapsed",
                        "mode": mode,
                        "observed_load": snapshot,
                    }
                return {
                    "action": "delay",
                    "reason": "strict_priority_batch_limited",
                    "mode": mode,
                    "observed_load": snapshot,
                }
            return {
                "action": "dispatch",
                "reason": "strict_priority_batch_slot_available",
                "mode": mode,
                "observed_load": snapshot,
            }
        raise ValueError(f"Unsupported direct-endpoint policy mode: {mode}")

    if deadline_class == "interactive-high" or priority >= int(policy.get("priority_cutoff") or 0):
        return {
            "action": "dispatch",
            "reason": "priority_bypass",
            "mode": mode,
            "observed_load": snapshot,
        }

    overloaded, reason = _policy_overload_state(policy, snapshot)
    return {
        "action": "delay" if overloaded else "dispatch",
        "reason": reason,
        "mode": mode,
        "observed_load": snapshot,
    }


async def _await_policy_dispatch_window(
    event: dict[str, Any],
    base_url: str,
    policy: dict[str, Any],
    current_load: dict[str, dict[str, float | None]],
) -> dict[str, Any]:
    total_delay_s = 0.0
    deferral_count = 0
    while True:
        snapshot = _live_load_snapshot(current_load, base_url)
        decision = _policy_dispatch_decision(policy, event, snapshot, elapsed_delay_s=total_delay_s)
        if decision["action"] == "dispatch":
            return {
                "policy_action": "dispatch",
                "policy_mode": decision["mode"],
                "policy_reason": decision["reason"],
                "dispatch_delay_s": round(total_delay_s, 6),
                "deferral_count": deferral_count,
                "observed_load": decision["observed_load"],
            }

        defer_interval_s = float(policy.get("defer_interval_sec") or 0.0)
        max_deferral_s = float(policy.get("max_deferral_sec") or 0.0)
        if defer_interval_s <= 0 or total_delay_s + defer_interval_s > max_deferral_s:
            if bool(policy.get("admission_control", False)):
                return {
                    "policy_action": "reject",
                    "policy_mode": decision["mode"],
                    "policy_reason": "admission_control_reject",
                    "dispatch_delay_s": round(total_delay_s, 6),
                    "deferral_count": deferral_count,
                    "observed_load": decision["observed_load"],
                }
            return {
                "policy_action": "dispatch",
                "policy_mode": decision["mode"],
                "policy_reason": "max_deferral_elapsed",
                "dispatch_delay_s": round(total_delay_s, 6),
                "deferral_count": deferral_count,
                "observed_load": decision["observed_load"],
            }

        await asyncio.sleep(defer_interval_s)
        total_delay_s += defer_interval_s
        deferral_count += 1


async def _run_one_request(
    index: int,
    event: dict[str, Any],
    start_perf: float,
    endpoint_map: dict[str, str],
    served_model_map: dict[str, str],
    variant_policy: dict[str, Any],
    execution_priority_mode: str,
    deadline_class_token_controller: dict[str, Any],
    deadline_class_max_tokens_source: str,
    current_load: dict[str, dict[str, float | None]],
    session: aiohttp.ClientSession,
) -> dict[str, Any]:
    metadata = dict(event.get("metadata") or {})
    serving_context = dict(event.get("serving_context") or {})
    trace_tags = dict(serving_context.get("trace_tags") or {})
    prefix_cache_key = str(serving_context.get("prefix_cache_key") or "").strip() or None
    request_id = str(event.get("request_id") or f"request-{index:05d}")
    execution_priority = _map_execution_priority(serving_context, execution_priority_mode)
    model_id = str(serving_context.get("model_id") or "")
    if not model_id:
        raise ValueError(f"Replay event {request_id} missing serving_context.model_id")
    base_url = endpoint_map.get(model_id)
    if base_url is None:
        raise ValueError(f"No endpoint configured for model_id {model_id}")

    scheduled_at_s = float(metadata.get("scheduled_at_s") or 0.0)
    sleep_for = start_perf + scheduled_at_s - time.perf_counter()
    if sleep_for > 0:
        await asyncio.sleep(sleep_for)

    policy_trace = await _await_policy_dispatch_window(event, base_url, variant_policy, current_load)
    _controller_decision_end = time.perf_counter()
    _controller_decision_us = (_controller_decision_end - (start_perf + scheduled_at_s + max(0, sleep_for))) * 1e6
    control_snapshot = dict(policy_trace.get("observed_load") or {})
    if not control_snapshot:
        control_snapshot = _live_load_snapshot(current_load, base_url)
    # Record controller overhead in the policy trace
    policy_trace["controller_decision_latency_us"] = round(_controller_decision_us, 1)
    deadline_class_max_tokens, deadline_class_cap_profile = _deadline_class_max_tokens_for_request(
        variant_policy,
        deadline_class_token_controller,
        control_snapshot,
        event=event,
    )
    # WFQ: apply class-proportional token budget cap
    wfq_class_budget = policy_trace.get("wfq_class_budget")
    if wfq_class_budget is not None:
        deadline_class = str(serving_context.get("deadline_class") or "unknown")
        existing_cap = deadline_class_max_tokens.get(deadline_class)
        wfq_cap = int(wfq_class_budget)
        if existing_cap is None or wfq_cap < existing_cap:
            deadline_class_max_tokens[deadline_class] = wfq_cap
            deadline_class_cap_profile = f"wfq-{wfq_cap}"
    requested_output_len, effective_output_len = _effective_output_len(
        serving_context,
        deadline_class_max_tokens,
    )

    scheduled_start_s = round(scheduled_at_s + float(policy_trace["dispatch_delay_s"]), 6)
    if str(policy_trace.get("policy_action") or "dispatch") == "reject":
        return {
            "request_id": request_id,
            "variant_kind": None,
            "variant_name": None,
            "model_id": model_id,
            "served_model_name": served_model_map[base_url],
            "base_url": base_url,
            "scheduled_at_s": round(scheduled_at_s, 6),
            "started_at_s": scheduled_start_s,
            "completed_at_s": scheduled_start_s,
            "phase": str(metadata.get("phase") or trace_tags.get("phase") or "unknown"),
            "deadline_class": str(serving_context.get("deadline_class") or "unknown"),
            "priority": serving_context.get("priority"),
            "prefix_cache_key": prefix_cache_key,
            "execution_priority": execution_priority,
            "requested_max_tokens": requested_output_len,
            "effective_max_tokens": effective_output_len,
            "deadline_class_cap_profile": deadline_class_cap_profile,
            "deadline_class_cap_source": deadline_class_max_tokens_source,
            "decision": "rejected",
            "used_spillover": False,
            "policy_mode": policy_trace["policy_mode"],
            "policy_reason": policy_trace["policy_reason"],
            "dispatch_delay_s": policy_trace["dispatch_delay_s"],
            "deferral_count": policy_trace["deferral_count"],
            "observed_load": policy_trace["observed_load"],
            "success": False,
            "ttft_ms": None,
            "e2e_ms": None,
            "output_tokens": 0,
            "prompt_len": int(serving_context.get("prompt_len") or 0),
            "target_ttft_ms": serving_context.get("target_ttft_ms"),
            "target_e2e_ms": serving_context.get("target_e2e_ms"),
            "slo_violated": True,
            "error": "rejected_by_policy",
            "response_metadata": {},
            "trace_tags": trace_tags,
        }

    prompt = str(((event.get("payload") or {}).get("input_payload") or {}).get("prompt") or "")
    if not prompt:
        raise ValueError(f"Replay event {request_id} missing payload.input_payload.prompt")

    extra_body: dict[str, Any] | None = None
    if execution_priority is not None or prefix_cache_key is not None:
        extra_body = {}
        if execution_priority is not None:
            extra_body["priority"] = execution_priority
        if prefix_cache_key is not None:
            extra_body["prefix_cache_key"] = prefix_cache_key
            extra_body["cache_salt"] = prefix_cache_key
    _, RequestFuncInput, async_request_openai_completions = _load_vllm_benchmark_deps()
    output = await async_request_openai_completions(
        RequestFuncInput(
            prompt=prompt,
            api_url=f"{base_url}/v1/completions",
            prompt_len=int(serving_context.get("prompt_len") or 0),
            output_len=effective_output_len,
            model=model_id,
            model_name=served_model_map[base_url],
            extra_body=extra_body,
            request_id=request_id,
        ),
        session,
    )
    response_metadata = _normalize_response_metadata(getattr(output, "response_metadata", None))
    used_spillover = _response_metadata_uses_spillover(response_metadata)

    started_at_s = output.start_time - start_perf
    completed_at_s = started_at_s + output.latency
    ttft_ms = round(output.ttft * 1000.0, 6) if output.ttft else None
    e2e_ms = round(output.latency * 1000.0, 6) if output.latency else None
    target_ttft_ms = serving_context.get("target_ttft_ms")
    target_e2e_ms = serving_context.get("target_e2e_ms")
    slo_violated = not output.success
    if ttft_ms is not None and target_ttft_ms is not None and ttft_ms > float(target_ttft_ms):
        slo_violated = True
    if e2e_ms is not None and target_e2e_ms is not None and e2e_ms > float(target_e2e_ms):
        slo_violated = True

    phase = str(metadata.get("phase") or trace_tags.get("phase") or "unknown")
    deadline_class = str(serving_context.get("deadline_class") or "unknown")
    decision = "admitted" if output.success else "rejected"
    return {
        "request_id": request_id,
        "variant_kind": None,
        "variant_name": None,
        "model_id": model_id,
        "served_model_name": served_model_map[base_url],
        "base_url": base_url,
        "scheduled_at_s": round(scheduled_at_s, 6),
        "started_at_s": round(started_at_s, 6),
        "completed_at_s": round(completed_at_s, 6),
        "phase": phase,
        "deadline_class": deadline_class,
        "priority": serving_context.get("priority"),
        "prefix_cache_key": prefix_cache_key,
        "execution_priority": execution_priority,
        "requested_max_tokens": requested_output_len,
        "effective_max_tokens": effective_output_len,
        "deadline_class_cap_profile": deadline_class_cap_profile,
        "deadline_class_cap_source": deadline_class_max_tokens_source,
        "decision": decision,
        "used_spillover": used_spillover,
        "policy_mode": policy_trace["policy_mode"],
        "policy_reason": policy_trace["policy_reason"],
        "dispatch_delay_s": policy_trace["dispatch_delay_s"],
        "deferral_count": policy_trace["deferral_count"],
        "observed_load": policy_trace["observed_load"],
        "success": output.success,
        "ttft_ms": ttft_ms,
        "e2e_ms": e2e_ms,
        "output_tokens": output.output_tokens,
        "prompt_len": output.prompt_len,
        "target_ttft_ms": target_ttft_ms,
        "target_e2e_ms": target_e2e_ms,
        "slo_violated": slo_violated,
        "error": output.error or None,
        "response_metadata": response_metadata,
        "trace_tags": trace_tags,
    }


def _build_metrics(
    run_plan: dict[str, Any],
    rows: list[dict[str, Any]],
    peak_load: dict[str, float | None],
) -> dict[str, Any]:
    total_requests = len(rows)
    completed_rows = [row for row in rows if row.get("success")]
    ttft_values = [float(row["ttft_ms"]) for row in completed_rows if row.get("ttft_ms") is not None]
    e2e_values = [float(row["e2e_ms"]) for row in completed_rows if row.get("e2e_ms") is not None]
    reject_count = sum(1 for row in rows if not row.get("success"))
    violation_count = sum(1 for row in rows if row.get("slo_violated"))
    delayed_count = 0
    if rows:
        delayed_count = sum(
            1
            for row in rows
            if float(row.get("started_at_s") or 0.0) - float(row.get("scheduled_at_s") or 0.0) > 0.05
        )
    duration_s = 0.0
    if rows:
        duration_s = max(float(row.get("completed_at_s") or 0.0) for row in rows)
        duration_s = max(duration_s, 1e-9)
    spillover_count = sum(1 for row in rows if row.get("used_spillover"))
    prefix_cache_queries_delta = _counter_delta(peak_load, "prefix_cache_queries")
    prefix_cache_hits_delta = _counter_delta(peak_load, "prefix_cache_hits")
    external_prefix_cache_queries_delta = _counter_delta(
        peak_load,
        "external_prefix_cache_queries",
    )
    external_prefix_cache_hits_delta = _counter_delta(
        peak_load,
        "external_prefix_cache_hits",
    )

    metrics: dict[str, Any] = {
        "ttft_p50_ms": _quantile(ttft_values, 50.0),
        "ttft_p95_ms": _quantile(ttft_values, 95.0),
        "e2e_p95_ms": _quantile(e2e_values, 95.0),
        "throughput_rps": round(len(completed_rows) / duration_s, 6) if duration_s else 0.0,
        "running_requests": peak_load.get("running_requests"),
        "waiting_requests": peak_load.get("waiting_requests"),
        "kv_cache_usage_perc": peak_load.get("kv_cache_usage_perc"),
        "prefix_cache_queries_delta": prefix_cache_queries_delta,
        "prefix_cache_hits_delta": prefix_cache_hits_delta,
        "prefix_cache_hit_rate": _rate_or_none(
            prefix_cache_hits_delta,
            prefix_cache_queries_delta,
        ),
        "external_prefix_cache_queries_delta": external_prefix_cache_queries_delta,
        "external_prefix_cache_hits_delta": external_prefix_cache_hits_delta,
        "external_prefix_cache_hit_rate": _rate_or_none(
            external_prefix_cache_hits_delta,
            external_prefix_cache_queries_delta,
        ),
        "free_vram_bytes": None,
        "reserved_vram_bytes": None,
        "slo_violation_rate": round(violation_count / total_requests, 6) if total_requests else None,
        "spillover_rate": round(spillover_count / total_requests, 6) if total_requests else None,
        "reject_rate": round(reject_count / total_requests, 6) if total_requests else None,
        "delayed_request_rate": round(delayed_count / total_requests, 6) if total_requests else None,
    }
    for metric_name in _metric_names(run_plan):
        metrics.setdefault(metric_name, None)
    return metrics


async def _run_replay(args: argparse.Namespace) -> dict[str, Any]:
    run_plan_path = Path(args.run_plan).resolve()
    replay_path = Path(args.workload_replay).resolve()
    experiment_manifest = Path(args.experiment_manifest).resolve()
    output_root = Path(args.output_root).resolve() if args.output_root else None

    run_plan = _load_run_plan(run_plan_path)
    variant = _find_variant(run_plan, args.variant_kind, args.variant_name)
    _validate_direct_endpoint_variant(variant)
    variant_policy = _variant_policy_for(args.variant_kind, args.variant_name)
    endpoint_map = _load_endpoint_map(args)
    deadline_class_token_controller, deadline_class_max_tokens_source = _resolve_deadline_class_max_tokens(
        args,
        variant_policy,
    )
    replay = _read_replay(replay_path)
    summary_output = _resolve_output_path(args.summary_output, output_root)
    trace_output = _resolve_output_path(args.trace_output, output_root)
    raw_log_output = _resolve_output_path(args.raw_log_output, output_root)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    trace_output.parent.mkdir(parents=True, exist_ok=True)
    raw_log_output.parent.mkdir(parents=True, exist_ok=True)

    for model_id, base_url in endpoint_map.items():
        await _wait_for_endpoint(base_url, model_id, args.ready_timeout_sec)

    aiohttp_timeout, _, _ = _load_vllm_benchmark_deps()
    connector = aiohttp.TCPConnector(ssl=False, limit=0)
    async with aiohttp.ClientSession(timeout=aiohttp_timeout, connector=connector) as session:
        served_model_map = {
            base_url: await _discover_served_model(base_url, session)
            for base_url in sorted(set(endpoint_map.values()))
        }
        peak_load: dict[str, float | None] = {
            "running_requests": None,
            "waiting_requests": None,
            "kv_cache_usage_perc": None,
        }
        current_load: dict[str, dict[str, float | None]] = {
            base_url: {
                "num_requests_running": None,
                "num_requests_waiting": None,
                "kv_cache_usage_perc": None,
            }
            for base_url in sorted(set(endpoint_map.values()))
        }
        stop_event = asyncio.Event()
        metrics_task = asyncio.create_task(
            _poll_metrics(
                set(endpoint_map.values()),
                args.metrics_poll_interval_sec,
                stop_event,
                peak_load,
                current_load,
            )
        )
        start_perf = time.perf_counter()
        run_started_at = datetime.now(timezone.utc).isoformat()
        tasks = [
            asyncio.create_task(
                _run_one_request(
                    index,
                    event,
                    start_perf,
                    endpoint_map,
                    served_model_map,
                    variant_policy,
                    args.execution_priority_mode,
                    deadline_class_token_controller,
                    deadline_class_max_tokens_source,
                    current_load,
                    session,
                )
            )
            for index, event in enumerate(replay)
        ]
        rows = await asyncio.gather(*tasks)
        stop_event.set()
        await metrics_task
        run_finished_at = datetime.now(timezone.utc).isoformat()

    for row in rows:
        row["variant_kind"] = args.variant_kind
        row["variant_name"] = args.variant_name

    metrics = _build_metrics(run_plan, rows, peak_load)
    phase_counts = Counter(str(row.get("phase") or "unknown") for row in rows)
    class_counts = Counter(str(row.get("deadline_class") or "unknown") for row in rows)
    prefix_cache_key_counts = Counter(str(row.get("prefix_cache_key") or "none") for row in rows)
    route_outcome_counts = Counter(
        str((row.get("response_metadata") or {}).get("x-vllm-route-outcome") or "unknown")
        for row in rows
    )
    backend_scope_counts = Counter(
        str((row.get("response_metadata") or {}).get("x-vllm-backend-scope") or "unknown")
        for row in rows
    )
    trace_rows = [
        {
            "request_id": row["request_id"],
            "variant_kind": args.variant_kind,
            "variant_name": args.variant_name,
            "phase": row["phase"],
            "deadline_class": row["deadline_class"],
            "model_id": row["model_id"],
            "served_model_name": row["served_model_name"],
            "prefix_cache_key": row.get("prefix_cache_key"),
            "decision_trace": {
                "decision": row["decision"],
                "used_spillover": row["used_spillover"],
                "policy_mode": row["policy_mode"],
                "policy_reason": row["policy_reason"],
                "dispatch_delay_s": row["dispatch_delay_s"],
                "deferral_count": row["deferral_count"],
                "observed_load": row["observed_load"],
                "priority": row["priority"],
                "prefix_cache_key": row.get("prefix_cache_key"),
                "execution_priority": row["execution_priority"],
                "requested_max_tokens": row["requested_max_tokens"],
                "effective_max_tokens": row["effective_max_tokens"],
                "deadline_class_cap_profile": row["deadline_class_cap_profile"],
                "deadline_class_cap_source": row["deadline_class_cap_source"],
                "target_ttft_ms": row["target_ttft_ms"],
                "target_e2e_ms": row["target_e2e_ms"],
                "success": row["success"],
                "ttft_ms": row["ttft_ms"],
                "e2e_ms": row["e2e_ms"],
                "response_metadata": row["response_metadata"],
            },
        }
        for row in rows
    ]

    summary = {
        "kind": args.variant_kind,
        "name": args.variant_name,
        "variant": args.variant_name,
        "experiment": str(
            run_plan.get("experiment", {}).get("name") or "burst-overload-baseline-matrix"
        ),
        "generated_at": run_finished_at,
        "carrier_mode": "real-openai-replay",
        "artifacts": {
            "summary": str(summary_output),
            "trace": str(trace_output),
            "raw_log": str(raw_log_output),
        },
        "inputs": {
            "experiment_manifest": str(experiment_manifest),
            "run_plan": str(run_plan_path),
            "workload_replay": str(replay_path),
            "seed": args.seed,
        },
        "systems": dict(run_plan.get("systems") or {}),
        "execution_metadata": {
            "sage_commit": _git_commit(Path(__file__).resolve().parents[2]),
            "benchmark_carrier_commit": _git_commit(Path(__file__).resolve().parents[2]),
            "hardware_metadata": _hardware_metadata(),
            "run_started_at": run_started_at,
            "run_finished_at": run_finished_at,
            "full_command_line": " ".join(sys.argv),
            "endpoint_map": endpoint_map,
            "variant_policy": variant_policy,
            "execution_priority_mode": args.execution_priority_mode,
            "deadline_class_max_tokens": dict(
                (deadline_class_token_controller.get("profiles") or {}).get("static") or {}
            ),
            "adaptive_deadline_class_max_tokens": dict(
                deadline_class_token_controller.get("profiles") or {}
            )
            if str(deadline_class_token_controller.get("mode") or "off") == "adaptive"
            else {},
            "deadline_class_max_tokens_source": deadline_class_max_tokens_source,
        },
        "metrics": metrics,
        "notes": [
            "Real execution-plane replay against OpenAI-compatible vllm-hust endpoints.",
            "Request-level raw logs and traces capture OpenAI response routing metadata when the endpoint exports x-vllm-* headers.",
            "baseline:load-aware defers lower-priority batch requests when live endpoint load exceeds configured thresholds.",
            "baseline:no-memory-aware keeps live running and waiting thresholds but ignores KV-cache pressure when deciding whether to defer lower-priority batch requests.",
            "baseline:full-policy adds a direct-endpoint admission-control gate that rejects lower-priority batch requests when overload persists after the bounded defer window.",
            "baseline:prism-style-static-sharing is a fixed vllm-hust endpoint control that approximates Prism-style static per-model sharing without reproducing Prism, SGLang, or kvcached internals.",
            "baseline:prism-style-elastic-sharing uses live load and KV pressure to defer lower-priority requests, approximating elastic sharing behavior on the same vllm-hust execution plane.",
            "baseline:prism-style-two-level-scheduler uses priority admission without VAMOS VRAM/KV-cache signal, approximating Prism-style two-level scheduling as a policy baseline rather than a full Prism system.",
            "baseline:vamos-slo-feasibility-controller uses the explicit VAMOS SLO contract to reshape deadline-class token budgets before dispatch; report the reduced effective_max_tokens as part of the tradeoff.",
            "baseline:vamos-slo-rescue-no-reject preserves the same interactive SLO-feasibility shaping while dispatching lower-priority requests after the bounded defer window instead of rejecting them.",
            "ablation:no-admission-control keeps the same defer policy surface as baseline:full-policy but dispatches once the bounded defer window expires instead of rejecting.",
            "ablation:no-profiling applies fixed static pacing to lower-priority batch requests instead of consulting live runtime profiling metrics.",
            "execution_priority_mode=invert-vamos maps larger replay priority values to smaller vLLM priority values for endpoints started with --scheduling-policy priority; execution_priority_mode=off leaves execution scheduling unchanged after any carrier-side gating.",
            "deadline_class_max_tokens clamps replay max_tokens budgets per deadline class before dispatch so objective-function changes remain explicit and auditable in the archived artifacts.",
            "baseline:balanced-operating-point and ablation:aggressive-upper-bound promote the current paper-facing class-cap profiles into first-class variant policies instead of ad hoc CLI overrides.",
            "ablation:adaptive-controller switches between balanced and aggressive class-cap profiles from live endpoint load so objective shaping becomes a runtime controller instead of a manually selected static profile.",
            "Remaining policy-distinct variants still require a policy-aware control-plane executor or endpoint pools per model.",
            "free_vram_bytes and reserved_vram_bytes remain null until engine-side memory state is exported in a carrier-consumable form.",
        ],
        "request_mix": {
            "phase_counts": dict(phase_counts),
            "deadline_class_counts": dict(class_counts),
            "prefix_cache_key_counts": dict(prefix_cache_key_counts),
            "route_outcome_counts": dict(route_outcome_counts),
            "backend_scope_counts": dict(backend_scope_counts),
        },
    }

    raw_log_output.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )
    trace_output.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in trace_rows)
        + ("\n" if trace_rows else ""),
        encoding="utf-8",
    )
    summary_output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "summary_output": str(summary_output),
        "trace_output": str(trace_output),
        "raw_log_output": str(raw_log_output),
        "variant": args.variant_name,
    }


def main() -> int:
    args = _parse_args()
    result = asyncio.run(_run_replay(args))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())