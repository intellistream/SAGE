"""RAG (Retrieval-Augmented Generation) module for SAGE.

This module provides the RAG interface layer.
Concrete implementations are provided by external packages (e.g., isage-rag).

Usage:
    from sage.libs.rag.interface import (
        DocumentLoader, TextChunker, Retriever, Reranker, QueryRewriter, RAGPipeline,
        create_loader, create_retriever, create_query_rewriter,
    )
"""

from .interface import (
    # Data types
    Chunk,
    Document,
    # Base classes
    DocumentLoader,
    QueryRewriter,
    RAGPipeline,
    # Exception
    RAGRegistryError,
    Reranker,
    RetrievalResult,
    Retriever,
    TextChunker,
    # Chunker registry
    create_chunker,
    # Loader registry
    create_loader,
    # Pipeline registry
    create_pipeline,
    # QueryRewriter registry
    create_query_rewriter,
    # Reranker registry
    create_reranker,
    # Retriever registry
    create_retriever,
    register_chunker,
    register_loader,
    register_pipeline,
    register_query_rewriter,
    register_reranker,
    register_retriever,
    registered_chunkers,
    registered_loaders,
    registered_pipelines,
    registered_query_rewriters,
    registered_rerankers,
    registered_retrievers,
)

__all__ = [
    # Data types
    "Document",
    "Chunk",
    "RetrievalResult",
    # Base classes
    "DocumentLoader",
    "TextChunker",
    "Retriever",
    "Reranker",
    "QueryRewriter",
    "RAGPipeline",
    # Loader registry
    "register_loader",
    "create_loader",
    "registered_loaders",
    # Chunker registry
    "register_chunker",
    "create_chunker",
    "registered_chunkers",
    # Retriever registry
    "register_retriever",
    "create_retriever",
    "registered_retrievers",
    # Reranker registry
    "register_reranker",
    "create_reranker",
    "registered_rerankers",
    # QueryRewriter registry
    "register_query_rewriter",
    "create_query_rewriter",
    "registered_query_rewriters",
    # Pipeline registry
    "register_pipeline",
    "create_pipeline",
    "registered_pipelines",
    # Exception
    "RAGRegistryError",
]
