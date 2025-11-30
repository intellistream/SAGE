"""Hierarchical Memory Service - 分层记忆存储

支持三种模式:
1. two_tier: 双层结构 (STM + LTM) - 参考 MemoryBank, LD-Agent
2. three_tier: 三层结构 (STM + MTM + LTM) - 参考 MemoryOS
3. functional: 功能分层 (Core + Archival + Recall) - 参考 MemGPT
"""

from __future__ import annotations

import json
import time
import uuid
from collections import deque
from datetime import datetime
from typing import Any, Literal

import numpy as np

from sage.platform.service import BaseService


def get_timestamp() -> str:
    """获取当前时间戳"""
    return datetime.now().strftime("%Y%m%d%H%M%S")


def compute_time_decay(
    last_time: str,
    current_time: str,
    tau_hours: float = 24.0,
) -> float:
    """计算时间衰减因子"""
    try:
        last_dt = datetime.strptime(last_time, "%Y%m%d%H%M%S")
        current_dt = datetime.strptime(current_time, "%Y%m%d%H%M%S")
        hours_diff = (current_dt - last_dt).total_seconds() / 3600
        return np.exp(-hours_diff / tau_hours)
    except Exception:
        return 1.0


class HierarchicalMemoryService(BaseService):
    """分层记忆服务

    支持 two_tier, three_tier, functional 三种模式。
    """

    def __init__(
        self,
        tier_mode: Literal["two_tier", "three_tier", "functional"] = "three_tier",
        tier_capacities: dict[str, int] | None = None,
        migration_policy: Literal["time", "heat", "manual", "overflow"] = "overflow",
        migration_threshold: float = 0.7,
        migration_interval: int = 3600,
        embedding_dim: int = 768,
        heat_alpha: float = 1.0,
        heat_beta: float = 1.0,
        heat_gamma: float = 1.0,
    ):
        """初始化分层记忆服务

        Args:
            tier_mode: 分层模式
            tier_capacities: 各层容量配置
            migration_policy: 迁移策略
            migration_threshold: 热度迁移阈值
            migration_interval: 时间迁移间隔(秒)
            embedding_dim: 向量维度
            heat_alpha: 访问次数权重
            heat_beta: 交互长度权重
            heat_gamma: 时间衰减权重
        """
        super().__init__()

        self.tier_mode = tier_mode
        self.migration_policy = migration_policy
        self.migration_threshold = migration_threshold
        self.migration_interval = migration_interval
        self.embedding_dim = embedding_dim
        self.heat_alpha = heat_alpha
        self.heat_beta = heat_beta
        self.heat_gamma = heat_gamma

        # 初始化各层容量
        if tier_mode == "two_tier":
            self.tier_names = ["stm", "ltm"]
            default_capacities = {"stm": 100, "ltm": -1}
        elif tier_mode == "three_tier":
            self.tier_names = ["stm", "mtm", "ltm"]
            default_capacities = {"stm": 100, "mtm": 1000, "ltm": -1}
        else:  # functional
            self.tier_names = ["core", "archival", "recall"]
            default_capacities = {"core": 50, "archival": -1, "recall": 500}

        self.tier_capacities = tier_capacities or default_capacities

        # 初始化存储
        self._init_storage()

        # 上次迁移时间
        self._last_migration_time = time.time()

    def _init_storage(self) -> None:
        """初始化存储结构"""
        self.tiers: dict[str, Any] = {}

        for tier_name in self.tier_names:
            capacity = self.tier_capacities.get(tier_name, -1)
            if capacity > 0:
                self.tiers[tier_name] = {
                    "data": deque(maxlen=capacity),
                    "capacity": capacity,
                    "embeddings": {},
                    "metadata": {},
                }
            else:
                self.tiers[tier_name] = {
                    "data": [],
                    "capacity": -1,
                    "embeddings": {},
                    "metadata": {},
                }

    def insert(
        self,
        entry: str,
        vector: np.ndarray | None = None,
        metadata: dict | None = None,
    ) -> str:
        """插入记忆条目

        Args:
            entry: 文本内容
            vector: 向量表示
            metadata: 元数据，可包含:
                - tier: 指定层级
                - importance: 重要性评分
                - keywords: 关键词
                - summary: 摘要

        Returns:
            entry_id: 条目 ID
        """
        metadata = metadata or {}
        entry_id = metadata.get("id", str(uuid.uuid4()))
        target_tier = metadata.get("tier", self.tier_names[0])

        # 检查是否需要迁移
        if self.migration_policy == "overflow":
            self._check_overflow_migration(target_tier)
        elif self.migration_policy == "time":
            self._check_time_migration()

        # 创建记忆条目
        memory_entry = {
            "id": entry_id,
            "content": entry,
            "timestamp": get_timestamp(),
            "last_accessed": get_timestamp(),
            "access_count": 0,
            "heat": 1.0,
            "importance": metadata.get("importance", 1.0),
            "keywords": metadata.get("keywords", []),
            "summary": metadata.get("summary", ""),
            "metadata": metadata,
        }

        # 添加到目标层
        tier_storage = self.tiers[target_tier]
        if isinstance(tier_storage["data"], deque):
            tier_storage["data"].append(memory_entry)
        else:
            tier_storage["data"].append(memory_entry)

        # 存储向量
        if vector is not None:
            tier_storage["embeddings"][entry_id] = np.array(vector, dtype=np.float32)

        return entry_id

    def retrieve(
        self,
        query: str | None = None,
        vector: np.ndarray | None = None,
        metadata: dict | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """检索记忆

        Args:
            query: 查询文本
            vector: 查询向量
            metadata: 查询元数据，可包含:
                - tiers: 要检索的层级列表
                - method: 检索方法 ("all" | "semantic" | "recent")
            top_k: 返回结果数

        Returns:
            检索结果列表
        """
        metadata = metadata or {}
        tiers_to_search = metadata.get("tiers", self.tier_names)
        method = metadata.get("method", "semantic" if vector is not None else "recent")

        all_results = []

        for tier_name in tiers_to_search:
            if tier_name not in self.tiers:
                continue

            tier_storage = self.tiers[tier_name]

            if method == "semantic" and vector is not None:
                results = self._semantic_search(tier_storage, vector, top_k)
            elif method == "recent":
                results = self._recent_search(tier_storage, top_k)
            else:
                results = self._all_search(tier_storage, top_k)

            # 更新访问统计
            for r in results:
                self._update_access_stats(tier_name, r.get("id"))

            all_results.extend(results)

        # 按分数排序
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)

        return all_results[:top_k]

    def _semantic_search(
        self,
        tier_storage: dict,
        query_vector: np.ndarray,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """语义检索"""
        embeddings = tier_storage["embeddings"]
        if not embeddings:
            return []

        query_vec = np.array(query_vector, dtype=np.float32)
        if len(query_vec.shape) == 1:
            query_vec = query_vec.reshape(1, -1)

        entry_ids = list(embeddings.keys())
        emb_matrix = np.array([embeddings[eid] for eid in entry_ids], dtype=np.float32)

        if len(emb_matrix) == 0:
            return []

        # 归一化
        query_norm = query_vec / (np.linalg.norm(query_vec, axis=1, keepdims=True) + 1e-8)
        emb_norm = emb_matrix / (np.linalg.norm(emb_matrix, axis=1, keepdims=True) + 1e-8)

        # 计算相似度
        scores = np.dot(emb_norm, query_norm.T).flatten()

        # 获取 top-k
        top_indices = np.argsort(scores)[::-1][:top_k]

        # 构建结果
        data_list = list(tier_storage["data"])
        id_to_entry = {e["id"]: e for e in data_list}

        results = []
        for idx in top_indices:
            entry_id = entry_ids[idx]
            entry = id_to_entry.get(entry_id, {})
            results.append(
                {
                    "id": entry_id,
                    "text": entry.get("content", ""),
                    "score": float(scores[idx]),
                    "metadata": entry.get("metadata", {}),
                }
            )

        return results

    def _recent_search(
        self,
        tier_storage: dict,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """最近访问检索"""
        data_list = list(tier_storage["data"])

        # 按时间戳排序
        sorted_data = sorted(data_list, key=lambda x: x.get("timestamp", ""), reverse=True)

        results = []
        for entry in sorted_data[:top_k]:
            results.append(
                {
                    "id": entry.get("id", ""),
                    "text": entry.get("content", ""),
                    "score": 1.0,
                    "metadata": entry.get("metadata", {}),
                }
            )

        return results

    def _all_search(
        self,
        tier_storage: dict,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """返回所有记忆"""
        data_list = list(tier_storage["data"])

        results = []
        for entry in data_list[:top_k]:
            results.append(
                {
                    "id": entry.get("id", ""),
                    "text": entry.get("content", ""),
                    "score": entry.get("heat", 1.0),
                    "metadata": entry.get("metadata", {}),
                }
            )

        return results

    def _update_access_stats(self, tier_name: str, entry_id: str | None) -> None:
        """更新访问统计"""
        if entry_id is None:
            return

        tier_storage = self.tiers[tier_name]
        data_list = list(tier_storage["data"])

        for entry in data_list:
            if entry.get("id") == entry_id:
                entry["access_count"] = entry.get("access_count", 0) + 1
                entry["last_accessed"] = get_timestamp()
                entry["heat"] = self._compute_heat(entry)
                break

    def _compute_heat(self, entry: dict) -> float:
        """计算热度值 (参考 MemoryOS)"""
        n_visit = entry.get("access_count", 0)
        l_interaction = len(entry.get("content", ""))
        r_recency = compute_time_decay(
            entry.get("last_accessed", get_timestamp()),
            get_timestamp(),
        )

        return (
            self.heat_alpha * n_visit
            + self.heat_beta * (l_interaction / 1000)
            + self.heat_gamma * r_recency
        )

    def _check_overflow_migration(self, current_tier: str) -> None:
        """检查溢出迁移"""
        tier_idx = self.tier_names.index(current_tier)
        if tier_idx >= len(self.tier_names) - 1:
            return

        tier_storage = self.tiers[current_tier]
        capacity = tier_storage["capacity"]

        if capacity > 0 and len(tier_storage["data"]) >= capacity:
            # 迁移最旧的条目到下一层
            next_tier = self.tier_names[tier_idx + 1]
            self._migrate_entry(current_tier, next_tier)

    def _check_time_migration(self) -> None:
        """检查时间迁移"""
        current_time = time.time()
        if current_time - self._last_migration_time < self.migration_interval:
            return

        self._last_migration_time = current_time

        # 对每一层执行迁移检查
        for i, tier_name in enumerate(self.tier_names[:-1]):
            next_tier = self.tier_names[i + 1]
            self._migrate_by_time(tier_name, next_tier)

    def _migrate_entry(self, from_tier: str, to_tier: str) -> None:
        """迁移单个条目"""
        from_storage = self.tiers[from_tier]
        to_storage = self.tiers[to_tier]

        if not from_storage["data"]:
            return

        # 获取最旧的条目
        if isinstance(from_storage["data"], deque):
            oldest_entry = from_storage["data"].popleft()
        else:
            oldest_entry = from_storage["data"].pop(0)

        entry_id = oldest_entry.get("id")

        # 迁移向量
        if entry_id in from_storage["embeddings"]:
            to_storage["embeddings"][entry_id] = from_storage["embeddings"].pop(entry_id)

        # 添加到目标层
        if isinstance(to_storage["data"], deque):
            to_storage["data"].append(oldest_entry)
        else:
            to_storage["data"].append(oldest_entry)

    def _migrate_by_time(self, from_tier: str, to_tier: str) -> None:
        """按时间迁移多个条目"""
        from_storage = self.tiers[from_tier]
        current_time = get_timestamp()

        entries_to_migrate = []
        remaining_entries = []

        for entry in list(from_storage["data"]):
            decay = compute_time_decay(
                entry.get("last_accessed", current_time),
                current_time,
                tau_hours=24.0,
            )
            if decay < self.migration_threshold:
                entries_to_migrate.append(entry)
            else:
                remaining_entries.append(entry)

        # 更新源层
        if isinstance(from_storage["data"], deque):
            from_storage["data"].clear()
            from_storage["data"].extend(remaining_entries)
        else:
            from_storage["data"] = remaining_entries

        # 迁移到目标层
        to_storage = self.tiers[to_tier]
        for entry in entries_to_migrate:
            entry_id = entry.get("id")

            if entry_id in from_storage["embeddings"]:
                to_storage["embeddings"][entry_id] = from_storage["embeddings"].pop(entry_id)

            if isinstance(to_storage["data"], deque):
                to_storage["data"].append(entry)
            else:
                to_storage["data"].append(entry)

    def migrate_by_heat(self, heat_threshold: float | None = None) -> int:
        """按热度迁移 (手动触发)"""
        threshold = heat_threshold or self.migration_threshold
        migrated_count = 0

        for i, tier_name in enumerate(self.tier_names[:-1]):
            next_tier = self.tier_names[i + 1]
            from_storage = self.tiers[tier_name]
            to_storage = self.tiers[next_tier]

            entries_to_migrate = []
            remaining_entries = []

            for entry in list(from_storage["data"]):
                heat = self._compute_heat(entry)
                entry["heat"] = heat
                if heat < threshold:
                    entries_to_migrate.append(entry)
                else:
                    remaining_entries.append(entry)

            # 更新源层
            if isinstance(from_storage["data"], deque):
                from_storage["data"].clear()
                from_storage["data"].extend(remaining_entries)
            else:
                from_storage["data"] = remaining_entries

            # 迁移到目标层
            for entry in entries_to_migrate:
                entry_id = entry.get("id")

                if entry_id in from_storage["embeddings"]:
                    to_storage["embeddings"][entry_id] = from_storage["embeddings"].pop(entry_id)

                if isinstance(to_storage["data"], deque):
                    to_storage["data"].append(entry)
                else:
                    to_storage["data"].append(entry)

                migrated_count += 1

        return migrated_count

    def get_tier_stats(self) -> dict[str, dict]:
        """获取各层统计信息"""
        stats = {}
        for tier_name in self.tier_names:
            tier_storage = self.tiers[tier_name]
            stats[tier_name] = {
                "count": len(tier_storage["data"]),
                "capacity": tier_storage["capacity"],
                "embeddings_count": len(tier_storage["embeddings"]),
            }
        return stats

    def consolidate(self, tier_name: str) -> str | None:
        """整合记忆 (生成摘要)

        Args:
            tier_name: 要整合的层级

        Returns:
            摘要文本
        """
        if tier_name not in self.tiers:
            return None

        tier_storage = self.tiers[tier_name]
        data_list = list(tier_storage["data"])

        if not data_list:
            return None

        # 简单拼接所有内容作为摘要基础
        contents = [entry.get("content", "") for entry in data_list]
        summary = " | ".join(contents[:10])  # 只取前10条

        return summary

    def clear_tier(self, tier_name: str) -> bool:
        """清空指定层级"""
        if tier_name not in self.tiers:
            return False

        tier_storage = self.tiers[tier_name]
        if isinstance(tier_storage["data"], deque):
            tier_storage["data"].clear()
        else:
            tier_storage["data"] = []

        tier_storage["embeddings"] = {}
        return True


if __name__ == "__main__":

    def test_hierarchical_memory():
        print("\n" + "=" * 70)
        print("HierarchicalMemoryService 测试")
        print("=" * 70 + "\n")

        # 三层模式测试
        service = HierarchicalMemoryService(
            tier_mode="three_tier",
            tier_capacities={"stm": 3, "mtm": 10, "ltm": -1},
            migration_policy="overflow",
        )

        # 插入记忆
        for i in range(5):
            vec = np.random.randn(768).astype(np.float32)
            service.insert(
                f"这是第 {i + 1} 条记忆内容",
                vector=vec,
                metadata={"importance": float(i) / 5},
            )
            print(f"插入第 {i + 1} 条记忆")

        # 打印统计
        stats = service.get_tier_stats()
        print(f"\n层级统计: {json.dumps(stats, indent=2)}")

        # 检索测试
        query_vec = np.random.randn(768).astype(np.float32)
        results = service.retrieve(
            vector=query_vec,
            metadata={"method": "semantic"},
            top_k=3,
        )
        print(f"\n检索结果: {len(results)} 条")
        for r in results:
            print(f"  - {r['text'][:30]}... (score: {r['score']:.4f})")

        print("\n✅ 测试完成!")

    test_hierarchical_memory()
