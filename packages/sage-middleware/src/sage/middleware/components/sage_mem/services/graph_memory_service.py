"""Graph Memory Service - 基于图结构的记忆存储

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
"""

from __future__ import annotations

import hashlib
import time
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

    支持两种变体:
    - HippoRAG 基础版: ppr_depth=2, enhanced_rerank=False
    - HippoRAG2 改进版: ppr_depth=3, enhanced_rerank=True
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

        # === 被动插入状态管理（A-Mem 链接/HippoRAG 同义边）===
        # 用于存储待处理的新节点和链接候选，供 PostInsert 查询
        self._pending_node: dict | None = None  # 新插入的节点
        self._pending_candidates: list[dict] = []  # 链接/同义候选
        self._pending_action: str | None = None  # "link" | "synonym" | None

        self.logger.info(
            f"GraphMemoryService initialized: collection={collection_name}, "
            f"graph_type={graph_type}, index={index_name}, "
            f"ppr_depth={ppr_depth}, ppr_damping={ppr_damping}, enhanced_rerank={enhanced_rerank}"
        )

    def get(self, entry_id: str) -> dict[str, Any] | None:
        """获取指定 ID 的记忆条目（节点）

        Args:
            entry_id: 条目 ID（节点 ID）

        Returns:
            dict: 条目数据（包含 text, metadata, vector 等），不存在返回 None
        """
        if not hasattr(self.collection, "text_storage"):
            return None

        text = self.collection.text_storage.get(entry_id)
        if text is None:
            return None

        metadata = None
        if hasattr(self.collection, "metadata_storage"):
            metadata = self.collection.metadata_storage.get(entry_id)

        result = {
            "id": entry_id,
            "text": text,
            "metadata": metadata or {},
        }

        # 如果存在 vector_index，添加 embedding
        if entry_id in self._vector_index:
            result["embedding"] = self._vector_index[entry_id]

        return result

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

        # === 被动插入模式：查找候选并更新状态供 PostInsert 查询 ===
        if insert_mode == "passive" and vector is not None:
            self._update_pending_status(node_id, entry, vector, metadata)

        self.logger.debug(f"Inserted node {node_id} to graph")
        return node_id

    def _update_pending_status(
        self,
        node_id: str,
        entry: str,
        vector: np.ndarray,
        metadata: dict | None = None,
    ) -> None:
        """更新待处理状态（被动插入模式核心方法）

        根据图类型查找候选，更新状态供 PostInsert 决策：
        - link_graph (A-Mem): 查找链接候选
        - knowledge_graph (HippoRAG): 查找同义词边候选

        Args:
            node_id: 新插入的节点 ID
            entry: 节点文本内容
            vector: 节点向量
            metadata: 节点元数据
        """
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
            # A-Mem: 链接建立
            self._pending_action = "link"
        else:
            # knowledge_graph (HippoRAG): 同义边建立
            self._pending_action = "synonym"

        self.logger.debug(
            f"Pending {self._pending_action} status updated: node={node_id[:16]}..., "
            f"candidates={len(candidates)}"
        )

    def get_status(self) -> dict:
        """查询服务状态（被动插入模式唯一对外接口）

        供 PostInsert 算子查询待处理状态，决定是否需要 LLM 进行链接决策。

        Returns:
            dict: 服务状态字典
                - pending_action: "link" | "synonym" | None
                - pending_node: 新插入的节点信息
                - pending_candidates: 链接/同义候选列表
        """
        return {
            "pending_action": self._pending_action,
            "pending_node": self._pending_node.copy() if self._pending_node else None,
            "pending_candidates": self._pending_candidates.copy(),
        }

    def clear_pending_status(self) -> None:
        """清除待处理状态

        在 PostInsert 处理完成后调用，或无需处理时清除。
        """
        self._pending_node = None
        self._pending_candidates = []
        self._pending_action = None

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
                - max_depth: 最大遍历深度（默认使用 self.max_depth）
                - method: 检索方法 ("bfs" | "neighbors" | "vector_only" | "ppr")
                - num_start_nodes: 使用多少个起始节点（默认使用 self.num_start_nodes）
            top_k: 返回结果数量
            hints: 检索策略提示（可选，由 PreRetrieval route action 生成）
            threshold: 相似度阈值（可选，过滤低于阈值的结果）

        Returns:
            list[dict]: 检索结果
        """
        _ = hints  # 保留用于未来扩展
        metadata = metadata or {}
        start_node = metadata.get("start_node")
        # 使用实例配置作为默认值（支持 HippoRAG2 的更深遍历）
        max_depth = metadata.get("max_depth", self.max_depth)
        method = metadata.get("method", "bfs")
        num_start_nodes = metadata.get("num_start_nodes", self.num_start_nodes)

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

        # PPR 检索方法（HippoRAG/HippoRAG2）
        if method == "ppr" and vector is not None:
            # 找到多个起始节点
            start_nodes_list = self._find_similar_nodes(
                vector, top_k=num_start_nodes, threshold=threshold
            )
            seed_node_ids = [n["node_id"] for n in start_nodes_list]
            if seed_node_ids:
                return self.ppr_retrieve(
                    seed_nodes=seed_node_ids,
                    alpha=1.0 - self.ppr_damping,  # alpha = 1 - damping
                    max_iter=self.ppr_depth * 50,  # 迭代次数与深度相关
                    top_k=top_k,
                )
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
        alpha: float | None = None,
        max_iter: int | None = None,
        top_k: int = 10,
        query_vector: np.ndarray | list[float] | None = None,
    ) -> list[dict[str, Any]]:
        """PPR (Personalized PageRank) 检索

        用于 HippoRAG/HippoRAG2 等基于图的检索场景。
        HippoRAG2 支持 enhanced_rerank，结合 PPR 分数和语义相似度。

        Args:
            seed_nodes: 种子节点 ID 列表
            alpha: 重启概率（默认使用 1 - self.ppr_damping）
            max_iter: 最大迭代次数（默认使用 self.ppr_depth * 50）
            top_k: 返回数量
            query_vector: 查询向量（用于 enhanced_rerank）

        Returns:
            检索结果列表 [{"node_id": ..., "text": ..., "score": ...}, ...]
        """
        # 使用实例配置作为默认值
        if alpha is None:
            alpha = 1.0 - self.ppr_damping
        if max_iter is None:
            max_iter = self.ppr_depth * 50

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
            top_k=top_k * 2 if self.enhanced_rerank else top_k,  # 增强重排时获取更多候选
        )

        # 组装返回结果
        formatted_results = []
        for node_id, ppr_score in ppr_results:
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

            # 计算最终分数
            final_score = ppr_score
            if self.enhanced_rerank and query_vector is not None and node_id in self._vector_index:
                # HippoRAG2 增强重排序：结合 PPR 分数和语义相似度
                node_vector = self._vector_index[node_id]
                if isinstance(query_vector, list):
                    query_vector = np.array(query_vector)

                # 计算余弦相似度
                query_norm = np.linalg.norm(query_vector)
                node_norm = np.linalg.norm(node_vector)
                if query_norm > 0 and node_norm > 0:
                    semantic_score = float(
                        np.dot(query_vector, node_vector) / (query_norm * node_norm)
                    )
                else:
                    semantic_score = 0.0

                # 融合分数（PPR 权重 0.6，语义相似度权重 0.4）
                final_score = 0.6 * ppr_score + 0.4 * semantic_score

            formatted_results.append(
                {
                    "node_id": node_id,
                    "entry_id": node_id,
                    "text": text or "",
                    "score": final_score,
                    "ppr_score": ppr_score,
                    "metadata": metadata or {},
                }
            )

        # 如果启用了增强重排序，按融合分数重新排序并截取
        if self.enhanced_rerank:
            formatted_results.sort(key=lambda x: x["score"], reverse=True)
            formatted_results = formatted_results[:top_k]

        return formatted_results

    # ==================== 论文算法实现 ====================

    def _create_auto_links(
        self,
        node_id: str,
        config: dict[str, Any] | None = None,
    ) -> list[str]:
        """A-Mem: 自动链接生成

        论文要求:
        1. 检索 top-k 最近邻
        2. 基于相似度阈值建立链接
        3. 建立双向链接

        Args:
            node_id: 新插入的节点 ID
            config: 配置参数
                - max_auto_links: 最大链接数，默认 5
                - similarity_threshold: 相似度阈值，默认 0.7
                - edge_weight: 边权重，默认 1.0

        Returns:
            新建立链接的目标节点 ID 列表
        """
        config = config or {}
        max_links = int(config.get("max_auto_links", 5))
        threshold = float(config.get("similarity_threshold", 0.7))
        edge_weight = float(config.get("edge_weight", self.link_weight_init))

        if node_id not in self._vector_index:
            return []

        query_vector = self._vector_index[node_id]
        linked_nodes: list[str] = []

        # 找到最相似的节点
        similarities: list[tuple[str, float]] = []
        for other_id, other_vector in self._vector_index.items():
            if other_id == node_id:
                continue

            # 余弦相似度
            sim = float(
                np.dot(query_vector, other_vector)
                / (np.linalg.norm(query_vector) * np.linalg.norm(other_vector) + 1e-8)
            )
            if sim >= threshold:
                similarities.append((other_id, sim))

        # 按相似度排序，取 top-k
        similarities.sort(key=lambda x: x[1], reverse=True)

        for other_id, sim in similarities[:max_links]:
            # 建立双向链接
            if self.link_policy == "bidirectional":
                self.collection.add_edge(
                    from_node=node_id,
                    to_node=other_id,
                    weight=edge_weight * sim,
                    index_name=self.index_name,
                )
                self.collection.add_edge(
                    from_node=other_id,
                    to_node=node_id,
                    weight=edge_weight * sim,
                    index_name=self.index_name,
                )
            else:
                self.collection.add_edge(
                    from_node=node_id,
                    to_node=other_id,
                    weight=edge_weight * sim,
                    index_name=self.index_name,
                )
            linked_nodes.append(other_id)

        self.logger.debug(f"Auto-linked {node_id[:16]}... to {len(linked_nodes)} nodes")
        return linked_nodes

    def _memory_evolution(
        self,
        node_id: str,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """A-Mem: 记忆演化

        论文要求:
        对新插入节点的每个邻居，判断是否需要更新其 keywords/tags/context

        Args:
            node_id: 新插入的节点 ID
            config: 配置参数
                - evolution_threshold: 演化相似度阈值，默认 0.8
                - merge_keywords: 是否合并关键词，默认 True

        Returns:
            演化统计信息
        """
        config = config or {}
        evolution_threshold = float(config.get("evolution_threshold", 0.8))
        merge_keywords = config.get("merge_keywords", True)

        stats = {"updated_nodes": 0, "merged_keywords": 0}

        # 获取新节点的信息
        if node_id not in self._vector_index:
            return stats

        new_vector = self._vector_index[node_id]
        new_meta = self.collection.metadata_storage.get(node_id) or {}
        new_keywords = set(new_meta.get("keywords", []))

        # 获取邻居节点
        if self.index_name not in self.collection.indexes:
            return stats

        index = self.collection.indexes[self.index_name]
        neighbors = index.adjacency.get(node_id, {})

        for neighbor_id in neighbors:
            if neighbor_id not in self._vector_index:
                continue

            neighbor_vector = self._vector_index[neighbor_id]

            # 计算相似度
            sim = float(
                np.dot(new_vector, neighbor_vector)
                / (np.linalg.norm(new_vector) * np.linalg.norm(neighbor_vector) + 1e-8)
            )

            if sim >= evolution_threshold and merge_keywords:
                # 合并关键词
                neighbor_meta = self.collection.metadata_storage.get(neighbor_id) or {}
                neighbor_keywords = set(neighbor_meta.get("keywords", []))

                # 将新节点的关键词添加到邻居
                merged = neighbor_keywords | new_keywords
                if merged != neighbor_keywords:
                    neighbor_meta["keywords"] = list(merged)
                    neighbor_meta["evolved_at"] = time.time()
                    self.collection.metadata_storage[neighbor_id] = neighbor_meta
                    stats["updated_nodes"] += 1
                    stats["merged_keywords"] += len(merged - neighbor_keywords)

        self.logger.debug(
            f"Memory evolution for {node_id[:16]}...: updated {stats['updated_nodes']} neighbors"
        )
        return stats

    def _build_synonym_edges_batch(
        self,
        config: dict[str, Any] | None = None,
    ) -> int:
        """HippoRAG: 批量建立同义词边

        论文要求:
        对所有 Phrase Node，计算两两嵌入相似度，若 > τ，建立 synonym 边

        优化:
        - 仅在 session 结束时批量执行
        - 避免重复建边

        Args:
            config: 配置参数
                - synonymy_threshold: 同义词相似度阈值，默认使用实例的 synonymy_threshold

        Returns:
            新建立的边数量
        """
        config = config or {}
        threshold = float(config.get("synonymy_threshold", self.synonymy_threshold))

        if self.index_name not in self.collection.indexes:
            return 0

        index = self.collection.indexes[self.index_name]
        node_ids = list(self._vector_index.keys())
        edges_created = 0

        # 记录已存在的边，避免重复
        existing_edges: set[tuple[str, str]] = set()
        for from_node, neighbors in index.adjacency.items():
            for to_node in neighbors:
                existing_edges.add((from_node, to_node))

        # 计算两两相似度
        for i, node_a in enumerate(node_ids):
            vec_a = self._vector_index[node_a]

            for node_b in node_ids[i + 1 :]:
                vec_b = self._vector_index[node_b]

                # 检查是否已有边
                if (node_a, node_b) in existing_edges or (node_b, node_a) in existing_edges:
                    continue

                # 余弦相似度
                sim = float(
                    np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b) + 1e-8)
                )

                if sim >= threshold:
                    # 建立双向同义词边
                    self.collection.add_edge(
                        from_node=node_a,
                        to_node=node_b,
                        weight=sim,
                        edge_type="synonym",
                        index_name=self.index_name,
                    )
                    self.collection.add_edge(
                        from_node=node_b,
                        to_node=node_a,
                        weight=sim,
                        edge_type="synonym",
                        index_name=self.index_name,
                    )
                    edges_created += 2

        self.logger.debug(f"Built {edges_created} synonym edges (threshold={threshold})")
        return edges_created

    def optimize(
        self,
        trigger: str = "auto",
        config: dict[str, Any] | None = None,
        entries: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """优化图结构

        支持的触发类型:
        - auto: 自动执行所有优化
        - link_evolution: 链接演化（synonym_edge, knn, auto_link）
        - memory_evolution: 记忆演化（A-Mem）
        - decay: 边权重衰减
        - strengthen: 边权重增强

        支持的配置参数 (通过 config 传入):
        - link_policy: 链接策略 ("synonym_edge" | "knn" | "auto_link")
        - similarity_threshold: 相似度阈值
        - edge_weight: 默认边权重
        - max_auto_links: 自动链接最大数量
        - synonymy_threshold: 同义词边阈值
        - evolution_threshold: 演化阈值
        - decay_rate: 边衰减率
        - strengthen_factor: 边增强因子

        Args:
            trigger: 触发类型
            config: 优化配置参数
            entries: 相关的记忆条目

        Returns:
            dict: 优化统计信息
        """
        config = config or {}
        entries = entries or []

        if self.index_name not in self.collection.indexes:
            return {"success": False, "message": "Index not found"}

        index = self.collection.indexes[self.index_name]
        edges_before = sum(len(edges) for edges in index.adjacency.values())

        stats: dict[str, Any] = {
            "success": True,
            "trigger": trigger,
            "nodes_count": len(index.nodes),
            "edges_before": edges_before,
            "edges_created": 0,
            "nodes_evolved": 0,
        }

        # 根据触发类型执行不同的优化
        if trigger in ("auto", "link_evolution"):
            link_policy = config.get("link_policy", "synonym_edge")

            if link_policy == "synonym_edge":
                # HippoRAG: 批量建立同义词边
                edges_created = self._build_synonym_edges_batch(config)
                stats["edges_created"] += edges_created

            elif link_policy == "knn":
                # KNN 链接：基于向量相似度
                self._create_knn_edges(index, config)

            elif link_policy == "auto_link":
                # A-Mem: 对新插入的节点建立自动链接
                for entry in entries:
                    node_id = entry.get("node_id") or entry.get("entry_id")
                    if node_id:
                        linked = self._create_auto_links(node_id, config)
                        stats["edges_created"] += len(linked) * 2  # 双向

            # 同时执行原有的 synonym_edge 逻辑
            if link_policy != "synonym_edge":
                self._create_synonym_edges(index, config)

        if trigger in ("auto", "memory_evolution"):
            # A-Mem: 记忆演化
            for entry in entries:
                node_id = entry.get("node_id") or entry.get("entry_id")
                if node_id:
                    evo_stats = self._memory_evolution(node_id, config)
                    stats["nodes_evolved"] += evo_stats.get("updated_nodes", 0)

        if trigger == "decay":
            # 边权重衰减
            decay_rate = float(config.get("decay_rate", 0.95))
            decayed = self._decay_edge_weights(decay_rate)
            stats["edges_decayed"] = decayed

        if trigger == "strengthen":
            # 边权重增强
            strengthen_factor = float(config.get("strengthen_factor", 1.1))
            node_ids = [e.get("node_id") or e.get("entry_id") for e in entries if e]
            strengthened = self._strengthen_edges(node_ids, strengthen_factor)
            stats["edges_strengthened"] = strengthened

        edges_after = sum(len(edges) for edges in index.adjacency.values())
        stats["edges_after"] = edges_after
        stats["edges_created"] = max(0, edges_after - edges_before)

        self.logger.info(
            f"Graph optimization triggered: {trigger}, edges: {edges_before} -> {edges_after}"
        )
        return stats

    def _decay_edge_weights(self, decay_rate: float) -> int:
        """衰减所有边的权重

        Args:
            decay_rate: 衰减率 (0-1)

        Returns:
            衰减的边数量
        """
        if self.index_name not in self.collection.indexes:
            return 0

        index = self.collection.indexes[self.index_name]
        decayed = 0

        for from_node in index.adjacency:
            for to_node in index.adjacency[from_node]:
                current_weight = index.adjacency[from_node][to_node]
                new_weight = current_weight * decay_rate
                index.adjacency[from_node][to_node] = new_weight
                decayed += 1

        return decayed

    def _strengthen_edges(self, node_ids: list[str], factor: float) -> int:
        """增强指定节点的边权重

        Args:
            node_ids: 要增强的节点 ID 列表
            factor: 增强因子 (>1)

        Returns:
            增强的边数量
        """
        if self.index_name not in self.collection.indexes:
            return 0

        index = self.collection.indexes[self.index_name]
        strengthened = 0

        for node_id in node_ids:
            if node_id not in index.adjacency:
                continue

            for to_node in index.adjacency[node_id]:
                current_weight = index.adjacency[node_id][to_node]
                new_weight = min(current_weight * factor, 10.0)  # 限制最大权重
                index.adjacency[node_id][to_node] = new_weight
                strengthened += 1

        return strengthened

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
            base_stats = {
                "memory_count": 0,
                "edges_count": 0,
                "graph_type": self.graph_type,
                "collection_name": self.collection_name,
            }
        else:
            index = self.collection.indexes[self.index_name]
            base_stats = {
                "memory_count": len(index.nodes),
                "edges_count": sum(len(edges) for edges in index.adjacency.values()),
                "graph_type": self.graph_type,
                "collection_name": self.collection_name,
                "index_name": self.index_name,
            }

        # 添加存储统计
        if hasattr(self.collection, "get_storage_stats"):
            base_stats["storage"] = self.collection.get_storage_stats()

        return base_stats
