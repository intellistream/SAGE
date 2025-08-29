# file sage/core/sage.middleware.services.neuromem./search_engine/vdb_index/base_vdb_index.py

from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any
import numpy as np

class BaseVDBIndex(ABC):
    def __init__(self):
        """
        """

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
    
    @classmethod
    @abstractmethod
    def load(cls, name: str, root_path: str) -> "BaseVDBIndex":
        """
        加载索引实例。
        Load the index instance.
        """
        pass

    @abstractmethod
    def store(self, root_path: str) -> Dict[str, Any]:
        """
        存储索引数据到指定目录。
        Store the index data to the specified directory.
        """
        pass

