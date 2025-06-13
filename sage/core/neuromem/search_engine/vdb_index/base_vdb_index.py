# file sage/core/neuromem/search_engine/vdb_index/base_vdb_index.py

from abc import ABC, abstractmethod
from typing import List, Tuple
import numpy as np

class BaseKVIndex(ABC):
    def __init__(self, name: str, dim: int):
        """
        基础索引类初始化
        :param name: 索引名称
        :param dim: 向量维度
        """
        self.name = name
        self.dim = dim

    @abstractmethod
    def insert(self, vector: np.ndarray, string_id: str) -> None:
        """插入单个向量"""
        pass

    @abstractmethod
    def batch_insert(self, vectors: List[np.ndarray], string_ids: List[str]) -> None:
        """批量插入向量"""
        pass

    @abstractmethod
    def delete(self, string_id: str) -> None:
        """删除一个向量（物理或逻辑）"""
        pass

    @abstractmethod
    def update(self, string_id: str, new_vector: np.ndarray) -> None:
        """更新向量内容"""
        pass

    @abstractmethod
    def search(self, query_vector: np.ndarray, topk: int = 10) -> Tuple[List[str], List[float]]:
        """向量检索，返回 (string_id, 距离) 列表"""
        pass
