from __future__ import annotations

import asyncio
import json
from typing import Any


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

DIRECT_ENDPOINT_VARIANT_POLICIES: dict[tuple[str, str], dict[str, Any]] = {
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

EXECUTION_PRIORITY_MODES = ("off", "invert-vamos")


def load_deadline_class_max_tokens(args: Any) -> dict[str, int]:
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


def normalize_deadline_class_max_tokens(
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


def normalize_adaptive_deadline_class_max_tokens(
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
        profiles[str(profile_name)] = normalize_deadline_class_max_tokens(
            max_tokens,
            source_label=f"{source_label} adaptive_deadline_class_max_tokens[{profile_name!r}]",
        )
    if "default" not in profiles or "overload" not in profiles:
        raise ValueError(
            f"{source_label} adaptive_deadline_class_max_tokens must define both 'default' and 'overload' profiles."
        )
    return profiles


def resolve_deadline_class_max_tokens(
    args: Any,
    variant_policy: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    cli_caps = load_deadline_class_max_tokens(args)
    policy_caps = normalize_deadline_class_max_tokens(
        variant_policy.get("deadline_class_max_tokens"),
        source_label="variant policy",
    )
    adaptive_policy_caps = normalize_adaptive_deadline_class_max_tokens(
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


def policy_overload_state(
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


def compute_pressure_ratio(
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


def graduated_shaping_caps(
    policy: dict[str, Any],
    snapshot: dict[str, float | None],
) -> tuple[dict[str, int], str | None]:
    graduated_config = policy.get("graduated_shaping")
    if not graduated_config:
        return {}, None
    pressure = compute_pressure_ratio(policy, snapshot)
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


def risk_aware_shaping_caps(
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


def deadline_class_max_tokens_for_request(
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
        return graduated_shaping_caps(policy, snapshot)
    if controller_mode == "risk-aware":
        return risk_aware_shaping_caps(policy, event or {}, snapshot)
    if controller_mode != "adaptive":
        return {}, None
    overloaded, _ = policy_overload_state(policy, snapshot)
    profile_name = "overload" if overloaded else "default"
    return dict(profiles.get(profile_name) or {}), profile_name


def validate_direct_endpoint_variant(variant: dict[str, Any]) -> None:
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


def variant_policy_for(kind: str, name: str) -> dict[str, Any]:
    try:
        return dict(DIRECT_ENDPOINT_VARIANT_POLICIES[(kind, name)])
    except KeyError as exc:
        raise ValueError(f"No direct-endpoint policy profile defined for {kind}:{name}") from exc


def map_execution_priority(serving_context: dict[str, Any], mode: str) -> int | None:
    if mode == "off":
        return None
    priority = int(serving_context.get("priority") or 0)
    if mode == "invert-vamos":
        return -priority
    raise ValueError(f"Unsupported execution priority mode: {mode}")


def effective_output_len(
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


def policy_dispatch_decision(
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

    overloaded, reason = policy_overload_state(policy, snapshot)
    return {
        "action": "delay" if overloaded else "dispatch",
        "reason": reason,
        "mode": mode,
        "observed_load": snapshot,
    }


def live_load_snapshot(
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


async def await_policy_dispatch_window(
    event: dict[str, Any],
    base_url: str,
    policy: dict[str, Any],
    current_load: dict[str, dict[str, float | None]],
) -> dict[str, Any]:
    total_delay_s = 0.0
    deferral_count = 0
    while True:
        snapshot = live_load_snapshot(current_load, base_url)
        decision = policy_dispatch_decision(policy, event, snapshot, elapsed_delay_s=total_delay_s)
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
