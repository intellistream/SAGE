from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

FLOW_ENDPOINT_PUBLISHED = "published"
FLOW_ENDPOINT_RELEASED = "released"
_FLOW_ENDPOINT_STATUSES = frozenset({FLOW_ENDPOINT_PUBLISHED, FLOW_ENDPOINT_RELEASED})


@dataclass(frozen=True)
class FlowEndpointDescriptor:
    endpoint_id: str
    name: str
    namespace: str
    flow_uri: str
    owner: str
    version: str
    flow_instance_id: str
    in_topic: str
    out_topic: str
    status: str = FLOW_ENDPOINT_PUBLISHED
    flow_process_uri: str | None = None
    declaration_id: str | None = None
    definition_hash: str | None = None
    bind_hash: str | None = None
    shared_state_bindings: tuple[dict[str, Any], ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    published_at_epoch_ms: int = field(default_factory=lambda: int(time.time() * 1000))

    def __post_init__(self) -> None:
        object.__setattr__(self, "endpoint_id", _normalize_non_empty(self.endpoint_id, field_name="endpoint_id"))
        object.__setattr__(self, "name", _normalize_non_empty(self.name, field_name="name"))
        object.__setattr__(self, "namespace", _normalize_non_empty(self.namespace, field_name="namespace"))
        object.__setattr__(self, "flow_uri", _normalize_non_empty(self.flow_uri, field_name="flow_uri"))
        object.__setattr__(self, "owner", _normalize_non_empty(self.owner, field_name="owner"))
        object.__setattr__(self, "version", _normalize_non_empty(self.version, field_name="version"))
        object.__setattr__(self, "flow_instance_id", _normalize_non_empty(self.flow_instance_id, field_name="flow_instance_id"))
        object.__setattr__(self, "in_topic", _normalize_non_empty(self.in_topic, field_name="in_topic"))
        object.__setattr__(self, "out_topic", _normalize_non_empty(self.out_topic, field_name="out_topic"))
        normalized_status = _normalize_non_empty(self.status, field_name="status").lower()
        if normalized_status not in _FLOW_ENDPOINT_STATUSES:
            raise ValueError("status must be one of: published, released.")
        object.__setattr__(self, "status", normalized_status)
        object.__setattr__(self, "flow_process_uri", _normalize_optional_non_empty(self.flow_process_uri))
        object.__setattr__(self, "declaration_id", _normalize_optional_non_empty(self.declaration_id))
        object.__setattr__(self, "definition_hash", _normalize_optional_non_empty(self.definition_hash))
        object.__setattr__(self, "bind_hash", _normalize_optional_non_empty(self.bind_hash))
        object.__setattr__(
            self,
            "shared_state_bindings",
            tuple(_normalize_shared_state_bindings(self.shared_state_bindings)),
        )
        object.__setattr__(self, "metadata", _normalize_mapping(self.metadata, field_name="metadata"))
        object.__setattr__(
            self,
            "published_at_epoch_ms",
            _normalize_non_negative_int(self.published_at_epoch_ms, field_name="published_at_epoch_ms"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "endpoint_id": self.endpoint_id,
            "name": self.name,
            "namespace": self.namespace,
            "flow_uri": self.flow_uri,
            "owner": self.owner,
            "version": self.version,
            "flow_instance_id": self.flow_instance_id,
            "in_topic": self.in_topic,
            "out_topic": self.out_topic,
            "status": self.status,
            "flow_process_uri": self.flow_process_uri,
            "declaration_id": self.declaration_id,
            "definition_hash": self.definition_hash,
            "bind_hash": self.bind_hash,
            "shared_state_bindings": [dict(item) for item in self.shared_state_bindings],
            "metadata": dict(self.metadata),
            "published_at_epoch_ms": int(self.published_at_epoch_ms),
        }


def _normalize_shared_state_bindings(raw_value: Any) -> list[dict[str, Any]]:
    if raw_value is None:
        return []
    if not isinstance(raw_value, Sequence) or isinstance(raw_value, (str, bytes, bytearray)):
        raise TypeError("shared_state_bindings must be a sequence when provided.")
    normalized: list[dict[str, Any]] = []
    for item in raw_value:
        if not isinstance(item, Mapping):
            raise TypeError("shared_state_bindings items must be mappings.")
        normalized.append(dict(item))
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


def _normalize_non_negative_int(raw_value: Any, *, field_name: str) -> int:
    try:
        normalized = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a non-negative integer.") from exc
    if normalized < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return normalized


__all__ = [
    "FLOW_ENDPOINT_PUBLISHED",
    "FLOW_ENDPOINT_RELEASED",
    "FlowEndpointDescriptor",
]