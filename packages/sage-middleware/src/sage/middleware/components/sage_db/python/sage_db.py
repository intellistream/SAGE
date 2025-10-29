"""
SAGE DB - High-performance vector database with FAISS backend (Python side)

This module exposes Python APIs backed by the compiled _sage_db extension.
It supports efficient similarity search, metadata filtering, and hybrid search.
"""

from collections.abc import Callable
from typing import Any

import numpy as np

_sage_db: Any = None

try:
    # Prefer relative import when installed as a package
    from . import _sage_db  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - repo/local build fallback
    import ctypes
    import importlib
    import os
    import sys
    from pathlib import Path

    here = Path(__file__).resolve().parent
    candidates = [
        here,  # same directory as this file (editable install case)
        here / "build" / "lib",  # python dir local build
        here.parent / "build" / "lib",  # component-level build
        here.parent,  # compiled module copied next to python/
        here.parent / "build",  # build directory
        here.parent / "install",  # install directory
    ]

    # Allow explicit override so CI can point to installed location
    extra_paths = os.environ.get("SAGE_DB_LIBRARY_PATH")
    if extra_paths:
        for token in extra_paths.split(os.pathsep):
            token_path = Path(token.strip())
            if token_path and token_path.exists():
                candidates.append(token_path)

    # Add paths and try direct import
    for p in candidates:
        if p.exists() and str(p) not in sys.path:
            sys.path.insert(0, str(p))

    # Try to find the .so file directly
    for p in candidates:
        if p.exists():
            # Look for _sage_db.*.so files
            so_files = list(p.glob("_sage_db*.so"))
            if so_files:
                # Add this directory to sys.path if not already there
                if str(p) not in sys.path:
                    sys.path.insert(0, str(p))
                break

    # Ensure the native lib dependency is preloaded so dlopen can succeed
    lib_loaded = False
    lib_names = [
        "libsage_db.so",  # Linux
        "libsage_db.dylib",  # macOS
        "sage_db.dll",  # Windows
    ]

    for p in candidates:
        if not p.exists():
            continue
        for lib_name in lib_names:
            lib_path = p / lib_name
            if lib_path.exists():
                try:
                    ctypes.CDLL(str(lib_path))
                    lib_loaded = True
                    break
                except OSError:
                    continue
        if lib_loaded:
            break

    if not lib_loaded:
        # Some build layouts place the shared library one level deeper (e.g. install/lib)
        for p in candidates:
            if not p.exists():
                continue
            for child in p.rglob("libsage_db*.so"):
                try:
                    ctypes.CDLL(str(child))
                    lib_loaded = True
                    break
                except OSError:
                    continue
            if lib_loaded:
                break

    if _sage_db is None:
        try:
            _sage_db = importlib.import_module("_sage_db")  # type: ignore[assignment]
        except ImportError as e:
            raise ImportError(
                f"Failed to import _sage_db module. "
                f"Please ensure the C++ extension is built. "
                f"Original error: {e}"
            ) from e

# Ensure _sage_db is loaded
if _sage_db is None:
    raise RuntimeError("_sage_db module could not be loaded")

# Re-export C++ classes and enums
IndexType = _sage_db.IndexType  # type: ignore[union-attr]
DistanceMetric = _sage_db.DistanceMetric  # type: ignore[union-attr]
QueryResult = _sage_db.QueryResult  # type: ignore[union-attr]
SearchParams = _sage_db.SearchParams  # type: ignore[union-attr]
DatabaseConfig = _sage_db.DatabaseConfig  # type: ignore[union-attr]
SageDBException = _sage_db.SageDBException  # type: ignore[union-attr]


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
        self._db = _sage_db.create_database(dimension, index_type, metric)  # type: ignore[union-attr]

    @classmethod
    def from_config(cls, config: DatabaseConfig):
        instance = cls.__new__(cls)
        instance._db = _sage_db.create_database(config)  # type: ignore[union-attr]
        return instance

    def add(
        self,
        vector: list[float] | np.ndarray,
        metadata: dict[str, str] | None = None,
    ) -> int:
        if isinstance(vector, np.ndarray):
            vector = vector.tolist()
        return self._db.add(vector, metadata or {})

    def add_batch(
        self,
        vectors: list[list[float]] | np.ndarray,
        metadata: list[dict[str, str]] | None = None,
    ) -> list[int]:
        if isinstance(vectors, np.ndarray):
            if len(vectors.shape) != 2:
                raise ValueError("Vectors array must be 2-dimensional")
            return _sage_db.add_numpy(self._db, vectors, metadata or [])  # type: ignore[union-attr]
        else:
            return self._db.add_batch(vectors, metadata or [])

    def search(
        self,
        query: list[float] | np.ndarray,
        k: int = 10,
        include_metadata: bool = True,
    ) -> list[QueryResult]:
        if isinstance(query, np.ndarray):
            return _sage_db.search_numpy(self._db, query, SearchParams(k))  # type: ignore[union-attr]
        return self._db.search(query, k, include_metadata)

    def search_with_params(
        self, query: list[float] | np.ndarray, params: SearchParams
    ) -> list[QueryResult]:
        if isinstance(query, np.ndarray):
            return _sage_db.search_numpy(self._db, query, params)  # type: ignore[union-attr]
        return self._db.search(query, params)

    def filtered_search(
        self,
        query: list[float] | np.ndarray,
        params: SearchParams,
        filter_fn: Callable[[dict[str, str]], bool],
    ) -> list[QueryResult]:
        if isinstance(query, np.ndarray):
            query = query.tolist()
        return self._db.filtered_search(query, params, filter_fn)

    def search_by_metadata(
        self,
        query: list[float] | np.ndarray,
        params: SearchParams,
        metadata_key: str,
        metadata_value: str,
    ) -> list[QueryResult]:
        if isinstance(query, np.ndarray):
            query = query.tolist()
        return self._db.query_engine().search_with_metadata(
            query, params, metadata_key, metadata_value
        )

    def hybrid_search(
        self,
        query: list[float] | np.ndarray,
        params: SearchParams,
        text_query: str = "",
        vector_weight: float = 0.7,
        text_weight: float = 0.3,
    ) -> list[QueryResult]:
        if isinstance(query, np.ndarray):
            query = query.tolist()
        return self._db.query_engine().hybrid_search(
            query, params, text_query, vector_weight, text_weight
        )

    def build_index(self):
        self._db.build_index()

    def train_index(self, training_vectors: list[list[float]] | np.ndarray | None = None):
        if training_vectors is None:
            self._db.train_index()
        elif isinstance(training_vectors, np.ndarray):
            training_list = [training_vectors[i].tolist() for i in range(training_vectors.shape[0])]
            self._db.train_index(training_list)
        else:
            self._db.train_index(training_vectors)

    def is_trained(self) -> bool:
        return self._db.is_trained()

    def set_metadata(self, vector_id: int, metadata: dict[str, str]) -> bool:
        return self._db.set_metadata(vector_id, metadata)

    def get_metadata(self, vector_id: int) -> dict[str, str] | None:
        return self._db.get_metadata(vector_id)

    def find_by_metadata(self, key: str, value: str) -> list[int]:
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

    def get_search_stats(self) -> dict[str, Any]:
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
