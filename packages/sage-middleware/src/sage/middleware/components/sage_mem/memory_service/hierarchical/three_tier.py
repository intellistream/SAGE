"""三层记忆服务 - Hierarchical 类

支持三层记忆结构 (STM + MTM + LTM)，用于模拟人类记忆的分层特性。

设计原则:
- Service : Collection = 1 : 1
- 使用单一 HybridCollection，通过 tier 元数据区分层级
- 每层使用独立的 VDB 索引（stm_index, mtm_index, ltm_index）
- 支持跨层迁移（remove_from_index + insert_to_index）

论文算法实现:
- MemoryBank: Ebbinghaus 遗忘曲线 (R = e^(-t/S))
- MemoryOS: Heat Score 计算 (基于访问次数、交互深度、时间衰减)
- MemGPT: Core Memory + Recall Memory
- SECOM: 语义层级分类

Layer: L4 (Middleware)
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Literal

import numpy as np

from sage.common.config.output_paths import get_appropriate_sage_dir
from sage.kernel.runtime.factory.service_factory import ServiceFactory
from sage.middleware.components.sage_mem.neuromem.memory_collection.base_collection import (
    IndexType,
)
from sage.middleware.components.sage_mem.neuromem.memory_collection.hybrid_collection import (
    HybridCollection,
)
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager

from ..base_service import BaseMemoryService

if TYPE_CHECKING:
    pass


class ThreeTierMemoryService(BaseMemoryService):
    """三层记忆服务 - Hierarchical 类

    三层结构（STM/MTM/LTM），支持层间迁移和容量管理。

    设计原则：
    - Service : Collection = 1 : 1
    - 使用单一 HybridCollection
    - 每层对应一个独立的 VDB 索引
    - 支持 overflow/importance/time 迁移策略
    """

    def __init__(
        self,
        tier_capacities: dict[str, int] | None = None,
        migration_policy: Literal["overflow", "importance", "time", "none"] = "overflow",
        embedding_dim: int = 384,
        collection_name: str = "three_tier_memory",
        # MemGPT 特有配置
        use_core_embedding: bool = True,
        use_recall_hybrid: bool = False,
        rrf_k: int = 60,
        vector_weight: float = 0.5,
        fts_weight: float = 0.5,
    ):
        """初始化三层记忆服务

        Args:
            tier_capacities: 各层容量限制 (如 {"stm": 10, "mtm": 100, "ltm": -1})
                -1 表示无限制
            migration_policy: 迁移策略
                - "overflow": 容量溢出时迁移到下一层
                - "importance": 按重要性迁移（基于 Heat Score）
                - "time": 按时间迁移（遗忘曲线）
                - "none": 不迁移
            embedding_dim: embedding 向量维度
            collection_name: NeuroMem collection 名称
            use_core_embedding: MemGPT 核心记忆是否使用 embedding
            use_recall_hybrid: MemGPT 检索记忆是否使用混合检索
            rrf_k: RRF 融合参数
            vector_weight: 向量检索权重
            fts_weight: 文本检索权重
        """
        super().__init__()

        self.tier_names = ["stm", "mtm", "ltm"]
        self.migration_policy = migration_policy
        self.embedding_dim = embedding_dim
        self.collection_name = collection_name

        # MemGPT 特有配置
        self.use_core_embedding = use_core_embedding
        self.use_recall_hybrid = use_recall_hybrid
        self.rrf_k = rrf_k
        self.vector_weight = vector_weight
        self.fts_weight = fts_weight

        # 设置容量（默认值：stm=10, mtm=100, ltm=-1）
        default_capacities = {"stm": 10, "mtm": 100, "ltm": -1}
        self.tier_capacities = tier_capacities or default_capacities

        # 初始化 MemoryManager
        self.manager = MemoryManager(self._get_default_data_dir())

        # 创建或获取单一 HybridCollection (Service:Collection = 1:1)
        self._init_collection()

        # 记录每层的条目数量（用于溢出检测）
        self._tier_counts: dict[str, int] = {}
        self._update_tier_counts()

        # 插入顺序追踪（用于遗忘曲线时间模拟）
        self._insertion_counter: int = 0  # 全局插入计数器
        self._time_span_days: float = 5.0  # 数据集时间跨度(天)

        # 被动插入状态管理（溢出待处理）
        self._pending_items: list[dict] = []
        self._pending_action: str | None = None  # "migrate" | "forget" | None
        self._pending_source_tier: str | None = None
        self._pending_target_tier: str | None = None

        self.logger.info(
            f"ThreeTierMemoryService initialized: "
            f"capacities={self.tier_capacities}, policy={migration_policy}"
        )

    @classmethod
    def from_config(cls, service_name: str, config: Any) -> ServiceFactory:
        """从配置创建 ServiceFactory

        配置示例:
            services:
              hierarchical.three_tier:
                tier_capacities:
                  stm: 10
                  mtm: 100
                  ltm: -1
                migration_policy: overflow
                embedding_dim: 384
                collection_name: three_tier_memory
                use_core_embedding: true
                use_recall_hybrid: false
        """
        # 读取配置
        tier_capacities = config.get(f"services.{service_name}.tier_capacities")
        migration_policy = config.get(f"services.{service_name}.migration_policy", "overflow")
        embedding_dim = config.get(f"services.{service_name}.embedding_dim", 384)
        collection_name = config.get(
            f"services.{service_name}.collection_name",
            f"three_tier_{service_name.replace('.', '_')}",
        )

        # MemGPT 特有配置
        use_core_embedding = config.get(f"services.{service_name}.use_core_embedding", True)
        use_recall_hybrid = config.get(f"services.{service_name}.use_recall_hybrid", False)
        rrf_k = config.get(f"services.{service_name}.rrf_k", 60)
        vector_weight = config.get(f"services.{service_name}.vector_weight", 0.5)
        fts_weight = config.get(f"services.{service_name}.fts_weight", 0.5)

        return ServiceFactory(
            service_name=service_name,
            service_class=cls,
            service_kwargs={
                "tier_capacities": tier_capacities,
                "migration_policy": migration_policy,
                "embedding_dim": embedding_dim,
                "collection_name": collection_name,
                "use_core_embedding": use_core_embedding,
                "use_recall_hybrid": use_recall_hybrid,
                "rrf_k": rrf_k,
                "vector_weight": vector_weight,
                "fts_weight": fts_weight,
            },
        )

    def _get_default_data_dir(self) -> str:
        """获取默认数据目录"""
        sage_dir = get_appropriate_sage_dir()
        data_dir = sage_dir / "data" / "three_tier_memory"
        data_dir.mkdir(parents=True, exist_ok=True)
        return str(data_dir)

    def _get_tier_index_name(self, tier_name: str) -> str:
        """获取层级对应的索引名"""
        return f"{tier_name}_index"

    def _init_collection(self) -> None:
        """初始化 HybridCollection 并为每个层级创建索引"""
        # 创建或获取 HybridCollection
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
                    "backend_type": "hybrid",
                    "description": "Three-tier hierarchical memory (STM/MTM/LTM)",
                }
            )

        self.collection: HybridCollection = collection

        if self.collection is None:
            raise RuntimeError(f"Failed to create HybridCollection '{self.collection_name}'")

        # 为每个层级创建独立的 VDB 索引
        for tier in self.tier_names:
            index_name = self._get_tier_index_name(tier)
            if index_name not in self.collection.indexes:
                self.collection.create_index(
                    {
                        "name": index_name,
                        "type": IndexType.VDB,
                        "dim": self.embedding_dim,
                        "index_type": "IndexFlatL2",
                    }
                )

    def _update_tier_counts(self) -> None:
        """更新每层的条目数量统计"""
        self._tier_counts = {}
        for tier in self.tier_names:
            index_name = self._get_tier_index_name(tier)
            if index_name in self.collection.indexes:
                index_info = self.collection.list_indexes()
                for info in index_info:
                    if info.get("name") == index_name:
                        self._tier_counts[tier] = info.get("item_count", 0)
                        break
            else:
                self._tier_counts[tier] = 0

    def _check_overflow(self, tier: str) -> bool:
        """检查层级是否溢出"""
        capacity = self.tier_capacities.get(tier, -1)
        if capacity == -1:
            return False
        current_count = self._tier_counts.get(tier, 0)
        return current_count >= capacity

    def _migrate_overflow(self, tier: str) -> None:
        """处理层级溢出（迁移到下一层）"""
        if tier == "ltm":
            # LTM 溢出：删除最旧的记忆
            self._delete_oldest(tier)
            return

        # 确定目标层级
        tier_idx = self.tier_names.index(tier)
        if tier_idx >= len(self.tier_names) - 1:
            return
        target_tier = self.tier_names[tier_idx + 1]

        # 获取最旧的记忆（简化实现：按插入顺序）
        index_name = self._get_tier_index_name(tier)
        results = self.collection.retrieve(
            query=None,
            index_names=[index_name],
            top_k=1,
            with_metadata=True,
        )

        if results:
            item_id = results[0].get("stable_id")
            if item_id:
                # 迁移到下一层
                target_index = self._get_tier_index_name(target_tier)
                self.collection.remove_from_index(item_id, index_name)
                self.collection.insert_to_index(item_id, target_index)

                # 更新元数据中的 tier
                metadata = self.collection.metadata_storage.get(item_id)
                if metadata:
                    metadata["tier"] = target_tier
                    self.collection.metadata_storage.update(item_id, metadata)

                self.logger.debug(f"Migrated memory {item_id} from {tier} to {target_tier}")

    def _delete_oldest(self, tier: str) -> None:
        """删除最旧的记忆"""
        index_name = self._get_tier_index_name(tier)
        results = self.collection.retrieve(
            query=None,
            index_names=[index_name],
            top_k=1,
            with_metadata=True,
        )

        if results:
            item_id = results[0].get("stable_id")
            if item_id:
                self.delete(item_id)
                self.logger.debug(f"Deleted oldest memory {item_id} from {tier}")

    def insert(
        self,
        entry: str,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        *,
        insert_mode: Literal["active", "passive"] = "passive",
        insert_params: dict[str, Any] | None = None,
    ) -> str:
        """插入记忆

        Args:
            entry: 记忆文本
            vector: 向量表示
            metadata: 元数据（可包含 tier 指定目标层级）
            insert_mode: 插入模式
                - "passive": 自动插入到 STM
                - "active": 显式指定目标层级（通过 insert_params.target_tier）
            insert_params: 插入参数
                - target_tier: 目标层级（"stm"/"mtm"/"ltm"）
        """
        # 转换 vector
        if isinstance(vector, list):
            vector = np.array(vector, dtype=np.float32)

        # 确定目标层级
        if insert_mode == "active" and insert_params:
            target_tier = insert_params.get("target_tier", "stm")
        else:
            # Passive 模式：默认插入 STM
            target_tier = metadata.get("tier", "stm") if metadata else "stm"

        # 检查溢出并处理
        if self._check_overflow(target_tier) and self.migration_policy == "overflow":
            self._migrate_overflow(target_tier)

        # 准备元数据
        meta = metadata or {}
        meta["tier"] = target_tier
        meta["insert_time"] = time.time()
        meta["access_count"] = 0

        # 插入到 Collection
        index_name = self._get_tier_index_name(target_tier)
        memory_id = self.collection.insert(
            content=entry,
            index_names=[index_name],
            vector=vector,
            metadata=meta,
        )

        # 更新计数
        self._tier_counts[target_tier] = self._tier_counts.get(target_tier, 0) + 1
        self._insertion_counter += 1

        self.logger.debug(f"Inserted memory {memory_id} to {target_tier}")
        return memory_id

    def retrieve(
        self,
        query: str | None = None,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """检索记忆

        Args:
            query: 查询文本
            vector: 查询向量
            metadata: 筛选条件
                - tiers: 指定检索的层级列表（如 ["stm", "mtm"]）
                - method: 检索方法（"vector"/"text"/"hybrid"）
            top_k: 返回数量
        """
        # 转换 vector
        if isinstance(vector, list):
            vector = np.array(vector, dtype=np.float32)

        # 确定检索的层级
        meta = metadata or {}
        tiers = meta.get("tiers", self.tier_names)

        # 构建索引列表
        index_names = [self._get_tier_index_name(tier) for tier in tiers]

        # 检索
        results = self.collection.retrieve(
            query=vector if vector is not None else query,
            index_names=index_names,
            top_k=top_k,
            with_metadata=True,
        )

        # 转换为统一格式
        return [
            {
                "text": r.get("text", ""),
                "metadata": r.get("metadata", {}),
                "score": r.get("distance", 0.0),
                "id": r.get("stable_id", ""),
            }
            for r in results
        ]

    def delete(self, item_id: str) -> bool:
        """删除记忆"""
        try:
            self.collection.delete(item_id)
            # 更新计数
            self._update_tier_counts()
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete memory {item_id}: {e}")
            return False

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        self._update_tier_counts()
        return {
            "total_count": sum(self._tier_counts.values()),
            "tier_counts": self._tier_counts.copy(),
            "tier_capacities": self.tier_capacities.copy(),
            "migration_policy": self.migration_policy,
            "collection_name": self.collection_name,
        }
