"""SageVDB Backend Adapter - VectorStore implementation using SageVDB

This module provides a VectorStore adapter for SageVDB, enabling it to be used
with the unified IndexBuilder interface.

Layer: L4 (sage-middleware)
Dependencies: isage-vdb (PyPI package, Python import: sagevdb)

SageVDB is now an independent PyPI package. Install with: pip install isage-vdb
"""

from pathlib import Path
from typing import Any

from sagevdb import SageVDB


class SageVDBBackend:
    """VectorStore adapter for SageVDB (C++ vector database).

    This class wraps SageVDB to conform to the VectorStore Protocol,
    enabling it to be used with IndexBuilder via dependency injection.

    Architecture:
        - Implements VectorStore Protocol from L3 (sage-libs)
        - Uses SageVDB from isage-vdb (PyPI package, Python: sagevdb)
        - Injected into IndexBuilder by L6 (sage-cli)

    Example:
        >>> from sage.libs.rag.index_builder import IndexBuilder
        >>> from sage.middleware.components.sage_db import SageVDBBackend
        >>>
        >>> def factory(path: Path, dim: int):
        ...     return SageVDBBackend(path, dim)
        >>>
        >>> builder = IndexBuilder(backend_factory=factory)
    """

    def __init__(self, persist_path: Path, dim: int):
        """Initialize SageVDB backend.

        Args:
            persist_path: Path where index will be saved
            dim: Vector dimension
        """
        self.db = SageVDB(dim)
        self.persist_path = persist_path
        self.dim = dim
        self._count = 0

    def add(self, vector: list[float], metadata: dict[str, Any]) -> None:
        """Add vector with metadata to SageVDB.

        Args:
            vector: Dense vector embedding
            metadata: Associated metadata
        """
        self.db.add(vector, metadata)
        self._count += 1

    def build_index(self) -> None:
        """Build SageVDB index for efficient search."""
        self.db.build_index()

    def save(self, path: str) -> None:
        """Persist SageVDB index to disk.

        Args:
            path: Absolute path to save location
        """
        self.db.save(path)

    def load(self, path: str) -> None:
        """Load SageVDB index from disk.

        Args:
            path: Absolute path to load from
        """
        self.db.load(path)

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for nearest neighbors in SageVDB.

        Args:
            query_vector: Query embedding
            top_k: Number of results to return
            filter_metadata: Optional metadata filters

        Returns:
            List of search results with metadata and scores
        """
        # SageVDB search returns QueryResult objects
        results = self.db.search(query_vector, top_k=top_k)

        # Convert to standard format
        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "vector": result.vector,
                    "metadata": result.metadata,
                    "score": result.distance,  # or result.score
                    "id": result.id,
                }
            )

        # Apply metadata filter if provided
        if filter_metadata:
            formatted_results = [
                r
                for r in formatted_results
                if all(r["metadata"].get(k) == v for k, v in filter_metadata.items())
            ]

        return formatted_results

    def get_dim(self) -> int:
        """Get vector dimension.

        Returns:
            Vector dimension
        """
        return self.dim

    def count(self) -> int:
        """Get total number of vectors.

        Returns:
            Total vector count
        """
        return self._count
