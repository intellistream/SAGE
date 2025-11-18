"""Foundation layer - Low-level utilities and building blocks.

This module provides foundational utilities that are used across SAGE:
- tools: Tool base classes and registry
- io: Source/Sink/Batch abstractions for data flow
- context: Context compression algorithms

These utilities have minimal dependencies and form the base layer of sage-libs.
"""

from . import context, io, tools

__all__ = [
    "tools",
    "io",
    "context",
]
