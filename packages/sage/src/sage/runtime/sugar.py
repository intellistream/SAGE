"""High-level sugar APIs for invoking SAGE services from user scripts."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from concurrent.futures import Future
    from sage.kernel.runtime.context.base_context import BaseRuntimeContext


__all__ = [
    "bind_runtime_context",
    "call_service",
    "call_service_async",
    "clear_runtime_context",
    "get_current_runtime_context",
]


_CURRENT_CONTEXT: ContextVar[Optional["BaseRuntimeContext"]] = ContextVar(
    "sage_current_runtime_context", default=None
)


def get_current_runtime_context() -> Optional["BaseRuntimeContext"]:
    """Return the runtime context bound to the current execution scope."""

    return _CURRENT_CONTEXT.get()


@contextmanager
def bind_runtime_context(ctx: "BaseRuntimeContext"):
    """Bind a runtime context within a scoped block.

    This is primarily useful for user scripts that need to issue service
    calls outside of operator or service implementations.
    """

    token = _CURRENT_CONTEXT.set(ctx)
    try:
        yield ctx
    finally:
        _CURRENT_CONTEXT.reset(token)


def call_service(
    service_name: str,
    *args: Any,
    timeout: Optional[float] = None,
    method: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    """Invoke a service synchronously using the current runtime context."""

    ctx = get_current_runtime_context()
    if ctx is None:
        raise RuntimeError(
            "No runtime context bound. Use 'bind_runtime_context' or run inside a pipeline."
        )
    return ctx.call_service(
        service_name, *args, timeout=timeout, method=method, **kwargs
    )


def call_service_async(
    service_name: str,
    *args: Any,
    timeout: Optional[float] = None,
    method: Optional[str] = None,
    **kwargs: Any,
) -> "Future":
    """Invoke a service asynchronously using the current runtime context."""

    ctx = get_current_runtime_context()
    if ctx is None:
        raise RuntimeError(
            "No runtime context bound. Use 'bind_runtime_context' or run inside a pipeline."
        )
    return ctx.call_service_async(
        service_name, *args, timeout=timeout, method=method, **kwargs
    )


def clear_runtime_context() -> None:
    """Explicitly clear the bound runtime context."""

    _CURRENT_CONTEXT.set(None)
