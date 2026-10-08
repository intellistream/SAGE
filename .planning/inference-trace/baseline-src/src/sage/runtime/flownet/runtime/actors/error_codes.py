from __future__ import annotations

ACTOR_POLICY_MAX_PENDING_EXCEEDED = "actor_policy_max_pending_exceeded"
ACTOR_POLICY_MAX_PARALLEL_TOOLS_EXCEEDED = "actor_policy_max_parallel_tools_exceeded"
ACTOR_TASK_TIMEOUT = "actor_task_timeout"
ACTOR_TASK_CANCELLED = "actor_task_cancelled"
ACTOR_CALLBACK_DETACHED = "actor_callback_detached"


def build_error_message(code: str, **fields) -> str:
    normalized_code = str(code or "").strip()
    if not normalized_code:
        raise ValueError("code must be non-empty.")
    if not fields:
        return normalized_code
    pairs: list[str] = []
    for key in sorted(fields):
        pairs.append(f"{key}={fields[key]}")
    return f"{normalized_code}:{','.join(pairs)}"


__all__ = [
    "ACTOR_POLICY_MAX_PENDING_EXCEEDED",
    "ACTOR_POLICY_MAX_PARALLEL_TOOLS_EXCEEDED",
    "ACTOR_TASK_TIMEOUT",
    "ACTOR_TASK_CANCELLED",
    "ACTOR_CALLBACK_DETACHED",
    "build_error_message",
]
