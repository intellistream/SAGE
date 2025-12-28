"""
Faiss HNSW Optimized Algorithm Implementation
使用 Gorder 图重排序优化的 HNSW 索引

基于 PyCANDYAlgo.IndexHNSWFlatOptimized 实现
支持 reorder_gorder(window) 进行图重排序优化
"""

import numpy as np

from ..base import BaseStreamingANN

try:
    import PyCANDYAlgo

    PYCANDY_AVAILABLE = True
except ImportError:
    PYCANDY_AVAILABLE = False


class FaissHnswOptimized(BaseStreamingANN):
    """
    Faiss HNSW Optimized 算法实现

    使用 IndexHNSWFlatOptimized 索引，支持 Gorder 图重排序优化

    Parameters:
        metric: 距离度量 ('euclidean' 或 'ip')
        index_params: 索引参数字典
            - indexkey: 索引类型 (如 'HNSWOptimized32')
            - efConstruction: 构建时的 ef 值 (暂未使用)
            - gorder_window: Gorder 窗口大小，默认 5
            - apply_gorder: 是否应用 Gorder 优化，默认 True
    """

    def __init__(self, metric, index_params):
        self.indexkey = index_params.get("indexkey", "HNSWOptimized32")
        self.efConstruction = index_params.get("efConstruction", 40)
        self.gorder_window = index_params.get("gorder_window", 5)  # Gorder 窗口大小
        self.apply_gorder = index_params.get("apply_gorder", True)  # 是否应用 Gorder
        self.metric = metric
        self.name = "faiss_HNSW_Optimized"
        self.ef = 16
        self.trained = False
        self.index = None
        self.ntotal = 0

        # ID 映射：faiss 内部 ID <-> 外部 ID
        self.my_index = None  # my_index[internal_id] = external_id
        self.my_inverse_index = None  # my_inverse_index[external_id] = internal_id

    def setup(self, dtype, max_pts, ndim):
        """
        初始化索引

        Args:
            dtype: 数据类型
            max_pts: 最大点数
            ndim: 向量维度
        """
        if not PYCANDY_AVAILABLE:
            raise RuntimeError("PyCANDYAlgo not available. Please run deploy.sh to build it.")

        # 使用 PyCANDYAlgo 的 index_factory 创建 IndexHNSWFlatOptimized 索引
        if self.metric == "euclidean":
            self.index = PyCANDYAlgo.index_factory_l2(ndim, self.indexkey)
        else:
            self.index = PyCANDYAlgo.index_factory_ip(ndim, self.indexkey)

        # 初始化 ID 映射表
        self.my_index = -1 * np.ones(max_pts, dtype=np.int64)
        self.my_inverse_index = -1 * np.ones(max_pts, dtype=np.int64)

        self.ndim = ndim
        self.ntotal = 0
        self.trained = False

    def insert(self, X, ids):
        """
        插入向量

        Args:
            X: 向量数据 (n, d)
            ids: 外部 ID 数组
        """
        X = np.ascontiguousarray(X, dtype=np.float32)

        # 过滤已存在的 ID（避免重复插入）
        mask = self.my_inverse_index[ids] == -1
        new_ids = ids[mask]
        new_data = X[mask]

        if new_data.shape[0] == 0:
            print("Not Inserting Same Data!")
            return

        # 训练索引（首次插入时，对于 Flat 存储这是 no-op）
        if not self.trained:
            self.index.train(new_data.shape[0], new_data.flatten())
            self.trained = True

        # 添加向量到索引
        self.index.add(new_data.shape[0], new_data.flatten())

        # 更新 ID 映射
        indices = np.arange(self.ntotal, self.ntotal + new_data.shape[0])
        self.my_index[indices] = new_ids
        self.my_inverse_index[new_ids] = indices
        self.ntotal += new_data.shape[0]

        print(f"Faiss indices {indices[0]}:{indices[-1]} to Global {new_ids[0]}:{new_ids[-1]}")

    def delete(self, ids):
        """
        删除向量（仅从映射表移除，HNSW 不支持真正删除）

        Args:
            ids: 要删除的外部 ID 数组
        """
        for ext_id in ids:
            ext_id = int(ext_id)
            if ext_id < len(self.my_inverse_index):
                internal_id = self.my_inverse_index[ext_id]
                if internal_id != -1:
                    self.my_inverse_index[ext_id] = -1
                    if internal_id < len(self.my_index):
                        self.my_index[internal_id] = -1

    def offline_build(self):
        """
        在所有数据插入完成后调用，应用 Gorder 优化

        Gorder 算法通过图重排序优化缓存局部性，提高搜索性能
        """
        if self.apply_gorder and hasattr(self.index, "reorder_gorder"):
            print(f"Applying Gorder reordering with window={self.gorder_window}...")
            self.index.reorder_gorder(self.gorder_window)
            print("Gorder optimization completed!")
        elif self.apply_gorder:
            print("Warning: reorder_gorder method not available on this index")

    def query(self, X, k):
        """
        查询最近邻

        Args:
            X: 查询向量 (nq, d)
            k: 返回的最近邻数量

        Returns:
            (ids, distances): 最近邻 ID 和距离
        """
        X = np.ascontiguousarray(X, dtype=np.float32)
        nq = X.shape[0]

        # 调用 IndexHNSWFlatOptimized.search(n, x, k, ef_search)
        # 返回 list[int]，长度为 nq * k
        results = self.index.search(nq, X.flatten(), k, self.ef)

        # 转换为 numpy array 并 reshape
        results_np = np.array(results, dtype=np.int64)

        # 将 faiss 内部 ID 映射回外部 ID
        # 处理无效结果（-1）
        valid_mask = (results_np >= 0) & (results_np < len(self.my_index))
        ids = np.full_like(results_np, -1)
        ids[valid_mask] = self.my_index[results_np[valid_mask]]

        res = ids.reshape(nq, k)
        self.res = res
        return res, None  # 返回 (ids, distances)，distances 暂时为 None

    def set_query_arguments(self, query_args):
        """设置查询参数"""
        self.ef = query_args.get("ef", 16)

    def get_results(self):
        """获取最近一次查询结果"""
        return self.res

    def get_index_stats(self):
        """获取索引统计信息"""
        return {
            "name": self.name,
            "ntotal": self.ntotal,
            "index_ntotal": self.index.ntotal if self.index else 0,
            "metric": self.metric,
            "indexkey": self.indexkey,
            "gorder_window": self.gorder_window,
            "apply_gorder": self.apply_gorder,
            "ef": self.ef,
        }
