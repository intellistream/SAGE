"""Hybrid Memory Service - 多索引混合存储

支持多维向量索引和多路检索融合。
参考实现: EmotionalRAG (双向量索引)

特性:
1. 多索引支持: 语义向量、情感向量、BM25关键词等
2. 融合策略: weighted, rrf (Reciprocal Rank Fusion), learned

设计原则:
- Service : Collection = 1 : 1
- 使用单一 HybridCollection，支持 VDB + KV + Graph 多种索引类型
- Collection = 一份数据 + 多种类型的索引
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

import numpy as np

from sage.middleware.components.sage_mem.neuromem.memory_collection.base_collection import (
    IndexType,
)
from sage.middleware.components.sage_mem.neuromem.memory_collection.hybrid_collection import (
    HybridCollection,
)
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager
from sage.platform.service import BaseService

if TYPE_CHECKING:
    pass


class HybridMemoryService(BaseService):
    """混合记忆服务

    设计原则: Service : Collection = 1 : 1
    底层使用单一 HybridCollection，支持创建多种类型的索引（VDB, KV, Graph）。
    数据只存一份，可以通过多种索引访问。

    支持两种模式:
    - graph_enabled=False: 纯向量+关键词混合检索 (Mem0 基础版)
    - graph_enabled=True: 向量+关键词+图检索 (Mem0ᵍ 图记忆版)
    """

    def __init__(
        self,
        indexes: list[dict] | None = None,
        fusion_strategy: Literal["weighted", "rrf", "union"] = "rrf",
        fusion_weights: dict[str, float] | None = None,
        rrf_k: int = 60,
        collection_name: str = "hybrid_memory",
        graph_enabled: bool = False,
        entity_extraction: bool = False,
        relation_extraction: bool = False,
    ):
        """初始化混合记忆服务

        Args:
            indexes: 索引配置列表，每个配置包含:
                - name: 索引名称
                - type: 索引类型 ("vdb" | "kv" | "graph")
                - dim: 向量维度 (vdb 类型必需)
                - index_type: 子类型 (kv: "bm25s", graph: "simple")
            fusion_strategy: 融合策略 ("weighted" | "rrf" | "union")
            fusion_weights: 索引权重 {"index_name": weight} (weighted 策略)
            rrf_k: RRF 参数 (rrf 策略)
            collection_name: Collection 名称
            graph_enabled: 是否启用图索引（Mem0ᵍ 图记忆版）
            entity_extraction: 是否启用实体抽取（与 graph_enabled 配合使用）
            relation_extraction: 是否启用关系抽取（与 graph_enabled 配合使用）
        """
        super().__init__()

        # 图索引相关配置
        self.graph_enabled = graph_enabled
        self.entity_extraction = entity_extraction
        self.relation_extraction = relation_extraction

        # 默认索引配置
        default_indexes = [
            {"name": "semantic", "type": "vdb", "dim": 768},
            {"name": "keyword", "type": "kv", "index_type": "bm25s"},
        ]

        # 如果启用图索引，添加图索引配置
        if graph_enabled and indexes is None:
            default_indexes.append({"name": "entity_graph", "type": "graph"})

        self.index_configs = indexes or default_indexes
        self.fusion_strategy = fusion_strategy
        self.fusion_weights = fusion_weights or {}
        self.rrf_k = rrf_k
        self.collection_name = collection_name

        # 初始化 MemoryManager
        self.manager = MemoryManager(self._get_default_data_dir())

        # 创建或获取单一 HybridCollection (Service:Collection = 1:1)
        self._init_collection()

        # === 被动插入状态管理（Mem0 CRUD 模式）===
        # 用于存储待处理的新条目和相似条目，供 PostInsert 查询
        self._pending_items: list[dict] = []  # 新插入的待决策条目
        self._pending_similar: list[dict] = []  # 相似的已有条目
        self._pending_action: str | None = None  # "crud" | None

        self.logger.info(
            f"HybridMemoryService initialized: strategy={fusion_strategy}, "
            f"indexes={[c['name'] for c in self.index_configs]}, "
            f"graph_enabled={graph_enabled}"
        )

    @classmethod
    def _get_default_data_dir(cls) -> str:
        """获取默认数据目录

        使用 SAGE 标准目录结构: .sage/data/hybrid_memory
        """
        from sage.common.config.output_paths import get_appropriate_sage_dir

        sage_dir = get_appropriate_sage_dir()
        data_dir = sage_dir / "data" / "hybrid_memory"
        data_dir.mkdir(parents=True, exist_ok=True)
        return str(data_dir)

    def _init_collection(self) -> None:
        """初始化 HybridCollection 并创建索引"""
        # 创建或获取 HybridCollection
        # 注意：has_collection 可能返回 True，但 get_collection 返回 None（磁盘数据丢失）
        # 或者返回的不是 HybridCollection，这种情况下需要删除旧记录并重新创建
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
            elif not isinstance(collection, HybridCollection):
                # Collection 存在但类型不对
                self.logger.warning(
                    f"Collection '{self.collection_name}' exists but is not a HybridCollection, "
                    "will recreate."
                )
                self.manager.delete_collection(self.collection_name)
                collection = None

        if collection is None:
            collection = self.manager.create_collection(
                {
                    "name": self.collection_name,
                    "backend_type": "hybrid",
                    "rrf_k": self.rrf_k,
                    "description": "Hybrid memory with multiple index types",
                }
            )

        self.collection = collection

        if self.collection is None:
            raise RuntimeError(f"Failed to create HybridCollection '{self.collection_name}'")

        # 创建配置的索引
        for config in self.index_configs:
            index_name = config.get("name")
            if not index_name:
                continue

            # 检查索引是否已存在
            existing_indexes = {idx["name"] for idx in self.collection.list_indexes()}
            if index_name in existing_indexes:
                continue

            # 确定索引类型
            type_str = config.get("type", "vdb").lower()
            if type_str in ("vdb", "vector"):
                index_type = IndexType.VDB
            elif type_str in ("kv", "text", "bm25", "keyword"):
                index_type = IndexType.KV
            elif type_str == "graph":
                index_type = IndexType.GRAPH
            else:
                self.logger.warning(f"Unknown index type: {type_str}, skipping")
                continue

            # 创建索引
            self.collection.create_index(config, index_type)

    def insert(
        self,
        entry: str,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict | None = None,
        *,
        insert_mode: Literal["active", "passive"] = "passive",
        insert_params: dict | None = None,
    ) -> str:
        """插入文档到多个索引

        数据只存一份，同时加入多个索引。

        支持两种插入模式：
        - passive: 由服务自行决定存储方式（默认插入所有索引）
        - active: 根据 insert_params 指定存储方式

        Args:
            entry: 文本内容
            vector: embedding 向量（用于 VDB 索引）
            metadata: 元数据，可包含:
                - vectors: 多个向量 {"index_name": vector}
                - edges: 图边 [(target_id, weight, relation)]
            insert_mode: 插入模式 ("active" | "passive")
            insert_params: 主动插入参数
                - target_indexes: 目标索引列表（仅插入到指定索引）
                - priority: 优先级

        Returns:
            str: 文档 ID (stable_id)
        """
        metadata = metadata or {}

        # 处理插入模式
        target_indexes: list[str] | None = None
        if insert_mode == "active" and insert_params:
            target_indexes = insert_params.get("target_indexes")
            if "priority" in insert_params:
                metadata["priority"] = insert_params["priority"]

        # 确定要插入的索引
        if target_indexes is None:
            target_indexes = [c["name"] for c in self.index_configs if c.get("name")]

        # 准备多向量支持
        vectors_map = metadata.get("vectors", {})
        if vector is not None:
            # 为所有 VDB 索引设置默认向量
            for config in self.index_configs:
                if config.get("type", "vdb").lower() in ("vdb", "vector"):
                    idx_name = config.get("name")
                    if idx_name and idx_name not in vectors_map:
                        vectors_map[idx_name] = vector

        # 图边信息
        edges = metadata.get("edges", [])

        # 使用 HybridCollection 的 insert 方法
        # 数据只存一份，同时加入多个索引
        stable_id = self.collection.insert(
            content=entry,
            index_names=target_indexes,
            vector=vector,
            metadata=metadata,
            vectors=vectors_map,
            edges=edges,
        )

        # === 被动插入模式：检测相似项，更新状态供 PostInsert 查询 ===
        if insert_mode == "passive" and vector is not None:
            self._update_pending_status(
                entry=entry,
                entry_id=stable_id,
                vector=vector,
                metadata=metadata,
            )

        self.logger.debug(f"Inserted document to hybrid memory: {stable_id[:16]}...")
        return stable_id

    def _update_pending_status(
        self,
        entry: str,
        entry_id: str,
        vector: np.ndarray | list[float],
        metadata: dict | None = None,
    ) -> None:
        """更新待处理状态（被动插入模式核心方法）

        在插入后检索相似项，更新状态供 PostInsert 的 Mem0 CRUD 决策。

        Args:
            entry: 插入的文本内容
            entry_id: 插入后的条目 ID
            vector: 插入的向量
            metadata: 插入的元数据
        """
        # 检索相似条目（排除刚插入的条目）
        try:
            similar_results = self.retrieve_single(
                query=np.array(vector, dtype=np.float32),
                index_name=self.index_configs[0].get("name") if self.index_configs else "semantic",
                top_k=10,
            )

            # 过滤掉刚插入的条目
            similar_results = [r for r in similar_results if r.get("entry_id") != entry_id]

            if similar_results:
                # 有相似条目，设置待处理状态
                self._pending_items = [
                    {
                        "entry_id": entry_id,
                        "text": entry,
                        "vector": (
                            vector.tolist()
                            if isinstance(vector, np.ndarray)
                            else list(vector)
                            if vector
                            else None
                        ),
                        "metadata": metadata or {},
                    }
                ]
                self._pending_similar = similar_results
                self._pending_action = "crud"

                self.logger.debug(
                    f"Pending CRUD status updated: new_item={entry_id[:16]}..., "
                    f"similar_count={len(similar_results)}"
                )
            else:
                # 无相似条目，清除状态
                self.clear_pending_status()

        except Exception as e:
            self.logger.warning(f"Failed to update pending status: {e}")
            self.clear_pending_status()

    def get_status(self) -> dict:
        """查询服务状态（被动插入模式唯一对外接口）

        供 PostInsert 算子查询待处理状态，决定是否需要 LLM 进行 CRUD 决策。

        Returns:
            dict: 服务状态字典
                - pending_action: "crud" | None
                - pending_items: 新插入的待决策条目
                - pending_similar: 相似的已有条目
        """
        return {
            "pending_action": self._pending_action,
            "pending_items": self._pending_items.copy(),
            "pending_similar": self._pending_similar.copy(),
        }

    def clear_pending_status(self) -> None:
        """清除待处理状态

        在 PostInsert 处理完成后调用，或无需处理时清除。
        """
        self._pending_items = []
        self._pending_similar = []
        self._pending_action = None

    def retrieve(
        self,
        query: str | None = None,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict | None = None,
        top_k: int = 10,
        hints: dict | None = None,
        threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """多路检索并融合结果

        Args:
            query: 查询文本（用于 KV 索引）
            vector: 查询向量（用于 VDB 索引）
            metadata: 查询参数:
                - indexes: 要检索的索引列表（默认所有）
                - vectors: 多个查询向量 {"index_name": vector}
                - fusion_weights: 覆盖默认权重
                - start_node: 图检索起始节点
            top_k: 返回结果数量
            hints: 检索策略提示（可选，由 PreRetrieval route action 生成）
            threshold: 相似度阈值（可选，过滤低于阈值的结果）

        Returns:
            list[dict]: 融合后的检索结果
        """
        _ = hints  # 保留用于未来扩展
        _ = threshold  # 融合检索使用融合分数，暂不使用 threshold
        metadata = metadata or {}

        # 确定要检索的索引
        indexes_to_search = metadata.get("indexes")
        if indexes_to_search is None:
            indexes_to_search = [c["name"] for c in self.index_configs if c.get("name")]

        # 准备查询
        queries: dict[str, Any] = {}
        vectors_map = metadata.get("vectors", {})

        for idx_name in indexes_to_search:
            idx_type = self.collection.get_index_type(idx_name)
            if idx_type is None:
                continue

            if idx_type == IndexType.VDB:
                # VDB 索引使用向量查询
                vec = vectors_map.get(idx_name, vector)
                if vec is not None:
                    queries[idx_name] = np.array(vec, dtype=np.float32)
            elif idx_type == IndexType.KV:
                # KV 索引使用文本查询
                if query:
                    queries[idx_name] = query
            elif idx_type == IndexType.GRAPH:
                # Graph 索引使用起始节点或文本查询
                start_node = metadata.get("start_node")
                if start_node:
                    queries[idx_name] = start_node
                elif query:
                    queries[idx_name] = query

        if not queries:
            self.logger.warning("No valid queries for retrieval")
            return []

        # 使用 HybridCollection 的 retrieve_multi 方法
        results = self.collection.retrieve_multi(
            queries=queries,
            top_k=top_k,
            fusion_strategy=self.fusion_strategy,
            weights=metadata.get("fusion_weights", self.fusion_weights),
        )

        # 格式化结果
        formatted_results = []
        for item in results:
            formatted_results.append(
                {
                    "text": item.get("text", ""),
                    "score": item.get("fused_score", item.get("score", 0.0)),
                    "entry_id": item.get("id", ""),
                    "metadata": item.get("metadata", {}),
                }
            )

        return formatted_results

    def retrieve_single(
        self,
        query: str | np.ndarray | None = None,
        index_name: str | None = None,
        top_k: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """单索引检索（不融合）

        Args:
            query: 查询（文本或向量）
            index_name: 索引名称
            top_k: 返回数量
            **kwargs: 额外参数（传递给 Collection.retrieve）

        Returns:
            检索结果列表
        """
        if index_name is None:
            # 默认使用第一个索引
            index_name = self.index_configs[0].get("name") if self.index_configs else None

        if index_name is None:
            return []

        results = self.collection.retrieve(
            query=query,
            index_name=index_name,
            top_k=top_k,
            with_metadata=True,
            **kwargs,
        )

        # 格式化结果
        formatted_results = []
        for item in results:
            formatted_results.append(
                {
                    "text": item.get("text", ""),
                    "score": item.get("score", 0.0),
                    "entry_id": item.get("id", ""),
                    "metadata": item.get("metadata", {}),
                }
            )

        return formatted_results

    def delete(self, entry_id: str) -> bool:
        """删除文档（从数据存储和所有索引中移除）

        Args:
            entry_id: 文档 ID

        Returns:
            bool: 是否删除成功
        """
        return self.collection.delete(entry_id)

    def remove_from_index(self, entry_id: str, index_name: str) -> bool:
        """从指定索引移除（保留数据）

        用于 MemoryOS 场景：从一个索引移除，加入另一个索引。

        Args:
            entry_id: 文档 ID
            index_name: 索引名称

        Returns:
            bool: 是否成功
        """
        return self.collection.remove_from_index(entry_id, index_name)

    def insert_to_index(
        self,
        entry_id: str,
        index_name: str,
        vector: np.ndarray | None = None,
        **kwargs: Any,
    ) -> bool:
        """将已有数据加入索引

        用于 MemoryOS 场景：数据已存在，加入新索引。

        Args:
            entry_id: 数据 ID
            index_name: 目标索引名
            vector: 向量（VDB 索引需要）
            **kwargs: 额外参数

        Returns:
            bool: 是否成功
        """
        return self.collection.insert_to_index(entry_id, index_name, vector, **kwargs)

    def optimize(self, trigger: str = "auto") -> dict[str, Any]:
        """优化记忆结构

        Args:
            trigger: 触发类型

        Returns:
            dict: 优化统计信息
        """
        stats = {
            "success": True,
            "trigger": trigger,
            "indexes": {},
        }

        for idx_info in self.collection.list_indexes():
            idx_name = idx_info["name"]
            idx_count = self.collection.get_index_count(idx_name)
            stats["indexes"][idx_name] = {
                "type": idx_info["type"].value,
                "count": idx_count,
            }

        return stats

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        index_stats = {}
        for idx_info in self.collection.list_indexes():
            idx_name = idx_info["name"]
            index_stats[idx_name] = {
                "type": idx_info["type"].value,
                "count": self.collection.get_index_count(idx_name),
            }

        return {
            "memory_count": len(self.collection.get_all_ids()),
            "fusion_strategy": self.fusion_strategy,
            "index_count": len(self.index_configs),
            "indexes": index_stats,
            "collection_name": self.collection_name,
        }
