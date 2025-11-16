"""Compatibility shim for RAG type definitions.

Import from ``sage.libs.rag.types`` instead of middleware.
"""

from sage.libs.rag.types import (  # noqa: F401
    RAGDocument,
    RAGInput,
    RAGOutput,
    RAGQuery,
    RAGResponse,
    create_rag_response,
    ensure_rag_response,
    extract_query,
    extract_results,
)

__all__ = [
    "RAGDocument",
    "RAGQuery",
    "RAGResponse",
    "RAGInput",
    "RAGOutput",
    "ensure_rag_response",
    "extract_query",
    "extract_results",
    "create_rag_response",
]
