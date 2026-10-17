from __future__ import annotations

import copy
import inspect
import os
import pickle
import sqlite3
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .errors import StatefulProcessContractError
from .models import _StateEntry
from .protocols import StatefulSpec
from .utils import _stable_key_fragment


class StateMutation(Enum):
    """Explicit batch mutation markers; None remains an ordinary stored value."""

    DELETE = "delete"


@dataclass(frozen=True)
class StatefulStateHandle:
    stage_id: str
    namespace: str
    key: str
    ttl_seconds: float | None
    _runtime: StatefulProcessRuntime = field(repr=False, compare=False)
    _slot: tuple[str, str, str] = field(repr=False, compare=False)

    def get(self, default: Any = None) -> Any:
        return self._runtime.get(self._slot, default=default, ttl_seconds=self.ttl_seconds)

    def set(self, value: Any) -> Any:
        self._runtime.set(self._slot, value, ttl_seconds=self.ttl_seconds)
        return value

    def clear(self) -> bool:
        return self._runtime.delete(self._slot)

    def update(self, transform: Callable[[Any], Any], *, default: Any = None) -> Any:
        """Atomically replace state; transform must be pure and must not reenter storage."""
        return self._runtime.update(
            self._slot, transform, default=default, ttl_seconds=self.ttl_seconds
        )


class _StateBackend:
    def scan_stage(self, *, stage_id, namespace, after_key, limit):  # pragma: no cover
        raise NotImplementedError

    def update(self, slot, transform):
        return self.update_many((slot,), lambda entries: {slot: transform(entries[slot])})[slot]

    def update_many(self, slots, transform):  # pragma: no cover - interface
        raise NotImplementedError

    def get(self, slot: tuple[str, str, str]) -> _StateEntry | None:  # pragma: no cover - interface
        raise NotImplementedError

    def put(
        self, slot: tuple[str, str, str], entry: _StateEntry
    ) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def delete(self, slot: tuple[str, str, str]) -> bool:  # pragma: no cover - interface
        raise NotImplementedError

    def query(
        self,
        *,
        namespace: str,
        prefix: str,
        limit: int,
        cursor: int,
    ) -> tuple[list[dict[str, Any]], int | None]:  # pragma: no cover - interface
        raise NotImplementedError

    def close(self) -> None:  # pragma: no cover - interface
        return None


class _MemoryStateBackend(_StateBackend):
    def __init__(self) -> None:
        self._state: dict[tuple[str, str, str], _StateEntry] = {}

    def scan_stage(self, *, stage_id, namespace, after_key, limit):
        keys = sorted(key for stage, ns, key in self._state
                      if stage == stage_id and ns == namespace
                      and (after_key is None or key > after_key))
        page = keys[:limit]
        rows = []
        for key in page:
            entry = self._state[(stage_id, namespace, key)]
            rows.append({"stage_id": stage_id, "namespace": namespace, "key": key,
                         "updated_at_ms": int(entry.updated_at * 1000), "value": entry.value})
        return rows, page[-1] if len(keys) > limit else None

    def update_many(self, slots, transform):
        entries = transform(copy.deepcopy({slot: self._state.get(slot) for slot in slots}))
        # All potentially failing copies precede publication of any entry.
        saved = copy.deepcopy(entries)
        result = copy.deepcopy(entries)
        for slot, entry in saved.items():
            if entry is None:
                self._state.pop(slot, None)
            else:
                self._state[slot] = entry
        return result

    def get(self, slot: tuple[str, str, str]) -> _StateEntry | None:
        return self._state.get(slot)

    def put(self, slot: tuple[str, str, str], entry: _StateEntry) -> None:
        self._state[slot] = entry

    def delete(self, slot: tuple[str, str, str]) -> bool:
        return self._state.pop(slot, None) is not None

    def query(
        self,
        *,
        namespace: str,
        prefix: str,
        limit: int,
        cursor: int,
    ) -> tuple[list[dict[str, Any]], int | None]:
        rows: list[dict[str, Any]] = []
        for (stage_id, entry_namespace, key), entry in self._state.items():
            if entry_namespace != namespace:
                continue
            if prefix and not key.startswith(prefix):
                continue
            rows.append(
                {
                    "key": key,
                    "namespace": entry_namespace,
                    "stage_id": stage_id,
                    "updated_at_ms": int(entry.updated_at * 1000.0),
                    "value": entry.value,
                }
            )
        rows.sort(key=lambda item: (str(item.get("key") or ""), str(item.get("stage_id") or "")))
        page = rows[cursor : cursor + limit]
        next_cursor: int | None = None
        if cursor + limit < len(rows):
            next_cursor = cursor + limit
        return page, next_cursor


