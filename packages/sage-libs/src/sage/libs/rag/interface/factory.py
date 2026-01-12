"""Factory and registry for RAG component implementations.

This module provides a registry pattern for RAG components.
External packages (like isage-rag) can register their implementations here.

Example:
    # Register implementations
    from sage.libs.rag.interface import (
        register_loader,
        register_chunker,
        register_retriever,
        register_pipeline,
    )
    register_loader("pdf", PDFLoader)
    register_chunker("sentence_transformer", SentenceTransformerChunker)
    register_retriever("faiss", FAISSRetriever)
    register_pipeline("simple_rag", SimpleRAGPipeline)

    # Create instances
    from sage.libs.rag.interface import (
        create_loader,
        create_chunker,
        create_retriever,
        create_pipeline,
    )
    loader = create_loader("pdf")
    chunker = create_chunker("sentence_transformer", chunk_size=512)
    retriever = create_retriever("faiss", dimension=768)
    pipeline = create_pipeline("simple_rag")
"""

from typing import Any

from .base import DocumentLoader, QueryRewriter, RAGPipeline, Reranker, Retriever, TextChunker

_LOADER_REGISTRY: dict[str, type[DocumentLoader]] = {}
_CHUNKER_REGISTRY: dict[str, type[TextChunker]] = {}
_RETRIEVER_REGISTRY: dict[str, type[Retriever]] = {}
_RERANKER_REGISTRY: dict[str, type[Reranker]] = {}
_QUERY_REWRITER_REGISTRY: dict[str, type[QueryRewriter]] = {}
_PIPELINE_REGISTRY: dict[str, type[RAGPipeline]] = {}


class RAGRegistryError(Exception):
    """Error raised when registry operations fail."""

    pass


# ========================================
# Document Loader Registry
# ========================================


def register_loader(name: str, cls: type[DocumentLoader]) -> None:
    """Register a document loader implementation.

    Args:
        name: Unique identifier (e.g., "pdf", "docx", "markdown")
        cls: Loader class (should inherit from DocumentLoader)

    Raises:
        RAGRegistryError: If name already registered
    """
    if name in _LOADER_REGISTRY:
        raise RAGRegistryError(f"Loader '{name}' already registered")

    if not issubclass(cls, DocumentLoader):
        raise TypeError(f"Class must inherit from DocumentLoader, got {cls}")

    _LOADER_REGISTRY[name] = cls


def create_loader(name: str, **kwargs: Any) -> DocumentLoader:
    """Create a document loader instance by name.

    Args:
        name: Name of the registered loader
        **kwargs: Arguments to pass to the loader constructor

    Returns:
        Instance of the loader

    Raises:
        RAGRegistryError: If loader not found
    """
    if name not in _LOADER_REGISTRY:
        available = ", ".join(_LOADER_REGISTRY.keys()) if _LOADER_REGISTRY else "none"
        raise RAGRegistryError(
            f"Loader '{name}' not found. Available: {available}. Did you install 'isage-rag'?"
        )

    cls = _LOADER_REGISTRY[name]
    return cls(**kwargs)


def registered_loaders() -> list[str]:
    """Get list of registered loader names."""
    return list(_LOADER_REGISTRY.keys())


# ========================================
# Text Chunker Registry
# ========================================


def register_chunker(name: str, cls: type[TextChunker]) -> None:
    """Register a text chunker implementation.

    Args:
        name: Unique identifier (e.g., "character", "token", "semantic")
        cls: Chunker class (should inherit from TextChunker)

    Raises:
        RAGRegistryError: If name already registered
    """
    if name in _CHUNKER_REGISTRY:
        raise RAGRegistryError(f"Chunker '{name}' already registered")

    if not issubclass(cls, TextChunker):
        raise TypeError(f"Class must inherit from TextChunker, got {cls}")

    _CHUNKER_REGISTRY[name] = cls


def create_chunker(name: str, **kwargs: Any) -> TextChunker:
    """Create a text chunker instance by name.

    Args:
        name: Name of the registered chunker
        **kwargs: Arguments to pass to the chunker constructor

    Returns:
        Instance of the chunker

    Raises:
        RAGRegistryError: If chunker not found
    """
    if name not in _CHUNKER_REGISTRY:
        available = ", ".join(_CHUNKER_REGISTRY.keys()) if _CHUNKER_REGISTRY else "none"
        raise RAGRegistryError(
            f"Chunker '{name}' not found. Available: {available}. Did you install 'isage-rag'?"
        )

    cls = _CHUNKER_REGISTRY[name]
    return cls(**kwargs)


