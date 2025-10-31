from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ..sage_db import DatabaseConfig, IndexType, SageDB


@dataclass
class SageDBServiceConfig:
    dimension: int = 4
    index_type: str = "AUTO"  # one of IndexType names


class SageDBService:
    """
    A minimal micro-service style wrapper for SageDB used by examples.

    Methods:
      - add(vector: np.ndarray | list, metadata: dict) -> int
      - add_batch(vectors: np.ndarray | list[list], metadata_list: list[dict]) -> list[int]
      - search(query: np.ndarray | list, k: int = 5) -> list[dict]
    """

    def __init__(self, dimension: int = 4, index_type: str = "AUTO") -> None:
        try:
            idx_enum = getattr(IndexType, index_type)
        except AttributeError:
            idx_enum = IndexType.AUTO
        cfg = DatabaseConfig(dimension)
        cfg.index_type = idx_enum
        self._db = SageDB.from_config(cfg)
        self._dim = dimension

    def add(
        self,
        vector: np.ndarray | list[float],
        metadata: dict[str, str] | None = None,
    ) -> int:
        if not isinstance(vector, np.ndarray):
            vector = np.asarray(vector, dtype=np.float32)
        if vector.ndim != 1 or vector.shape[0] != self._dim:
            raise ValueError(f"vector shape must be ({self._dim},)")
        return self._db.add(vector, metadata or {})

    def add_batch(
        self,
        vectors: np.ndarray | list[list[float]],
        metadata_list: list[dict[str, str]] | None = None,
    ) -> list[int]:
        if isinstance(vectors, list):
            arr = np.asarray(vectors, dtype=np.float32)
        else:
            arr = vectors.astype(np.float32, copy=False)
        if arr.ndim != 2 or arr.shape[1] != self._dim:
            raise ValueError(f"vectors shape must be (N, {self._dim})")
        return self._db.add_batch(arr, metadata_list or [])

    def search(
        self, query: np.ndarray | list[float], k: int = 5, include_metadata: bool = True
    ) -> list[dict[str, Any]]:
        if not isinstance(query, np.ndarray):
            query = np.asarray(query, dtype=np.float32)
        results = self._db.search(query, k=k, include_metadata=include_metadata)
        formatted = []
        for r in results:
            formatted.append(
                {
                    "id": int(r.id),
                    "score": float(r.score),
                    "metadata": dict(r.metadata) if include_metadata else {},
                }
            )
        return formatted

    def stats(self) -> dict[str, Any]:
        s = self._db.get_search_stats()
        return {
            "size": self._db.size,
            "dimension": self._db.dimension,
            **s,
        }
