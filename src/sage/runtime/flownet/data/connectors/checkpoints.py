from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from threading import RLock
from typing import Any

from sage.runtime.flownet.client.handles import InstanceHandle

from .core import ConnectorCheckpoint


@dataclass(frozen=True)
class StoredConnectorCheckpoint:
    scope: str
    checkpoint: ConnectorCheckpoint
    revision: int
    updated_at_epoch_ms: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "checkpoint": self.checkpoint.as_dict(),
            "revision": int(self.revision),
            "updated_at_epoch_ms": int(self.updated_at_epoch_ms),
            "metadata": dict(self.metadata),
        }


class ConnectorCheckpointStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._records: dict[str, StoredConnectorCheckpoint] = {}

    def save_connector_checkpoint(
        self,
        scope: str,
        checkpoint: ConnectorCheckpoint | Mapping[str, Any],
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> StoredConnectorCheckpoint:
        normalized_scope = _normalize_non_empty(scope, field_name="scope")
        normalized_checkpoint = _coerce_connector_checkpoint(checkpoint)
        normalized_metadata = _normalize_mapping(metadata, field_name="metadata")
        with self._lock:
            previous = self._records.get(normalized_scope)
            revision = 1 if previous is None else int(previous.revision) + 1
            record = StoredConnectorCheckpoint(
                scope=normalized_scope,
                checkpoint=normalized_checkpoint,
                revision=revision,
                updated_at_epoch_ms=_now_epoch_ms(),
                metadata=normalized_metadata,
            )
            self._records[normalized_scope] = record
            return record

    def load_connector_checkpoint(self, scope: str) -> StoredConnectorCheckpoint | None:
        normalized_scope = _normalize_non_empty(scope, field_name="scope")
        with self._lock:
            return self._records.get(normalized_scope)

    def resolve_resume_offset(self, scope: str) -> int:
        record = self.load_connector_checkpoint(scope)
        if record is None:
            return 0
        return int(record.checkpoint.cursor)

    def clear_connector_checkpoint(self, scope: str) -> bool:
        normalized_scope = _normalize_non_empty(scope, field_name="scope")
        with self._lock:
            return self._records.pop(normalized_scope, None) is not None

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            records = list(self._records.values())
        records.sort(key=lambda item: item.scope)
        return [record.as_dict() for record in records]

    def snapshot_state(self) -> dict[str, Any]:
        return {"records": self.snapshot()}

    def restore_state(self, snapshot: Mapping[str, Any]) -> None:
        if not isinstance(snapshot, Mapping):
            raise TypeError("checkpoint snapshot must be a mapping.")
        raw_records = snapshot.get("records")
        if not isinstance(raw_records, list):
            raise TypeError("checkpoint snapshot records must be a list.")
        restored_records: dict[str, StoredConnectorCheckpoint] = {}
        for raw_record in raw_records:
            record = _coerce_stored_connector_checkpoint(raw_record)
            restored_records[record.scope] = record
        with self._lock:
            self._records = restored_records


def build_connector_checkpoint_scope(
    *,
    connector: str,
    path: str,
    source: InstanceHandle | str | None = None,
    flow_instance_id: str | None = None,
    namespace: str | None = None,
) -> str:
    parts = [
        f"connector={_normalize_non_empty(connector, field_name='connector')}",
        f"path={_normalize_non_empty(path, field_name='path')}",
    ]
    normalized_source_uri = _normalize_source_uri(source)
    if normalized_source_uri is not None:
        parts.append(f"source={normalized_source_uri}")
    normalized_flow_instance_id = _normalize_optional_non_empty(flow_instance_id)
    if normalized_flow_instance_id is not None:
        parts.append(f"flow_instance_id={normalized_flow_instance_id}")
    normalized_namespace = _normalize_optional_non_empty(namespace)
    if normalized_namespace is not None:
        parts.append(f"namespace={normalized_namespace}")
    return "|".join(parts)


def build_connector_checkpoint_handler(
    store: Any,
    scope: str,
    *,
    metadata: Mapping[str, Any] | None = None,
) -> Callable[[ConnectorCheckpoint], None]:
    normalized_scope = _normalize_non_empty(scope, field_name="scope")
    normalized_metadata = _normalize_mapping(metadata, field_name="metadata")

    def _handle(checkpoint: ConnectorCheckpoint) -> None:
        save_connector_checkpoint(
            store,
            normalized_scope,
            checkpoint,
            metadata=normalized_metadata,
        )

    return _handle


def save_connector_checkpoint(
    store: Any,
    scope: str,
    checkpoint: ConnectorCheckpoint | Mapping[str, Any],
    *,
    metadata: Mapping[str, Any] | None = None,
) -> StoredConnectorCheckpoint:
    resolved_store = _resolve_connector_checkpoint_store(store)
    return resolved_store.save_connector_checkpoint(scope, checkpoint, metadata=metadata)


def load_connector_checkpoint(store: Any, scope: str) -> StoredConnectorCheckpoint | None:
    resolved_store = _resolve_connector_checkpoint_store(store)
    return resolved_store.load_connector_checkpoint(scope)


def resolve_connector_resume_offset(store: Any, scope: str) -> int:
    resolved_store = _resolve_connector_checkpoint_store(store)
    return resolved_store.resolve_resume_offset(scope)


def clear_connector_checkpoint(store: Any, scope: str) -> bool:
    resolved_store = _resolve_connector_checkpoint_store(store)
    return resolved_store.clear_connector_checkpoint(scope)


def _resolve_connector_checkpoint_store(store: Any) -> ConnectorCheckpointStore:
    candidate = getattr(store, "service_object", store)
    if not hasattr(candidate, "save_connector_checkpoint"):
        raise TypeError(
            "checkpoint store must expose save_connector_checkpoint/load_connector_checkpoint methods."
        )
    return candidate


def _coerce_connector_checkpoint(
    checkpoint: ConnectorCheckpoint | Mapping[str, Any],
) -> ConnectorCheckpoint:
    if isinstance(checkpoint, ConnectorCheckpoint):
        return checkpoint
    if not isinstance(checkpoint, Mapping):
        raise TypeError("checkpoint must be ConnectorCheckpoint or mapping.")
    return ConnectorCheckpoint(
        connector=_normalize_non_empty(checkpoint.get("connector"), field_name="connector"),
        path=_normalize_non_empty(checkpoint.get("path"), field_name="path"),
        cursor=_coerce_non_negative_int(checkpoint.get("cursor"), field_name="cursor"),
        rows_seen=_coerce_non_negative_int(checkpoint.get("rows_seen"), field_name="rows_seen"),
        rows_emitted=_coerce_non_negative_int(
            checkpoint.get("rows_emitted"),
            field_name="rows_emitted",
        ),
    )


def _coerce_stored_connector_checkpoint(raw_value: Any) -> StoredConnectorCheckpoint:
    if not isinstance(raw_value, Mapping):
        raise TypeError("stored checkpoint snapshot rows must be mappings.")
    return StoredConnectorCheckpoint(
        scope=_normalize_non_empty(raw_value.get("scope"), field_name="scope"),
        checkpoint=_coerce_connector_checkpoint(raw_value.get("checkpoint")),
        revision=_coerce_non_negative_int(raw_value.get("revision"), field_name="revision"),
        updated_at_epoch_ms=_coerce_non_negative_int(
            raw_value.get("updated_at_epoch_ms"),
            field_name="updated_at_epoch_ms",
        ),
        metadata=_normalize_mapping(raw_value.get("metadata"), field_name="metadata"),
    )


def _normalize_source_uri(source: InstanceHandle | str | None) -> str | None:
    if source is None:
        return None
    if isinstance(source, InstanceHandle):
        return _normalize_non_empty(source.uri, field_name="source_uri")
    return _normalize_optional_non_empty(source)


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


def _coerce_non_negative_int(raw_value: Any, *, field_name: str) -> int:
    try:
        normalized = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a non-negative integer.") from exc
    if normalized < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return normalized


def _now_epoch_ms() -> int:
    return int(time.time() * 1000)


__all__ = [
    "ConnectorCheckpointStore",
    "StoredConnectorCheckpoint",
    "build_connector_checkpoint_handler",
    "build_connector_checkpoint_scope",
    "clear_connector_checkpoint",
    "load_connector_checkpoint",
    "resolve_connector_resume_offset",
    "save_connector_checkpoint",
]
