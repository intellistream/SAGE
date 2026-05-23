from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

RecoveryPolicy = Literal["best_effort", "restart", "checkpoint_restore"]
RecoverySummaryStatus = Literal[
    "not_attempted",
    "restarted",
    "checkpoint_restored",
    "failed",
]

_RECOVERY_POLICIES = frozenset({"best_effort", "restart", "checkpoint_restore"})
_RECOVERY_SUMMARY_STATUSES = frozenset(
    {"not_attempted", "restarted", "checkpoint_restored", "failed"}
)
_CHECKPOINT_METHODS = ("snapshot_state", "restore_state")


@dataclass(frozen=True)
class RecoveryStatusSummary:
    status: RecoverySummaryStatus = "not_attempted"
    last_action: RecoveryPolicy | None = None
    updated_at_epoch_ms: int | None = None
    detail: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "status",
            _normalize_choice(
                self.status,
                field_name="status",
                allowed=_RECOVERY_SUMMARY_STATUSES,
            ),
        )
        last_action = _normalize_optional_non_empty(self.last_action)
        if last_action is not None:
            last_action = normalize_recovery_policy(last_action, field_name="last_action")
        object.__setattr__(self, "last_action", last_action)
        updated_at_epoch_ms = self.updated_at_epoch_ms
        if updated_at_epoch_ms is not None:
            try:
                updated_at_epoch_ms = int(updated_at_epoch_ms)
            except (TypeError, ValueError) as exc:
                raise ValueError("updated_at_epoch_ms must be an integer when provided.") from exc
            if updated_at_epoch_ms < 0:
                raise ValueError("updated_at_epoch_ms must be >= 0 when provided.")
        object.__setattr__(self, "updated_at_epoch_ms", updated_at_epoch_ms)
        object.__setattr__(self, "detail", _normalize_optional_non_empty(self.detail))
        object.__setattr__(
            self, "metadata", _normalize_mapping(self.metadata, field_name="metadata")
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "last_action": self.last_action,
            "updated_at_epoch_ms": self.updated_at_epoch_ms,
            "detail": self.detail,
            "metadata": dict(self.metadata),
        }


def normalize_recovery_policy(
    raw_value: Any, *, field_name: str = "recovery_policy"
) -> RecoveryPolicy:
    return _normalize_choice(raw_value, field_name=field_name, allowed=_RECOVERY_POLICIES)


def normalize_recovery_status_summary(
    raw_value: RecoveryStatusSummary | Mapping[str, Any] | None,
) -> RecoveryStatusSummary:
    if raw_value is None:
        return RecoveryStatusSummary()
    if isinstance(raw_value, RecoveryStatusSummary):
        return raw_value
    if not isinstance(raw_value, Mapping):
        raise TypeError("recovery summary must be a RecoveryStatusSummary or mapping.")
    return RecoveryStatusSummary(
        status=raw_value.get("status", "not_attempted"),
        last_action=raw_value.get("last_action"),
        updated_at_epoch_ms=raw_value.get("updated_at_epoch_ms"),
        detail=raw_value.get("detail"),
        metadata=_normalize_mapping(raw_value.get("metadata"), field_name="metadata"),
    )


def build_initial_recovery_summary() -> RecoveryStatusSummary:
    return RecoveryStatusSummary(status="not_attempted")


def build_recovery_success_summary(
    *,
    action: RecoveryPolicy,
    updated_at_epoch_ms: int | None = None,
    detail: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> RecoveryStatusSummary:
    normalized_action = normalize_recovery_policy(action, field_name="action")
    status: RecoverySummaryStatus = "checkpoint_restored"
    if normalized_action != "checkpoint_restore":
        status = "restarted"
    return RecoveryStatusSummary(
        status=status,
        last_action=normalized_action,
        updated_at_epoch_ms=updated_at_epoch_ms,
        detail=detail,
        metadata=_normalize_mapping(metadata, field_name="metadata"),
    )


def build_recovery_failure_summary(
    *,
    action: RecoveryPolicy,
    error: Any,
    updated_at_epoch_ms: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> RecoveryStatusSummary:
    normalized_metadata = _normalize_mapping(metadata, field_name="metadata")
    if error is not None:
        normalized_metadata.setdefault("error", str(error))
    return RecoveryStatusSummary(
        status="failed",
        last_action=normalize_recovery_policy(action, field_name="action"),
        updated_at_epoch_ms=updated_at_epoch_ms,
        detail=_normalize_optional_non_empty(error),
        metadata=normalized_metadata,
    )


def checkpoint_restore_supported(target: Any) -> bool:
    return not missing_checkpoint_restore_methods(target)


def missing_checkpoint_restore_methods(target: Any) -> tuple[str, ...]:
    missing: list[str] = []
    for method_name in _CHECKPOINT_METHODS:
        if not callable(getattr(target, method_name, None)):
            missing.append(method_name)
    return tuple(missing)


def require_checkpoint_restore_support(
    target: Any,
    *,
    error_prefix: str,
    details: Mapping[str, Any] | None = None,
) -> None:
    missing_methods = missing_checkpoint_restore_methods(target)
    if not missing_methods:
        return
    payload = dict(details or {})
    payload.setdefault("object_type", type(target).__name__)
    payload["missing_methods"] = ",".join(missing_methods)
    raise RuntimeError(_format_error(error_prefix, payload))


def snapshot_checkpoint_state(target: Any) -> Any:
    return target.snapshot_state()


def restore_checkpoint_state(target: Any, snapshot: Any) -> None:
    target.restore_state(snapshot)


def _format_error(error_prefix: str, details: Mapping[str, Any]) -> str:
    parts = [str(error_prefix).strip()]
    rendered = []
    for key, value in details.items():
        normalized_key = str(key or "").strip()
        if not normalized_key:
            continue
        rendered.append(f"{normalized_key}={value}")
    if rendered:
        parts.append(" ".join(rendered))
    return ":".join(parts)


def _normalize_choice(
    raw_value: Any, *, field_name: str, allowed: set[str] | frozenset[str]
) -> str:
    normalized = _normalize_non_empty(raw_value, field_name=field_name).lower()
    if normalized not in allowed:
        raise ValueError(f"{field_name} must be one of: {', '.join(sorted(allowed))}.")
    return normalized


def _normalize_mapping(raw_value: Any, *, field_name: str) -> dict[str, Any]:
    if raw_value is None:
        return {}
    if not isinstance(raw_value, Mapping):
        raise TypeError(f"{field_name} must be a mapping when provided.")
    return dict(raw_value)


def _normalize_non_empty(raw_value: Any, *, field_name: str) -> str:
    normalized = str(raw_value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty.")
    return normalized


def _normalize_optional_non_empty(raw_value: Any) -> str | None:
    if raw_value is None:
        return None
    normalized = str(raw_value).strip()
    if not normalized:
        return None
    return normalized


__all__ = [
    "RecoveryPolicy",
    "RecoveryStatusSummary",
    "RecoverySummaryStatus",
    "build_initial_recovery_summary",
    "build_recovery_failure_summary",
    "build_recovery_success_summary",
    "checkpoint_restore_supported",
    "missing_checkpoint_restore_methods",
    "normalize_recovery_policy",
    "normalize_recovery_status_summary",
    "require_checkpoint_restore_support",
    "restore_checkpoint_state",
    "snapshot_checkpoint_state",
]
