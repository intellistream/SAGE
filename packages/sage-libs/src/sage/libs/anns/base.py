"""
Base Algorithm Classes

合并了 streaming 和 congestion 的功能，提供统一的算法基类
"""

from typing import Optional

import numpy as np
import numpy.typing as npt


class BaseANN:
    """
    所有 ANN 算法的基类
    """

    def __init__(self, metric: str = "euclidean"):
        """
        Args:
            metric: 距离度量 ("euclidean", "angular", "ip")
        """
        self.metric = metric
        self.name = self.__class__.__name__

    def track(self) -> str:
        """
        返回算法类型: "traditional" 或 "stream"
        """
        return "traditional"

    def fit(self, X: np.ndarray) -> None:
        """
        在数据集上训练索引（用于传统算法）

        Args:
            X: (n, d) 训练数据
        """
        raise NotImplementedError

    def query(self, X: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
        """
        查询最近邻

        Args:
            X: (nq, d) 查询向量
            k: 返回的最近邻数量

        Returns:
            (I, D): I 是索引 (nq, k), D 是距离 (nq, k)
        """
        raise NotImplementedError

    def batch_query(self, X: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
        """
        批量查询（默认实现调用 query）

        Args:
            X: (nq, d) 查询向量
            k: 返回的最近邻数量

        Returns:
            (I, D): I 是索引 (nq, k), D 是距离 (nq, k)
        """
        return self.query(X, k)

    def get_memory_usage(self) -> float:
        """
        返回内存使用量（MB）
        """
        return 0.0

    def __str__(self) -> str:
        return f"{self.name}(metric={self.metric})"


class BaseStreamingANN(BaseANN):
    """
    流式 ANN 算法的基类

    合并了原来的 BaseStreamingANN 和 Congestion 功能
    支持动态插入、删除和查询
    """

    def track(self) -> str:
        """
        返回算法类型
        """
        return "stream"

    def setup(self, dtype: str, max_pts: int, ndims: int) -> None:
        """
        初始化数据结构

        Args:
            dtype: 数据类型 ('uint8', 'int8', 'float32')
            max_pts: 索引必须支持的最大非删除点数上界
            ndims: 向量维度
        """
        raise NotImplementedError

    def insert(self, X: np.ndarray, ids: npt.NDArray[np.uint32]) -> None:
        """
        插入向量

        Args:
            X: (num_vectors, ndims) 向量矩阵
            ids: (num_vectors,) 向量 ID 数组
        """
        raise NotImplementedError

    def delete(self, ids: npt.NDArray[np.uint32]) -> None:
        """
        删除向量

        Args:
            ids: 要删除的向量 ID 数组
        """
        raise NotImplementedError

    def batch_search(
        self, X: np.ndarray, k: int, timestamps: Optional[np.ndarray] = None
    ) -> tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
        """
        批量搜索（支持时间戳）

        Args:
            X: (nq, d) 查询向量
            k: 返回的最近邻数量
            timestamps: (nq,) 查询时间戳（可选）

        Returns:
            (indices, distances, timestamps_out):
                indices: 索引 (nq, k)
                distances: 距离 (nq, k)
                timestamps_out: 处理时间戳 (nq,) - 如果提供了 timestamps
        """
        indices, distances = self.query(X, k)

        if timestamps is not None:
            # 如果提供了时间戳，返回当前时间作为处理时间
            import time

            T = np.full(len(X), int(time.time() * 1e6), dtype=np.int64)
            return indices, distances, T

        return indices, distances, None

    def fit(self, dataset) -> None:
        """
        不适用于流式索引，不要覆盖此方法
        """
        raise NotImplementedError("fit() does not apply to streaming indices")

    def load_index(self, dataset) -> bool:
        """
        不适用于流式索引
        """
        return False

    def get_index_components(self, dataset):
        """
        不适用于流式索引
        """
        raise NotImplementedError("get_index_components() does not apply to streaming indices")

    def index_files_to_store(self, dataset):
        """
        不适用于流式索引
        """
        raise NotImplementedError("index_files_to_store() does not apply to streaming indices")

    def supports_delete(self) -> bool:
        """
        返回算法是否支持删除操作
        """
        return True

    def supports_insert(self) -> bool:
        """
        返回算法是否支持插入操作
        """
        return True

    def initial_load(self, X: np.ndarray, ids: npt.NDArray[np.uint32]) -> None:
        """
        初始加载数据（默认实现调用 insert）

        Args:
            X: (num_vectors, ndims) 向量矩阵
            ids: (num_vectors,) 向量 ID 数组
        """
        self.insert(X, ids)

    def replace(self, X: np.ndarray, ids: npt.NDArray[np.uint32]) -> None:
        """
        替换向量（默认实现为先删除再插入）

        Args:
            X: (num_vectors, ndims) 新向量矩阵
            ids: (num_vectors,) 要替换的向量 ID 数组
        """
        self.delete(ids)
        self.insert(X, ids)

    def get_results(self) -> Optional[np.ndarray]:
        """
        获取最后一次查询的结果
        某些算法需要异步获取结果

        Returns:
            结果数组或 None
        """
        return None

    def get_additional(self) -> dict:
        """
        获取算法的额外信息

        Returns:
            额外信息字典
        """
        return {}

    def wait_pending_operations(self) -> None:
        """
        等待待处理操作完成
        """
        pass

    def reset_state(self, dtype: str, max_pts: int, ndims: int) -> None:
        """
        重置算法状态（用于重建）
        默认实现调用 setup

        Args:
            dtype: 数据类型
            max_pts: 最大点数
            ndims: 向量维度
        """
        self.setup(dtype, max_pts, ndims)

    def get_drop_count_delta(self) -> int:
        """
        获取自上次调用以来的丢弃数量

        Returns:
            丢弃数量
        """
        return 0

    def get_pending_queue_len(self) -> int:
        """
        获取待处理队列长度

        Returns:
            队列长度
        """
        return 0

    def enable_scenario(
        self,
        random_contamination: bool = False,
        random_contamination_prob: float = 0.0,
        random_drop: bool = False,
        random_drop_prob: float = 0.0,
        out_of_order: bool = False,
    ) -> None:
        """
        启用测试场景

        Args:
            random_contamination: 随机污染数据
            random_contamination_prob: 污染概率
            random_drop: 随机丢弃数据
            random_drop_prob: 丢弃概率
            out_of_order: 乱序摄入
        """
        pass

    def set_backpressure_logic(self, use_backpressure: bool = True) -> None:
        """
        设置背压逻辑

        Args:
            use_backpressure: 是否使用背压逻辑
        """
        pass


class DummyStreamingANN(BaseStreamingANN):
    """
    一个简单的流式算法实现（用于测试）
    使用暴力搜索
    """

    def __init__(self, metric: str = "euclidean"):
        super().__init__(metric)
        self.vectors = []
        self.ids = []
        self.max_pts = 0
        self.ndims = 0
        self.dtype_str = "float32"

    def setup(self, dtype: str, max_pts: int, ndims: int) -> None:
        self.max_pts = max_pts
        self.ndims = ndims
        self.dtype_str = dtype
        self.vectors = []
        self.ids = []

    def insert(self, X: np.ndarray, ids: npt.NDArray[np.uint32]) -> None:
        for i, vec in enumerate(X):
            if ids[i] not in self.ids:
                self.vectors.append(vec)
                self.ids.append(ids[i])

    def delete(self, ids: npt.NDArray[np.uint32]) -> None:
        ids_to_delete = set(ids)
        new_vectors = []
        new_ids = []

        for i, vec_id in enumerate(self.ids):
            if vec_id not in ids_to_delete:
                new_vectors.append(self.vectors[i])
                new_ids.append(vec_id)

        self.vectors = new_vectors
        self.ids = new_ids

    def query(self, X: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
        if len(self.vectors) == 0:
            # 返回空结果
            return (
                np.full((len(X), k), -1, dtype=np.int32),
                np.full((len(X), k), np.inf, dtype=np.float32),
            )

        data = np.array(self.vectors)
        ids_array = np.array(self.ids)

        # 计算距离
        if self.metric == "euclidean":
            # (nq, n) 距离矩阵
            distances = np.linalg.norm(data[np.newaxis, :, :] - X[:, np.newaxis, :], axis=2)
        elif self.metric == "ip":
            distances = -np.dot(X, data.T)
        else:
            distances = np.linalg.norm(data[np.newaxis, :, :] - X[:, np.newaxis, :], axis=2)

        # 找到最近的 k 个
        k_actual = min(k, len(data))
        indices = np.argsort(distances, axis=1)[:, :k_actual]

        # 转换为实际 ID
        neighbor_ids = ids_array[indices]
        neighbor_distances = np.take_along_axis(distances, indices, axis=1)

        # 如果 k 大于实际数量，填充
        if k > k_actual:
            I_padded = np.full((len(X), k), -1, dtype=np.int32)
            D_padded = np.full((len(X), k), np.inf, dtype=np.float32)
            I_padded[:, :k_actual] = neighbor_ids
            D_padded[:, :k_actual] = neighbor_distances
            return I_padded, D_padded

        return neighbor_ids, neighbor_distances
