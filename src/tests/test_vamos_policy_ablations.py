from __future__ import annotations

import asyncio

from sage.serving.integrations.policy import (
    DIRECT_ENDPOINT_VARIANT_POLICIES,
    SUPPORTED_DIRECT_ENDPOINT_VARIANTS,
    await_policy_dispatch_window,
    effective_output_len,
    policy_dispatch_decision,
)


EVENT = {
    "serving_context": {
        "deadline_class": "batch-standard",
        "priority": 20,
        "max_tokens": 256,
    }
}
OVERLOADED = {
    "http://endpoint": {
        "num_requests_running": 4.0,
        "num_requests_waiting": 1.0,
        "kv_cache_usage_perc": 0.1,
    }
}


def test_shaping_only_changes_budget_without_flow_control() -> None:
    key = ("ablation", "shaping-only")
    assert key in SUPPORTED_DIRECT_ENDPOINT_VARIANTS
    policy = DIRECT_ENDPOINT_VARIANT_POLICIES[key]
    decision = policy_dispatch_decision(
        policy,
        EVENT,
        OVERLOADED["http://endpoint"],
    )
    assert decision["action"] == "dispatch"
    assert effective_output_len(
        EVENT["serving_context"],
        policy["deadline_class_max_tokens"],
    ) == (256, 64)
    assert "admission_control" not in policy


def test_deferral_only_preserves_original_budget_and_never_policy_rejects() -> None:
    key = ("ablation", "deferral-only")
    assert key in SUPPORTED_DIRECT_ENDPOINT_VARIANTS
    policy = DIRECT_ENDPOINT_VARIANT_POLICIES[key]
    decision = policy_dispatch_decision(
        policy,
        EVENT,
        OVERLOADED["http://endpoint"],
    )
    assert decision["action"] == "delay"
    assert effective_output_len(EVENT["serving_context"], {}) == (256, 256)
    assert policy["admission_control"] is False


def test_admission_only_rejects_residual_overload_without_shaping() -> None:
    key = ("ablation", "admission-only")
    assert key in SUPPORTED_DIRECT_ENDPOINT_VARIANTS
    policy = dict(DIRECT_ENDPOINT_VARIANT_POLICIES[key])
    policy["defer_interval_sec"] = 0.0
    result = asyncio.run(
        await_policy_dispatch_window(
            EVENT,
            "http://endpoint",
            policy,
            OVERLOADED,
        )
    )
    assert result["policy_action"] == "reject"
    assert effective_output_len(EVENT["serving_context"], {}) == (256, 256)
