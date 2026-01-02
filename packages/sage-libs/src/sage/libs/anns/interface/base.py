"""Core ANN abstractions for shared use across SAGE.

These interfaces will be used by benchmark_anns, sage-db, and sage-flow
once algorithms are migrated into ``sage.libs.ann``.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import numpy as np
import numpy.typing as npt


@dataclass(frozen=True)
class AnnIndexMeta:
    """Static capabilities for an ANN implementation."""

    name: str
    metric: str
    supports_insert: bool = True
    supports_delete: bool = True


class AnnIndex(ABC):
    """Minimal ANN interface to standardize build/insert/search flows."""

    @property
    @abstractmethod
    def meta(self) -> AnnIndexMeta:
        """Return static metadata describing this index."""

    @abstractmethod
    def setup(self, dtype: str, max_points: int, dim: int) -> None:
        """Initialize the index with type, capacity, and dimension."""

    @abstractmethod
    def insert(self, vectors: np.ndarray, ids: npt.NDArray[np.uint32]) -> None:
        """Insert vectors with their ids."""

    @abstractmethod
    def delete(self, ids: npt.NDArray[np.uint32]) -> None:
        """Delete vectors by ids."""

    @abstractmethod
    def search(self, queries: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
        """Search top-k nearest neighbors."""

    def batch_search(
        self, queries: np.ndarray, k: int, *, timestamps: Optional[np.ndarray] = None
    ) -> tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
        """Batch search with optional timestamp passthrough."""

        indices, distances = self.search(queries, k)
        if timestamps is None:
            return indices, distances, None

        # Attach processing timestamps to align with benchmark_anns expectations.
        now_us = np.full(len(queries), int(time.time() * 1e6), dtype=np.int64)
        return indices, distances, now_us

    def initial_load(self, vectors: np.ndarray, ids: npt.NDArray[np.uint32]) -> None:
        """Initial ingest; defaults to insert."""

        self.insert(vectors, ids)

    def replace(self, vectors: np.ndarray, ids: npt.NDArray[np.uint32]) -> None:
        """Replace by delete then insert."""

        self.delete(ids)
        self.insert(vectors, ids)

    def get_stats(self) -> dict:
        """Return optional diagnostic stats."""

        return {}

    def wait_pending_operations(self) -> None:
        """Hook for async implementations; no-op by default."""

        return None
