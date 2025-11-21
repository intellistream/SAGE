"""
LLM wrapper clients tailored for DyFlow designer and executor roles.

This module provides specialized LLM clients for:
- Designer role: Generate dynamic workflow stages
- Executor role: Execute instructions and generate responses

The clients wrap ModelService to provide role-specific interfaces
with appropriate prompting and response handling.

Layer: L3 (Core Library)
"""

from .clients import ExecutorLLMClient

__all__ = [
    "ExecutorLLMClient",
]
