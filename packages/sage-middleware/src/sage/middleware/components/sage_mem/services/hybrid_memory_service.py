"""Hybrid Memory Service - 多索引混合存储

支持多维向量索引和多路检索融合。
参考实现: EmotionalRAG (双向量索引)

特性:
1. 多索引支持: 语义向量、情感向量、BM25关键词等
2. 融合策略: weighted, rrf (Reciprocal Rank Fusion), learned

使用 VDBMemoryCollection + KVMemoryCollection 作为底层存储。
"""

from __future__ import annotations

import os
import uuid
from typing import TYPE_CHECKING, Any, Literal

import numpy as np

from sage.middleware.components.sage_mem.neuromem.memory_collection.kv_collection import (
    KVMemoryCollection,
)
from sage.middleware.components.sage_mem.neuromem.memory_collection.vdb_collection import (
    VDBMemoryCollection,
)
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager
from sage.platform.service import BaseService

if TYPE_CHECKING:
    pass


class HybridMemoryService(BaseService):
    """混合记忆服务

    支持多索引和多路检索融合。
    底层使用 MemoryManager + VDBMemoryCollection + KVMemoryCollection 存储。
    """

    def __init__(
        self,
        indexes: list[dict] | None = None,
        fusion_strategy: Literal["weighted", "rrf", "learned"] = "weighted",
        fusion_weights: list[float] | None = None,
        rrf_k: int = 60,
        collection_prefix: str = "hybrid_memory",
    ):
        """初始化混合记忆服务

        Args:
            indexes: 索引配置列表，每个配置包含:
                - name: 索引名称
                - type: 索引类型 ("vector" | "bm25" | "keyword")
                - dim: 向量维度 (vector 类型)
            fusion_strategy: 融合策略
            fusion_weights: 融合权重 (weighted 策略)
            rrf_k: RRF 参数 (rrf 策略)
            collection_prefix: Collection 名称前缀
        """
        super().__init__()

        # 默认索引配置
        default_indexes = [
            {"name": "semantic", "type": "vector", "dim": 768},
            {"name": "keyword", "type": "bm25"},
        ]

        self.index_configs = indexes or default_indexes
        self.fusion_strategy = fusion_strategy
        self.fusion_weights = fusion_weights or [1.0 / len(self.index_configs)] * len(
            self.index_configs
        )
        self.rrf_k = rrf_k
        self.collection_prefix = collection_prefix

        # 初始化 MemoryManager
        self.manager = MemoryManager(self._get_default_data_dir())

        # 创建索引对应的 collections
        self.vector_collection: VDBMemoryCollection | None = None
        self.kv_collection: KVMemoryCollection | None = None

        self._init_collections()

        # 文档存储（entry_id -> 文档信息）
        self._documents: dict[str, dict[str, Any]] = {}

        self.logger.info(
            f"HybridMemoryService initialized: strategy={fusion_strategy}, "
            f"indexes={[c['name'] for c in self.index_configs]}"
        )

    @classmethod
    def _get_default_data_dir(cls) -> str:
        """获取默认数据目录"""
        cur_dir = os.getcwd()
        data_dir = os.path.join(cur_dir, "data", "hybrid_memory")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir

    def _init_collections(self) -> None:
        """初始化 collections"""
        for config in self.index_configs:
            index_type = config.get("type", "vector")

            if index_type == "vector":
                # 创建 VDB collection
                vdb_name = f"{self.collection_prefix}_vdb"
                if self.manager.has_collection(vdb_name):
                    collection = self.manager.get_collection(vdb_name)
                else:
                    collection = self.manager.create_collection(
                        {
                            "name": vdb_name,
                            "backend_type": "VDB",
                            "description": "Hybrid memory vector index",
                        }
                    )

                if isinstance(collection, VDBMemoryCollection):
                    self.vector_collection = collection
                    # 创建向量索引
                    index_name = config.get("name", "semantic")
                    if index_name not in collection.index_info:
                        collection.create_index(
                            {
                                "name": index_name,
                                "dim": config.get("dim", 768),
                                "backend_type": "FAISS",
                                "description": f"Vector index: {index_name}",
                            }
                        )

            elif index_type in ("bm25", "keyword"):
                # 创建 KV collection
                kv_name = f"{self.collection_prefix}_kv"
                if self.manager.has_collection(kv_name):
                    collection = self.manager.get_collection(kv_name)
                else:
                    collection = self.manager.create_collection(
                        {
                            "name": kv_name,
                            "backend_type": "KV",
                            "description": "Hybrid memory keyword index",
                        }
                    )

                if isinstance(collection, KVMemoryCollection):
                    self.kv_collection = collection
                    # 创建 BM25 索引
                    index_name = config.get("name", "keyword")
                    if index_name not in collection.indexes:
                        collection.create_index(
                            {
                                "name": index_name,
                                "index_type": "bm25s",
                                "description": f"BM25 index: {index_name}",
                            }
                        )

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

        支持两种插入模式：
        - passive: 由服务自行决定存储方式（默认）
        - active: 根据 insert_params 指定存储方式

        Args:
            entry: 文本内容
            vector: embedding 向量（用于向量索引）
            metadata: 元数据，可包含:
                - vectors: 多个向量 {"index_name": vector}
                - keywords: 关键词列表
            insert_mode: 插入模式 ("active" | "passive")
            insert_params: 主动插入参数
                - target_indexes: 目标索引列表（仅插入到指定索引）
                - priority: 优先级

        Returns:
            str: 文档 ID
        """
        metadata = metadata or {}

        # 处理插入模式
        target_indexes = None
        if insert_mode == "active" and insert_params:
            target_indexes = insert_params.get("target_indexes")
            if "priority" in insert_params:
                metadata["priority"] = insert_params["priority"]

        # 生成文档 ID
        entry_id = metadata.get("id", str(uuid.uuid4()))

        # 存储文档信息
        self._documents[entry_id] = {
            "text": entry,
            "metadata": metadata,
        }

        # 插入到向量索引（根据 target_indexes 过滤）
        if self.vector_collection is not None:
            vectors = metadata.get("vectors", {})
            if vector is not None:
                # 使用默认向量
                default_index = next(
                    (c["name"] for c in self.index_configs if c.get("type") == "vector"), "semantic"
                )
                vectors[default_index] = vector

            for index_name, vec in vectors.items():
                # 如果指定了 target_indexes，只插入到指定索引
                if target_indexes and index_name not in target_indexes:
                    continue
                if index_name in self.vector_collection.index_info:
                    vec_array = np.array(vec, dtype=np.float32)
                    self.vector_collection.insert(
                        index_name=index_name,
                        text=entry,
                        vector=vec_array,
                        metadata={"entry_id": entry_id, **metadata},
                    )

        # 插入到关键词索引（根据 target_indexes 过滤）
        if self.kv_collection is not None:
            for config in self.index_configs:
                if config.get("type") in ("bm25", "keyword"):
                    index_name = config.get("name", "keyword")
                    # 如果指定了 target_indexes，只插入到指定索引
                    if target_indexes and index_name not in target_indexes:
                        continue
                    if index_name in self.kv_collection.indexes:
                        self.kv_collection.insert(entry, {"entry_id": entry_id}, index_name)

        self.logger.debug(f"Inserted document to hybrid memory: {entry_id[:16]}...")
        return entry_id

    def retrieve(
        self,
        query: str | None = None,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """多路检索并融合结果

        Args:
            query: 查询文本
            vector: 查询向量
            metadata: 查询参数:
                - vectors: 多个查询向量
                - fusion_weights: 覆盖默认权重
            top_k: 返回结果数量

        Returns:
            list[dict]: 融合后的检索结果
        """
        metadata = metadata or {}
        all_results: dict[str, list[tuple[str, float]]] = {}  # index_name -> [(entry_id, score)]

        # 向量检索
        if self.vector_collection is not None:
            vectors = metadata.get("vectors", {})
            if vector is not None:
                default_index = next(
                    (c["name"] for c in self.index_configs if c.get("type") == "vector"), "semantic"
                )
                vectors[default_index] = vector

            for index_name, vec in vectors.items():
                if index_name in self.vector_collection.index_info:
                    vec_array = np.array(vec, dtype=np.float32)
                    results = self.vector_collection.retrieve(
                        query_text=query,
                        query_vector=vec_array,
                        index_name=index_name,
                        topk=top_k * 2,  # 获取更多以便融合
                        with_metadata=True,
                    )
                    if results:
                        all_results[index_name] = [
                            (r.get("metadata", {}).get("entry_id", ""), r.get("score", 0))
                            for r in results
                            if isinstance(r, dict)
                        ]

        # 关键词检索
        if self.kv_collection is not None and query:
            for config in self.index_configs:
                if config.get("type") in ("bm25", "keyword"):
                    index_name = config.get("name", "keyword")
                    if index_name in self.kv_collection.indexes:
                        results = self.kv_collection.retrieve(
                            raw_text=query,
                            topk=top_k * 2,
                            with_metadata=True,
                            index_name=index_name,
                        )
                        if results:
                            all_results[index_name] = [
                                (r.get("metadata", {}).get("entry_id", ""), 1.0 / (i + 1))
                                for i, r in enumerate(results)
                                if isinstance(r, dict)
                            ]

        # 融合结果
        fused_scores = self._fuse_results(all_results, metadata.get("fusion_weights"))

        # 按分数排序并返回
        sorted_entries = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
        results = []
        for entry_id, score in sorted_entries[:top_k]:
            if entry_id in self._documents:
                doc = self._documents[entry_id]
                results.append(
                    {
                        "text": doc["text"],
                        "score": score,
                        "entry_id": entry_id,
                        "metadata": doc.get("metadata", {}),
                    }
                )

        return results

    def _fuse_results(
        self,
        all_results: dict[str, list[tuple[str, float]]],
        weights: list[float] | None = None,
    ) -> dict[str, float]:
        """融合多路检索结果

        Args:
            all_results: 各索引的检索结果
            weights: 融合权重

        Returns:
            dict: entry_id -> 融合分数
        """
        weights = weights or self.fusion_weights
        fused_scores: dict[str, float] = {}

        if self.fusion_strategy == "weighted":
            # 加权融合
            for i, (index_name, results) in enumerate(all_results.items()):
                weight = weights[i] if i < len(weights) else 1.0 / len(all_results)
                for entry_id, score in results:
                    if entry_id:
                        fused_scores[entry_id] = fused_scores.get(entry_id, 0) + weight * score

        elif self.fusion_strategy == "rrf":
            # Reciprocal Rank Fusion
            for results in all_results.values():
                for rank, (entry_id, _) in enumerate(results):
                    if entry_id:
                        rrf_score = 1.0 / (self.rrf_k + rank + 1)
                        fused_scores[entry_id] = fused_scores.get(entry_id, 0) + rrf_score

        else:
            # 默认：简单合并
            for results in all_results.values():
                for entry_id, score in results:
                    if entry_id:
                        fused_scores[entry_id] = max(fused_scores.get(entry_id, 0), score)

        return fused_scores

    def delete(self, entry_id: str) -> bool:
        """删除文档

        Args:
            entry_id: 文档 ID

        Returns:
            bool: 是否删除成功
        """
        if entry_id not in self._documents:
            return False

        doc = self._documents.pop(entry_id)
        text = doc.get("text", "")

        # 从各索引删除
        if self.vector_collection is not None:
            try:
                self.vector_collection.delete(text)
            except Exception:
                pass

        if self.kv_collection is not None:
            try:
                self.kv_collection.delete(text)
            except Exception:
                pass

        self.logger.debug(f"Deleted document from hybrid memory: {entry_id[:16]}...")
        return True

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            "memory_count": len(self._documents),
            "fusion_strategy": self.fusion_strategy,
            "index_count": len(self.index_configs),
            "indexes": [c["name"] for c in self.index_configs],
        }
