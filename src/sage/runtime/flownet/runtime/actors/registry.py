from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock
from typing import Any


@dataclass(frozen=True)
class V1ActorRef:
    address: str
    actor_id: str
    method: str


@dataclass
class V1ActorRecord:
    actor_id: str
    object: Any
    config: Any | None = None
    created_at: float = field(default_factory=time.time)
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)


class LocalActorRegistry:
    """v1 local actor registry (local lifecycle + local lookup only)."""

    def __init__(
        self,
        *,
        local_address: str | Callable[[], str],
        id_factory: Callable[[], str] | None = None,
        time_fn: Callable[[], float] | None = None,
    ) -> None:
        if callable(local_address):
            self._local_address_fn = local_address
        else:
            normalized = _normalize_non_empty(local_address, field_name="local_address")
            self._local_address_fn = lambda: normalized
        self._id_factory = id_factory or (lambda: uuid.uuid4().hex)
        self._time_fn = time_fn or time.time
        self._records: dict[str, V1ActorRecord] = {}
        self._lock = Lock()

    def local_address(self) -> str:
        return _normalize_non_empty(self._local_address_fn(), field_name="local_address")

    def register_local_actor(
        self,
        actor_object: Any,
        *,
        actor_id: str | None = None,
        config: Any | None = None,
    ) -> str:
        if actor_object is None:
            raise TypeError("actor_object must not be None.")
        resolved_actor_id = (
            _normalize_non_empty(actor_id, field_name="actor_id")
            if actor_id is not None
            else _normalize_non_empty(self._id_factory(), field_name="actor_id")
        )
        record = V1ActorRecord(
            actor_id=resolved_actor_id,
            object=actor_object,
            config=config,
            created_at=float(self._time_fn()),
        )
        with self._lock:
            if resolved_actor_id in self._records:
                raise ValueError(f"actor_already_exists:{resolved_actor_id}")
            self._records[resolved_actor_id] = record
        return resolved_actor_id

    def resolve_local_actor(self, actor_id: str) -> V1ActorRecord:
        normalized_actor_id = _normalize_non_empty(actor_id, field_name="actor_id")
        with self._lock:
            record = self._records.get(normalized_actor_id)
        if record is None:
            raise ValueError(f"actor_not_found:{normalized_actor_id}")
        return record

    def lookup_local_actor(self, actor_id: str) -> V1ActorRecord | None:
        normalized_actor_id = _normalize_non_empty(actor_id, field_name="actor_id")
        with self._lock:
            return self._records.get(normalized_actor_id)

    def delete_local_actor(self, actor_id: str) -> bool:
        normalized_actor_id = _normalize_non_empty(actor_id, field_name="actor_id")
        with self._lock:
            return self._records.pop(normalized_actor_id, None) is not None

    def list_local_actors(self) -> list[V1ActorRecord]:
        with self._lock:
            items = list(self._records.values())
        items.sort(key=lambda item: item.actor_id)
        return items

    def method_ref(self, *, actor_id: str, method: str) -> V1ActorRef:
        normalized_actor_id = _normalize_non_empty(actor_id, field_name="actor_id")
        normalized_method = _normalize_non_empty(method, field_name="method")
        return V1ActorRef(
            address=self.local_address(),
            actor_id=normalized_actor_id,
            method=normalized_method,
        )


def normalize_target(target: Any) -> V1ActorRef:
    if isinstance(target, V1ActorRef):
        return V1ActorRef(
            address=_normalize_non_empty(target.address, field_name="address"),
            actor_id=_normalize_non_empty(target.actor_id, field_name="actor_id"),
            method=_normalize_non_empty(target.method, field_name="method"),
        )
    if isinstance(target, dict):
        return V1ActorRef(
            address=_normalize_non_empty(target.get("address"), field_name="address"),
            actor_id=_normalize_non_empty(target.get("actor_id"), field_name="actor_id"),
            method=_normalize_non_empty(target.get("method"), field_name="method"),
        )
    if _is_target_like_object(target):
        return V1ActorRef(
            address=_normalize_non_empty(getattr(target, "address", None), field_name="address"),
            actor_id=_normalize_non_empty(getattr(target, "actor_id", None), field_name="actor_id"),
            method=_normalize_non_empty(getattr(target, "method", None), field_name="method"),
        )
    raise TypeError(
        "target must be V1ActorRef, target-like object(address, actor_id, method), or "
        "dict(address, actor_id, method)."
    )


def _normalize_non_empty(value: Any, *, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty.")
    return normalized


def _is_target_like_object(target: Any) -> bool:
    if target is None or isinstance(target, dict):
        return False
    return all(hasattr(target, attr) for attr in ("address", "actor_id", "method"))


__all__ = [
    "V1ActorRef",
    "V1ActorRecord",
    "LocalActorRegistry",
    "normalize_target",
]
