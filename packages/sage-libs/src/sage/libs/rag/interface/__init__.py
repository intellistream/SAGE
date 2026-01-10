"""RAG (Retrieval-Augmented Generation) interface layer for SAGE.

This module provides abstract interfaces for RAG components.
Concrete implementations are provided by external packages (e.g., isage-rag).

Architecture:
    - base.py: Abstract base classes (DocumentLoader, TextChunker, Retriever, etc.)
    - factory.py: Registry and factory functions for each component type
    - External packages register their implementations at import time

Usage:
    # Option 1: Direct instantiation (if you know the implementation)
    from isage_rag import PDFLoader, FAISSRetriever
    loader = PDFLoader()
    retriever = FAISSRetriever(dimension=768)

    # Option 2: Factory pattern (more flexible)
    from sage.libs.rag.interface import create_loader, create_retriever
    loader = create_loader("pdf")
    retriever = create_retriever("faiss", dimension=768)

    # Use components
    document = loader.load("document.pdf")
    results = retriever.retrieve("query text", top_k=5)
"""

# Base classes and data types
from .base import (
    Chunk,
    Document,
    DocumentLoader,
    QueryRewriter,
    RAGPipeline,
    Reranker,
    RetrievalResult,
    Retriever,
    TextChunker,
)

# Factory functions
from .factory import (
    RAGRegistryError,
    create_chunker,
    create_loader,
    create_pipeline,
    create_query_rewriter,
    create_reranker,
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
    unregister_chunker,
    unregister_loader,
    unregister_pipeline,
    unregister_query_rewriter,
    unregister_reranker,
    unregister_retriever,
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
    "unregister_loader",
    # Chunker registry
    "register_chunker",
    "create_chunker",
    "registered_chunkers",
    "unregister_chunker",
    # Retriever registry
    "register_retriever",
    "create_retriever",
    "registered_retrievers",
    "unregister_retriever",
    # Reranker registry
    "register_reranker",
    "create_reranker",
    "registered_rerankers",
    "unregister_reranker",
    # QueryRewriter registry
    "register_query_rewriter",
    "create_query_rewriter",
    "registered_query_rewriters",
    "unregister_query_rewriter",
    # Pipeline registry
    "register_pipeline",
    "create_pipeline",
    "registered_pipelines",
    "unregister_pipeline",
    # Exception
    "RAGRegistryError",
]
