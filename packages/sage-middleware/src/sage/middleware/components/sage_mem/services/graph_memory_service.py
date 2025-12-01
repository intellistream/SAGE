"""Graph Memory Service - 基于图结构的记忆存储

支持两种模式:
1. knowledge_graph: 知识图谱模式 (参考 HippoRAG)
2. link_graph: 链接图模式 (参考 A-mem / Zettelkasten)

使用 GraphMemoryCollection 作为底层存储。
"""

from __future__ import annotations

import hashlib
import os
from typing import TYPE_CHECKING, Any, Literal

from sage.middleware.components.sage_mem.neuromem.memory_collection.graph_collection import (
    GraphMemoryCollection,
)
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager
from sage.platform.service import BaseService

if TYPE_CHECKING:
    import numpy as np


def compute_mdhash_id(content: str, prefix: str = "") -> str:
    """计算内容的 MD5 哈希 ID"""
    return prefix + hashlib.md5(content.encode()).hexdigest()[:16]


class GraphMemoryService(BaseService):
    """图结构记忆服务

    支持 knowledge_graph 和 link_graph 两种模式。
    底层使用 MemoryManager + GraphMemoryCollection 存储。
    """

    def __init__(
        self,
        collection_name: str = "graph_memory",
        graph_type: Literal["knowledge_graph", "link_graph"] = "knowledge_graph",
        index_name: str = "default",
        link_policy: Literal["bidirectional", "directed"] = "bidirectional",
        max_links_per_node: int = 50,
        link_weight_init: float = 1.0,
    ):
        """初始化图记忆服务

        Args:
            collection_name: NeuroMem collection 名称
            graph_type: 图类型 ("knowledge_graph" | "link_graph")
            index_name: 图索引名称
            link_policy: 链接策略 ("bidirectional" | "directed")
            max_links_per_node: 每个节点最大链接数
            link_weight_init: 链接初始权重
        """
        super().__init__()

        self.collection_name = collection_name
        self.graph_type = graph_type
        self.index_name = index_name
        self.link_policy = link_policy
        self.max_links_per_node = max_links_per_node
        self.link_weight_init = link_weight_init

        # 初始化 MemoryManager
        self.manager = MemoryManager(self._get_default_data_dir())

        # 创建或获取 GraphMemoryCollection
        if self.manager.has_collection(collection_name):
            collection = self.manager.get_collection(collection_name)
            if not isinstance(collection, GraphMemoryCollection):
                raise TypeError(f"Collection '{collection_name}' is not a GraphMemoryCollection")
            self.collection = collection
        else:
            self.collection = self.manager.create_collection(
                {
                    "name": collection_name,
                    "backend_type": "graph",
                    "description": f"Graph memory collection ({graph_type})",
                }
            )

        # 确保有默认索引
        if isinstance(self.collection, GraphMemoryCollection):
            if index_name not in self.collection.indexes:
                self.collection.create_index({"name": index_name})

        self.logger.info(
            f"GraphMemoryService initialized: collection={collection_name}, "
            f"graph_type={graph_type}, index={index_name}"
        )

    @classmethod
    def _get_default_data_dir(cls) -> str:
        """获取默认数据目录"""
        cur_dir = os.getcwd()
        data_dir = os.path.join(cur_dir, "data", "graph_memory")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir

    def insert(
        self,
        entry: str,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict | None = None,
        *,
        insert_mode: Literal["active", "passive"] = "passive",
        insert_params: dict | None = None,
    ) -> str:
        """插入记忆条目（节点）

        支持两种插入模式：
        - passive: 由服务自行决定存储方式（默认行为）
        - active: 根据 insert_params 指定存储方式

        Args:
            entry: 文本内容
            vector: embedding 向量（可选，用于语义链接）
            metadata: 元数据，可包含:
                - node_type: 节点类型 ("entity" | "fact" | "passage")
                - triples: 三元组列表 [(subject, relation, object), ...]
                - links: 链接目标节点 ID 列表
                - keywords: 关键词列表
            insert_mode: 插入模式 ("active" | "passive")
            insert_params: 主动插入参数
                - node_type: 节点类型 (覆盖 metadata)
                - create_edges: 是否自动创建边
                - priority: 优先级

        Returns:
            str: 节点 ID
        """
        metadata = metadata or {}

        # 处理插入模式
        if insert_mode == "active" and insert_params:
            # 主动插入：从 insert_params 获取参数
            if "node_type" in insert_params:
                metadata["node_type"] = insert_params["node_type"]
            if "priority" in insert_params:
                metadata["priority"] = insert_params["priority"]
            create_edges = insert_params.get("create_edges", True)
        else:
            # 被动插入：使用默认行为
            create_edges = True

        # 生成节点 ID
        node_id = metadata.get("node_id") or compute_mdhash_id(entry, prefix="node_")

        # 添加节点到图
        self.collection.add_node(
            node_id=node_id,
            text=entry,
            metadata=metadata,
            index_name=self.index_name,
        )

        # 处理三元组（知识图谱模式，仅在 create_edges=True 时）
        if create_edges and self.graph_type == "knowledge_graph" and "triples" in metadata:
            for triple in metadata["triples"]:
                if len(triple) >= 2:
                    # triple 格式: (subject, object) 或 (subject, relation, object)
                    obj = triple[1] if len(triple) == 2 else triple[2]
                    # 创建关系边
                    self._add_link(node_id, obj, weight=self.link_weight_init)

        # 处理显式链接（仅在 create_edges=True 时）
        if create_edges and "links" in metadata:
            for target_id in metadata["links"]:
                self._add_link(node_id, target_id, weight=self.link_weight_init)

        self.logger.debug(f"Inserted node {node_id} to graph")
        return node_id

    def _add_link(self, from_node: str, to_node: str, weight: float = 1.0) -> None:
        """添加链接（边）"""
        self.collection.add_edge(
            from_node=from_node,
            to_node=to_node,
            weight=weight,
            index_name=self.index_name,
        )

        # 双向链接
        if self.link_policy == "bidirectional":
            self.collection.add_edge(
                from_node=to_node,
                to_node=from_node,
                weight=weight,
                index_name=self.index_name,
            )

    def retrieve(
        self,
        query: str | None = None,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """检索记忆

        Args:
            query: 查询文本（作为起始节点 ID 或用于查找起始节点）
            vector: 查询向量（可选）
            metadata: 检索参数:
                - start_node: 起始节点 ID
                - max_depth: 最大遍历深度 (默认 2)
                - method: 检索方法 ("bfs" | "neighbors")
            top_k: 返回结果数量

        Returns:
            list[dict]: 检索结果
        """
        metadata = metadata or {}
        start_node = metadata.get("start_node") or query
        max_depth = metadata.get("max_depth", 2)
        method = metadata.get("method", "bfs")

        if not start_node:
            self.logger.warning("No start_node provided for graph retrieval")
            return []

        if method == "neighbors":
            # 只获取直接邻居
            results = self.collection.get_neighbors(
                node_id=start_node,
                k=top_k,
                index_name=self.index_name,
            )
        else:
            # BFS 遍历
            results = self.collection.retrieve_by_graph(
                start_node=start_node,
                max_depth=max_depth,
                max_nodes=top_k,
                index_name=self.index_name,
            )

        # 转换为统一格式
        formatted_results = []
        for item in results:
            formatted_results.append(
                {
                    "text": item.get("data", ""),
                    "node_id": item.get("node_id", ""),
                    "depth": item.get("depth", 0),
                    "score": 1.0 / (1 + item.get("depth", 0)),  # 深度越小分数越高
                    "metadata": {},
                }
            )

        return formatted_results

    def delete(self, entry_id: str) -> bool:
        """删除节点

        Args:
            entry_id: 节点 ID

        Returns:
            bool: 是否删除成功
        """
        if self.index_name not in self.collection.indexes:
            return False

        index = self.collection.indexes[self.index_name]
        if not index.has_node(entry_id):
            return False

        index.remove_node(entry_id)
        self.logger.debug(f"Deleted node {entry_id} from graph")
        return True

    def add_edge(
        self,
        from_node: str,
        to_node: str,
        weight: float = 1.0,
        edge_type: str = "relation",
    ) -> bool:
        """添加边

        Args:
            from_node: 源节点 ID
            to_node: 目标节点 ID
            weight: 边权重
            edge_type: 边类型

        Returns:
            bool: 是否成功
        """
        self._add_link(from_node, to_node, weight)
        return True

    def optimize(self, trigger: str = "auto") -> dict[str, Any]:
        """优化图结构

        Args:
            trigger: 触发类型 ("auto" | "manual" | "decay" | "strengthen")

        Returns:
            dict: 优化统计信息
        """
        if self.index_name not in self.collection.indexes:
            return {"success": False, "message": "Index not found"}

        index = self.collection.indexes[self.index_name]
        stats = {
            "success": True,
            "trigger": trigger,
            "nodes_count": len(index.nodes),
            "edges_count": sum(len(edges) for edges in index.adjacency.values()),
        }

        # TODO: 实现具体的优化逻辑（如边权重衰减、剪枝等）
        self.logger.info(f"Graph optimization triggered: {trigger}")
        return stats

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        if self.index_name not in self.collection.indexes:
            return {
                "memory_count": 0,
                "edges_count": 0,
                "graph_type": self.graph_type,
                "collection_name": self.collection_name,
            }

        index = self.collection.indexes[self.index_name]
        return {
            "memory_count": len(index.nodes),
            "edges_count": sum(len(edges) for edges in index.adjacency.values()),
            "graph_type": self.graph_type,
            "collection_name": self.collection_name,
            "index_name": self.index_name,
        }
