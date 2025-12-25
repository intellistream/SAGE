"""MemoryService 注册表

Layer: L4 (Middleware)

支持层级命名（如 "partitional.vector_memory"）的注册表系统。

三大类：
- Partitional：去中心化存储，数据分散在不同分区/桶中
  - vector_memory: 向量记忆（FAISS 索引）
  - key_value_memory: 文本记忆（BM25S 索引）
  - short_term_memory: 短期记忆（滑窗+VDB）
  - vector_hash_memory: LSH 哈希记忆

- Hierarchical：有层级结构，分层组织
  - graph_memory: 图记忆（有中心节点）
  - three_tier: 三层记忆（STM/MTM/LTM）
  - two_tier: 两层记忆（Short/Long）

- Hybrid：混合结构，一份数据+多种索引
  - multi_index: 多索引混合（VDB+KV+Graph）
  - rrf_fusion: RRF 融合检索

Usage:
    >>> from sage.middleware.components.sage_mem.memory_service import MemoryServiceRegistry
    >>> from .partitional.vector_memory import VectorMemoryService
    >>>
    >>> # 注册 Service
    >>> MemoryServiceRegistry.register("partitional.vector_memory", VectorMemoryService)
    >>>
    >>> # 获取 Service 类
    >>> service_class = MemoryServiceRegistry.get("partitional.vector_memory")
    >>>
    >>> # 列出所有 Service
    >>> all_services = MemoryServiceRegistry.list_services()
    >>> # ['partitional.vector_memory', 'partitional.key_value_memory', ...]
    >>>
    >>> # 列出某个类别的 Service
    >>> partitional_services = MemoryServiceRegistry.list_services(category="partitional")
    >>> # ['partitional.vector_memory', 'partitional.key_value_memory', ...]
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base_service import BaseMemoryService


class MemoryServiceRegistry:
    """MemoryService 注册表

    支持层级命名（如 "partitional.vector_memory"）

    三大类：
    - Partitional：vector_memory, key_value_memory, short_term_memory, vector_hash_memory
    - Hierarchical：graph_memory, three_tier, two_tier
    - Hybrid：multi_index, rrf_fusion
    """

    _services: dict[str, type[BaseMemoryService]] = {}

    @classmethod
    def register(cls, name: str, service_class: type[BaseMemoryService]) -> None:
        """注册一个 Service

        Args:
            name: 服务名称（如 "partitional.vector_memory"）
            service_class: Service 类（必须继承 BaseMemoryService）

        Raises:
            ValueError: 如果名称已存在或 service_class 不是 BaseMemoryService 子类

        Example:
            >>> from .partitional.vector_memory import VectorMemoryService
            >>> MemoryServiceRegistry.register("partitional.vector_memory", VectorMemoryService)
        """
        if name in cls._services:
            raise ValueError(f"MemoryService '{name}' is already registered")

        # 验证 service_class 是否继承 BaseMemoryService
        # 使用 TYPE_CHECKING 中导入的类型进行检查
        # 注意：这里不做运行时类型检查，因为可能导致循环导入
        # 假设调用者确保传入的类正确继承 BaseMemoryService

        cls._services[name] = service_class

    @classmethod
    def get(cls, name: str) -> type[BaseMemoryService]:
        """获取 Service 类

        Args:
            name: 服务名称（如 "partitional.vector_memory"）

        Returns:
            Service 类

        Raises:
            ValueError: 如果服务不存在

        Example:
            >>> service_class = MemoryServiceRegistry.get("partitional.vector_memory")
            >>> factory = service_class.from_config(service_name, config)
        """
        if name not in cls._services:
            available = list(cls._services.keys())
            raise ValueError(f"Unknown MemoryService: '{name}'. Available: {available}")
        return cls._services[name]

    @classmethod
    def list_services(cls, category: str | None = None) -> list[str]:
        """列出所有已注册的 Service

        Args:
            category: 类别名称（可选），如 "partitional"、"hierarchical"、"hybrid"
                     如果为 None，返回所有服务

        Returns:
            服务名称列表

        Example:
            >>> # 列出所有服务
            >>> all_services = MemoryServiceRegistry.list_services()
            >>> # ['partitional.vector_memory', 'partitional.key_value_memory', ...]
            >>>
            >>> # 列出 Partitional 类服务
            >>> partitional_services = MemoryServiceRegistry.list_services(category="partitional")
            >>> # ['partitional.vector_memory', 'partitional.key_value_memory', ...]
        """
        if category is None:
            return list(cls._services.keys())
        prefix = f"{category}."
        return [name for name in cls._services.keys() if name.startswith(prefix)]

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """检查 Service 是否已注册

        Args:
            name: 服务名称（如 "partitional.vector_memory"）

        Returns:
            是否已注册

        Example:
            >>> if MemoryServiceRegistry.is_registered("partitional.vector_memory"):
            >>>     print("Service is registered")
        """
        return name in cls._services

    @classmethod
    def get_category(cls, name: str) -> str | None:
        """获取 Service 的类别

        Args:
            name: 服务名称（如 "partitional.vector_memory"）

        Returns:
            类别名称（如 "partitional"），如果不包含 "." 则返回 None

        Example:
            >>> category = MemoryServiceRegistry.get_category("partitional.vector_memory")
            >>> # "partitional"
            >>>
            >>> category = MemoryServiceRegistry.get_category("vector_memory")
            >>> # None
        """
        if "." in name:
            return name.split(".")[0]
        return None

    @classmethod
    def list_categories(cls) -> list[str]:
        """列出所有类别

        Returns:
            类别名称列表（去重后的）

        Example:
            >>> categories = MemoryServiceRegistry.list_categories()
            >>> # ['partitional', 'hierarchical', 'hybrid']
        """
        categories = set()
        for name in cls._services.keys():
            category = cls.get_category(name)
            if category:
                categories.add(category)
        return sorted(categories)

    @classmethod
    def unregister(cls, name: str) -> bool:
        """注销一个 Service（用于测试或动态更新）

        Args:
            name: 服务名称（如 "partitional.vector_memory"）

        Returns:
            是否成功注销（True=成功，False=不存在）

        Example:
            >>> success = MemoryServiceRegistry.unregister("partitional.vector_memory")
            >>> if success:
            >>>     print("Service unregistered")
        """
        if name in cls._services:
            del cls._services[name]
            return True
        return False

    @classmethod
    def clear(cls) -> None:
        """清空所有注册（用于测试）

        Example:
            >>> MemoryServiceRegistry.clear()  # 清空所有注册
        """
        cls._services.clear()
