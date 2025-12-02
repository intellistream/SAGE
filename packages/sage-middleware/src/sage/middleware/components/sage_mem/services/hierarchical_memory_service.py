"""Hierarchical Memory Service - 分层记忆存储

支持多层记忆结构:
1. two_tier: 双层 (STM + LTM)
2. three_tier: 三层 (STM + MTM + LTM)
3. functional: 功能分区 (episodic + semantic + procedural)

使用多个 VDBMemoryCollection 作为底层存储。
"""

from __future__ import annotations

import os
import time
import uuid
from typing import TYPE_CHECKING, Any, Literal

import numpy as np

from sage.middleware.components.sage_mem.neuromem.memory_collection.vdb_collection import (
    VDBMemoryCollection,
)
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager
from sage.platform.service import BaseService

if TYPE_CHECKING:
    pass


class HierarchicalMemoryService(BaseService):
    """分层记忆服务

    底层使用 MemoryManager + 多个 VDBMemoryCollection 存储。
    支持记忆在各层之间的迁移。
    """

    def __init__(
        self,
        tier_mode: Literal["two_tier", "three_tier", "functional"] = "three_tier",
        tier_capacities: dict[str, int] | None = None,
        migration_policy: Literal["overflow", "importance", "time"] = "overflow",
        embedding_dim: int = 384,
        collection_prefix: str = "hierarchical",
    ):
        """初始化分层记忆服务

        Args:
            tier_mode: 分层模式
                - "two_tier": STM + LTM
                - "three_tier": STM + MTM + LTM
                - "functional": episodic + semantic + procedural
            tier_capacities: 各层容量限制 (如 {"stm": 10, "mtm": 100, "ltm": -1})
            migration_policy: 迁移策略
                - "overflow": 容量溢出时迁移
                - "importance": 按重要性迁移
                - "time": 按时间迁移
            embedding_dim: 向量维度
            collection_prefix: Collection 名称前缀
        """
        super().__init__()

        self.tier_mode = tier_mode
        self.migration_policy = migration_policy
        self.embedding_dim = embedding_dim
        self.collection_prefix = collection_prefix

        # 根据模式确定层级名称
        if tier_mode == "two_tier":
            self.tier_names = ["stm", "ltm"]
        elif tier_mode == "three_tier":
            self.tier_names = ["stm", "mtm", "ltm"]
        else:  # functional
            self.tier_names = ["episodic", "semantic", "procedural"]

        # 设置容量
        default_capacities = {
            "stm": 10,
            "mtm": 100,
            "ltm": -1,
            "episodic": 100,
            "semantic": -1,
            "procedural": 50,
        }
        self.tier_capacities = tier_capacities or {
            name: default_capacities.get(name, -1) for name in self.tier_names
        }

        # 初始化 MemoryManager
        self.manager = MemoryManager(self._get_default_data_dir())

        # 为每一层创建 VDBMemoryCollection
        self.tier_collections: dict[str, VDBMemoryCollection] = {}
        for tier_name in self.tier_names:
            collection_name = f"{collection_prefix}_{tier_name}"
            if self.manager.has_collection(collection_name):
                collection = self.manager.get_collection(collection_name)
            else:
                collection = self.manager.create_collection(
                    {
                        "name": collection_name,
                        "backend_type": "VDB",
                        "description": f"Hierarchical memory tier: {tier_name}",
                    }
                )

            if isinstance(collection, VDBMemoryCollection):
                # 确保有 global_index
                if "global_index" not in collection.index_info:
                    collection.create_index(
                        {
                            "name": "global_index",
                            "dim": embedding_dim,
                            "backend_type": "FAISS",
                            "description": f"Index for {tier_name} tier",
                        }
                    )
                self.tier_collections[tier_name] = collection

        # 记录每层的条目数量（用于溢出检测）
        self._tier_counts: dict[str, int] = dict.fromkeys(self.tier_names, 0)

        self.logger.info(
            f"HierarchicalMemoryService initialized: mode={tier_mode}, "
            f"tiers={self.tier_names}, capacities={self.tier_capacities}"
        )

    @classmethod
    def _get_default_data_dir(cls) -> str:
        """获取默认数据目录"""
        cur_dir = os.getcwd()
        data_dir = os.path.join(cur_dir, "data", "hierarchical_memory")
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
        """插入记忆条目

        支持两种插入模式：
        - passive: 由服务自行决定存储方式（默认存入第一层）
        - active: 根据 insert_params 指定存储方式

        Args:
            entry: 文本内容
            vector: embedding 向量
            metadata: 元数据，可包含:
                - importance: 重要性分数 (0-1)
                - tier: 指定目标层级
            insert_mode: 插入模式 ("active" | "passive")
            insert_params: 主动插入参数
                - target_tier: 目标层级
                - priority: 优先级
                - force: 是否强制插入（跳过容量检查）

        Returns:
            str: 条目 ID
        """
        metadata = metadata or {}

        # 处理插入模式
        effective_tier = None
        if insert_mode == "active" and insert_params:
            # 主动插入：从 insert_params 获取参数
            effective_tier = insert_params.get("target_tier")
            force_insert = insert_params.get("force", False)
            if "priority" in insert_params:
                metadata["priority"] = insert_params["priority"]
        else:
            # 被动插入：使用默认行为
            force_insert = False

        # 如果 insert_params 没有指定，从 metadata 获取
        if effective_tier is None:
            effective_tier = metadata.get("tier")

        # 确定目标层级
        tier_name = effective_tier or self.tier_names[0]
        if tier_name not in self.tier_collections:
            tier_name = self.tier_names[0]

        # 生成 ID
        entry_id = metadata.get("id", str(uuid.uuid4()))
        timestamp = time.time()

        # 准备元数据
        full_metadata = metadata.copy()
        full_metadata["entry_id"] = entry_id
        full_metadata["timestamp"] = timestamp
        full_metadata["tier"] = tier_name
        full_metadata["importance"] = metadata.get("importance", 0.5)

        # 检查容量，必要时触发迁移（force_insert 跳过容量检查）
        capacity = self.tier_capacities.get(tier_name, -1)
        if not force_insert and capacity > 0 and self._tier_counts[tier_name] >= capacity:
            self._migrate_overflow(tier_name)

        # 插入到目标层的 collection
        collection = self.tier_collections[tier_name]
        if vector is not None:
            vec = np.array(vector, dtype=np.float32)
            collection.insert(
                index_name="global_index",
                raw_data=entry,
                vector=vec,
                metadata=full_metadata,
            )
        else:
            # 没有向量时，调用父类 BaseMemoryCollection 的 insert
            collection.insert(entry, full_metadata)

        self._tier_counts[tier_name] += 1

        self.logger.debug(f"Inserted entry to {tier_name}: {entry_id[:16]}...")
        return entry_id

    def _migrate_overflow(self, from_tier: str) -> int:
        """处理容量溢出迁移

        Args:
            from_tier: 源层级

        Returns:
            int: 迁移的条目数
        """
        tier_idx = self.tier_names.index(from_tier)
        if tier_idx >= len(self.tier_names) - 1:
            # 已经是最后一层，执行遗忘
            return self._forget_oldest(from_tier, count=1)

        # 迁移到下一层
        to_tier = self.tier_names[tier_idx + 1]
        # TODO: 实现具体的迁移逻辑
        self.logger.info(f"Migration triggered: {from_tier} -> {to_tier}")
        return 0

    def _forget_oldest(self, tier_name: str, count: int = 1) -> int:
        """遗忘最旧的条目

        Args:
            tier_name: 层级名称
            count: 遗忘数量

        Returns:
            int: 实际遗忘的数量
        """
        # TODO: 实现遗忘逻辑
        self.logger.info(f"Forgetting {count} oldest entries from {tier_name}")
        return 0

    def retrieve(
        self,
        query: str | None = None,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """检索记忆

        Args:
            query: 查询文本
            vector: 查询向量
            metadata: 检索参数:
                - tiers: 要搜索的层级列表
                - method: "semantic" | "recent"
            top_k: 返回结果数量

        Returns:
            list[dict]: 检索结果
        """
        metadata = metadata or {}
        tiers_to_search = metadata.get("tiers", self.tier_names)
        method = metadata.get("method", "semantic" if vector is not None else "recent")

        all_results = []

        for tier_name in tiers_to_search:
            if tier_name not in self.tier_collections:
                continue

            collection = self.tier_collections[tier_name]

            if method == "semantic" and vector is not None:
                query_vec = np.array(vector, dtype=np.float32)
                results = collection.retrieve(
                    query_text=query,
                    query_vector=query_vec,
                    index_name="global_index",
                    topk=top_k,
                    with_metadata=True,
                )
                if results:
                    for r in results:
                        if isinstance(r, dict):
                            r["tier"] = tier_name
                    all_results.extend(results)
            else:
                # 获取最近的记忆（按时间）
                # TODO: 实现基于时间的检索
                pass

        # 按分数排序
        all_results.sort(
            key=lambda x: x.get("score", 0) if isinstance(x, dict) else 0, reverse=True
        )
        return all_results[:top_k]

    def delete(self, entry_id: str) -> bool:
        """删除记忆条目

        Args:
            entry_id: 条目 ID

        Returns:
            bool: 是否删除成功
        """
        for tier_name, collection in self.tier_collections.items():
            try:
                # 尝试在每一层删除
                collection.delete(entry_id)
                self._tier_counts[tier_name] = max(0, self._tier_counts[tier_name] - 1)
                self.logger.debug(f"Deleted entry {entry_id[:16]}... from {tier_name}")
                return True
            except Exception:
                continue

        return False

    def optimize(self, trigger: str = "auto") -> dict[str, Any]:
        """优化记忆结构

        Args:
            trigger: 触发类型 ("auto" | "migrate" | "forgetting")

        Returns:
            dict: 优化统计信息
        """
        stats = {
            "success": True,
            "trigger": trigger,
            "migrated": 0,
            "forgotten": 0,
        }

        if trigger in ("auto", "migrate"):
            # 检查各层是否需要迁移
            for tier_name in self.tier_names[:-1]:
                capacity = self.tier_capacities.get(tier_name, -1)
                if capacity > 0 and self._tier_counts[tier_name] > capacity:
                    migrated = self._migrate_overflow(tier_name)
                    stats["migrated"] += migrated

        if trigger in ("auto", "forgetting"):
            # 检查最后一层是否需要遗忘
            last_tier = self.tier_names[-1]
            capacity = self.tier_capacities.get(last_tier, -1)
            if capacity > 0 and self._tier_counts[last_tier] > capacity:
                forgotten = self._forget_oldest(last_tier)
                stats["forgotten"] += forgotten

        self.logger.info(f"Optimization complete: {stats}")
        return stats

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        tier_stats = {}
        for tier_name in self.tier_names:
            tier_stats[tier_name] = {
                "count": self._tier_counts.get(tier_name, 0),
                "capacity": self.tier_capacities.get(tier_name, -1),
            }

        return {
            "memory_count": sum(self._tier_counts.values()),
            "tier_mode": self.tier_mode,
            "tier_distribution": tier_stats,
            "migration_policy": self.migration_policy,
        }

    def get_tier_stats(self) -> dict[str, dict]:
        """获取各层统计信息"""
        stats = {}
        for tier_name in self.tier_names:
            stats[tier_name] = {
                "count": self._tier_counts.get(tier_name, 0),
                "capacity": self.tier_capacities.get(tier_name, -1),
            }
        return stats
