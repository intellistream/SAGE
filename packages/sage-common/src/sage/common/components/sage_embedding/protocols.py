"""Embedding Protocol Definitions for SAGE.

Layer: L1 (Foundation - Common Components)

This module defines the standard embedding interface protocol and adapter
for SAGE. Components requiring embeddings should use EmbeddingProtocol.

Usage:
    from sage.common.components.sage_embedding.protocols import (
        EmbeddingProtocol,
        EmbeddingClientAdapter,
        adapt_embedding_client,
    )

    # Type hint for functions accepting embedders
    def process(embedder: EmbeddingProtocol) -> None:
        vectors = embedder.embed(["hello", "world"])

    # Adapt BaseEmbedding instances to EmbeddingProtocol
    from sage.common.components.sage_embedding.factory import EmbeddingFactory
    raw = EmbeddingFactory.create("hash", dim=64)
    client = adapt_embedding_client(raw)  # Now has batch interface
"""

import inspect
from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProtocol(Protocol):
    """Standard embedding interface for SAGE.

    This protocol defines the expected interface for embedding clients
    used by selectors and other components that require text embeddings.

    Interface:
        - embed(texts, model=None): Batch embed multiple texts
        - get_dim(): Get embedding dimension

    Examples:
        >>> class MyEmbedder:
        ...     def embed(self, texts: list[str], model=None) -> list[list[float]]:
        ...         return [[0.1, 0.2] for _ in texts]
        ...     def get_dim(self) -> int:
        ...         return 2
        >>>
        >>> embedder = MyEmbedder()
        >>> isinstance(embedder, EmbeddingProtocol)
        True
    """

    def embed(self, texts: list[str], model: Optional[str] = None) -> list[list[float]]:
        """Embed multiple texts into vectors.

        Args:
            texts: List of texts to embed
            model: Optional model name (backend-specific, often ignored)

        Returns:
            List of embedding vectors, one per input text
        """
        ...

    def get_dim(self) -> int:
        """Get the dimensionality of embedding vectors."""
        ...


class EmbeddingClientAdapter:
    """Adapter converting single-text embedders to EmbeddingProtocol.

    Wraps BaseEmbedding-style embedders (embed(text: str) -> list[float])
    to provide the standard batch interface (embed(texts: list[str]) -> list[list[float]]).

    Examples:
        >>> from sage.common.components.sage_embedding.factory import EmbeddingFactory
        >>> raw = EmbeddingFactory.create("hash", dim=64)
        >>> client = EmbeddingClientAdapter(raw)
        >>> vectors = client.embed(["hello", "world"])  # Batch interface
    """

    def __init__(self, embedder: Any):
        """Initialize adapter with a single-text embedder.

        Args:
            embedder: Embedder with embed(text: str) and get_dim() methods
        """
        self._embedder = embedder

    def embed(self, texts: list[str], model: Optional[str] = None) -> list[list[float]]:
        """Embed multiple texts.

        Args:
            texts: List of texts to embed
            model: Ignored (uses embedder's configured model)

        Returns:
            List of embedding vectors
        """
        if hasattr(self._embedder, "embed_batch"):
            return self._embedder.embed_batch(texts)
        return [self._embedder.embed(text) for text in texts]

    def get_dim(self) -> int:
        """Get embedding dimension."""
        return self._embedder.get_dim()


def adapt_embedding_client(embedder: Any) -> EmbeddingProtocol:
    """Adapt any embedder to EmbeddingProtocol interface.

    Inspects the embedder's embed() signature:
    - If embed(texts: list[str], ...) → returns as-is
    - If embed(text: str) → wraps with EmbeddingClientAdapter

    Args:
        embedder: Any embedding implementation

    Returns:
        Embedder conforming to EmbeddingProtocol

    Raises:
        TypeError: If embedder lacks embed() or get_dim() methods

    Examples:
        >>> from sage.common.components.sage_embedding.factory import EmbeddingFactory
        >>> raw = EmbeddingFactory.create("hash", dim=64)
        >>> client = adapt_embedding_client(raw)
        >>> vectors = client.embed(["hello", "world"])
    """
    if not hasattr(embedder, "embed") or not hasattr(embedder, "get_dim"):
        raise TypeError(
            f"Cannot adapt {type(embedder).__name__} to EmbeddingProtocol. "
            f"Missing 'embed' or 'get_dim' method."
        )

    # Check embed() signature
    sig = inspect.signature(embedder.embed)
    params = list(sig.parameters.keys())

    # Already has batch interface: embed(texts=...)
    if "texts" in params:
        return embedder

    # Single-text interface: embed(text=...) or positional only
    return EmbeddingClientAdapter(embedder)
