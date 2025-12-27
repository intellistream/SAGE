"""Compatibility shim for legacy ``sage.llm.compat`` imports.

Re-exports adapter classes from ``sage.common.components.sage_llm.compat``.
"""

from sage.common.components.sage_llm.compat import (
    EmbeddingClientAdapter,
    LLMClientAdapter,
)

__all__ = ["EmbeddingClientAdapter", "LLMClientAdapter"]
