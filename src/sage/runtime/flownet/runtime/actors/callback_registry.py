from __future__ import annotations

import uuid
from collections.abc import Callable
from concurrent.futures import Future
from dataclasses import dataclass
from threading import Lock
from typing import Any

from sage.runtime.flownet.runtime.actors.callback_handle import (
    CallbackHandle,
    coerce_callback_handle,
)
from sage.runtime.flownet.runtime.actors.comm_bridge import call_actor_via_comm
from sage.runtime.flownet.runtime.actors.error_codes import ACTOR_CALLBACK_DETACHED
from sage.runtime.flownet.runtime.actors.registry import V1ActorRef, normalize_target
from sage.runtime.flownet.runtime.comm import V1CommHub
from sage.runtime.flownet.runtime.topics.topic_api import TopicAPI

CALLBACK_REGISTRY_SERVICE_ACTOR_ID = "__flownet_v1_callback_registry_service__"
CALLBACK_REGISTRY_TOPIC_EVENT_LISTENER_ID = "__flownet_v1_actor_callback_registry_listener__"


@dataclass(frozen=True)
class CallbackRecord:
    callback_id: str
    topic_uri: str
    callback_target: V1ActorRef
    detached: bool
    owner_address: str | None


class CallbackRegistry:
    """Worker-local topic callback registry and dispatch scheduler."""

    def __init__(
        self,
        *,
        local_address: str | Callable[[], str],
        topic_api: TopicAPI,
        submit_user_coro: Callable[[Any], Future],
        invoke_callback: Callable[[V1ActorRef, dict[str, Any]], Any],
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        if callable(local_address):
            self._local_address_fn = local_address
        else:
            normalized_local_address = _normalize_non_empty(
                local_address,
                field_name="local_address",
            )
            self._local_address_fn = lambda: normalized_local_address
        self._topic_api = topic_api
        self._submit_user_coro = submit_user_coro
        self._invoke_callback = invoke_callback
        self._id_factory = id_factory or (lambda: uuid.uuid4().hex)
        self._records: dict[str, CallbackRecord] = {}
        self._inflight: set[Future] = set()
        self._callback_detach_total = 0
        self._last_callback_detach: dict[str, Any] | None = None
        self._lock = Lock()
        self._closed = False
        self._topic_api.add_topic_event_listener(
            listener_id=CALLBACK_REGISTRY_TOPIC_EVENT_LISTENER_ID,
            listener=self._on_topic_event,
        )

    def register_callback(
        self,
        *,
        topic_uri: str,
        callback_target: Any,
        callback_id: str | None = None,
        detached: bool = False,
        owner_address: str | None = None,
    ) -> CallbackHandle:
        normalized_topic_uri = _normalize_non_empty(topic_uri, field_name="topic_uri")
        resolved_topic_uri = self._topic_api.require_topic_route(
            normalized_topic_uri,
            epoch=None,
        ).topic_uri
        normalized_target = normalize_target(callback_target)
        resolved_callback_id = (
            _normalize_non_empty(callback_id, field_name="callback_id")
            if callback_id is not None
            else _normalize_non_empty(self._id_factory(), field_name="callback_id")
        )
        resolved_owner_address = (
            _normalize_non_empty(owner_address, field_name="owner_address")
            if owner_address is not None
            else None
        )
        record = CallbackRecord(
            callback_id=resolved_callback_id,
            topic_uri=resolved_topic_uri,
            callback_target=normalized_target,
            detached=bool(detached),
            owner_address=resolved_owner_address,
        )
        with self._lock:
            self._ensure_open()
            if resolved_callback_id in self._records:
                raise ValueError(f"callback_already_exists:{resolved_callback_id}")
            self._records[resolved_callback_id] = record
        return self._build_handle(record)

    def unregister_callback(self, callback_id: str) -> bool:
        resolved_callback_id = _normalize_non_empty(callback_id, field_name="callback_id")
        with self._lock:
            record = self._records.pop(resolved_callback_id, None)
            if record is None:
                return False
            if record.detached:
                self._callback_detach_total += 1
                self._last_callback_detach = {
                    "code": ACTOR_CALLBACK_DETACHED,
                    "callback_id": record.callback_id,
                    "topic_uri": record.topic_uri,
                    "owner_address": record.owner_address,
                }
            return True

    def active_callback_count(self) -> int:
        with self._lock:
            return len(self._records)

    def observability_snapshot(self) -> dict[str, Any]:
        with self._lock:
            snapshot = {
                "callback_detach_total": int(self._callback_detach_total),
            }
            if self._last_callback_detach is not None:
                snapshot["last_callback_detach"] = dict(self._last_callback_detach)
            return snapshot

    def shutdown(self, *, wait: bool = True, cancel_futures: bool = False) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._records = {}
            inflight = list(self._inflight)
            self._inflight = set()
        self._topic_api.remove_topic_event_listener(
            listener_id=CALLBACK_REGISTRY_TOPIC_EVENT_LISTENER_ID,
        )

        if cancel_futures:
            for future in inflight:
                future.cancel()

        if not wait:
            return

        for future in inflight:
            try:
                future.result(timeout=0.5)
            except Exception:
                continue

    def _build_handle(self, record: CallbackRecord) -> CallbackHandle:
        return CallbackHandle(
            callback_id=record.callback_id,
            topic_uri=record.topic_uri,
            worker_address=self._local_address(),
            callback_target={
                "address": record.callback_target.address,
                "actor_id": record.callback_target.actor_id,
                "method": record.callback_target.method,
            },
            detached=record.detached,
            owner_address=record.owner_address,
        )

    def _on_topic_event(self, event_record: dict[str, Any]) -> None:
        if not isinstance(event_record, dict):
            return
        topic_uri = event_record.get("topic_uri")
        if not isinstance(topic_uri, str):
            return
        with self._lock:
            if self._closed:
                return
            records = [record for record in self._records.values() if record.topic_uri == topic_uri]
        if not records:
            return

        for record in records:
            payload = dict(event_record)
            try:
                future = self._submit_user_coro(
                    self._dispatch_callback(record, payload),
                )
            except Exception:
                continue
            with self._lock:
                if self._closed:
                    future.cancel()
                    continue
                self._inflight.add(future)
            future.add_done_callback(self._on_future_done)

    async def _dispatch_callback(
        self,
        record: CallbackRecord,
        event_record: dict[str, Any],
    ) -> None:
        try:
            result = self._invoke_callback(record.callback_target, event_record)
            if hasattr(result, "__await__"):
                await result
        except Exception:
            return

    def _on_future_done(self, future: Future) -> None:
        with self._lock:
            self._inflight.discard(future)

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("callback_registry_closed")

    def _local_address(self) -> str:
        return _normalize_non_empty(
            self._local_address_fn(),
            field_name="local_address",
        )


class CallbackRegistryServiceActor:
    """Owner-side service actor used for remote callback register/detach."""

    def __init__(self, callback_registry: CallbackRegistry) -> None:
        self._callback_registry = callback_registry

    def register_detached_callback(self, request: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(request, dict):
            raise TypeError("request must be a dict.")
        handle = self._callback_registry.register_callback(
            topic_uri=_normalize_non_empty(request.get("topic_uri"), field_name="topic_uri"),
            callback_target=request.get("callback_target"),
            callback_id=request.get("callback_id"),
            detached=True,
            owner_address=request.get("owner_address"),
        )
        return handle.as_dict()

    def unregister_callback(self, request: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(request, dict):
            raise TypeError("request must be a dict.")
        removed = self._callback_registry.unregister_callback(
            _normalize_non_empty(request.get("callback_id"), field_name="callback_id"),
        )
        return {"removed": bool(removed)}

    def active_callback_count(self) -> int:
        return self._callback_registry.active_callback_count()


class ActorCallbackRuntime:
    """ActorAPI callback facade: local register + remote register-and-detach."""

    def __init__(
        self,
        *,
        local_address: str | Callable[[], str],
        actor_api,
        comm_hub: V1CommHub,
        callback_registry: CallbackRegistry,
    ) -> None:
        if callable(local_address):
            self._local_address_fn = local_address
        else:
            normalized_local_address = _normalize_non_empty(
                local_address,
                field_name="local_address",
            )
            self._local_address_fn = lambda: normalized_local_address
        self._actor_api = actor_api
        self._comm_hub = comm_hub
        self._callback_registry = callback_registry

    async def register_topic_callback(
        self,
        *,
        topic_uri: str,
        callback_target: Any,
        worker_address: str | None = None,
        callback_id: str | None = None,
    ) -> CallbackHandle:
        resolved_worker_address = _normalize_non_empty(
            worker_address or self._local_address(),
            field_name="worker_address",
        )
        if resolved_worker_address == self._local_address():
            return self._callback_registry.register_callback(
                topic_uri=topic_uri,
                callback_target=callback_target,
                callback_id=callback_id,
                detached=False,
                owner_address=self._local_address(),
            )

        callback_target_ref = normalize_target(callback_target)
        request = {
            "topic_uri": _normalize_non_empty(topic_uri, field_name="topic_uri"),
            "callback_target": {
                "address": callback_target_ref.address,
                "actor_id": callback_target_ref.actor_id,
                "method": callback_target_ref.method,
            },
            "owner_address": self._local_address(),
        }
        if callback_id is not None:
            request["callback_id"] = _normalize_non_empty(callback_id, field_name="callback_id")

        remote_result = await call_actor_via_comm(
            self._actor_api,
            self._comm_hub,
            V1ActorRef(
                address=resolved_worker_address,
                actor_id=CALLBACK_REGISTRY_SERVICE_ACTOR_ID,
                method="register_detached_callback",
            ),
            request,
            request_ref_id=request["topic_uri"],
        )
        payload = _unwrap_actor_call_result(remote_result)
        handle = coerce_callback_handle(payload)
        if handle.worker_address != resolved_worker_address:
            raise RuntimeError(
                "remote_callback_worker_mismatch:"
                f" expected={resolved_worker_address},"
                f" actual={handle.worker_address}",
            )
        return handle

    async def unregister_topic_callback(
        self,
        *,
        handle_or_callback_id: Any,
        worker_address: str | None = None,
    ) -> bool:
        callback_id, resolved_worker_address = self._resolve_callback_identity(
            handle_or_callback_id=handle_or_callback_id,
            worker_address=worker_address,
        )
        if resolved_worker_address == self._local_address():
            return self._callback_registry.unregister_callback(callback_id)

        remote_result = await call_actor_via_comm(
            self._actor_api,
            self._comm_hub,
            V1ActorRef(
                address=resolved_worker_address,
                actor_id=CALLBACK_REGISTRY_SERVICE_ACTOR_ID,
                method="unregister_callback",
            ),
            {"callback_id": callback_id},
            request_ref_id=callback_id,
        )
        payload = _unwrap_actor_call_result(remote_result)
        if not isinstance(payload, dict):
            raise TypeError("remote unregister callback payload must be a dict.")
        return bool(payload.get("removed"))

    def active_topic_callback_count(self) -> int:
        return self._callback_registry.active_callback_count()

    def observability_snapshot(self) -> dict[str, Any]:
        return self._callback_registry.observability_snapshot()

    def shutdown(self, *, wait: bool = True, cancel_futures: bool = False) -> None:
        self._callback_registry.shutdown(
            wait=wait,
            cancel_futures=cancel_futures,
        )

    def _resolve_callback_identity(
        self,
        *,
        handle_or_callback_id: Any,
        worker_address: str | None,
    ) -> tuple[str, str]:
        if isinstance(handle_or_callback_id, str):
            callback_id = _normalize_non_empty(handle_or_callback_id, field_name="callback_id")
            resolved_worker_address = _normalize_non_empty(
                worker_address or self._local_address(),
                field_name="worker_address",
            )
            return callback_id, resolved_worker_address
        handle = coerce_callback_handle(handle_or_callback_id)
        return (
            _normalize_non_empty(handle.callback_id, field_name="callback_id"),
            _normalize_non_empty(
                worker_address or handle.worker_address,
                field_name="worker_address",
            ),
        )

    def _local_address(self) -> str:
        return _normalize_non_empty(
            self._local_address_fn(),
            field_name="local_address",
        )


def _unwrap_actor_call_result(result: dict[str, Any]) -> Any:
    if not isinstance(result, dict):
        raise TypeError("actor call result must be a dict.")
    mode = _normalize_non_empty(result.get("mode"), field_name="mode")
    if mode in {"local_result", "applied_actor_call"}:
        return result.get("result")
    if mode == "applied_actor_call_error":
        error_type = _normalize_non_empty(result.get("error_type"), field_name="error_type")
        message = str(result.get("message") or "")
        raise RuntimeError(f"callback_remote_call_failed:{error_type}:{message}")
    raise RuntimeError(f"unsupported_callback_actor_call_mode:{mode}")


def _normalize_non_empty(value: Any, *, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty.")
    return normalized


__all__ = [
    "CALLBACK_REGISTRY_SERVICE_ACTOR_ID",
    "CALLBACK_REGISTRY_TOPIC_EVENT_LISTENER_ID",
    "CallbackRecord",
    "CallbackRegistry",
    "CallbackRegistryServiceActor",
    "ActorCallbackRuntime",
]
