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
    RetrievalResult,
    # Base classes
    DocumentLoader,
    QueryRewriter,
    RAGPipeline,
    Reranker,
    Retriever,
    TextChunker,
    # Loader registry
    create_loader,
    register_loader,
    registered_loaders,
    # Chunker registry
    create_chunker,
    register_chunker,
    registered_chunkers,
    # Retriever registry
    create_retriever,
    register_retriever,
    registered_retrievers,
    # Reranker registry
    create_reranker,
    register_reranker,
    registered_rerankers,
    # QueryRewriter registry
    create_query_rewriter,
    register_query_rewriter,
    registered_query_rewriters,
    # Pipeline registry
    create_pipeline,
    register_pipeline,
    registered_pipelines,
    # Exception
    RAGRegistryError,
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
