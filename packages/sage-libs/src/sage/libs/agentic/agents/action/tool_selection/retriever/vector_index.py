"""
Vector index for efficient similarity search.

Provides lightweight vector storage and similarity search using numpy.
"""

import logging
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


class VectorIndex:
    """
    Lightweight vector index for similarity search.

    Stores vectors in memory and performs brute-force search.
    Suitable for up to ~10K vectors with acceptable performance.
    """

    def __init__(self, dimension: Optional[int] = None, metric: str = "cosine"):
        """
        Initialize vector index.

        Args:
            dimension: Vector dimension (inferred from first vector if None)
            metric: Similarity metric: cosine, dot, euclidean
        """
        self.dimension = dimension
        self.metric = metric

        self._vectors: Optional[np.ndarray] = None
        self._ids: list[str] = []
        self._id_to_idx: dict[str, int] = {}
        self._metadata: dict[str, Any] = {}

    def add(
        self, vector_id: str, vector: np.ndarray, metadata: Optional[dict[str, Any]] = None
    ) -> None:
        """
        Add vector to index.

        Args:
            vector_id: Unique identifier for the vector
            vector: Vector array
            metadata: Optional metadata
        """
        # Ensure vector is 1D
        vector = np.asarray(vector).flatten()

        # Infer dimension from first vector
        if self.dimension is None:
            self.dimension = len(vector)

        # Validate dimension
        if len(vector) != self.dimension:
            raise ValueError(f"Vector dimension {len(vector)} != index dimension {self.dimension}")

        # Check for duplicate ID
        if vector_id in self._id_to_idx:
            logger.warning(f"Overwriting existing vector: {vector_id}")
            idx = self._id_to_idx[vector_id]
            self._vectors[idx] = vector
        else:
            # Add new vector
            idx = len(self._ids)
            self._ids.append(vector_id)
            self._id_to_idx[vector_id] = idx

            if self._vectors is None:
                self._vectors = vector.reshape(1, -1)
            else:
                self._vectors = np.vstack([self._vectors, vector])

        # Store metadata
        if metadata:
            self._metadata[vector_id] = metadata

    def add_batch(
        self,
        vector_ids: list[str],
        vectors: np.ndarray,
        metadata: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        """
        Add multiple vectors in batch.

        Args:
            vector_ids: List of vector IDs
            vectors: Array of vectors (shape: N x D)
            metadata: Optional list of metadata dicts
        """
        vectors = np.asarray(vectors)
        if vectors.ndim != 2:
            raise ValueError(f"Vectors must be 2D array, got shape {vectors.shape}")

        if len(vector_ids) != vectors.shape[0]:
            raise ValueError(
                f"Number of IDs {len(vector_ids)} != number of vectors {vectors.shape[0]}"
            )

        for i, vector_id in enumerate(vector_ids):
            meta = metadata[i] if metadata and i < len(metadata) else None
            self.add(vector_id, vectors[i], meta)

    def search(
        self, query_vector: np.ndarray, top_k: int = 5, filter_ids: Optional[list[str]] = None
    ) -> list[tuple[str, float]]:
        """
        Search for similar vectors.

        Args:
            query_vector: Query vector
            top_k: Number of results to return
            filter_ids: Optional list of IDs to restrict search to

        Returns:
            List of (vector_id, score) tuples, sorted by score (descending)
        """
        if self._vectors is None or len(self._ids) == 0:
            return []

        query_vector = np.asarray(query_vector).flatten()

        if len(query_vector) != self.dimension:
            raise ValueError(
                f"Query dimension {len(query_vector)} != index dimension {self.dimension}"
            )

        # Compute similarities
        if self.metric == "cosine":
            scores = self._cosine_similarity(query_vector, self._vectors)
        elif self.metric == "dot":
            scores = np.dot(self._vectors, query_vector)
        elif self.metric == "euclidean":
            scores = -np.linalg.norm(self._vectors - query_vector, axis=1)
        else:
            raise ValueError(f"Unknown metric: {self.metric}")

        # Filter by IDs if provided
        if filter_ids:
            filter_indices = [self._id_to_idx[id_] for id_ in filter_ids if id_ in self._id_to_idx]
            if not filter_indices:
                return []

            filtered_scores = np.full_like(scores, -np.inf)
            filtered_scores[filter_indices] = scores[filter_indices]
            scores = filtered_scores

        # Get top-k
        top_k = min(top_k, len(self._ids))
        top_indices = np.argpartition(scores, -top_k)[-top_k:]
        top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

        results = [(self._ids[idx], float(scores[idx])) for idx in top_indices]
        return results

    def get_vector(self, vector_id: str) -> Optional[np.ndarray]:
        """Get vector by ID."""
        idx = self._id_to_idx.get(vector_id)
        if idx is None:
            return None
        return self._vectors[idx].copy()

    def get_metadata(self, vector_id: str) -> Optional[dict[str, Any]]:
        """Get metadata by ID."""
        return self._metadata.get(vector_id)

    def __len__(self) -> int:
        """Get number of vectors in index."""
        return len(self._ids)

    @staticmethod
    def _cosine_similarity(query: np.ndarray, vectors: np.ndarray) -> np.ndarray:
        """Compute cosine similarity between query and vectors."""
        query_norm = np.linalg.norm(query)
        vectors_norm = np.linalg.norm(vectors, axis=1)

        # Avoid division by zero
        query_norm = max(query_norm, 1e-10)
        vectors_norm = np.maximum(vectors_norm, 1e-10)

        dot_products = np.dot(vectors, query)
        similarities = dot_products / (query_norm * vectors_norm)

        return similarities

    def clear(self) -> None:
        """Clear all vectors from index."""
        self._vectors = None
        self._ids.clear()
        self._id_to_idx.clear()
        self._metadata.clear()
        logger.info("Cleared vector index")