def registered_chunkers() -> list[str]:
    """Get list of registered chunker names."""
    return list(_CHUNKER_REGISTRY.keys())


# ========================================
# Retriever Registry
# ========================================


def register_retriever(name: str, cls: type[Retriever]) -> None:
    """Register a retriever implementation.

    Args:
        name: Unique identifier (e.g., "faiss", "bm25", "hybrid")
        cls: Retriever class (should inherit from Retriever)

    Raises:
        RAGRegistryError: If name already registered
    """
    if name in _RETRIEVER_REGISTRY:
        raise RAGRegistryError(f"Retriever '{name}' already registered")

    if not issubclass(cls, Retriever):
        raise TypeError(f"Class must inherit from Retriever, got {cls}")

    _RETRIEVER_REGISTRY[name] = cls


def create_retriever(name: str, **kwargs: Any) -> Retriever:
    """Create a retriever instance by name.

    Args:
        name: Name of the registered retriever
        **kwargs: Arguments to pass to the retriever constructor

    Returns:
        Instance of the retriever

    Raises:
        RAGRegistryError: If retriever not found
    """
    if name not in _RETRIEVER_REGISTRY:
        available = ", ".join(_RETRIEVER_REGISTRY.keys()) if _RETRIEVER_REGISTRY else "none"
        raise RAGRegistryError(
            f"Retriever '{name}' not found. Available: {available}. Did you install 'isage-rag'?"
        )

    cls = _RETRIEVER_REGISTRY[name]
    return cls(**kwargs)


def registered_retrievers() -> list[str]:
    """Get list of registered retriever names."""
    return list(_RETRIEVER_REGISTRY.keys())


# ========================================
# Reranker Registry
# ========================================


def register_reranker(name: str, cls: type[Reranker]) -> None:
    """Register a reranker implementation.

    Args:
        name: Unique identifier (e.g., "cross_encoder", "llm")
        cls: Reranker class (should inherit from Reranker)

    Raises:
        RAGRegistryError: If name already registered
    """
    if name in _RERANKER_REGISTRY:
        raise RAGRegistryError(f"Reranker '{name}' already registered")

    if not issubclass(cls, Reranker):
        raise TypeError(f"Class must inherit from Reranker, got {cls}")

    _RERANKER_REGISTRY[name] = cls


def create_reranker(name: str, **kwargs: Any) -> Reranker:
    """Create a reranker instance by name.

    Args:
        name: Name of the registered reranker
        **kwargs: Arguments to pass to the reranker constructor

    Returns:
        Instance of the reranker

    Raises:
        RAGRegistryError: If reranker not found
    """
    if name not in _RERANKER_REGISTRY:
        available = ", ".join(_RERANKER_REGISTRY.keys()) if _RERANKER_REGISTRY else "none"
        raise RAGRegistryError(
            f"Reranker '{name}' not found. Available: {available}. Did you install 'isage-rag'?"
        )

    cls = _RERANKER_REGISTRY[name]
    return cls(**kwargs)


def registered_rerankers() -> list[str]:
    """Get list of registered reranker names."""
    return list(_RERANKER_REGISTRY.keys())


# ========================================
# Query Rewriter Registry
# ========================================


def register_query_rewriter(name: str, cls: type[QueryRewriter]) -> None:
    """Register a query rewriter implementation.

    Args:
        name: Unique identifier (e.g., "llm", "hyde", "multi_query")
        cls: QueryRewriter class (should inherit from QueryRewriter)

    Raises:
        RAGRegistryError: If name already registered
    """
    if name in _QUERY_REWRITER_REGISTRY:
        raise RAGRegistryError(f"QueryRewriter '{name}' already registered")

    if not issubclass(cls, QueryRewriter):
        raise TypeError(f"Class must inherit from QueryRewriter, got {cls}")

    _QUERY_REWRITER_REGISTRY[name] = cls


