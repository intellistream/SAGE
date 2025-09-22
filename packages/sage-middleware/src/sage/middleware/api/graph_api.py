"""
Graph Service API Interface
图数据库服务的API接口定义
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class GraphServiceAPI(ABC):
    """Graph服务API接口"""

    @abstractmethod
    def add_node(
        self, node_id: str, node_type: str, properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """添加节点"""
        pass

    @abstractmethod
    def add_edge(
        self,
        from_node: str,
        to_node: str,
        edge_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """添加边"""
        pass

    @abstractmethod
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """获取节点"""
        pass

    @abstractmethod
    def get_neighbors(
        self, node_id: str, edge_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取邻居节点"""
        pass

    @abstractmethod
    def find_path(
        self, start_node: str, end_node: str, max_depth: int = 3
    ) -> Optional[List[Dict[str, Any]]]:
        """查找路径"""
        pass

    @abstractmethod
    def delete_node(self, node_id: str) -> bool:
        """删除节点"""
        pass

    @abstractmethod
    def delete_edge(self, from_node: str, to_node: str, edge_type: str) -> bool:
        """删除边"""
        pass

    @abstractmethod
    def query_nodes(
        self,
        node_type: Optional[str] = None,
        properties_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """查询节点"""
        pass
