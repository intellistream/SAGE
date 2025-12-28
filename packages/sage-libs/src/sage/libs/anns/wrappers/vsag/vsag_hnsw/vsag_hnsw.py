"""VSAG HNSW streaming integration for SAGE benchmarks."""

# Todo: VSAG的查询似乎只支持单向量查询
from __future__ import annotations

import copy
import json
from typing import Any, Optional

import numpy as np

from ..base import BaseStreamingANN


def _import_pyvsag():
    try:
        import pyvsag  # type: ignore
    except ImportError as exc:  # pragma: no cover - runtime guard
        raise RuntimeError(
            "pyvsag is not available. Please build VSAG python bindings before using vsag_hnsw."
        ) from exc
    return pyvsag


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


class VsagIndexWrapper:
    """Lightweight helper around pyvsag.Index with streaming semantics."""

    _METRIC_MAP = {
        "euclidean": "l2",
        "ip": "ip",
        "angular": "cosine",
    }

    def __init__(self, metric: str, index_params: Optional[dict[str, Any]] = None):
        raw = copy.deepcopy(index_params or {})
        self.index_name = raw.pop("index_name", "hnsw")
        self._search_params_template: dict[str, Any] = raw.pop("search_params", {})
        base_payload = raw.pop("index_config", None)
        if base_payload is None:
            base_payload = raw
        self._index_payload_template: dict[str, Any] = base_payload or {}

        # 判断是否为 hgraph 索引
        self._is_hgraph = self.index_name == "hgraph"

        self.metric = metric
        self.dim: Optional[int] = None
        self.dtype: Optional[str] = None
        self.max_pts: Optional[int] = None

        self._pyvsag = None
        self._index = None
        self._is_built = False
        self._last_results: Optional[np.ndarray] = None
        self._search_params_json = json.dumps(self._effective_search_params({}))

    @property
    def index(self):
        if self._index is None:
            raise RuntimeError("VSAG index is not initialized. Call setup() first.")
        return self._index

    def setup(self, dtype: str, max_pts: int, ndims: int) -> None:
        self.dtype = dtype
        self.max_pts = max_pts
        self.dim = ndims
        self._pyvsag = _import_pyvsag()
        params = self._build_index_params()
        params_json = json.dumps(params)
        self._index = self._pyvsag.Index(self.index_name, params_json)
        self._is_built = False
        self._last_results = None
        self._search_params_json = json.dumps(
            self._effective_search_params(self._search_params_template)
        )

    def insert(self, vectors: np.ndarray, ids: np.ndarray) -> None:
        dense = self._prepare_dense_vectors(vectors)
        id_array = self._prepare_ids(ids, dense.shape[0])
        if dense.size == 0:
            return
        if not self._is_built:
            self.index.build(vectors=dense, ids=id_array, num_elements=dense.shape[0], dim=self.dim)
            self._is_built = True
        else:
            self.index.add(vectors=dense, ids=id_array, num_elements=dense.shape[0], dim=self.dim)

    def delete(self, ids: np.ndarray) -> None:
        if ids.size == 0:
            return
        id_array = self._prepare_ids(ids, ids.size)
        self.index.remove(id_array)

    def query(self, queries: np.ndarray, k: int):
        dense_queries = self._prepare_dense_vectors(queries)
        num_queries = dense_queries.shape[0]

        # pyvsag的knn_search每次只能查询一个向量，需要循环处理
        all_ids = []
        all_dists = []

        for i in range(num_queries):
            query_vec = dense_queries[i]
            ids, dists = self.index.knn_search(query_vec, k, self._search_params_json)
            all_ids.append(ids)
            all_dists.append(dists)

        ids_np = np.array(all_ids, dtype=np.int64)
        dists_np = np.array(all_dists, dtype=np.float32)

        # 确保输出形状正确
        if ids_np.ndim == 1:
            ids_np = ids_np.reshape(1, -1)
            dists_np = dists_np.reshape(1, -1)

        self._last_results = ids_np
        self.res = ids_np  # 兼容 worker.py 的直接属性访问
        return ids_np, dists_np

    def update_search_params(self, overrides: Optional[dict[str, Any]]) -> None:
        if overrides:
            self._search_params_template = _deep_merge(
                copy.deepcopy(self._search_params_template) or {},
                overrides,
            )
        self._search_params_json = json.dumps(
            self._effective_search_params(self._search_params_template)
        )

    def get_last_results(self) -> Optional[np.ndarray]:
        return self._last_results

    def _build_index_params(self) -> dict[str, Any]:
        if self.dim is None:
            raise RuntimeError("setup() must be called before building index parameters")
        payload = copy.deepcopy(self._index_payload_template)

        if self._is_hgraph:
            # hgraph 参数结构: {"dtype", "metric_type", "dim", "index_param": {...}}
            payload["dim"] = self.dim
            payload["metric_type"] = self._metric_to_vsag(self.metric)
            payload.setdefault("dtype", self._dtype_to_vsag(self.dtype))
            # 确保 index_param 存在并设置必要的默认值
            if "index_param" not in payload:
                payload["index_param"] = {}
            # base_quantization_type 是必需的
            payload["index_param"].setdefault("base_quantization_type", "fp32")
            if self.max_pts is not None:
                payload["index_param"].setdefault("hgraph_init_capacity", self.max_pts)
        else:
            # hnsw 参数结构: {"dtype", "metric_type", "dim", "hnsw": {...}}
            payload["dim"] = self.dim
            payload["metric_type"] = self._metric_to_vsag(self.metric)
            payload.setdefault("dtype", self._dtype_to_vsag(self.dtype))
            if self.max_pts is not None:
                payload.setdefault("max_elements", self.max_pts)
        return payload

    def _prepare_dense_vectors(self, vectors: np.ndarray) -> np.ndarray:
        if self.dim is None:
            raise RuntimeError("setup() must be called before inserting/querying data")
        arr = np.asarray(vectors, dtype=np.float32)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        if arr.shape[1] != self.dim:
            raise ValueError(f"Vector dimension {arr.shape[1]} does not match index dim {self.dim}")
        return np.ascontiguousarray(arr, dtype=np.float32)

    @staticmethod
    def _prepare_ids(ids: np.ndarray, expected: int) -> np.ndarray:
        arr = np.asarray(ids, dtype=np.int64).reshape(-1)
        if arr.size != expected:
            raise ValueError(f"Expected {expected} ids, got {arr.size}")
        return np.ascontiguousarray(arr, dtype=np.int64)

    def _effective_search_params(self, overrides: dict[str, Any]) -> dict[str, Any]:
        # 根据索引类型选择默认搜索参数
        if self._is_hgraph:
            defaults = {"hgraph": {"ef_search": 64}}
        else:
            defaults = {"hnsw": {"ef_search": 64}}
        return _deep_merge(defaults, overrides or {})

    def _metric_to_vsag(self, metric: str) -> str:
        try:
            return self._METRIC_MAP[metric]
        except KeyError as exc:  # pragma: no cover - defensive
            raise ValueError(f"Unsupported metric '{metric}' for VSAG HNSW") from exc

    @staticmethod
    def _dtype_to_vsag(dtype: Optional[str]) -> str:
        if dtype in ("int8", "sparse"):
            return dtype
        return "float32"


class VsagHnsw(BaseStreamingANN):
    """BaseStreamingANN adapter around the VSAG HNSW implementation."""

    def __init__(self, metric: str = "euclidean", index_params: Optional[dict[str, Any]] = None):
        super().__init__(metric)
        self.name = "vsag_hnsw"
        self._wrapper = VsagIndexWrapper(metric, index_params)
        self.res = None  # 兼容 worker.py 的直接属性访问

    def setup(self, dtype: str, max_pts: int, ndims: int) -> None:
        self._wrapper.setup(dtype, max_pts, ndims)
        self.res = None

    def insert(self, X: np.ndarray, ids: np.ndarray) -> None:
        self._wrapper.insert(X, ids)

    def delete(self, ids: np.ndarray) -> None:
        self._wrapper.delete(ids)

    def query(self, X: np.ndarray, k: int):
        ids, dists = self._wrapper.query(X, k)
        self.res = ids  # 兼容 worker.py 的直接属性访问
        return ids, dists

    def set_query_arguments(self, query_args: dict[str, Any]) -> None:
        self._wrapper.update_search_params(query_args)

    def get_results(self) -> Optional[np.ndarray]:
        return self._wrapper.get_last_results()
