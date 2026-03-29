from __future__ import annotations

import asyncio
import contextlib
import inspect
from collections.abc import Callable
from concurrent.futures import Future as ConcurrentFuture
from dataclasses import dataclass, field
from typing import Any, Literal

from sage.runtime.flownet.runtime.actors.error_codes import (
    ACTOR_TASK_CANCELLED,
    ACTOR_TASK_TIMEOUT,
    build_error_message,
)
from sage.runtime.flownet.runtime.actors.event_emitter import (
    ActorEmittedEvent,
    ActorTaskEventBuffer,
    actor_task_event_scope,
    resolve_task_event_policy,
)

SYNC_RETURN_MODE = "sync_return"
TASK_RETURN_MODE = "task_return"
TaskReturnMode = Literal["sync_return", "task_return"]
EventDispatcher = Callable[[ActorEmittedEvent], Any]


@dataclass(frozen=True)
class ActorTaskResult:
    """Resolved actor main-entry result under task-return protocol."""

    result: Any
    return_mode: TaskReturnMode
    event_delivery_reports: tuple[dict[str, Any], ...] = ()
    runtime_report: dict[str, Any] = field(default_factory=dict)


def is_runtime_task_submission(value: Any) -> bool:
    """Return True when actor main-entry returned a runtime task object."""

    if inspect.isgenerator(value):
        return False
    if inspect.isasyncgen(value):
        return False
    if asyncio.iscoroutine(value):
        return True
    if isinstance(value, (asyncio.Future, ConcurrentFuture)):
        return True
    return inspect.isawaitable(value)


class ActorTaskRuntime:
    """Resolve runtime-managed task objects returned by actor main-entry."""

    def __init__(self, *, event_dispatcher: EventDispatcher | None = None) -> None:
        self._event_dispatcher = event_dispatcher

    def set_event_dispatcher(self, event_dispatcher: EventDispatcher | None) -> None:
        self._event_dispatcher = event_dispatcher

    @contextlib.contextmanager
    def open_task_event_scope(
        self,
        *,
        task_policy: Any | None = None,
    ):
        policy = resolve_task_event_policy(task_policy)
        with actor_task_event_scope(policy=policy) as buffer:
            yield buffer

    async def resolve_main_entry_return(
        self,
        value: Any,
        *,
        event_buffer: ActorTaskEventBuffer | None = None,
        task_timeout_ms: int | None = None,
        max_parallel_tools: int | None = None,
        max_pending: int | None = None,
    ) -> ActorTaskResult:
        runtime_report = _build_runtime_report(
            task_timeout_ms=task_timeout_ms,
            max_parallel_tools=max_parallel_tools,
            max_pending=max_pending,
        )
        if not is_runtime_task_submission(value):
            reports = await self._dispatch_events(event_buffer)
            return ActorTaskResult(
                result=value,
                return_mode=SYNC_RETURN_MODE,
                event_delivery_reports=reports,
                runtime_report=runtime_report,
            )
        try:
            resolved_result = await _await_runtime_task(
                value,
                timeout_ms=task_timeout_ms,
            )
        except RuntimeError as exc:
            if str(exc).startswith(ACTOR_TASK_TIMEOUT):
                runtime_report["task_timeout_hit"] = True
            if str(exc).startswith(ACTOR_TASK_CANCELLED):
                runtime_report["task_cancelled"] = True
            await self._dispatch_events(event_buffer)
            raise
        except Exception:
            await self._dispatch_events(event_buffer)
            raise
        reports = await self._dispatch_events(event_buffer)
        return ActorTaskResult(
            result=resolved_result,
            return_mode=TASK_RETURN_MODE,
            event_delivery_reports=reports,
            runtime_report=runtime_report,
        )

    async def _dispatch_events(
        self,
        event_buffer: ActorTaskEventBuffer | None,
    ) -> tuple[dict[str, Any], ...]:
        if event_buffer is None:
            return ()
        events = event_buffer.drain()
        if not events:
            return ()
        reports: list[dict[str, Any]] = []
        for event in events:
            if self._event_dispatcher is None:
                reports.append(
                    {
                        "status": "dropped_no_dispatcher",
                        "mode": event.mode,
                        "topic_uri": event.topic_uri,
                        "event_group_id": event.event_group_id,
                        "seq": event.seq,
                    }
                )
                continue
            try:
                dispatch_result = self._event_dispatcher(event)
                if inspect.isawaitable(dispatch_result):
                    dispatch_result = await dispatch_result
                reports.append(
                    {
                        "status": "dispatched",
                        "mode": event.mode,
                        "topic_uri": event.topic_uri,
                        "event_group_id": event.event_group_id,
                        "seq": event.seq,
                        "dispatch_result": dispatch_result,
                    }
                )
            except Exception as exc:
                reports.append(
                    {
                        "status": "dispatch_error",
                        "mode": event.mode,
                        "topic_uri": event.topic_uri,
                        "event_group_id": event.event_group_id,
                        "seq": event.seq,
                        "error_type": exc.__class__.__name__,
                        "message": str(exc),
                    }
                )
        return tuple(reports)


async def _await_runtime_task(value: Any, *, timeout_ms: int | None = None) -> Any:
    timeout_seconds: float | None = None
    if timeout_ms is not None:
        timeout_seconds = float(timeout_ms) / 1000.0
    awaitable = _coerce_runtime_task_awaitable(value)
    if timeout_seconds is None:
        return await awaitable
    try:
        return await asyncio.wait_for(awaitable, timeout=timeout_seconds)
    except asyncio.TimeoutError as exc:
        raise RuntimeError(
            build_error_message(
                ACTOR_TASK_TIMEOUT,
                task_timeout_ms=int(timeout_ms),
            )
        ) from exc
    except asyncio.CancelledError as exc:
        raise RuntimeError(ACTOR_TASK_CANCELLED) from exc


def _coerce_runtime_task_awaitable(value: Any):
    if asyncio.iscoroutine(value):
        return value
    if isinstance(value, asyncio.Future):
        return value
    if isinstance(value, ConcurrentFuture):
        return asyncio.wrap_future(value)
    if inspect.isawaitable(value):
        return value
    raise TypeError(
        "runtime_task_submission must be coroutine, awaitable, "
        "asyncio.Future, or concurrent.futures.Future.",
    )


def _build_runtime_report(
    *,
    task_timeout_ms: int | None,
    max_parallel_tools: int | None,
    max_pending: int | None,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "task_timeout_hit": False,
        "task_cancelled": False,
    }
    if task_timeout_ms is not None:
        report["task_timeout_ms"] = int(task_timeout_ms)
    if max_parallel_tools is not None:
        report["max_parallel_tools"] = int(max_parallel_tools)
    if max_pending is not None:
        report["max_pending"] = int(max_pending)
    return report


__all__ = [
    "SYNC_RETURN_MODE",
    "TASK_RETURN_MODE",
    "TaskReturnMode",
    "EventDispatcher",
    "ActorTaskResult",
    "is_runtime_task_submission",
    "ActorTaskRuntime",
]
