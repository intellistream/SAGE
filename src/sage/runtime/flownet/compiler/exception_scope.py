from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from sage.runtime.flownet.compiler.errors import FlowDefinitionError
from sage.runtime.flownet.compiler.targets import coerce_actor_symbol_target, is_actor_target

_flow_program_ctx: ContextVar[object | None] = ContextVar(
    "flownet_v1_flow_program",
    default=None,
)


def _set_current_flow_program(flow_program: object) -> None:
    _flow_program_ctx.set(flow_program)


def _clear_current_flow_program() -> None:
    _flow_program_ctx.set(None)


def _current_flow_program() -> object | None:
    return _flow_program_ctx.get()


@contextmanager
def flow_program_scope(flow_program: object) -> Iterator[None]:
    token = _flow_program_ctx.set(flow_program)
    try:
        yield
    finally:
        _flow_program_ctx.reset(token)


def _resolve_handler(handler: Any) -> Any | None:
    if handler is None:
        return None
    normalized_actor_symbol = coerce_actor_symbol_target(handler)
    if normalized_actor_symbol is not None:
        return normalized_actor_symbol
    if is_actor_target(handler):
        return handler
    raise FlowDefinitionError(
        "flow_exception_handler expects actor-like target "
        "(address/actor_id/method) or actor symbolic target.",
    )


@contextmanager
def flow_exception_handler(handler: Any) -> Iterator[None]:
    flow_program = _current_flow_program()
    if flow_program is None:
        raise RuntimeError("flow_exception_handler must be used inside v1 flow compilation.")

    stack = getattr(flow_program, "_exception_handler_stack", None)
    if not isinstance(stack, list):
        raise RuntimeError("invalid_v1_flow_program_exception_stack")

    resolved_handler = _resolve_handler(handler)
    stack.append(resolved_handler)
    try:
        yield
    finally:
        stack.pop()


exception_handler = flow_exception_handler


__all__ = [
    "flow_exception_handler",
    "exception_handler",
    "flow_program_scope",
    "_set_current_flow_program",
    "_clear_current_flow_program",
    "_current_flow_program",
]
