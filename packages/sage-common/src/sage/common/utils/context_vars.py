from __future__ import annotations

import contextvars
import functools
from contextlib import contextmanager
from typing import Any, Callable, Generator, Generic, TypeVar

T = TypeVar("T")


class ContextSlot(Generic[T]):
    def __init__(self, name: str, default: T | None = None):
        self._var: contextvars.ContextVar[T | None] = contextvars.ContextVar(
            name,
            default=default,
        )

    def get(self) -> T | None:
        return self._var.get()

    def set(self, value: T | None) -> contextvars.Token:
        return self._var.set(value)

    def reset(self, token: contextvars.Token) -> None:
        self._var.reset(token)

    @contextmanager
    def use(self, value: T | None) -> Generator[None, None, None]:
        token = self._var.set(value)
        try:
            yield
        finally:
            self._var.reset(token)


def run_in_executor_with_context(
    loop: Any,
    func: Callable[..., T],
    *args: Any,
    **kwargs: Any,
):
    ctx = contextvars.copy_context()
    bound = functools.partial(func, *args, **kwargs)
    return loop.run_in_executor(None, ctx.run, bound)


__all__ = [
    "ContextSlot",
    "run_in_executor_with_context",
]
