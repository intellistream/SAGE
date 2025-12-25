"""图记忆服务 - Hierarchical 类

基于图结构的记忆存储，支持节点、边的管理和 PPR 检索。

支持两种模式:
1. knowledge_graph: 知识图谱模式 (参考 HippoRAG)
2. link_graph: 链接图模式 (参考 A-mem / Zettelkasten)

设计原则:
- Service : Collection = 1 : 1
- 使用 GraphMemoryCollection 作为底层存储
- 支持 PPR (Personalized PageRank) 检索

论文算法实现:
- A-Mem: Link Generation (自动链接相似记忆)
- A-Mem: Memory Evolution (记忆演化更新)
- HippoRAG: Synonym Edge (同义词边建立)
- HippoRAG: PPR 检索优化
- HippoRAG2: 增强重排序 (enhanced_rerank)

Layer: L4 (Middleware)
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any, Literal

import numpy as np

from sage.common.config.output_paths import get_appropriate_sage_dir
from sage.kernel.runtime.factory.service_factory import ServiceFactory
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager

from ..base_service import BaseMemoryService

if TYPE_CHECKING:
    pass


def compute_mdhash_id(content: str, prefix: str = "") -> str:
    """计算内容的 MD5 哈希 ID"""
    return prefix + hashlib.md5(content.encode()).hexdigest()[:16]


class GraphMemoryService(BaseMemoryService):
    """图记忆服务 - Hierarchical 类

    基于图结构的记忆存储，支持节点/边操作和 PPR 检索。

    设计原则：
    - Service : Collection = 1 : 1
    - 使用 GraphMemoryCollection
    - 支持两种模式：knowledge_graph（HippoRAG）和 link_graph（A-Mem）
    """

    def __init__(
        self,
        collection_name: str = "graph_memory",
        graph_type: Literal["knowledge_graph", "link_graph"] = "knowledge_graph",
        index_name: str = "default",
        link_policy: Literal["bidirectional", "directed"] = "bidirectional",
        max_links_per_node: int = 50,
        link_weight_init: float = 1.0,
        node_embedding_dim: int = 768,
        edge_types: list[str] | None = None,
        synonymy_threshold: float = 0.8,
        damping: float = 0.5,
        ppr_depth: int = 2,
        ppr_damping: float = 0.85,
        enhanced_rerank: bool = False,
        retrieval_top_k: int = 20,
        num_start_nodes: int = 3,
        max_depth: int = 2,
    ):
        """初始化图记忆服务

        Args:
            collection_name: NeuroMem collection 名称
            graph_type: 图类型 ("knowledge_graph" | "link_graph")
            index_name: 图索引名称
            link_policy: 链接策略 ("bidirectional" | "directed")
            max_links_per_node: 每个节点最大链接数
            link_weight_init: 链接初始权重
            node_embedding_dim: 节点 embedding 维度
            edge_types: 支持的边类型列表
            synonymy_threshold: 同义词边的相似度阈值
            damping: PPR 阻尼系数（旧参数，保留兼容性）
            ppr_depth: PPR 迭代深度（HippoRAG=2, HippoRAG2=3）
            ppr_damping: PPR 阻尼系数（HippoRAG=0.85, HippoRAG2=0.9）
            enhanced_rerank: 是否启用增强重排序（HippoRAG2 特有）
            retrieval_top_k: 初始向量检索返回数量
            num_start_nodes: PPR 起始节点数量
            max_depth: 图遍历最大深度
        """
        super().__init__()

        self.collection_name = collection_name
        self.graph_type = graph_type
        self.index_name = index_name
        self.link_policy = link_policy
        self.max_links_per_node = max_links_per_node
        self.link_weight_init = link_weight_init
        self.node_embedding_dim = node_embedding_dim
        self.edge_types = edge_types
        self.synonymy_threshold = synonymy_threshold
        self.damping = damping

        # HippoRAG2 增强参数
        self.ppr_depth = ppr_depth
        self.ppr_damping = ppr_damping
        self.enhanced_rerank = enhanced_rerank
        self.retrieval_top_k = retrieval_top_k
        self.num_start_nodes = num_start_nodes
        self.max_depth = max_depth

        # 初始化 MemoryManager
        self.manager = MemoryManager(self._get_default_data_dir())

        # 创建或获取 GraphMemoryCollection
        self._init_collection()

        # 向量索引：用于通过向量相似度查找起始节点
        # 格式: {node_id: np.ndarray}
        self._vector_index: dict[str, np.ndarray] = {}

        # 被动插入状态管理（A-Mem 链接/HippoRAG 同义边）
        self._pending_node: dict | None = None
        self._pending_candidates: list[dict] = []
        self._pending_action: str | None = None  # "link" | "synonym" | None

        self.logger.info(
            f"GraphMemoryService initialized: collection={collection_name}, "
            f"graph_type={graph_type}, ppr_depth={ppr_depth}, enhanced_rerank={enhanced_rerank}"
        )

    @classmethod
    def from_config(cls, service_name: str, config: Any) -> ServiceFactory:
        """从配置创建 ServiceFactory

        配置示例:
            services:
              hierarchical.graph_memory:
                collection_name: graph_memory
                graph_type: knowledge_graph
                index_name: default
                link_policy: bidirectional
                max_links_per_node: 50
                node_embedding_dim: 768
                ppr_depth: 2
                ppr_damping: 0.85
                enhanced_rerank: false
                retrieval_top_k: 20
                num_start_nodes: 3
                max_depth: 2
        """
        # 读取配置
        collection_name = config.get(
            f"services.{service_name}.collection_name",
            f"graph_{service_name.replace('.', '_')}",
        )
        graph_type = config.get(f"services.{service_name}.graph_type", "knowledge_graph")
        index_name = config.get(f"services.{service_name}.index_name", "default")
        link_policy = config.get(f"services.{service_name}.link_policy", "bidirectional")
        max_links_per_node = config.get(f"services.{service_name}.max_links_per_node", 50)
        link_weight_init = config.get(f"services.{service_name}.link_weight_init", 1.0)
        node_embedding_dim = config.get(f"services.{service_name}.node_embedding_dim", 768)
        edge_types = config.get(f"services.{service_name}.edge_types")
        synonymy_threshold = config.get(f"services.{service_name}.synonymy_threshold", 0.8)
        damping = config.get(f"services.{service_name}.damping", 0.5)
        ppr_depth = config.get(f"services.{service_name}.ppr_depth", 2)
        ppr_damping = config.get(f"services.{service_name}.ppr_damping", 0.85)
        enhanced_rerank = config.get(f"services.{service_name}.enhanced_rerank", False)
        retrieval_top_k = config.get(f"services.{service_name}.retrieval_top_k", 20)
        num_start_nodes = config.get(f"services.{service_name}.num_start_nodes", 3)
        max_depth = config.get(f"services.{service_name}.max_depth", 2)

        return ServiceFactory(
            service_name=service_name,
            service_class=cls,
            service_kwargs={
                "collection_name": collection_name,
                "graph_type": graph_type,
                "index_name": index_name,
                "link_policy": link_policy,
                "max_links_per_node": max_links_per_node,
                "link_weight_init": link_weight_init,
                "node_embedding_dim": node_embedding_dim,
                "edge_types": edge_types,
                "synonymy_threshold": synonymy_threshold,
                "damping": damping,
                "ppr_depth": ppr_depth,
                "ppr_damping": ppr_damping,
                "enhanced_rerank": enhanced_rerank,
                "retrieval_top_k": retrieval_top_k,
                "num_start_nodes": num_start_nodes,
                "max_depth": max_depth,
            },
        )

    def _get_default_data_dir(self) -> str:
        """获取默认数据目录"""
        sage_dir = get_appropriate_sage_dir()
        data_dir = sage_dir / "data" / "graph_memory"
        data_dir.mkdir(parents=True, exist_ok=True)
        return str(data_dir)

    def _init_collection(self) -> None:
        """初始化 GraphMemoryCollection"""
        collection = None
        if self.manager.has_collection(self.collection_name):
            collection = self.manager.get_collection(self.collection_name)
            if collection is None:
                # Collection 元数据存在但磁盘数据丢失
                self.logger.warning(
                    f"Collection '{self.collection_name}' metadata exists but data is missing, "
                    "will recreate."
                )
                self.manager.delete_collection(self.collection_name)

        if collection is None:
            collection = self.manager.create_collection(
                {
                    "name": self.collection_name,
                    "backend_type": "graph",
                    "description": f"Graph memory collection ({self.graph_type})",
                }
            )

        self.collection = collection

        if self.collection is None:
            raise RuntimeError(f"Failed to create GraphMemoryCollection '{self.collection_name}'")

        # 确保有默认索引
        if self.index_name not in self.collection.indexes:
            self.collection.create_index({"name": self.index_name})

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

    def _find_similar_nodes(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """通过向量相似度查找节点"""
        if not self._vector_index:
            return []

        # 计算相似度
        similarities = []
        for node_id, node_vector in self._vector_index.items():
            # 余弦相似度
            sim = np.dot(query_vector, node_vector) / (
                np.linalg.norm(query_vector) * np.linalg.norm(node_vector) + 1e-8
            )
            if threshold is None or sim >= threshold:
                similarities.append({"node_id": node_id, "similarity": float(sim)})

        # 排序并返回 top_k
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        return similarities[:top_k]

    def insert(
        self,
        entry: str,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        *,
        insert_mode: Literal["active", "passive"] = "passive",
        insert_params: dict[str, Any] | None = None,
    ) -> str:
        """插入记忆条目（节点）

        Args:
            entry: 文本内容
            vector: embedding 向量（用于语义链接）
            metadata: 元数据，可包含:
                - node_type: 节点类型 ("entity" | "fact" | "passage")
                - triples: 三元组列表 [(subject, relation, object), ...]
                - links: 链接目标节点 ID 列表
                - keywords: 关键词列表
            insert_mode: 插入模式
                - "passive": 自动处理（默认）
                - "active": 显式控制（通过 insert_params）
            insert_params: 主动插入参数
                - node_type: 节点类型
                - create_edges: 是否自动创建边
                - priority: 优先级
        """
        # 转换 vector
        if isinstance(vector, list):
            vector = np.array(vector, dtype=np.float32)

        metadata = metadata or {}

        # 处理插入模式
        if insert_mode == "active" and insert_params:
            if "node_type" in insert_params:
                metadata["node_type"] = insert_params["node_type"]
            if "priority" in insert_params:
                metadata["priority"] = insert_params["priority"]
            create_edges = insert_params.get("create_edges", True)
        else:
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

        # 存储向量用于相似度检索
        if vector is not None:
            self._vector_index[node_id] = vector
            self.logger.debug(f"Stored vector for node {node_id}")

        # 处理三元组（知识图谱模式）
        if create_edges and self.graph_type == "knowledge_graph" and "triples" in metadata:
            for triple in metadata["triples"]:
                if len(triple) >= 2:
                    obj = triple[1] if len(triple) == 2 else triple[2]
                    self._add_link(node_id, obj, weight=self.link_weight_init)

        # 处理显式链接
        if create_edges and "links" in metadata:
            for target_id in metadata["links"]:
                self._add_link(node_id, target_id, weight=self.link_weight_init)

        # 被动插入模式：查找候选并更新状态
        if insert_mode == "passive" and vector is not None:
            self._update_pending_status(node_id, entry, vector, metadata)

        self.logger.debug(f"Inserted node {node_id} to graph")
        return node_id

    def _update_pending_status(
        self,
        node_id: str,
        entry: str,
        vector: np.ndarray,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """更新待处理状态（被动插入模式）"""
        # 查找相似节点作为候选
        candidates = self._find_similar_nodes(vector, top_k=10, threshold=0.5)
        # 过滤掉自己
        candidates = [c for c in candidates if c.get("node_id") != node_id]

        if not candidates:
            self.clear_pending_status()
            return

        # 设置待处理状态
        self._pending_node = {
            "node_id": node_id,
            "text": entry,
            "vector": vector.tolist() if isinstance(vector, np.ndarray) else list(vector),
            "metadata": metadata or {},
        }
        self._pending_candidates = candidates

        if self.graph_type == "link_graph":
            self._pending_action = "link"
        else:
            self._pending_action = "synonym"

        self.logger.debug(f"Pending {self._pending_action} status updated: node={node_id}")

    def get_status(self) -> dict[str, Any]:
        """查询服务状态（供 PostInsert 使用）"""
        return {
            "pending_action": self._pending_action,
            "pending_node": self._pending_node.copy() if self._pending_node else None,
            "pending_candidates": self._pending_candidates.copy(),
        }

    def clear_pending_status(self) -> None:
        """清除待处理状态"""
        self._pending_node = None
        self._pending_candidates = []
        self._pending_action = None

    def retrieve(
        self,
        query: str | None = None,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """检索记忆

        检索流程：
        1. 如果提供了 vector，使用向量相似度找到起始节点
        2. 从起始节点进行图遍历（BFS 或 PPR）
        3. 返回遍历结果

        Args:
            query: 查询文本（备用）
            vector: 查询向量（优先使用）
            metadata: 检索参数:
                - start_node: 起始节点 ID
                - max_depth: 最大遍历深度
                - method: 检索方法 ("bfs" | "neighbors" | "vector_only" | "ppr")
                - num_start_nodes: PPR 起始节点数量
            top_k: 返回结果数量
        """
        # 转换 vector
        if isinstance(vector, list):
            vector = np.array(vector, dtype=np.float32)

        metadata = metadata or {}
        start_node = metadata.get("start_node")
        max_depth = metadata.get("max_depth", self.max_depth)
        method = metadata.get("method", "bfs")
        num_start_nodes = metadata.get("num_start_nodes", self.num_start_nodes)

        # 如果没有指定起始节点，通过向量相似度查找
        if not start_node and vector is not None and self._vector_index:
            start_nodes = self._find_similar_nodes(vector, top_k=num_start_nodes)
            if start_nodes:
                start_node = start_nodes[0]["node_id"]
                self.logger.debug(f"Found start node via vector similarity: {start_node}")

        # 如果仍然没有起始节点，尝试文本匹配
        if not start_node and query:
            for node_id in self._vector_index.keys():
                text = self.collection.text_storage.get(node_id)
                if text and query.lower() in text.lower():
                    start_node = node_id
                    self.logger.debug(f"Found start node via text match: {start_node}")
                    break

        if not start_node:
            self.logger.warning("No start_node found for graph retrieval")
            # 回退到向量检索
            if vector is not None and self._vector_index:
                similar = self._find_similar_nodes(vector, top_k=top_k)
                return [
                    {
                        "text": self.collection.text_storage.get(s["node_id"], ""),
                        "metadata": self.collection.metadata_storage.get(s["node_id"], {}),
                        "score": s["similarity"],
                        "id": s["node_id"],
                    }
                    for s in similar
                ]
            return []

        # 仅向量检索
        if method == "vector_only" and vector is not None:
            similar = self._find_similar_nodes(vector, top_k=top_k)
            return [
                {
                    "text": self.collection.text_storage.get(s["node_id"], ""),
                    "metadata": self.collection.metadata_storage.get(s["node_id"], {}),
                    "score": s["similarity"],
                    "id": s["node_id"],
                }
                for s in similar
            ]

        # PPR 检索（HippoRAG/HippoRAG2）
        if method == "ppr" and vector is not None:
            start_nodes_list = self._find_similar_nodes(vector, top_k=num_start_nodes)
            seed_node_ids = [n["node_id"] for n in start_nodes_list]
            if seed_node_ids:
                # TODO: 实现 PPR 检索（需要 collection 支持）
                self.logger.warning("PPR retrieval not yet implemented, falling back to BFS")

        # BFS 遍历
        if method == "neighbors":
            results = self.collection.get_neighbors(
                node_id=start_node,
                k=top_k,
                index_name=self.index_name,
            )
        else:
            results = self.collection.retrieve_by_graph(
                start_node=start_node,
                max_depth=max_depth,
                max_nodes=top_k,
                index_name=self.index_name,
            )

        # 转换为统一格式
        return [
            {
                "text": r.get("text", ""),
                "metadata": r.get("metadata", {}),
                "score": r.get("distance", 0.0),
                "id": r.get("node_id", ""),
            }
            for r in results
        ]

    def delete(self, item_id: str) -> bool:
        """删除记忆（节点）"""
        try:
            # 删除节点（会自动删除相关的边）
            self.collection.delete(item_id)
            # 删除向量索引
            if item_id in self._vector_index:
                del self._vector_index[item_id]
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete node {item_id}: {e}")
            return False

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        node_count = len(self._vector_index)
        # TODO: 获取边的数量（需要 collection 支持）
        edge_count = 0

        return {
            "total_nodes": node_count,
            "total_edges": edge_count,
            "graph_type": self.graph_type,
            "collection_name": self.collection_name,
            "ppr_depth": self.ppr_depth,
            "enhanced_rerank": self.enhanced_rerank,
        }
