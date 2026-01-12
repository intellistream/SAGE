"""Abstract base classes for RAG components.

This module defines the core abstractions for Retrieval-Augmented Generation:
- DocumentLoader: Load and parse documents from various sources
- TextChunker: Split text into manageable chunks
- Retriever: Retrieve relevant documents/chunks
- Reranker: Rerank retrieved results for better relevance
- RAGPipeline: End-to-end RAG workflow orchestration

These interfaces enable pluggable implementations from external packages.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class Document:
    """A document with content and metadata."""

    content: str
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        """Validate document fields."""
        if not isinstance(self.content, str):
            raise TypeError("content must be a string")
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dict")


@dataclass
class Chunk:
    """A text chunk with position information."""

    text: str
    start_pos: int
    end_pos: int
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        """Validate chunk fields."""
        if not isinstance(self.text, str):
            raise TypeError("text must be a string")
        if self.start_pos < 0 or self.end_pos < self.start_pos:
            raise ValueError("Invalid chunk positions")


@dataclass
class RetrievalResult:
    """A retrieval result with document and score."""

    document: Document
    score: float
    rank: int = 0

    def __post_init__(self) -> None:
        """Validate result fields."""
        if not isinstance(self.document, Document):
            raise TypeError("document must be a Document instance")
        if not isinstance(self.score, (int, float)):
            raise TypeError("score must be numeric")


# ========================================
# Document Loader Interface
# ========================================


class DocumentLoader(ABC):
    """Abstract base class for document loaders.

    Implementations should support various file formats:
    - Text files (.txt, .md, .json)
    - PDFs (.pdf)
    - Word documents (.docx, .doc)
    - Web pages (HTML, URL)
    - Structured data (CSV, Excel)
    """

    @abstractmethod
    def load(self, source: str, **kwargs: Any) -> Document:
        """Load a single document from a source.

        Args:
            source: File path, URL, or identifier
            **kwargs: Loader-specific options (encoding, page_range, etc.)

        Returns:
            Loaded document with content and metadata

        Raises:
            FileNotFoundError: If source doesn't exist
            ValueError: If source format is unsupported
        """
        pass

    @abstractmethod
    def load_batch(self, sources: list[str], **kwargs: Any) -> list[Document]:
        """Load multiple documents in batch.

        Args:
            sources: List of file paths, URLs, or identifiers
            **kwargs: Loader-specific options

        Returns:
            List of loaded documents
        """
        pass

    @abstractmethod
    def supported_formats(self) -> list[str]:
        """Get list of supported file formats.

        Returns:
            List of file extensions (e.g., [".txt", ".pdf", ".docx"])
        """
        pass


# ========================================
# Text Chunker Interface
# ========================================


class TextChunker(ABC):
    """Abstract base class for text chunking strategies.

    Implementations can use various chunking methods:
    - Character-based splitting
    - Token-based splitting (using tokenizers)
    - Sentence-based splitting
    - Semantic chunking (paragraph boundaries)
    - Sliding window with overlap
    """

    @abstractmethod
    def chunk(self, text: str, **kwargs: Any) -> list[Chunk]:
        """Split text into chunks.

        Args:
            text: Input text to chunk
            **kwargs: Chunker-specific options (chunk_size, overlap, etc.)

        Returns:
            List of text chunks with position information
        """
        pass

    @abstractmethod
    def chunk_document(self, document: Document, **kwargs: Any) -> list[Chunk]:
        """Chunk a document while preserving metadata.

        Args:
            document: Document to chunk
            **kwargs: Chunker-specific options

        Returns:
            List of chunks, each inheriting document metadata
        """
        pass

    @abstractmethod
    def get_chunk_size(self) -> int:
        """Get the configured chunk size.

        Returns:
            Chunk size (in characters or tokens depending on implementation)
        """
        pass


# ========================================
# Retriever Interface
# ========================================


class Retriever(ABC):
    """Abstract base class for retrieval strategies.

    Implementations can use various retrieval methods:
    - Vector search (dense retrieval)
    - Keyword search (BM25, TF-IDF)
    - Hybrid search (vector + keyword)
    - Graph-based retrieval
    """

    @abstractmethod
    def retrieve(self, query: str, top_k: int = 10, **kwargs: Any) -> list[RetrievalResult]:
        """Retrieve relevant documents for a query.

        Args:
            query: Search query
            top_k: Number of results to return
            **kwargs: Retriever-specific options (filters, boost, etc.)

        Returns:
            List of retrieval results ranked by relevance
        """
        pass

    @abstractmethod
    def add_documents(self, documents: list[Document]) -> None:
        """Add documents to the retrieval index.

        Args:
            documents: Documents to index
        """
        pass

    @abstractmethod
    def delete_documents(self, doc_ids: list[str]) -> None:
        """Delete documents from the index.

        Args:
            doc_ids: List of document IDs to delete
        """
        pass


# ========================================
# Reranker Interface
# ========================================


class Reranker(ABC):
    """Abstract base class for reranking strategies.

    Rerankers refine retrieval results using:
    - Cross-encoder models
    - LLM-based relevance scoring
    - Feature-based ranking (diversity, recency)
    """

    @abstractmethod
    def rerank(
        self, query: str, results: list[RetrievalResult], top_k: int = 10, **kwargs: Any
    ) -> list[RetrievalResult]:
        """Rerank retrieval results.

        Args:
            query: Original search query
            results: Initial retrieval results
            top_k: Number of results to return after reranking
            **kwargs: Reranker-specific options

        Returns:
            Reranked results with updated scores and ranks
        """
        pass


# ========================================
# Query Rewriter Interface
# ========================================


class QueryRewriter(ABC):
    """Abstract base class for query rewriting.

    Query rewriting improves retrieval by transforming user queries:
    - Query expansion: Add synonyms and related terms
    - Query decomposition: Break complex queries into sub-queries
    - Hypothetical Document Embeddings (HyDE): Generate hypothetical answers
    - Step-back prompting: Abstract to more general queries
    - Multi-query generation: Create query variants for fusion
    """

    @abstractmethod
    def rewrite(self, query: str, **kwargs: Any) -> str:
        """Rewrite a single query.

        Args:
            query: Original user query
            **kwargs: Rewriter-specific options (context, history, etc.)

        Returns:
            Rewritten query optimized for retrieval
        """
        pass

    @abstractmethod
    def rewrite_multi(self, query: str, num_variants: int = 3, **kwargs: Any) -> list[str]:
        """Generate multiple query variants.

        Args:
            query: Original user query
            num_variants: Number of variants to generate
            **kwargs: Rewriter-specific options

        Returns:
            List of query variants for multi-query retrieval
        """
        pass

    @abstractmethod
    def decompose(self, query: str, **kwargs: Any) -> list[str]:
        """Decompose a complex query into sub-queries.

        Args:
            query: Complex user query
            **kwargs: Decomposition options

        Returns:
            List of simpler sub-queries
        """
        pass


# ========================================
# RAG Pipeline Interface
# ========================================


class RAGPipeline(ABC):
    """Abstract base class for RAG pipeline orchestration.

    A complete RAG pipeline coordinates:
    1. Document loading and preprocessing
    2. Text chunking
    3. Embedding and indexing
    4. Retrieval (vector, keyword, or hybrid)
    5. Reranking (optional)
    6. Context assembly
    7. LLM generation with context

    This is the top-level abstraction for end-to-end RAG workflows.
    """

    @abstractmethod
    def index_documents(self, sources: list[str], **kwargs: Any) -> dict[str, Any]:
        """Index documents into the RAG system.

        Args:
            sources: Document sources (file paths, URLs, etc.)
            **kwargs: Pipeline-specific options

        Returns:
            Indexing statistics (num_docs, num_chunks, etc.)
        """
        pass

    @abstractmethod
    def query(self, query: str, top_k: int = 5, **kwargs: Any) -> dict[str, Any]:
        """Query the RAG system.

        Args:
            query: User query
            top_k: Number of retrieved chunks
            **kwargs: Pipeline-specific options (filters, rerank, etc.)

        Returns:
            RAG response with:
                - answer: Generated answer
                - sources: Retrieved source documents
                - metadata: Query metadata (latency, scores, etc.)
        """
        pass

    @abstractmethod
    def configure(self, **config: Any) -> None:
        """Configure pipeline components.

        Args:
            **config: Configuration options (loader, chunker, retriever, etc.)
        """
        pass


__all__ = [
    # Data classes
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
]
