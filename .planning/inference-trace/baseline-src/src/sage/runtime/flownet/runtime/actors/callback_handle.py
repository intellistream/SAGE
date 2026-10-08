from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CallbackHandle:
    """Opaque callback registration handle returned to API callers."""

    callback_id: str
    topic_uri: str
    worker_address: str
    callback_target: dict[str, str]
    detached: bool = False
    owner_address: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "callback_id": self.callback_id,
            "topic_uri": self.topic_uri,
            "worker_address": self.worker_address,
            "callback_target": dict(self.callback_target),
            "detached": bool(self.detached),
        }
        if self.owner_address is not None:
            payload["owner_address"] = self.owner_address
        return payload


def coerce_callback_handle(value: Any) -> CallbackHandle:
    if isinstance(value, CallbackHandle):
        return value
    if not isinstance(value, dict):
        raise TypeError("callback handle must be CallbackHandle or dict.")
    callback_target = value.get("callback_target")
    if not isinstance(callback_target, dict):
        raise TypeError("callback_target must be a dict.")
    normalized_target = {
        "address": _normalize_non_empty(
            callback_target.get("address"), field_name="callback_target.address"
        ),
        "actor_id": _normalize_non_empty(
            callback_target.get("actor_id"),
            field_name="callback_target.actor_id",
        ),
        "method": _normalize_non_empty(
            callback_target.get("method"),
            field_name="callback_target.method",
        ),
    }
    owner_address = value.get("owner_address")
    if owner_address is not None:
        owner_address = _normalize_non_empty(owner_address, field_name="owner_address")
    return CallbackHandle(
        callback_id=_normalize_non_empty(value.get("callback_id"), field_name="callback_id"),
        topic_uri=_normalize_non_empty(value.get("topic_uri"), field_name="topic_uri"),
        worker_address=_normalize_non_empty(
            value.get("worker_address"),
            field_name="worker_address",
        ),
        callback_target=normalized_target,
        detached=bool(value.get("detached", False)),
        owner_address=owner_address,
    )


def _normalize_non_empty(value: Any, *, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty.")
    return normalized


__all__ = ["CallbackHandle", "coerce_callback_handle"]