def create_query_rewriter(name: str, **kwargs: Any) -> QueryRewriter:
    """Create a query rewriter instance by name.

    Args:
        name: Name of the registered query rewriter
        **kwargs: Arguments to pass to the query rewriter constructor

    Returns:
        Instance of the query rewriter

    Raises:
        RAGRegistryError: If query rewriter not found
    """
    if name not in _QUERY_REWRITER_REGISTRY:
        available = (
            ", ".join(_QUERY_REWRITER_REGISTRY.keys()) if _QUERY_REWRITER_REGISTRY else "none"
        )
        raise RAGRegistryError(
            f"QueryRewriter '{name}' not found. Available: {available}. Did you install 'isage-rag'?"
        )

    cls = _QUERY_REWRITER_REGISTRY[name]
    return cls(**kwargs)


def registered_query_rewriters() -> list[str]:
    """Get list of registered query rewriter names."""
    return list(_QUERY_REWRITER_REGISTRY.keys())


# ========================================
# RAG Pipeline Registry
# ========================================


def register_pipeline(name: str, cls: type[RAGPipeline]) -> None:
    """Register a RAG pipeline implementation.

    Args:
        name: Unique identifier (e.g., "simple_rag", "advanced_rag")
        cls: Pipeline class (should inherit from RAGPipeline)

    Raises:
        RAGRegistryError: If name already registered
    """
    if name in _PIPELINE_REGISTRY:
        raise RAGRegistryError(f"Pipeline '{name}' already registered")

    if not issubclass(cls, RAGPipeline):
        raise TypeError(f"Class must inherit from RAGPipeline, got {cls}")

    _PIPELINE_REGISTRY[name] = cls


def create_pipeline(name: str, **kwargs: Any) -> RAGPipeline:
    """Create a RAG pipeline instance by name.

    Args:
        name: Name of the registered pipeline
        **kwargs: Arguments to pass to the pipeline constructor

    Returns:
        Instance of the pipeline

    Raises:
        RAGRegistryError: If pipeline not found
    """
    if name not in _PIPELINE_REGISTRY:
        available = ", ".join(_PIPELINE_REGISTRY.keys()) if _PIPELINE_REGISTRY else "none"
        raise RAGRegistryError(
            f"Pipeline '{name}' not found. Available: {available}. Did you install 'isage-rag'?"
        )

    cls = _PIPELINE_REGISTRY[name]
    return cls(**kwargs)


def registered_pipelines() -> list[str]:
    """Get list of registered pipeline names."""
    return list(_PIPELINE_REGISTRY.keys())


# ========================================
# Testing Utilities
# ========================================


def unregister_loader(name: str) -> None:
    """Unregister a loader (for testing)."""
    _LOADER_REGISTRY.pop(name, None)


def unregister_chunker(name: str) -> None:
    """Unregister a chunker (for testing)."""
    _CHUNKER_REGISTRY.pop(name, None)


def unregister_retriever(name: str) -> None:
    """Unregister a retriever (for testing)."""
    _RETRIEVER_REGISTRY.pop(name, None)


def unregister_reranker(name: str) -> None:
    """Unregister a reranker (for testing)."""
    _RERANKER_REGISTRY.pop(name, None)


def unregister_query_rewriter(name: str) -> None:
    """Unregister a query rewriter (for testing)."""
    _QUERY_REWRITER_REGISTRY.pop(name, None)


def unregister_pipeline(name: str) -> None:
    """Unregister a pipeline (for testing)."""
    _PIPELINE_REGISTRY.pop(name, None)


__all__ = [
    "RAGRegistryError",
    # Loader
    "register_loader",
    "create_loader",
    "registered_loaders",
    "unregister_loader",
    # Chunker
    "register_chunker",
    "create_chunker",
    "registered_chunkers",
    "unregister_chunker",
    # Retriever
    "register_retriever",
    "create_retriever",
    "registered_retrievers",
    "unregister_retriever",
    # Reranker
    "register_reranker",
    "create_reranker",
    "registered_rerankers",
    "unregister_reranker",
    # QueryRewriter
    "register_query_rewriter",
    "create_query_rewriter",
    "registered_query_rewriters",
    "unregister_query_rewriter",
    # Pipeline
    "register_pipeline",
    "create_pipeline",
    "registered_pipelines",
    "unregister_pipeline",
]
