from __future__ import annotations

import contextlib
import contextvars
from typing import Any

_loop_ctx_var: contextvars.ContextVar[Any | None] = contextvars.ContextVar(
    "flownet_v1_loop_ctx",
    default=None,
)


@contextlib.contextmanager
def bind_loop_ctx(loop_ctx: Any):
    token = _loop_ctx_var.set(loop_ctx)
    try:
        yield loop_ctx
    finally:
        _loop_ctx_var.reset(token)


def current_loop_ctx() -> Any | None:
    return _loop_ctx_var.get()


def require_loop_ctx() -> Any:
    loop_ctx = current_loop_ctx()
    if loop_ctx is None:
        raise RuntimeError("flownet_v1_loop_ctx_not_bound")
    return loop_ctx


class _LoopCtxProxy:
    def __getattr__(self, name: str) -> Any:
        loop_ctx = require_loop_ctx()
        attr = getattr(loop_ctx, name, None)
        if attr is None:
            raise AttributeError(f"flownet_v1_loop_ctx_attribute_not_found:{name}")
        return attr


ctx = _LoopCtxProxy()


__all__ = [
    "ctx",
    "bind_loop_ctx",
    "current_loop_ctx",
    "require_loop_ctx",
]
