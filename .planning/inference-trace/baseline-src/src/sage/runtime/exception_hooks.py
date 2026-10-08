from __future__ import annotations

from typing import Any

_PUSH_HANDLER: Any | None = None
_POP_HANDLER: Any | None = None


def register_kernel_exception_handler_hook(push, pop) -> None:
    """Register the active runtime's exception-scope push/pop hooks."""

    global _PUSH_HANDLER, _POP_HANDLER
    if not callable(push):
        raise TypeError(f"push hook must be callable, got {type(push)!r}")
    if not callable(pop):
        raise TypeError(f"pop hook must be callable, got {type(pop)!r}")
    _PUSH_HANDLER = push
    _POP_HANDLER = pop


def get_registered_exception_handler_hook() -> tuple[Any | None, Any | None]:
    return _PUSH_HANDLER, _POP_HANDLER
