"""RAG Index Building Service (L4 Middleware Operator)

This module provides index building functionality for RAG systems.
It orchestrates document processing, embedding, and vector storage.

Layer: L4 (sage-middleware/operators/rag)
Dependencies:
  - sage.libs.rag (L3) - chunk, document_loaders
  - sage.middleware.components.sage_db (L4) - SageDB backend
  - sage.common (L1) - embedding models

Components:
- VectorStore: Protocol defining vector storage interface
- IndexManifest: Metadata describing a built index
- IndexBuilder: Service for building vector indices

Architecture Pattern:
- L4 defines IndexBuilder (orchestration)
- L4 provides SageDB backend implementation
- L3 provides ChromaDB backend via integrations
- L6 (sage-cli, sage-gateway) uses IndexBuilder

Example Usage:
    >>> from sage.middleware.operators.rag.index_builder import IndexBuilder
    >>> from sage.middleware.components.sage_db import SageVDBBackend
    >>>
    >>> # Create backend factory
    >>> def factory(path, dim):
    ...     return SageVDBBackend(path, dim)
    >>>
    >>> # Build index
    >>> builder = IndexBuilder(backend_factory=factory)
    >>> manifest = builder.build_from_docs(
    ...     source_dir=Path("docs"),
    ...     persist_path=Path(".sage/index"),
    ...     embedding_model=embedder,
    ... )
"""

from sage.middleware.operators.rag.index_builder.builder import IndexBuilder
from sage.middleware.operators.rag.index_builder.manifest import IndexManifest
from sage.middleware.operators.rag.index_builder.storage import VectorStore

__all__ = [
    "IndexBuilder",
    "IndexManifest",
    "VectorStore",
]
