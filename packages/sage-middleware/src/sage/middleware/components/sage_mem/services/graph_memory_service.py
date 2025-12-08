"""Graph Memory Service - 基于图结构的记忆存储

支持两种模式:
1. knowledge_graph: 知识图谱模式 (参考 HippoRAG)
2. link_graph: 链接图模式 (参考 A-mem / Zettelkasten)

设计原则:
- Service : Collection = 1 : 1
- 使用 GraphMemoryCollection 作为底层存储
- 支持 PPR (Personalized PageRank) 检索
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any, Literal

import numpy as np

from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager
from sage.platform.service import BaseService

if TYPE_CHECKING:
    from sage.middleware.components.sage_mem.neuromem.memory_collection.graph_collection import (
        SimpleGraphIndex,
    )


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
        node_embedding_dim: int = 768,
        edge_types: list[str] | None = None,
        synonymy_threshold: float = 0.8,
        damping: float = 0.5,
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
            damping: PPR 阻尼系数
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

        # 初始化 MemoryManager
        self.manager = MemoryManager(self._get_default_data_dir())

        # 创建或获取 GraphMemoryCollection
        # 注意：has_collection 可能返回 True，但 get_collection 返回 None（磁盘数据丢失）
        # 这种情况下需要删除旧记录并重新创建
        collection = None
        if self.manager.has_collection(collection_name):
            collection = self.manager.get_collection(collection_name)
            if collection is None:
                # Collection 元数据存在但磁盘数据丢失，需要清理并重建
                self.logger.warning(
                    f"Collection '{collection_name}' metadata exists but data is missing, "
                    "will recreate."
                )
                self.manager.delete_collection(collection_name)

        if collection is None:
            collection = self.manager.create_collection(
                {
                    "name": collection_name,
                    "backend_type": "graph",
                    "description": f"Graph memory collection ({graph_type})",
                }
            )

        self.collection = collection

        if self.collection is None:
            raise RuntimeError(f"Failed to create GraphMemoryCollection '{collection_name}'")

        # 确保有默认索引
        if index_name not in self.collection.indexes:
            self.collection.create_index({"name": index_name})

        # 向量索引：用于通过向量相似度查找起始节点
        # 格式: {node_id: np.ndarray}
        self._vector_index: dict[str, np.ndarray] = {}

        self.logger.info(
            f"GraphMemoryService initialized: collection={collection_name}, "
            f"graph_type={graph_type}, index={index_name}"
        )

    @classmethod
    def _get_default_data_dir(cls) -> str:
        """获取默认数据目录

        使用 SAGE 标准目录结构: .sage/data/graph_memory
        """
        from sage.common.config.output_paths import get_appropriate_sage_dir

        sage_dir = get_appropriate_sage_dir()
        data_dir = sage_dir / "data" / "graph_memory"
        data_dir.mkdir(parents=True, exist_ok=True)
        return str(data_dir)

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

        # 存储向量用于相似度检索
        if vector is not None:
            if isinstance(vector, list):
                vector = np.array(vector)
            self._vector_index[node_id] = vector
            self.logger.debug(
                f"Stored vector for node {node_id}, vector_index size: {len(self._vector_index)}"
            )
        else:
            self.logger.debug(f"No vector provided for node {node_id}")

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
        hints: dict | None = None,
        threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """检索记忆

        检索流程：
        1. 如果提供了 vector，使用向量相似度找到最相关的节点作为起始点
        2. 从起始节点进行图遍历（BFS 或邻居检索）
        3. 返回遍历结果

        Args:
            query: 查询文本（备用，用于文本匹配查找起始节点）
            vector: 查询向量（优先使用，用于相似度检索起始节点）
            metadata: 检索参数:
                - start_node: 起始节点 ID（直接指定，跳过向量检索）
                - max_depth: 最大遍历深度 (默认 2)
                - method: 检索方法 ("bfs" | "neighbors" | "vector_only")
                - num_start_nodes: 使用多少个起始节点（默认 3）
            top_k: 返回结果数量
            hints: 检索策略提示（可选，由 PreRetrieval route action 生成）
            threshold: 相似度阈值（可选，过滤低于阈值的结果）

        Returns:
            list[dict]: 检索结果
        """
        _ = hints  # 保留用于未来扩展
        metadata = metadata or {}
        start_node = metadata.get("start_node")
        max_depth = metadata.get("max_depth", 2)
        method = metadata.get("method", "bfs")
        num_start_nodes = metadata.get("num_start_nodes", 3)

        # 日志：检查向量索引状态
        self.logger.debug(
            f"retrieve called: vector={'provided' if vector is not None else 'None'}, "
            f"vector_index_size={len(self._vector_index)}, query={query[:50] if query else 'None'}..."
        )

        # 如果没有指定起始节点，尝试通过向量相似度找到起始节点
        if not start_node and vector is not None and self._vector_index:
            start_nodes = self._find_similar_nodes(
                vector, top_k=num_start_nodes, threshold=threshold
            )
            if start_nodes:
                start_node = start_nodes[0]["node_id"]  # 使用最相似的节点
                self.logger.debug(f"Found start node via vector similarity: {start_node}")
            else:
                self.logger.warning("No similar nodes found via vector search")

        # 如果仍然没有起始节点，尝试文本匹配（回退方案）
        if not start_node and query:
            # 遍历所有节点查找文本匹配
            for node_id in self._vector_index.keys():
                text = self.collection.text_storage.get(node_id)
                if text and query.lower() in text.lower():
                    start_node = node_id
                    self.logger.debug(f"Found start node via text match: {start_node}")
                    break

        if not start_node:
            self.logger.warning("No start_node found for graph retrieval")
            # 如果有向量索引，返回向量相似度结果
            if vector is not None and self._vector_index:
                return self._find_similar_nodes(vector, top_k=top_k, threshold=threshold)
            return []

        # 如果只需要向量检索结果
        if method == "vector_only" and vector is not None:
            return self._find_similar_nodes(vector, top_k=top_k, threshold=threshold)

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
            node_id = item.get("node_id", "")
            # 获取节点的 metadata（包含 original_text）
            node_metadata = self.collection.metadata_storage.get(node_id) or {}
            formatted_results.append(
                {
                    "text": item.get("data", ""),
                    "entry_id": node_id,
                    "node_id": node_id,
                    "depth": item.get("depth", 0),
                    "score": 1.0 / (1 + item.get("depth", 0)),  # 深度越小分数越高
                    "metadata": node_metadata,
                }
            )

        return formatted_results

    def _find_similar_nodes(
        self,
        query_vector: np.ndarray | list[float],
        top_k: int = 10,
        threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """通过向量相似度查找相似节点

        Args:
            query_vector: 查询向量
            top_k: 返回数量
            threshold: 相似度阈值

        Returns:
            相似节点列表
        """
        if not self._vector_index:
            return []

        if isinstance(query_vector, list):
            query_vector = np.array(query_vector)

        # 归一化查询向量
        query_norm = np.linalg.norm(query_vector)
        if query_norm > 0:
            query_vector = query_vector / query_norm

        # 计算与所有节点的余弦相似度
        similarities = []
        for node_id, node_vector in self._vector_index.items():
            node_norm = np.linalg.norm(node_vector)
            if node_norm > 0:
                similarity = float(np.dot(query_vector, node_vector / node_norm))
            else:
                similarity = 0.0

            if threshold is None or similarity >= threshold:
                similarities.append((node_id, similarity))

        # 按相似度降序排序
        similarities.sort(key=lambda x: x[1], reverse=True)

        # 返回 top_k 结果
        results = []
        for node_id, score in similarities[:top_k]:
            text = self.collection.text_storage.get(node_id) or ""
            # 获取节点的 metadata（包含 original_text）
            node_metadata = self.collection.metadata_storage.get(node_id) or {}
            results.append(
                {
                    "text": text,
                    "entry_id": node_id,
                    "node_id": node_id,
                    "score": score,
                    "depth": 0,
                    "metadata": node_metadata,
                }
            )

        return results

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

    def get_neighbors(self, node_id: str, k: int = 10) -> list[dict[str, Any]]:
        """获取节点的邻居

        Args:
            node_id: 节点 ID
            k: 返回数量

        Returns:
            邻居列表 [{"node_id": ..., "text": ..., "weight": ...}, ...]
        """
        results = self.collection.get_neighbors(
            node_id=node_id,
            k=k,
            index_name=self.index_name,
        )
        return results

    def ppr_retrieve(
        self,
        seed_nodes: list[str],
        alpha: float = 0.15,
        max_iter: int = 100,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """PPR (Personalized PageRank) 检索

        用于 HippoRAG 等基于图的检索场景。

        Args:
            seed_nodes: 种子节点 ID 列表
            alpha: 重启概率 (0.15 typical)
            max_iter: 最大迭代次数
            top_k: 返回数量

        Returns:
            检索结果列表 [{"node_id": ..., "text": ..., "score": ...}, ...]
        """
        if self.index_name not in self.collection.indexes:
            self.logger.warning(f"Index '{self.index_name}' not found")
            return []

        graph_index = self.collection.indexes[self.index_name]

        # 执行 PPR
        if not hasattr(graph_index, "ppr"):
            self.logger.warning("Graph index does not support PPR")
            return []

        ppr_results = graph_index.ppr(
            seed_nodes=seed_nodes,
            alpha=alpha,
            max_iter=max_iter,
            top_k=top_k,
        )

        # 组装返回结果
        formatted_results = []
        for node_id, score in ppr_results:
            text = (
                self.collection.text_storage.get(node_id)
                if hasattr(self.collection, "text_storage")
                else ""
            )
            metadata = (
                self.collection.metadata_storage.get(node_id)
                if hasattr(self.collection, "metadata_storage")
                else {}
            )
            formatted_results.append(
                {
                    "node_id": node_id,
                    "entry_id": node_id,
                    "text": text or "",
                    "score": score,
                    "metadata": metadata or {},
                }
            )

        return formatted_results

    def optimize(
        self,
        trigger: str = "auto",
        config: dict[str, Any] | None = None,
        entries: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """优化图结构

        Args:
            trigger: 触发类型 ("auto" | "link_evolution" | "decay" | "strengthen")
            config: 优化配置参数，支持:
                - link_policy: 链接策略 ("synonym_edge" | "knn" | "semantic")
                - similarity_threshold: 相似度阈值
                - edge_weight: 默认边权重
            entries: 相关的记忆条目

        Returns:
            dict: 优化统计信息
        """
        config = config or {}

        if self.index_name not in self.collection.indexes:
            return {"success": False, "message": "Index not found"}

        index = self.collection.indexes[self.index_name]
        edges_before = sum(len(edges) for edges in index.adjacency.values())

        # 根据触发类型执行不同的优化
        if trigger == "link_evolution":
            link_policy = config.get("link_policy", "synonym_edge")

            if link_policy == "synonym_edge":
                # HippoRAG 风格：连接共享相同实体的节点
                self._create_synonym_edges(index, config)
            elif link_policy == "knn":
                # KNN 链接：基于向量相似度
                self._create_knn_edges(index, config)

        edges_after = sum(len(edges) for edges in index.adjacency.values())
        edges_created = edges_after - edges_before

        stats = {
            "success": True,
            "trigger": trigger,
            "nodes_count": len(index.nodes),
            "edges_count": edges_after,
            "edges_created": edges_created,
        }

        self.logger.info(f"Graph optimization triggered: {trigger}, created {edges_created} edges")
        return stats

    def _create_synonym_edges(self, index: SimpleGraphIndex, config: dict[str, Any]) -> None:
        """创建 synonym edges - 连接共享相同实体的节点

        HippoRAG 核心：如果两个三元组共享相同的 subject 或 object，
        则它们应该通过边连接。

        优化：
        1. 跳过空 node_id 避免 metadata_storage 校验错误
        2. 限制每个实体最多连接 max_connections 个节点，避免 O(n²) 爆炸

        Args:
            index: 图索引
            config: 配置参数
        """
        edge_weight = config.get("edge_weight", 1.0)
        # 限制每个实体的最大连接数，避免常见词导致 O(n²) 爆炸
        max_connections = config.get("max_entity_connections", 50)

        # 构建实体到节点的映射
        entity_to_nodes: dict[str, list[str]] = {}

        for node_id in index.nodes:
            # 跳过空 node_id，避免 metadata_storage.get() 校验错误
            if not node_id or not isinstance(node_id, str):
                continue

            # 从 collection 的 metadata_storage 获取元数据
            try:
                metadata = self.collection.metadata_storage.get(node_id) or {}
            except ValueError:
                # 跳过无效的 node_id
                continue

            triples = metadata.get("triples", [])

            for triple in triples:
                if len(triple) >= 2:
                    # 提取 subject 和 object
                    subject = str(triple[0]).lower().strip()
                    obj = str(triple[-1]).lower().strip()  # 最后一个元素是 object

                    # 添加到映射
                    if subject:
                        entity_to_nodes.setdefault(subject, []).append(node_id)
                    if obj and obj != subject:
                        entity_to_nodes.setdefault(obj, []).append(node_id)

        # 为共享实体的节点创建边
        edges_created = 0
        for entity, node_ids in entity_to_nodes.items():
            if len(node_ids) < 2:
                continue

            # 优化：如果一个实体被太多节点共享（如常见词），只连接前 max_connections 个
            # 避免 O(n²) 导致的性能问题
            if len(node_ids) > max_connections:
                self.logger.debug(
                    f"Entity '{entity}' has {len(node_ids)} nodes, limiting to {max_connections}"
                )
                node_ids = node_ids[:max_connections]

            # 连接所有共享该实体的节点
            for i in range(len(node_ids)):
                for j in range(i + 1, len(node_ids)):
                    node_a, node_b = node_ids[i], node_ids[j]
                    if node_a != node_b:
                        # 双向连接
                        self.collection.add_edge(
                            from_node=node_a,
                            to_node=node_b,
                            weight=edge_weight,
                            index_name=self.index_name,
                        )
                        self.collection.add_edge(
                            from_node=node_b,
                            to_node=node_a,
                            weight=edge_weight,
                            index_name=self.index_name,
                        )
                        edges_created += 2

        self.logger.debug(
            f"Created {edges_created} synonym edges from {len(entity_to_nodes)} entities"
        )

    def _create_knn_edges(self, index: SimpleGraphIndex, config: dict[str, Any]) -> None:
        """创建 KNN edges - 基于向量相似度连接节点

        Args:
            index: 图索引
            config: 配置参数
        """
        knn_k = config.get("knn_k", 5)
        threshold = config.get("similarity_threshold", 0.7)
        edge_weight = config.get("edge_weight", 1.0)

        node_ids = list(self._vector_index.keys())
        if len(node_ids) < 2:
            return

        # 为每个节点找到 K 个最近邻
        for node_id in node_ids:
            if node_id not in self._vector_index:
                continue

            query_vector = self._vector_index[node_id]
            similarities = []

            for other_id in node_ids:
                if other_id == node_id or other_id not in self._vector_index:
                    continue

                other_vector = self._vector_index[other_id]
                # 余弦相似度
                sim = float(
                    np.dot(query_vector, other_vector)
                    / (np.linalg.norm(query_vector) * np.linalg.norm(other_vector) + 1e-8)
                )
                if sim >= threshold:
                    similarities.append((other_id, sim))

            # 取 top-k
            similarities.sort(key=lambda x: x[1], reverse=True)
            for other_id, sim in similarities[:knn_k]:
                self.collection.add_edge(
                    from_node=node_id,
                    to_node=other_id,
                    weight=edge_weight * sim,
                    index_name=self.index_name,
                )

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