class _SQLiteStateBackend(_StateBackend):
    def scan_stage(self, *, stage_id, namespace, after_key, limit):
        predicate = " AND entry_key > ?" if after_key is not None else ""
        params = (stage_id, namespace) + ((after_key,) if after_key is not None else ())
        rows = self._conn.execute(
            "SELECT entry_key, updated_at, value_blob FROM state_entries "
            "WHERE stage_id = ? AND namespace = ?" + predicate +
            " ORDER BY entry_key LIMIT ?", (*params, limit + 1),
        ).fetchall()
        page = rows[:limit]
        result = [{"stage_id": stage_id, "namespace": namespace, "key": key,
                   "updated_at_ms": int(updated_at * 1000), "value": pickle.loads(blob)}
                  for key, updated_at, blob in page]
        return result, page[-1][0] if len(rows) > limit else None

    def __init__(self, *, sqlite_path: str) -> None:
        normalized_path = str(sqlite_path or "").strip()
        if not normalized_path:
            raise ValueError("sqlite_path must be provided when backend='sqlite'.")
        if normalized_path != ":memory:":
            parent = os.path.dirname(os.path.abspath(normalized_path))
            if parent:
                os.makedirs(parent, exist_ok=True)
        self._conn = sqlite3.connect(
            normalized_path,
            timeout=5.0,
            check_same_thread=False,
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS state_entries (
                stage_id TEXT NOT NULL,
                namespace TEXT NOT NULL,
                entry_key TEXT NOT NULL,
                updated_at REAL NOT NULL,
                value_blob BLOB NOT NULL,
                PRIMARY KEY (stage_id, namespace, entry_key)
            )
            """
        )
        self._conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_state_entries_namespace_key
            ON state_entries(namespace, entry_key, stage_id)
            """
        )
        self._conn.commit()

    def update_many(self, slots, transform):
        # Reserve the writer before reading, including across runtime instances.
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            entries = transform({slot: self.get(slot) for slot in slots})
            for slot, entry in entries.items():
                if entry is None:
                    self._conn.execute(
                        "DELETE FROM state_entries WHERE stage_id = ? AND namespace = ? AND entry_key = ?",
                        slot,
                    )
                else:
                    self._put_uncommitted(slot, entry)
            self._conn.commit()
            return entries
        except BaseException:
            self._conn.rollback()
            raise

    def get(self, slot: tuple[str, str, str]) -> _StateEntry | None:
        stage_id, namespace, key = slot
        row = self._conn.execute(
            """
            SELECT value_blob, updated_at
            FROM state_entries
            WHERE stage_id = ? AND namespace = ? AND entry_key = ?
            """,
            (stage_id, namespace, key),
        ).fetchone()
        if row is None:
            return None
        value_blob, updated_at = row
        return _StateEntry(
            value=pickle.loads(value_blob),
            updated_at=float(updated_at),
        )

    def put(self, slot: tuple[str, str, str], entry: _StateEntry) -> None:
        self._put_uncommitted(slot, entry)
        self._conn.commit()

    def _put_uncommitted(self, slot: tuple[str, str, str], entry: _StateEntry) -> None:
        stage_id, namespace, key = slot
        value_blob = sqlite3.Binary(pickle.dumps(entry.value, protocol=pickle.HIGHEST_PROTOCOL))
        self._conn.execute(
            """
            INSERT INTO state_entries(stage_id, namespace, entry_key, updated_at, value_blob)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(stage_id, namespace, entry_key)
            DO UPDATE SET
                updated_at = excluded.updated_at,
                value_blob = excluded.value_blob
            """,
            (stage_id, namespace, key, float(entry.updated_at), value_blob),
        )

    def delete(self, slot: tuple[str, str, str]) -> bool:
        stage_id, namespace, key = slot
        cursor = self._conn.execute(
            """
            DELETE FROM state_entries
            WHERE stage_id = ? AND namespace = ? AND entry_key = ?
            """,
            (stage_id, namespace, key),
        )
        self._conn.commit()
        return int(cursor.rowcount or 0) > 0

    def query(
        self,
        *,
        namespace: str,
        prefix: str,
        limit: int,
        cursor: int,
    ) -> tuple[list[dict[str, Any]], int | None]:
        query_limit = max(1, int(limit)) + 1
        query_cursor = max(0, int(cursor))
        if prefix:
            escaped_prefix = _escape_sql_like_prefix(prefix)
            rows = self._conn.execute(
                """
                SELECT stage_id, entry_key, updated_at, value_blob
                FROM state_entries
                WHERE namespace = ? AND entry_key LIKE ? ESCAPE '\\'
                ORDER BY entry_key ASC, stage_id ASC
                LIMIT ? OFFSET ?
                """,
                (namespace, f"{escaped_prefix}%", query_limit, query_cursor),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT stage_id, entry_key, updated_at, value_blob
                FROM state_entries
                WHERE namespace = ?
                ORDER BY entry_key ASC, stage_id ASC
                LIMIT ? OFFSET ?
                """,
                (namespace, query_limit, query_cursor),
            ).fetchall()

        next_cursor: int | None = None
        if len(rows) > limit:
            next_cursor = query_cursor + limit
            rows = rows[:limit]

        result: list[dict[str, Any]] = []
        for stage_id, key, updated_at, value_blob in rows:
            result.append(
                {
                    "key": str(key),
                    "namespace": namespace,
                    "stage_id": str(stage_id),
                    "updated_at_ms": int(float(updated_at) * 1000.0),
                    "value": pickle.loads(value_blob),
                }
            )
        return result, next_cursor

    def close(self) -> None:
        self._conn.close()


def _escape_sql_like_prefix(prefix: str) -> str:
    return str(prefix).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _normalize_state_slot(slot: tuple[Any, Any, Any]) -> tuple[str, str, str]:
    stage_id_raw, namespace_raw, key_raw = slot
    stage_id = str(stage_id_raw or "").strip()
    namespace = str(namespace_raw or "").strip()
    key = str(key_raw or "").strip()
    if not stage_id:
        raise ValueError("state slot stage_id must be non-empty.")
    if not namespace:
        raise ValueError("state slot namespace must be non-empty.")
    if not key:
        raise ValueError("state slot key must be non-empty.")
    return stage_id, namespace, key


def _build_state_backend(
    *,
    backend: str,
    sqlite_path: str | None,
) -> _StateBackend:
    normalized_backend = str(backend or "memory").strip().lower() or "memory"
    if normalized_backend in {"memory", "in-memory", "mem"}:
        return _MemoryStateBackend()
    if normalized_backend == "sqlite":
        return _SQLiteStateBackend(
            sqlite_path=str(sqlite_path or "").strip(),
        )
    raise ValueError(f"unsupported_state_backend:{backend!r}")


class StatefulProcessRuntime:
    """
    Minimal state store for v1 `sys/stateful-process`.

    Contract freeze (Lane-C, phase-2 first slice):
    1. key source priority: `state_spec.key_field` > `state_spec.key_index` > tag `state_partition_key` > `0`.
    2. handler receives a mutable `StatefulStateHandle` and can `get/set/clear` state per resolved key.
    3. unsupported advanced families (`reducer/join/merge`) fail fast with explicit error type.
    """

    def __init__(
        self,
        *,
        time_fn: Callable[[], float] | None = None,
        backend: str = "memory",
        sqlite_path: str | None = None,
    ) -> None:
        self._time_fn = time_fn or time.time
        self._lock = threading.RLock()
        self._backend = _build_state_backend(
            backend=backend,
            sqlite_path=sqlite_path,
        )

    def resolve_state_handle(
        self,
        *,
        transformation: Any,
        payload: Any,
        tags: Mapping[str, str],
    ) -> StatefulStateHandle:
        spec = _extract_stateful_spec(transformation)
        key_source = _resolve_state_key_source(
            payload=payload,
            tags=tags,
            state_spec=spec.state_spec,
        )
        key = _stable_key_fragment(key_source)
        slot = (spec.stage_id, spec.namespace, key)
        with self._lock:
            self._expire_if_needed(slot, ttl_seconds=spec.ttl_seconds)
        return StatefulStateHandle(
            stage_id=spec.stage_id,
            namespace=spec.namespace,
            key=key,
            ttl_seconds=spec.ttl_seconds,
            _runtime=self,
            _slot=slot,
        )

    def get(
        self,
        slot: tuple[Any, Any, Any],
        *,
        default: Any,
        ttl_seconds: float | None,
    ) -> Any:
        normalized_slot = _normalize_state_slot(slot)
        with self._lock:
            self._expire_if_needed(normalized_slot, ttl_seconds=ttl_seconds)
            entry = self._backend.get(normalized_slot)
            if entry is None:
                return default
            entry.updated_at = self._time_fn()
            self._backend.put(normalized_slot, entry)
            return entry.value

    def peek(self, slot: tuple[Any, Any, Any], *, default: Any = None) -> Any:
        """Inspect stored state without a write or sliding-TTL refresh.

        This returns a detached snapshot, including stored entries that an
        owner may later expire through its TTL-aware access policy. Durable
        journals use non-expiring state and must never rewrite it on reads.
        """
        normalized_slot = _normalize_state_slot(slot)
        with self._lock:
            entry = self._backend.get(normalized_slot)
            return copy.deepcopy(default if entry is None else entry.value)

    def set(
        self,
        slot: tuple[Any, Any, Any],
        value: Any,
        *,
        ttl_seconds: float | None,
    ) -> None:
        del ttl_seconds  # retained on handle; expiry checks are driven by caller contract
        normalized_slot = _normalize_state_slot(slot)
        with self._lock:
            self._backend.put(
                normalized_slot,
                _StateEntry(
                    value=value,
                    updated_at=self._time_fn(),
                ),
            )

    def delete(self, slot: tuple[Any, Any, Any]) -> bool:
        normalized_slot = _normalize_state_slot(slot)
        with self._lock:
            return self._backend.delete(normalized_slot)

    def update(self, slot, transform, *, default=None, ttl_seconds=None):
        """Atomic read/transform/write using the configured state backend.

        The callback must have no external effects and must not call storage.
        A callback or serialization failure leaves the previous state intact.
        """
        normalized_slot = _normalize_state_slot(slot)

        def apply(entry):
            now = self._time_fn()
            expired = (entry is not None and ttl_seconds is not None
                       and now - entry.updated_at >= ttl_seconds)
            value = default if entry is None or expired else entry.value
            return _StateEntry(value=transform(copy.deepcopy(value)), updated_at=now)

        with self._lock:
            return copy.deepcopy(self._backend.update(normalized_slot, apply).value)

    def update_many(self, slots, transform, *, default=None):
        """Atomically replace a fixed set of non-expiring state records.

        Slots are normalized before the transaction; duplicates and an empty
        set are rejected. The pure callback receives detached values keyed by
        normalized slots and must return exactly those keys. It must not call
        storage or perform external effects. This is one backend transaction,
        not a distributed transaction across databases or runtime instances.
        Use it to commit related destination state and work intents together.
        Return StateMutation.DELETE for a slot to remove it in the same
        transaction. The result preserves that marker; returning None stores
        None. Deleting an absent slot is idempotent and creates no tombstone.
        """
        normalized = tuple(_normalize_state_slot(slot) for slot in slots)
        if not normalized or len(set(normalized)) != len(normalized):
            raise ValueError("atomic_update_requires_distinct_nonempty_slots")

        def apply(entries):
            values = {slot: copy.deepcopy(default if entry is None else entry.value)
                      for slot, entry in entries.items()}
            result = transform(values)
            if not isinstance(result, Mapping) or set(result) != set(normalized):
                raise ValueError("atomic_update_result_slots_mismatch")
            now = self._time_fn()
            return {slot: (None if result[slot] is StateMutation.DELETE else
                           _StateEntry(value=copy.deepcopy(result[slot]), updated_at=now))
                    for slot in normalized}

        with self._lock:
            result = self._backend.update_many(normalized, apply)
            return {slot: (StateMutation.DELETE if entry is None else copy.deepcopy(entry.value))
                    for slot, entry in result.items()}

    def scan_stage_entries(self, *, stage_id: str, namespace: str,
                           after_key: str | None = None, limit: int = 100):
        """Read a detached keyset page for exactly one stage and namespace.

        Deletion of earlier keys cannot skip later records. This is not a
        snapshot: insertions at/before the cursor require a new sweep. SQLite
        uses the primary key range, without deserializing unrelated stages.
        A returned None cursor ends this sweep; restart with after_key=None.
        """
        stage_id, namespace, _ = _normalize_state_slot((stage_id, namespace, "scan"))
        if type(limit) is not int or limit <= 0:
            raise ValueError("scan_limit_must_be_positive_integer")
        if after_key is not None and not isinstance(after_key, str):
            raise ValueError("scan_cursor_must_be_string_or_none")
        with self._lock:
            return copy.deepcopy(self._backend.scan_stage(
                stage_id=stage_id, namespace=namespace, after_key=after_key, limit=limit,
            ))

    def query_namespace_entries(
        self,
        *,
        namespace: str,
        prefix: str,
        limit: int,
        cursor: int,
    ) -> tuple[list[dict[str, Any]], int | None]:
        normalized_limit = max(1, int(limit))
        normalized_cursor = max(0, int(cursor))
        normalized_namespace = str(namespace or "").strip()
        normalized_prefix = str(prefix or "")
        with self._lock:
            return self._backend.query(
                namespace=normalized_namespace,
                prefix=normalized_prefix,
                limit=normalized_limit,
                cursor=normalized_cursor,
            )

    def close(self) -> None:
        with self._lock:
            self._backend.close()

    def _expire_if_needed(
        self,
        slot: tuple[str, str, str],
        *,
        ttl_seconds: float | None,
    ) -> None:
        if ttl_seconds is None:
            return
        entry = self._backend.get(slot)
        if entry is None:
            return
        if (self._time_fn() - float(entry.updated_at)) >= float(ttl_seconds):
            self._backend.delete(slot)


def _invoke_stateful_target(
    *,
    transformation: Any,
    payload: Any,
    tags: Mapping[str, str],
    seq: int | None,
    invoke_target: Callable[[Any, Any, Mapping[str, str], int | None], Any] | None,
    state_runtime: StatefulProcessRuntime,
) -> Any:
    state_handle = state_runtime.resolve_state_handle(
        transformation=transformation,
        payload=payload,
        tags=tags,
    )
    target = getattr(transformation, "target", None)
    if callable(target):
        return _invoke_stateful_callable(
            target=target,
            payload=payload,
            state=state_handle,
            tags=tags,
            seq=seq,
        )
    if invoke_target is not None:
        return invoke_target(target, (payload, state_handle), tags, seq)
    raise StatefulProcessContractError(
        "sys/stateful-process target must be callable or invoke_target-capable.",
    )


def _invoke_stateful_callable(
    *,
    target: Callable[..., Any],
    payload: Any,
    state: StatefulStateHandle,
    tags: Mapping[str, str],
    seq: int | None,
) -> Any:
    try:
        signature = inspect.signature(target)
    except (TypeError, ValueError):
        return target(payload, state)

    positional_capacity = 0
    has_var_positional = False
    for parameter in signature.parameters.values():
        if parameter.kind == inspect.Parameter.VAR_POSITIONAL:
            has_var_positional = True
            break
        if parameter.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            positional_capacity += 1

    if has_var_positional or positional_capacity >= 4:
        return target(payload, state, tags, seq)
    if positional_capacity == 3:
        return target(payload, state, tags)
    if positional_capacity == 2:
        return target(payload, state)
    if positional_capacity == 1:
        return target(payload)
    return target()


def _extract_stateful_spec(transformation: Any) -> StatefulSpec:
    process_meta = _extract_stateful_process_meta(transformation)
    stage_id = _extract_state_stage_id(process_meta, transformation)
    namespace = _extract_state_namespace(process_meta, stage_id=stage_id)
    ttl_seconds = _extract_state_ttl_seconds(process_meta)
    state_spec_raw = process_meta.get("state_spec")
    if state_spec_raw is not None and not isinstance(state_spec_raw, Mapping):
        raise StatefulProcessContractError(
            "stateful_process.state_spec must be a mapping when provided.",
        )
    state_spec: Mapping[str, Any] | None = (
        dict(state_spec_raw) if isinstance(state_spec_raw, Mapping) else None
    )
    return StatefulSpec(
        stage_id=stage_id,
        namespace=namespace,
        ttl_seconds=ttl_seconds,
        state_spec=state_spec,
    )


def _extract_stateful_process_meta(transformation: Any) -> Mapping[str, Any]:
    operator_config = getattr(transformation, "operator_config", None)
    if not isinstance(operator_config, Mapping):
        raise StatefulProcessContractError(
            "stateful_process operator_config must be a mapping.",
        )
    process_meta = operator_config.get("stateful_process")
    if not isinstance(process_meta, Mapping):
        raise StatefulProcessContractError(
            "stateful_process operator_config.stateful_process must be a mapping.",
        )
    return process_meta


def _extract_state_stage_id(process_meta: Mapping[str, Any], transformation: Any) -> str:
    stage_id = process_meta.get("stage_id")
    if stage_id is None:
        stage_id = getattr(transformation, "trans_id", None)
    return _as_non_empty_str(
        stage_id,
        field_name="stateful_process.stage_id",
    )


def _extract_state_namespace(process_meta: Mapping[str, Any], *, stage_id: str) -> str:
    namespace = process_meta.get("state_namespace")
    if namespace is None:
        namespace = f"stateful_process:{stage_id}"
    return _as_non_empty_str(
        namespace,
        field_name="stateful_process.state_namespace",
    )


def _extract_state_ttl_seconds(process_meta: Mapping[str, Any]) -> float | None:
    ttl_value = process_meta.get("state_ttl_s")
    if ttl_value is None:
        return None
    return _as_positive_float(
        ttl_value,
        field_name="stateful_process.state_ttl_s",
    )


def _resolve_state_key_source(
    *,
    payload: Any,
    tags: Mapping[str, str],
    state_spec: Mapping[str, Any] | None,
) -> Any:
    if state_spec is not None:
        key_field = state_spec.get("key_field")
        if key_field is not None:
            key_field_name = _as_non_empty_str(
                key_field,
                field_name="stateful_process.state_spec.key_field",
            )
            if not isinstance(payload, Mapping):
                raise StatefulProcessContractError(
                    "stateful_process.state_spec.key_field requires mapping payload.",
                )
            if key_field_name not in payload:
                raise StatefulProcessContractError(
                    f"stateful_process.state_spec.key_field '{key_field_name}' is missing in payload.",
                )
            return payload[key_field_name]

        key_index = state_spec.get("key_index")
        if key_index is not None:
            if not isinstance(payload, (list, tuple)):
                raise StatefulProcessContractError(
                    "stateful_process.state_spec.key_index requires list/tuple payload.",
                )
            try:
                resolved_index = int(key_index)
            except (TypeError, ValueError) as exc:
                raise StatefulProcessContractError(
                    "stateful_process.state_spec.key_index must be an integer >= 0.",
                ) from exc
            if resolved_index < 0 or resolved_index >= len(payload):
                raise StatefulProcessContractError(
                    "stateful_process.state_spec.key_index out of range.",
                )
            return payload[resolved_index]

    fallback_key = tags.get("state_partition_key")
    if isinstance(fallback_key, str) and fallback_key.strip():
        return fallback_key.strip()
    return 0


def _as_non_empty_str(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StatefulProcessContractError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _as_positive_float(value: Any, *, field_name: str) -> float:
    try:
        resolved = float(value)
    except (TypeError, ValueError) as exc:
        raise StatefulProcessContractError(f"{field_name} must be a float > 0.") from exc
    if resolved <= 0:
        raise StatefulProcessContractError(f"{field_name} must be a float > 0.")
    return resolved


__all__ = [
    "StatefulStateHandle",
    "StatefulProcessRuntime",
    "_invoke_stateful_target",
]
