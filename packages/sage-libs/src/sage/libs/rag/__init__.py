"""RAG (Retrieval-Augmented Generation) module for SAGE.

This module provides:
1. RAG interface layer (abstract base classes and factory)
2. RAG-specific data types for pipeline interoperability
3. Built-in document loaders and chunkers

Concrete implementations are provided by external packages (e.g., isage-rag).

Usage:
    # Interface layer
    from sage.libs.rag.interface import (
        DocumentLoader, TextChunker, Retriever, Reranker, QueryRewriter, RAGPipeline,
        create_loader, create_retriever, create_query_rewriter,
    )

    # RAG-specific types (for middleware operators)
    from sage.libs.rag.types import (
        RAGDocument, RAGQuery, RAGResponse, RAGInput, RAGOutput,
        create_rag_response, ensure_rag_response, extract_query, extract_results,
    )

    # Built-in utilities
    from sage.libs.rag.document_loaders import TextLoader, PDFLoader, LoaderFactory
    from sage.libs.rag.chunk import CharacterSplitter, SentenceTransformersTokenTextSplitter
"""

# Interface layer
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
    # RAG-specific types (from types module)
    "RAGDocument",
    "RAGQuery",
    "RAGResponse",
    "RAGInput",
    "RAGOutput",
    "create_rag_response",
    "ensure_rag_response",
    "extract_query",
    "extract_results",
    # Built-in loaders (from document_loaders module)
    "TextLoader",
    "PDFLoader",
    "DocxLoader",
    "DocLoader",
    "MarkdownLoader",
    "LoaderFactory",
    # Built-in chunkers (from chunk module)
    "CharacterSplitter",
    "SentenceTransformersTokenTextSplitter",
]

# RAG-specific types for pipeline interoperability
# Built-in chunkers
from .chunk import (
    CharacterSplitter,
    SentenceTransformersTokenTextSplitter,
)

# Built-in document loaders
from .document_loaders import (
    DocLoader,
    DocxLoader,
    LoaderFactory,
    MarkdownLoader,
    PDFLoader,
    TextLoader,
)
from .types import (
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
