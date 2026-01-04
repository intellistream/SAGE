"""Vector Store Protocol - Abstract interface for vector storage backends

Layer: L4 (sage-middleware/operators/rag)
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class VectorStore(Protocol):
    """Abstract interface for vector storage backends.

    This Protocol defines the contract that all vector storage implementations
    must satisfy. It enables dependency injection and backend swapping without
    tight coupling to specific implementations (SageDB, ChromaDB, Milvus, etc.).

    Architecture Pattern:
        - L4 (sage-middleware): Defines this Protocol + SageDB implementation
        - L3 (sage-libs/integrations): Provides ChromaDB implementation
        - L6 (sage-cli, sage-gateway): Uses via factory injection

    Example Implementation:
        >>> class SageVDBBackend:
        ...     def __init__(self, persist_path: Path, dim: int):
        ...         from sage.middleware.components.sage_db import SageDB
        ...         self.db = SageDB(dim)
        ...         self.path = persist_path
        ...
        ...     def add(self, vector: list[float], metadata: dict) -> None:
        ...         self.db.add(vector, metadata)
        ...
        ...     # ... implement other methods

    Usage with IndexBuilder:
        >>> def backend_factory(path: Path, dim: int) -> VectorStore:
        ...     return SageDBBackend(path, dim)
        >>>
        >>> builder = IndexBuilder(backend_factory=backend_factory)
    """

    def add(self, vector: list[float], metadata: dict[str, Any]) -> None:
        """Add a single vector with metadata to the store.

        Args:
            vector: Dense vector embedding (must match dimension)
            metadata: Associated metadata (doc_path, title, heading, chunk, text, etc.)

        Raises:
            ValueError: If vector dimension doesn't match
        """
        ...

    def build_index(self) -> None:
        """Build/optimize the vector index for efficient search.

        This is typically called after all vectors are added via `add()`.
        Implementations may use various indexing strategies:
        - Flat index (brute force)
        - HNSW (Hierarchical Navigable Small World)
        - IVF (Inverted File Index)
        - Product Quantization

        Raises:
            RuntimeError: If index building fails
        """
        ...

    def save(self, path: str) -> None:
        """Persist the index to disk.

        Args:
            path: Absolute path to save location

        Raises:
            IOError: If save fails
        """
        ...

    def load(self, path: str) -> None:
        """Load a previously saved index from disk.

        Args:
            path: Absolute path to load from

        Raises:
            FileNotFoundError: If index doesn't exist
            IOError: If load fails
        """
        ...

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for nearest neighbor vectors.

        Args:
            query_vector: Query embedding
            top_k: Number of results to return
            filter_metadata: Optional metadata filters (e.g., {"doc_path": "intro.md"})

        Returns:
            List of results, each containing:
                - vector: The matched vector
                - metadata: Associated metadata
                - distance/score: Similarity score

        Example:
            >>> results = store.search([0.1, 0.2, ...], top_k=5)
            >>> for result in results:
            ...     print(result["metadata"]["title"], result["score"])
        """
        ...

    def get_dim(self) -> int:
        """Get the vector dimension of this store.

        Returns:
            Vector dimension (e.g., 384 for BGE-small, 768 for BERT)
        """
        ...

    def count(self) -> int:
        """Get total number of vectors in the store.

        Returns:
            Total vector count
        """
        ...
