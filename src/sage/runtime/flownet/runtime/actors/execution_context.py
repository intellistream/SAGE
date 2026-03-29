from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ActorExecutionContext:
    actor_id: str
    actor_config: Any | None
    runtime_host: Any | None


_CURRENT_ACTOR_EXECUTION_CONTEXT: ContextVar[ActorExecutionContext | None] = ContextVar(
    "flownet_actor_execution_context",
    default=None,
)


@contextmanager
def bind_actor_execution_context(
    *,
    actor_id: str,
    actor_config: Any | None,
    runtime_host: Any | None,
) -> Iterator[ActorExecutionContext]:
    context = ActorExecutionContext(
        actor_id=str(actor_id),
        actor_config=actor_config,
        runtime_host=runtime_host,
    )
    token: Token[ActorExecutionContext | None] = _CURRENT_ACTOR_EXECUTION_CONTEXT.set(context)
    try:
        yield context
    finally:
        _CURRENT_ACTOR_EXECUTION_CONTEXT.reset(token)


def current_actor_execution_context() -> ActorExecutionContext | None:
    return _CURRENT_ACTOR_EXECUTION_CONTEXT.get()


def require_actor_execution_context() -> ActorExecutionContext:
    context = current_actor_execution_context()
    if context is None:
        raise RuntimeError("actor_execution_context_not_available")
    return context


def current_actor_runtime_host() -> Any | None:
    context = current_actor_execution_context()
    if context is None:
        return None
    return context.runtime_host


def require_actor_runtime_host() -> Any:
    runtime_host = current_actor_runtime_host()
    if runtime_host is None:
        raise RuntimeError("actor_runtime_host_not_available")
    return runtime_host


__all__ = [
    "ActorExecutionContext",
    "bind_actor_execution_context",
    "current_actor_execution_context",
    "require_actor_execution_context",
    "current_actor_runtime_host",
    "require_actor_runtime_host",
]
