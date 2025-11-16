"""Compatibility shim for ``sage.middleware.operators.rag.pipeline``.

Use ``sage.libs.rag.pipeline.RAGPipeline`` going forward.
"""

from sage.libs.rag.pipeline import RAGPipeline  # noqa: F401

__all__ = ["RAGPipeline"]
