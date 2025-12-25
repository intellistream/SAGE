"""MemoryService 基类 - 定义统一接口

Layer: L4 (Middleware)

设计原则：
1. 一个 Service 对应一个 Collection（严格 1:1）
2. 统一接口：insert/retrieve/delete/get_stats
3. 配置通过 from_config 类方法读取

Architecture Note:
- 继承自 sage.platform.service.BaseService (L2)
- 提供 MemoryService 特定的抽象接口
- 支持 Registry 模式（纯类注册，无 Factory 层）
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    import numpy as np

    from sage.kernel.runtime.factory.service_factory import ServiceFactory

from sage.platform.service import BaseService


class BaseMemoryService(BaseService):
    """MemoryService 统一抽象基类

    所有 MemoryService 必须继承此类并实现以下方法：
    - from_config: 从配置创建 ServiceFactory
    - insert: 插入记忆
    - retrieve: 检索记忆
    - delete: 删除记忆
    - get_stats: 获取统计信息

    设计原则：
    1. 一个 Service 对应一个 Collection（严格 1:1）
    2. 统一接口：insert/retrieve/delete/get_stats
    3. 配置通过 from_config 类方法读取
    4. 支持 insert_mode（passive/active）和 insert_params
    """

    @classmethod
    @abstractmethod
    def from_config(cls, service_name: str, config: Any) -> ServiceFactory:
        """从配置创建 ServiceFactory（供 Pipeline 使用）

        Args:
            service_name: 服务名称（如 "partitional.vector_memory"）
            config: RuntimeConfig 对象

        Returns:
            ServiceFactory 实例

        Notes:
            - 子类必须实现此方法
            - 配置路径：services.{service_name}.*
            - 返回 ServiceFactory(service_name, service_class, service_kwargs)

        Example:
            >>> from sage.kernel.runtime.factory.service_factory import ServiceFactory
            >>> @classmethod
            >>> def from_config(cls, service_name: str, config: Any) -> ServiceFactory:
            >>>     dim = config.get(f"services.{service_name}.dim", 768)
            >>>     index_type = config.get(f"services.{service_name}.index_type", "IndexFlatL2")
            >>>     return ServiceFactory(
            >>>         service_name=service_name,
            >>>         service_class=cls,
            >>>         dim=dim,
            >>>         index_type=index_type,
            >>>     )
        """
        raise NotImplementedError(f"{cls.__name__} must implement from_config()")

    @abstractmethod
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
            vector: 向量表示（可选，如果为 None 则由服务自动生成）
            metadata: 元数据（可选，用于存储额外信息）
            insert_mode: 插入模式
                - "passive": 自动处理（默认，如自动选择 tier、自动生成 ID 等）
                - "active": 显式控制（通过 insert_params 指定详细参数）
            insert_params: 插入参数（仅在 insert_mode="active" 时有效）
                - target_tier: 目标层级（如 "STM", "MTM", "LTM"）
                - priority: 优先级（整数，越大越优先）
                - ttl: 过期时间（秒）
                - custom_id: 自定义 ID（如果不指定则自动生成）

        Returns:
            记忆ID（字符串）

        Raises:
            ValueError: 如果参数无效

        Example:
            >>> # Passive 模式（推荐）
            >>> memory_id = service.insert("Hello, world!", vector=embedding)
            >>>
            >>> # Active 模式（高级用法）
            >>> memory_id = service.insert(
            >>>     "Important message",
            >>>     vector=embedding,
            >>>     metadata={"source": "user"},
            >>>     insert_mode="active",
            >>>     insert_params={"target_tier": "LTM", "priority": 10}
            >>> )
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement insert()")

    @abstractmethod
    def retrieve(
        self,
        query: str | None = None,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """检索记忆

        Args:
            query: 查询文本（可选，如果为 None 则仅使用向量）
            vector: 查询向量（可选，如果为 None 则由服务自动生成）
            metadata: 筛选条件（可选），常用字段：
                - tiers: 指定检索的层级（如 ["STM", "MTM"]）
                - method: 检索方法（如 "vector", "text", "hybrid"）
                - min_score: 最小相似度阈值
                - time_range: 时间范围（如 {"start": ts, "end": ts}）
            top_k: 返回数量

        Returns:
            记忆列表，每个元素为 dict，包含：
                - text: 记忆文本（str）
                - metadata: 元数据（dict）
                - score: 相似度分数（float，越高越相似）
                - id: 记忆ID（str，可选）

        Raises:
            ValueError: 如果参数无效

        Example:
            >>> # 向量检索
            >>> results = service.retrieve(vector=query_embedding, top_k=5)
            >>>
            >>> # 文本检索
            >>> results = service.retrieve(query="Hello", top_k=5)
            >>>
            >>> # 层级筛选（仅检索 STM 和 MTM）
            >>> results = service.retrieve(
            >>>     vector=query_embedding,
            >>>     metadata={"tiers": ["STM", "MTM"]},
            >>>     top_k=5
            >>> )
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement retrieve()")

    @abstractmethod
    def delete(self, item_id: str) -> bool:
        """删除记忆

        Args:
            item_id: 记忆ID

        Returns:
            是否成功删除（True=成功，False=失败或不存在）

        Raises:
            ValueError: 如果 item_id 为空

        Example:
            >>> success = service.delete("memory_id_12345")
            >>> if success:
            >>>     print("Memory deleted")
            >>> else:
            >>>     print("Memory not found")
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement delete()")

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """获取统计信息

        Returns:
            统计数据，常见字段：
                - total_count: 总记忆数量（int）
                - tier_counts: 各层级记忆数量（dict，如 {"STM": 100, "MTM": 50}）
                - index_type: 索引类型（str，如 "IndexHNSWFlat"）
                - collection_name: Collection 名称（str）
                - last_updated: 最后更新时间（str 或 int）

        Example:
            >>> stats = service.get_stats()
            >>> print(f"Total memories: {stats['total_count']}")
            >>> print(f"STM count: {stats.get('tier_counts', {}).get('STM', 0)}")
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement get_stats()")

    # ========== 可选接口（子类可根据需要实现） ==========

    def clear(self) -> bool:
        """清空所有记忆（可选接口）

        Returns:
            是否成功清空

        Note:
            此方法为可选接口，子类可根据需要实现
        """
        raise NotImplementedError(f"{self.__class__.__name__} does not support clear()")

    def update(
        self, item_id: str, entry: str | None = None, metadata: dict[str, Any] | None = None
    ) -> bool:
        """更新记忆（可选接口）

        Args:
            item_id: 记忆ID
            entry: 新的记忆文本（可选）
            metadata: 新的元数据（可选）

        Returns:
            是否成功更新

        Note:
            此方法为可选接口，子类可根据需要实现
        """
        raise NotImplementedError(f"{self.__class__.__name__} does not support update()")
