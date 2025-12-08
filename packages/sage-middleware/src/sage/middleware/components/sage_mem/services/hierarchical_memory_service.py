"""Hierarchical Memory Service - 分层记忆存储

支持多层记忆结构:
1. two_tier: 双层 (STM + LTM)
2. three_tier: 三层 (STM + MTM + LTM)
3. functional: 功能分区 (episodic + semantic + procedural)

设计原则:
- Service : Collection = 1 : 1
- 使用单一 HybridCollection，通过 tier 元数据区分层级
- 每层使用独立的 VDB 索引（如 stm_index, mtm_index, ltm_index）
- 支持跨层迁移（remove_from_index + insert_to_index）
"""

from __future__ import annotations

import time
import uuid
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


class HierarchicalMemoryService(BaseService):
    """分层记忆服务

    设计原则: Service : Collection = 1 : 1
    底层使用单一 HybridCollection，每个层级对应一个 VDB 索引。
    数据只存一份，通过 tier 元数据和多索引实现分层。
    支持层间迁移（remove_from_index + insert_to_index）。
    """

    def __init__(
        self,
        tier_mode: Literal["two_tier", "three_tier", "functional"] = "three_tier",
        tier_capacities: dict[str, int] | None = None,
        migration_policy: Literal["overflow", "importance", "time"] = "overflow",
        embedding_dim: int = 384,
        collection_name: str = "hierarchical_memory",
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
            collection_name: Collection 名称
        """
        super().__init__()

        self.tier_mode = tier_mode
        self.migration_policy = migration_policy
        self.embedding_dim = embedding_dim
        self.collection_name = collection_name

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

        # 创建或获取单一 HybridCollection (Service:Collection = 1:1)
        self._init_collection()

        # 记录每层的条目数量（用于溢出检测）
        self._tier_counts: dict[str, int] = {}
        self._update_tier_counts()

        self.logger.info(
            f"HierarchicalMemoryService initialized: mode={tier_mode}, "
            f"tiers={self.tier_names}, capacities={self.tier_capacities}"
        )

    @classmethod
    def _get_default_data_dir(cls) -> str:
        """获取默认数据目录

        使用 SAGE 标准目录结构: .sage/data/hierarchical_memory
        """
        from sage.common.config.output_paths import get_appropriate_sage_dir

        sage_dir = get_appropriate_sage_dir()
        data_dir = sage_dir / "data" / "hierarchical_memory"
        data_dir.mkdir(parents=True, exist_ok=True)
        return str(data_dir)

    def _get_tier_index_name(self, tier_name: str) -> str:
        """获取层级对应的索引名"""
        return f"{tier_name}_index"

    def _init_collection(self) -> None:
        """初始化 HybridCollection 并为每个层级创建索引"""
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
                    "description": f"Hierarchical memory ({self.tier_mode})",
                }
            )

        self.collection = collection

        if self.collection is None:
            raise RuntimeError(f"Failed to create HybridCollection '{self.collection_name}'")

        # 为每个层级创建 VDB 索引
        existing_indexes = {idx["name"] for idx in self.collection.list_indexes()}
        self.logger.debug(f"Existing indexes: {existing_indexes}")

        for tier_name in self.tier_names:
            index_name = self._get_tier_index_name(tier_name)
            if index_name not in existing_indexes:
                success = self.collection.create_index(
                    {
                        "name": index_name,
                        "type": "vdb",
                        "dim": self.embedding_dim,
                        "backend_type": "FAISS",
                        "description": f"VDB index for tier: {tier_name}",
                    },
                    IndexType.VDB,
                )
                if success:
                    self.logger.info(
                        f"Created VDB index '{index_name}' for tier '{tier_name}' (dim={self.embedding_dim})"
                    )
                else:
                    self.logger.error(
                        f"Failed to create VDB index '{index_name}' for tier '{tier_name}'"
                    )
            else:
                self.logger.debug(f"Index '{index_name}' already exists for tier '{tier_name}'")

    def _update_tier_counts(self) -> None:
        """更新各层的计数"""
        for tier_name in self.tier_names:
            index_name = self._get_tier_index_name(tier_name)
            self._tier_counts[tier_name] = self.collection.get_index_count(index_name)

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

        数据只存一份，加入对应层级的索引。

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
        force_insert = False
        if insert_mode == "active" and insert_params:
            effective_tier = insert_params.get("target_tier")
            force_insert = insert_params.get("force", False)
            if "priority" in insert_params:
                metadata["priority"] = insert_params["priority"]

        # 如果 insert_params 没有指定，从 metadata 获取
        if effective_tier is None:
            effective_tier = metadata.get("tier")

        # 确定目标层级
        tier_name = effective_tier or self.tier_names[0]
        if tier_name not in self.tier_names:
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
        # 保存向量用于迁移（注意：这会增加存储开销）
        if vector is not None:
            vec_arr = (
                np.array(vector, dtype=np.float32) if not isinstance(vector, np.ndarray) else vector
            )
            full_metadata["_vector"] = vec_arr.tolist()  # 转为 list 便于序列化

        # 检查容量，必要时触发迁移（force_insert 跳过容量检查）
        capacity = self.tier_capacities.get(tier_name, -1)
        if not force_insert and capacity > 0 and self._tier_counts.get(tier_name, 0) >= capacity:
            self._migrate_overflow(tier_name)

        # 获取目标层级的索引名
        index_name = self._get_tier_index_name(tier_name)

        # 使用 HybridCollection 的 insert 方法
        # 数据只存一份，只加入对应层级的索引
        stable_id = self.collection.insert(
            content=entry,
            index_names=[index_name],
            vector=np.array(vector, dtype=np.float32) if vector is not None else None,
            metadata=full_metadata,
        )

        # 更新计数
        self._tier_counts[tier_name] = self._tier_counts.get(tier_name, 0) + 1

        self.logger.debug(f"Inserted entry to {tier_name}: {stable_id[:16]}...")
        return stable_id

    def _migrate_overflow(self, from_tier: str) -> int:
        """处理容量溢出迁移

        从 from_tier 索引移除，加入下一层索引（数据保留）。

        Args:
            from_tier: 源层级

        Returns:
            int: 迁移的条目数
        """
        tier_idx = self.tier_names.index(from_tier)
        if tier_idx >= len(self.tier_names) - 1:
            # 已经是最后一层，执行遗忘
            return self._forget_oldest(from_tier, count=1)

        to_tier = self.tier_names[tier_idx + 1]
        from_index = self._get_tier_index_name(from_tier)
        to_index = self._get_tier_index_name(to_tier)

        # 查找要迁移的条目（最旧的）
        oldest_items = self._find_oldest_items(from_tier, count=1)

        migrated = 0
        for item_id, item_vector in oldest_items:
            # 从源索引移除
            if self.collection.remove_from_index(item_id, from_index):
                # 加入目标索引
                if self.collection.insert_to_index(item_id, to_index, item_vector):
                    # 更新元数据中的 tier
                    old_meta = self.collection.get_metadata(item_id) or {}
                    old_meta["tier"] = to_tier
                    old_meta["migrated_at"] = time.time()
                    self.collection.update(item_id, new_metadata=old_meta)

                    # 更新计数
                    self._tier_counts[from_tier] = max(0, self._tier_counts.get(from_tier, 1) - 1)
                    self._tier_counts[to_tier] = self._tier_counts.get(to_tier, 0) + 1
                    migrated += 1

        self.logger.info(f"Migrated {migrated} entries: {from_tier} -> {to_tier}")
        return migrated

    def _find_oldest_items(
        self, tier_name: str, count: int = 1
    ) -> list[tuple[str, np.ndarray | None]]:
        """查找某层最旧的条目

        Args:
            tier_name: 层级名称
            count: 返回数量

        Returns:
            [(item_id, vector), ...]
        """
        # 获取所有数据 ID
        all_ids = self.collection.get_all_ids()

        # 过滤属于该层的条目
        tier_items = []
        for item_id in all_ids:
            meta = self.collection.get_metadata(item_id)
            if meta and meta.get("tier") == tier_name:
                timestamp = meta.get("timestamp", 0)
                # 获取保存的向量
                vec_list = meta.get("_vector")
                vec = np.array(vec_list, dtype=np.float32) if vec_list else None
                tier_items.append((item_id, timestamp, vec))

        # 按时间排序（最旧的在前）
        tier_items.sort(key=lambda x: x[1])

        return [(item_id, vec) for item_id, _, vec in tier_items[:count]]

    def _forget_oldest(self, tier_name: str, count: int = 1) -> int:
        """遗忘最旧的条目

        Args:
            tier_name: 层级名称
            count: 遗忘数量

        Returns:
            int: 实际遗忘的数量
        """
        oldest_items = self._find_oldest_items(tier_name, count)
        forgotten = 0

        for item_id, _ in oldest_items:
            if self.collection.delete(item_id):
                self._tier_counts[tier_name] = max(0, self._tier_counts.get(tier_name, 1) - 1)
                forgotten += 1

        self.logger.info(f"Forgot {forgotten} oldest entries from {tier_name}")
        return forgotten

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

        Args:
            query: 查询文本
            vector: 查询向量
            metadata: 检索参数:
                - tiers: 要搜索的层级列表（默认所有层）
                - method: "semantic" | "recent"
            top_k: 返回结果数量
            hints: 检索策略提示（可选，由 PreRetrieval route action 生成）
            threshold: 相似度阈值（可选，过滤低于阈值的结果）

        Returns:
            list[dict]: 检索结果
        """
        _ = hints  # 保留用于未来扩展
        metadata = metadata or {}
        tiers_to_search = metadata.get("tiers", self.tier_names)
        method = metadata.get("method", "semantic" if vector is not None else "recent")

        all_results: list[dict[str, Any]] = []

        if method == "semantic" and vector is not None:
            query_vec = np.array(vector, dtype=np.float32)

            for tier_name in tiers_to_search:
                if tier_name not in self.tier_names:
                    continue

                index_name = self._get_tier_index_name(tier_name)

                results = self.collection.retrieve(
                    query=query_vec,
                    index_name=index_name,
                    top_k=top_k,
                    with_metadata=True,
                )

                for item in results:
                    item["tier"] = tier_name
                    all_results.append(item)

        elif method == "recent":
            # 按时间获取最近的记忆
            for tier_name in tiers_to_search:
                items = self._find_oldest_items(tier_name, count=top_k)
                items.reverse()  # 最新的在前

                for item_id, _ in items:
                    text = self.collection.get_text(item_id)
                    item_meta = self.collection.get_metadata(item_id) or {}
                    all_results.append(
                        {
                            "id": item_id,
                            "text": text,
                            "metadata": item_meta,
                            "score": 1.0,  # 按时间排序，分数无意义
                            "tier": tier_name,
                        }
                    )

        # 按分数排序
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)

        # 格式化结果
        formatted_results = []
        for item in all_results[:top_k]:
            formatted_results.append(
                {
                    "text": item.get("text", ""),
                    "score": item.get("score", 0.0),
                    "entry_id": item.get("id", ""),
                    "metadata": item.get("metadata", {}),
                    "tier": item.get("tier", ""),
                }
            )

        # 应用相似度阈值过滤
        if threshold is not None:
            formatted_results = [r for r in formatted_results if r.get("score", 0) >= threshold]

        return formatted_results

    def migrate(self, entry_id: str, from_tier: str, to_tier: str) -> bool:
        """手动迁移条目

        Args:
            entry_id: 条目 ID
            from_tier: 源层级
            to_tier: 目标层级

        Returns:
            bool: 是否成功
        """
        if from_tier not in self.tier_names or to_tier not in self.tier_names:
            return False

        from_index = self._get_tier_index_name(from_tier)
        to_index = self._get_tier_index_name(to_tier)

        # 从源索引移除
        if not self.collection.remove_from_index(entry_id, from_index):
            return False

        # 获取该条目的向量（从元数据或重新计算）
        # 注意：VDB 索引需要向量，需要从存储获取
        meta = self.collection.get_metadata(entry_id) or {}
        vec_list = meta.get("_vector")
        vector = np.array(vec_list, dtype=np.float32) if vec_list else None

        # 加入目标索引
        if not self.collection.insert_to_index(entry_id, to_index, vector=vector):
            # 回滚：加回源索引
            self.collection.insert_to_index(entry_id, from_index, vector=vector)
            return False

        # 更新元数据
        meta = self.collection.get_metadata(entry_id) or {}
        meta["tier"] = to_tier
        meta["migrated_at"] = time.time()
        self.collection.update(entry_id, new_metadata=meta)

        # 更新计数
        self._tier_counts[from_tier] = max(0, self._tier_counts.get(from_tier, 1) - 1)
        self._tier_counts[to_tier] = self._tier_counts.get(to_tier, 0) + 1

        self.logger.info(f"Migrated {entry_id[:16]}... from {from_tier} to {to_tier}")
        return True

    def delete(self, entry_id: str) -> bool:
        """删除记忆条目

        Args:
            entry_id: 条目 ID

        Returns:
            bool: 是否删除成功
        """
        # 获取元数据以更新计数
        meta = self.collection.get_metadata(entry_id)
        tier_name = meta.get("tier") if meta else None

        if self.collection.delete(entry_id):
            if tier_name and tier_name in self._tier_counts:
                self._tier_counts[tier_name] = max(0, self._tier_counts[tier_name] - 1)
            return True

        return False

    def optimize(
        self,
        trigger: str = "auto",
        config: dict[str, Any] | None = None,
        entries: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """优化记忆结构

        Args:
            trigger: 触发类型 ("auto" | "migrate" | "forgetting")
            config: 来自 PostInsert 的配置参数（预留扩展）
            entries: 相关记忆条目（预留扩展）

        Returns:
            dict: 优化统计信息
        """
        # 预留：config 和 entries 可用于更复杂的优化策略
        _ = config
        _ = entries

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
                current_count = self._tier_counts.get(tier_name, 0)
                if capacity > 0 and current_count > capacity:
                    migrated = self._migrate_overflow(tier_name)
                    stats["migrated"] += migrated

        if trigger in ("auto", "forgetting"):
            # 检查最后一层是否需要遗忘
            last_tier = self.tier_names[-1]
            capacity = self.tier_capacities.get(last_tier, -1)
            current_count = self._tier_counts.get(last_tier, 0)
            if capacity > 0 and current_count > capacity:
                forgotten = self._forget_oldest(last_tier)
                stats["forgotten"] += forgotten

        self.logger.info(f"Optimization complete: {stats}")
        return stats

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        # 刷新计数
        self._update_tier_counts()

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
            "collection_name": self.collection_name,
        }

    def get_tier_stats(self) -> dict[str, dict]:
        """获取各层统计信息"""
        self._update_tier_counts()
        stats = {}
        for tier_name in self.tier_names:
            stats[tier_name] = {
                "count": self._tier_counts.get(tier_name, 0),
                "capacity": self.tier_capacities.get(tier_name, -1),
            }
        return stats
