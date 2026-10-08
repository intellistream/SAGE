from __future__ import annotations

import asyncio
from collections.abc import Mapping
from threading import Lock
from typing import Any

from sage.runtime.flownet.runtime.actors.error_codes import (
    ACTOR_POLICY_MAX_PENDING_EXCEEDED,
    build_error_message,
)
from sage.runtime.flownet.runtime.actors.execution_context import bind_actor_execution_context
from sage.runtime.flownet.runtime.actors.executor_lanes import (
    ExecutorLanes,
    run_in_executor_with_context,
)
from sage.runtime.flownet.runtime.actors.registry import LocalActorRegistry
from sage.runtime.flownet.runtime.actors.task_runtime import (
    ActorTaskResult,
    ActorTaskRuntime,
    EventDispatcher,
)


class ActorInvoker:
    """Local actor invoker with stable serial/lockfree semantics."""

    def __init__(
        self,
        *,
        registry: LocalActorRegistry,
        executor_lanes: ExecutorLanes,
        task_runtime: ActorTaskRuntime | None = None,
        runtime_host: Any | None = None,
    ) -> None:
        self._registry = registry
        self._executor_lanes = executor_lanes
        self._task_runtime = task_runtime or ActorTaskRuntime()
        self._runtime_host = runtime_host
        self._pending_counts: dict[str, int] = {}
        self._running_counts: dict[str, int] = {}
        self._pending_lock = Lock()

    def set_event_dispatcher(self, event_dispatcher: EventDispatcher | None) -> None:
        self._task_runtime.set_event_dispatcher(event_dispatcher)

    def set_runtime_host(self, runtime_host: Any | None) -> None:
        self._runtime_host = runtime_host

    async def call_local(self, actor_id: str, method: str, *args, **kwargs) -> Any:
        outcome = await self.call_local_with_protocol(actor_id, method, *args, **kwargs)
        return outcome.result

    async def call_local_with_protocol(
        self,
        actor_id: str,
        method: str,
        *args,
        **kwargs,
    ) -> ActorTaskResult:
        record = self._registry.resolve_local_actor(actor_id)
        method_name = str(method or "").strip()
        if not method_name:
            raise ValueError("method must be non-empty.")
        target = getattr(record.object, method_name, None)
        if target is None:
            raise ValueError(f"actor_method_not_found:{record.actor_id}.{method_name}")
        if asyncio.iscoroutinefunction(target):
            raise RuntimeError(
                f"actor_main_entry_sync_only_violation:{record.actor_id}.{method_name}",
            )
        no_lock = bool(getattr(target, "__flownet_no_lock__", False))
        task_policy = _resolve_task_policy(record.config)
        lane = self._executor_lanes.lane_for(actor_config=record.config)
        max_pending = _resolve_positive_optional_int(task_policy, "max_pending")
        task_timeout_ms = _resolve_positive_optional_int(task_policy, "task_timeout_ms")
        max_parallel_tools = _resolve_positive_optional_int(
            task_policy,
            "max_parallel_tools",
        )

        self._acquire_pending_slot(
            actor_id=record.actor_id,
            lane=lane,
            max_pending=max_pending,
        )
        try:
            with bind_actor_execution_context(
                actor_id=record.actor_id,
                actor_config=record.config,
                runtime_host=self._runtime_host,
            ):
                with self._task_runtime.open_task_event_scope(
                    task_policy=task_policy
                ) as event_buffer:
                    main_entry_return = await self._call_sync_target(
                        target,
                        actor_id=record.actor_id,
                        actor_config=record.config,
                        lane=lane,
                        no_lock=no_lock,
                        lock=record.lock,
                        args=args,
                        kwargs=kwargs,
                    )
                    return await self._task_runtime.resolve_main_entry_return(
                        main_entry_return,
                        event_buffer=event_buffer,
                        task_timeout_ms=task_timeout_ms,
                        max_parallel_tools=max_parallel_tools,
                        max_pending=max_pending,
                    )
        finally:
            self._release_pending_slot(record.actor_id, lane=lane)

    async def _call_sync_target(
        self,
        target: Any,
        *,
        actor_id: str,
        actor_config: Any,
        lane: str,
        no_lock: bool,
        lock,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> Any:
        loop = asyncio.get_running_loop()
        executor = self._executor_lanes.executor_for(
            actor_id=actor_id,
            actor_config=actor_config,
        )

        if no_lock:
            self._record_running_start(actor_id=actor_id, lane=lane)
            try:
                return await run_in_executor_with_context(
                    loop,
                    target,
                    *args,
                    executor=executor,
                    **kwargs,
                )
            finally:
                self._record_running_end(actor_id=actor_id, lane=lane)

        def _locked_call(*inner_args, **inner_kwargs):
            with lock:
                return target(*inner_args, **inner_kwargs)

        self._record_running_start(actor_id=actor_id, lane=lane)
        try:
            return await run_in_executor_with_context(
                loop,
                _locked_call,
                *args,
                executor=executor,
                **kwargs,
            )
        finally:
            self._record_running_end(actor_id=actor_id, lane=lane)

    def _acquire_pending_slot(self, *, actor_id: str, lane: str, max_pending: int | None) -> None:
        with self._pending_lock:
            current = int(self._pending_counts.get(actor_id, 0))
            if max_pending is not None and current >= max_pending:
                raise RuntimeError(
                    build_error_message(
                        ACTOR_POLICY_MAX_PENDING_EXCEEDED,
                        actor_id=actor_id,
                        current_pending=current,
                        max_pending=max_pending,
                    )
                )
            self._pending_counts[actor_id] = current + 1

    def _release_pending_slot(self, actor_id: str, *, lane: str) -> None:
        with self._pending_lock:
            current = int(self._pending_counts.get(actor_id, 0))
            if current <= 1:
                self._pending_counts.pop(actor_id, None)
                return
            self._pending_counts[actor_id] = current - 1

    def _record_running_start(self, *, actor_id: str, lane: str) -> None:
        del lane
        with self._pending_lock:
            self._running_counts[actor_id] = int(self._running_counts.get(actor_id, 0)) + 1

    def _record_running_end(self, *, actor_id: str, lane: str) -> None:
        del lane
        with self._pending_lock:
            current = int(self._running_counts.get(actor_id, 0))
            if current <= 1:
                self._running_counts.pop(actor_id, None)
                return
            self._running_counts[actor_id] = current - 1

    def observability_snapshot(self) -> dict[str, Any]:
        with self._pending_lock:
            pending_counts = dict(self._pending_counts)
            running_counts = dict(self._running_counts)

        lane_rows: dict[str, dict[str, Any]] = {}
        for record in self._registry.list_local_actors():
            lane = self._executor_lanes.lane_for(actor_config=record.config)
            lane_row = lane_rows.setdefault(
                lane,
                {
                    "lane": lane,
                    "actor_count": 0,
                    "pending": 0,
                    "running": 0,
                    "queued": 0,
                },
            )
            lane_row["actor_count"] = int(lane_row["actor_count"]) + 1
            actor_pending = int(pending_counts.get(record.actor_id, 0))
            actor_running = int(running_counts.get(record.actor_id, 0))
            lane_row["pending"] = int(lane_row["pending"]) + actor_pending
            lane_row["running"] = int(lane_row["running"]) + actor_running

        rows: list[dict[str, Any]] = []
        pending_total = 0
        running_total = 0
        queued_total = 0
        for lane, row in sorted(lane_rows.items()):
            pending = int(row["pending"])
            running = int(row["running"])
            queued = max(0, pending - running)
            pending_total += pending
            running_total += running
            queued_total += queued
            rows.append(
                {
                    "lane": lane,
                    "actor_count": int(row["actor_count"]),
                    "pending": pending,
                    "running": running,
                    "queued": queued,
                }
            )

        return {
            "records": rows,
            "pending": pending_total,
            "running": running_total,
            "queued": queued_total,
        }


def _resolve_task_policy(actor_config: Any | None) -> dict[str, Any] | None:
    if actor_config is None:
        return None
    direct = _extract_mapping(actor_config, "task_policy")
    if direct is not None:
        return direct

    policies = _extract_mapping(actor_config, "policies")
    if policies is not None:
        nested = _extract_nested_mapping(policies, "task")
        if nested is not None:
            return nested

    execution_policy = _extract_mapping(actor_config, "execution_policy")
    if execution_policy is not None:
        nested = _extract_nested_mapping(execution_policy, "task")
        if nested is not None:
            return nested

    return None


def _extract_mapping(container: Any, key: str) -> dict[str, Any] | None:
    if isinstance(container, Mapping):
        value = container.get(key)
    else:
        value = getattr(container, key, None)
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise TypeError(f"{key} must be a mapping when provided.")
    return dict(value)


def _extract_nested_mapping(container: Mapping[str, Any], key: str) -> dict[str, Any] | None:
    value = container.get(key)
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise TypeError(f"{key} must be a mapping when provided.")
    return dict(value)


def _resolve_positive_optional_int(policy: dict[str, Any] | None, key: str) -> int | None:
    if policy is None:
        return None
    raw_value = policy.get(key)
    if raw_value is None:
        return None
    value = int(raw_value)
    if value <= 0:
        raise ValueError(f"{key} must be > 0 when provided.")
    return value


__all__ = ["ActorInvoker"]
