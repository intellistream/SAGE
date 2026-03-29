from __future__ import annotations


class FlowCompileError(RuntimeError):
    """Base error for v1 flow compilation failures."""


class FlowDefinitionError(FlowCompileError):
    """Raised when a v1 flow definition violates compile-time contracts."""


__all__ = [
    "FlowCompileError",
    "FlowDefinitionError",
]
