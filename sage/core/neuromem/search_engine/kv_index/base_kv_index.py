# file: sage/core/neuromem/search_engine/kv_index/base_kv_index.py

from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseKVIndex(ABC):
    def __init__(self, name: str, data: Dict[str, Any]):
        """
        创建静态KV索引
        :param name: 索引名称
        :param data: {id: 文本或结构化内容} 的字典
        """
        self.name = name
        self._build(data)

    @abstractmethod
    def _build(self, data: Dict[str, Any]):
        """构建索引的内部方法，由 __init__ 自动调用"""
        pass

    @abstractmethod
    def insert(self, key: str, value: Any) -> None:
        """插入单条记录到索引"""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """从索引中删除记录"""
        pass

    @abstractmethod
    def search(self, query: str, topk: int = 10) -> List[str]:
        """执行基于查询的检索，返回匹配的 id 列表"""
        pass

    @abstractmethod
    def update(self, key: str, new_value: Any) -> None:
        """更新索引中已存在记录"""
        pass

