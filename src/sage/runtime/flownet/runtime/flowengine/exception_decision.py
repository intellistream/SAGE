from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

DecisionAction = Literal["propagate", "fallback", "drop", "abort"]

_ALLOWED_DECISION_KEYS = frozenset({"action", "fallback_payloads", "metadata"})


@dataclass(frozen=True)
class ExceptionDecisionEnvelope:
    action: DecisionAction
    fallback_payloads: tuple[Any, ...] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ExceptionDecisionNormalizeError(ValueError):
    """Raised when exception decision payload cannot be normalized."""


def normalize_exception_decision(raw: Any) -> ExceptionDecisionEnvelope | None:
    if raw is None:
        return None
    if isinstance(raw, ExceptionDecisionEnvelope):
        return raw
    if not isinstance(raw, dict):
        raise ExceptionDecisionNormalizeError(
            f"unsupported_exception_decision_type:{type(raw).__name__}",
        )

    keys = set(raw.keys())
    unknown = sorted(key for key in keys - _ALLOWED_DECISION_KEYS)
    if unknown:
        raise ExceptionDecisionNormalizeError(f"exception_decision_unknown_keys:{unknown}")

    action = raw.get("action")
    if not isinstance(action, str):
        raise ExceptionDecisionNormalizeError("exception_decision_action_must_be_string")
    normalized_action = action.strip()
    if normalized_action not in {"propagate", "fallback", "drop", "abort"}:
        raise ExceptionDecisionNormalizeError(
            f"exception_decision_unknown_action:{normalized_action}",
        )

    metadata_raw = raw.get("metadata", {})
    if metadata_raw is None:
        metadata_raw = {}
    if not isinstance(metadata_raw, dict):
        raise ExceptionDecisionNormalizeError("exception_decision_metadata_must_be_dict")
    metadata = {str(key): value for key, value in metadata_raw.items()}

    fallback_payloads_raw = raw.get("fallback_payloads")
    fallback_payloads: tuple[Any, ...] | None
    if fallback_payloads_raw is None:
        fallback_payloads = None
    elif isinstance(fallback_payloads_raw, list):
        fallback_payloads = tuple(fallback_payloads_raw)
    elif isinstance(fallback_payloads_raw, tuple):
        fallback_payloads = tuple(fallback_payloads_raw)
    else:
        raise ExceptionDecisionNormalizeError(
            "exception_decision_fallback_payloads_must_be_list_or_tuple"
        )

    if normalized_action != "fallback" and fallback_payloads not in (
        None,
        (),
    ):  # strict no-op payloads
        raise ExceptionDecisionNormalizeError(
            "exception_decision_non_fallback_must_not_set_fallback_payloads",
        )

    if normalized_action == "fallback" and fallback_payloads is None:
        fallback_payloads = ()

    return ExceptionDecisionEnvelope(
        action=normalized_action,
        fallback_payloads=fallback_payloads,
        metadata=metadata,
    )


__all__ = [
    "DecisionAction",
    "ExceptionDecisionEnvelope",
    "ExceptionDecisionNormalizeError",
    "normalize_exception_decision",
]
