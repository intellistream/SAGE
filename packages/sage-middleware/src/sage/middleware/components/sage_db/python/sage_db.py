"""
SAGE DB - High-performance vector database with FAISS backend (Python side)

This module exposes Python APIs backed by the compiled _sage_db extension.
It supports efficient similarity search, metadata filtering, and hybrid search.
"""

from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np

try:
    # Prefer relative import when installed as a package
    from . import _sage_db  # type: ignore
except ImportError:  # pragma: no cover - repo/local build fallback
    import importlib
    import sys
    from pathlib import Path

    here = Path(__file__).resolve().parent
    candidates = [
        here / "build" / "lib",  # python dir local build
        here.parent / "build" / "lib",  # component-level build
        here.parent,  # compiled module copied next to python/
    ]
    for p in candidates:
        if p.exists() and str(p) not in sys.path:
            sys.path.insert(0, str(p))
    _sage_db = importlib.import_module("_sage_db")  # type: ignore


# Re-export C++ classes and enums
IndexType = _sage_db.IndexType
DistanceMetric = _sage_db.DistanceMetric
QueryResult = _sage_db.QueryResult
SearchParams = _sage_db.SearchParams
DatabaseConfig = _sage_db.DatabaseConfig
SageDBException = _sage_db.SageDBException


class SageDB:
    """
    High-performance vector database with FAISS backend.

    Supports efficient similarity search, metadata filtering, and hybrid search.
    """

    def __init__(
        self,
        dimension: int,
        index_type: IndexType = IndexType.AUTO,
        metric: DistanceMetric = DistanceMetric.L2,
    ):
        self._db = _sage_db.create_database(dimension, index_type, metric)

    @classmethod
    def from_config(cls, config: DatabaseConfig):
        instance = cls.__new__(cls)
        instance._db = _sage_db.create_database(config)
        return instance

    def add(
        self,
        vector: Union[List[float], np.ndarray],
        metadata: Optional[Dict[str, str]] = None,
    ) -> int:
        if isinstance(vector, np.ndarray):
            vector = vector.tolist()
        return self._db.add(vector, metadata or {})

    def add_batch(
        self,
        vectors: Union[List[List[float]], np.ndarray],
        metadata: Optional[List[Dict[str, str]]] = None,
    ) -> List[int]:
        if isinstance(vectors, np.ndarray):
            if len(vectors.shape) != 2:
                raise ValueError("Vectors array must be 2-dimensional")
            return _sage_db.add_numpy(self._db, vectors, metadata or [])
        else:
            return self._db.add_batch(vectors, metadata or [])

    def search(
        self,
        query: Union[List[float], np.ndarray],
        k: int = 10,
        include_metadata: bool = True,
    ) -> List[QueryResult]:
        if isinstance(query, np.ndarray):
            return _sage_db.search_numpy(self._db, query, SearchParams(k))
        return self._db.search(query, k, include_metadata)

    def search_with_params(
        self, query: Union[List[float], np.ndarray], params: SearchParams
    ) -> List[QueryResult]:
        if isinstance(query, np.ndarray):
            return _sage_db.search_numpy(self._db, query, params)
        return self._db.search(query, params)

    def filtered_search(
        self,
        query: Union[List[float], np.ndarray],
        params: SearchParams,
        filter_fn: Callable[[Dict[str, str]], bool],
    ) -> List[QueryResult]:
        if isinstance(query, np.ndarray):
            query = query.tolist()
        return self._db.filtered_search(query, params, filter_fn)

    def search_by_metadata(
        self,
        query: Union[List[float], np.ndarray],
        params: SearchParams,
        metadata_key: str,
        metadata_value: str,
    ) -> List[QueryResult]:
        if isinstance(query, np.ndarray):
            query = query.tolist()
        return self._db.query_engine().search_with_metadata(
            query, params, metadata_key, metadata_value
        )

    def hybrid_search(
        self,
        query: Union[List[float], np.ndarray],
        params: SearchParams,
        text_query: str = "",
        vector_weight: float = 0.7,
        text_weight: float = 0.3,
    ) -> List[QueryResult]:
        if isinstance(query, np.ndarray):
            query = query.tolist()
        return self._db.query_engine().hybrid_search(
            query, params, text_query, vector_weight, text_weight
        )

    def build_index(self):
        self._db.build_index()

    def train_index(
        self, training_vectors: Optional[Union[List[List[float]], np.ndarray]] = None
    ):
        if training_vectors is None:
            self._db.train_index()
        elif isinstance(training_vectors, np.ndarray):
            training_list = [
                training_vectors[i].tolist() for i in range(training_vectors.shape[0])
            ]
            self._db.train_index(training_list)
        else:
            self._db.train_index(training_vectors)

    def is_trained(self) -> bool:
        return self._db.is_trained()

    def set_metadata(self, vector_id: int, metadata: Dict[str, str]) -> bool:
        return self._db.set_metadata(vector_id, metadata)

    def get_metadata(self, vector_id: int) -> Optional[Dict[str, str]]:
        return self._db.get_metadata(vector_id)

    def find_by_metadata(self, key: str, value: str) -> List[int]:
        return self._db.find_by_metadata(key, value)

    def save(self, filepath: str):
        self._db.save(filepath)

    def load(self, filepath: str):
        self._db.load(filepath)

    @property
    def size(self) -> int:
        return self._db.size()

    @property
    def dimension(self) -> int:
        return self._db.dimension()

    @property
    def index_type(self) -> IndexType:
        return self._db.index_type()

    def get_search_stats(self) -> Dict[str, Any]:
        stats = self._db.query_engine().get_last_search_stats()
        return {
            "total_candidates": stats.total_candidates,
            "filtered_candidates": stats.filtered_candidates,
            "final_results": stats.final_results,
            "search_time_ms": stats.search_time_ms,
            "filter_time_ms": stats.filter_time_ms,
            "total_time_ms": stats.total_time_ms,
        }


def create_database(
    dimension: int,
    index_type: IndexType = IndexType.AUTO,
    metric: DistanceMetric = DistanceMetric.L2,
) -> SageDB:
    return SageDB(dimension, index_type, metric)


def create_database_from_config(config: DatabaseConfig) -> SageDB:
    return SageDB.from_config(config)


__all__ = [
    "SageDB",
    "IndexType",
    "DistanceMetric",
    "QueryResult",
    "SearchParams",
    "DatabaseConfig",
    "SageDBException",
    "create_database",
    "create_database_from_config",
]
