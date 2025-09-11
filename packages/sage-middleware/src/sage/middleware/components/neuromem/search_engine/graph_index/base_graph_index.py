from abc import ABC, abstractmethod
from typing import Any, List


class BaseGraphIndex(ABC):
    def __init__(self, name: str):
        """
        基础图索引类初始化
        :param name: 索引名称
        """
        self.name = name

    @abstractmethod
    def add_node(self, node_id: str, data: Any) -> None:
        """添加一个节点"""
        pass

    @abstractmethod
    def add_edge(self, from_node: str, to_node: str, weight: float = 1.0) -> None:
        """添加一条有向边"""
        pass

    @abstractmethod
    def remove_node(self, node_id: str) -> None:
        """删除一个节点及其相关边"""
        pass

    @abstractmethod
    def remove_edge(self, from_node: str, to_node: str) -> None:
        """删除一条边"""
        pass

    @abstractmethod
    def get_neighbors(self, node_id: str, k: int = 10) -> List[str]:
        """获取指定节点的前 k 个邻居节点"""
        pass

    @abstractmethod
    def has_node(self, node_id: str) -> bool:
        """判断节点是否存在"""
        pass
