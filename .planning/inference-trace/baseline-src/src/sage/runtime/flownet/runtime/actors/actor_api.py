from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sage.runtime.flownet.runtime.actors.callback_handle import CallbackHandle
from sage.runtime.flownet.runtime.actors.executor_lanes import ExecutorLanes
from sage.runtime.flownet.runtime.actors.invoker import ActorInvoker
from sage.runtime.flownet.runtime.actors.registry import (
    LocalActorRegistry,
    V1ActorRecord,
    V1ActorRef,
    normalize_target,
)
from sage.runtime.flownet.runtime.actors.task_runtime import ActorTaskResult, EventDispatcher


class ActorAPI:
    """v1 actor API: local execution + explicit actor-call intent."""

    def __init__(
        self,
        *,
        local_address: str | Callable[[], str],
        registry: LocalActorRegistry | None = None,
        executor_lanes: ExecutorLanes | None = None,
        invoker: ActorInvoker | None = None,
        runtime_host: Any | None = None,
    ) -> None:
        self._registry = registry or LocalActorRegistry(local_address=local_address)
        self._owns_executor_lanes = executor_lanes is None
        self._executor_lanes = executor_lanes or ExecutorLanes()
        self._invoker = invoker or ActorInvoker(
            registry=self._registry,
            executor_lanes=self._executor_lanes,
            runtime_host=runtime_host,
        )
        if invoker is not None:
            set_runtime_host = getattr(invoker, "set_runtime_host", None)
            if callable(set_runtime_host):
                set_runtime_host(runtime_host)
        self._callback_runtime: Any | None = None

    def register_local_actor(
        self,
        actor_object: Any,
        *,
        actor_id: str | None = None,
        config: Any | None = None,
    ) -> str:
        return self._registry.register_local_actor(
            actor_object,
            actor_id=actor_id,
            config=config,
        )

    def resolve_local_actor(self, actor_id: str) -> V1ActorRecord:
        return self._registry.resolve_local_actor(actor_id)

    def list_local_actors(self) -> list[V1ActorRecord]:
        return self._registry.list_local_actors()

    def method_ref(self, *, actor_id: str, method: str) -> V1ActorRef:
        return self._registry.method_ref(actor_id=actor_id, method=method)

    def set_event_dispatcher(self, event_dispatcher: EventDispatcher | None) -> None:
        self._invoker.set_event_dispatcher(event_dispatcher)

    def set_callback_runtime(self, callback_runtime: Any | None) -> None:
        self._callback_runtime = callback_runtime

    def set_runtime_host(self, runtime_host: Any | None) -> None:
        set_runtime_host = getattr(self._invoker, "set_runtime_host", None)
        if callable(set_runtime_host):
            set_runtime_host(runtime_host)

    async def call_local(self, actor_id: str, method: str, *args, **kwargs) -> Any:
        outcome = await self._call_local_with_protocol(
            actor_id,
            method,
            *args,
            **kwargs,
        )
        return outcome.result

    async def register_topic_callback(
        self,
        *,
        topic_uri: str,
        callback_target: Any,
        worker_address: str | None = None,
        callback_id: str | None = None,
    ) -> CallbackHandle:
        callback_runtime = self._require_callback_runtime()
        return await callback_runtime.register_topic_callback(
            topic_uri=topic_uri,
            callback_target=callback_target,
            worker_address=worker_address,
            callback_id=callback_id,
        )

    async def unregister_topic_callback(
        self,
        handle_or_callback_id: Any,
        *,
        worker_address: str | None = None,
    ) -> bool:
        callback_runtime = self._require_callback_runtime()
        return await callback_runtime.unregister_topic_callback(
            handle_or_callback_id=handle_or_callback_id,
            worker_address=worker_address,
        )

    def active_topic_callback_count(self) -> int:
        callback_runtime = self._require_callback_runtime()
        return int(callback_runtime.active_topic_callback_count())

    def callback_observability_snapshot(self) -> dict[str, Any]:
        callback_runtime = self._require_callback_runtime()
        snapshot = callback_runtime.observability_snapshot()
        if not isinstance(snapshot, dict):
            raise TypeError("callback observability snapshot must be a dict.")
        return dict(snapshot)

    def invocation_observability_snapshot(self) -> dict[str, Any]:
        snapshot = self._invoker.observability_snapshot()
        if not isinstance(snapshot, dict):
            raise TypeError("actor invoker observability snapshot must be a dict.")
        return dict(snapshot)

    def executor_lane_observability_snapshot(self) -> dict[str, Any]:
        snapshot = self._executor_lanes.observability_snapshot()
        if not isinstance(snapshot, dict):
            raise TypeError("executor lane observability snapshot must be a dict.")
        return dict(snapshot)

    async def call_or_prepare_call(self, target: Any, *args, **kwargs) -> dict[str, Any]:
        normalized_target = normalize_target(target)
        local_address = self._registry.local_address()
        if normalized_target.address == local_address:
            local_outcome = await self._call_local_with_protocol(
                normalized_target.actor_id,
                normalized_target.method,
                *args,
                **kwargs,
            )
            return {
                "mode": "local_result",
                "address": normalized_target.address,
                "actor_id": normalized_target.actor_id,
                "method": normalized_target.method,
                "result": local_outcome.result,
                "return_mode": local_outcome.return_mode,
                "event_delivery_reports": list(local_outcome.event_delivery_reports),
                "runtime_report": dict(local_outcome.runtime_report),
            }
        return {
            "mode": "actor_call_intent",
            "address": normalized_target.address,
            "actor_id": normalized_target.actor_id,
            "method": normalized_target.method,
            "args": list(args),
            "kwargs": dict(kwargs),
        }

    async def apply_call_intent(self, intent: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(intent, dict):
            raise TypeError("intent must be a dict.")
        mode = _normalize_non_empty(intent.get("mode"), field_name="mode")
        if mode != "actor_call_intent":
            raise ValueError(f"unsupported_actor_call_intent_mode:{mode}")

        address = _normalize_non_empty(intent.get("address"), field_name="address")
        local_address = self._registry.local_address()
        if address != local_address:
            raise RuntimeError(
                "call_intent_owner_mismatch:"
                f" expected_owner={address},"
                f" local_address={local_address}",
            )
        actor_id = _normalize_non_empty(intent.get("actor_id"), field_name="actor_id")
        method = _normalize_non_empty(intent.get("method"), field_name="method")
        args = _normalize_args(intent.get("args"))
        kwargs = _normalize_kwargs(intent.get("kwargs"))

        try:
            local_outcome = await self._call_local_with_protocol(
                actor_id,
                method,
                *args,
                **kwargs,
            )
        except Exception as exc:
            return {
                "mode": "applied_actor_call_error",
                "address": address,
                "actor_id": actor_id,
                "method": method,
                "error_type": exc.__class__.__name__,
                "message": str(exc),
            }
        return {
            "mode": "applied_actor_call",
            "address": address,
            "actor_id": actor_id,
            "method": method,
            "result": local_outcome.result,
            "return_mode": local_outcome.return_mode,
            "event_delivery_reports": list(local_outcome.event_delivery_reports),
            "runtime_report": dict(local_outcome.runtime_report),
        }

    async def _call_local_with_protocol(
        self,
        actor_id: str,
        method: str,
        *args,
        **kwargs,
    ) -> ActorTaskResult:
        return await self._invoker.call_local_with_protocol(actor_id, method, *args, **kwargs)

    def shutdown(self, *, wait: bool = True, cancel_futures: bool = False) -> None:
        if self._owns_executor_lanes:
            self._executor_lanes.shutdown(
                wait=wait,
                cancel_futures=cancel_futures,
            )

    def _require_callback_runtime(self):
        callback_runtime = self._callback_runtime
        if callback_runtime is None:
            raise RuntimeError("actor_callback_runtime_not_configured")
        return callback_runtime


def _normalize_non_empty(value: Any, *, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty.")
    return normalized


def _normalize_args(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, list):
        return list(value)
    raise TypeError("intent.args must be a list or tuple when provided.")


def _normalize_kwargs(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError("intent.kwargs must be a dict when provided.")
    return dict(value)


__all__ = ["ActorAPI"]
