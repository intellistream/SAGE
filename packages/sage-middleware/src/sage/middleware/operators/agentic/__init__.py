"""L4 Agentic Operators.

This package exposes ready-to-use operator wrappers (MapOperators) built on
sage.libs.agentic components so Studio and pipeline builders can drag-and-drop
agent runtimes without wiring boilerplate.
"""

from .runtime import AgentRuntimeOperator

__all__ = ["AgentRuntimeOperator"]
