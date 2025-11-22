"""记忆服务工厂 - 根据配置动态创建记忆服务的 ServiceFactory"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sage.kernel.runtime.factory.service_factory import ServiceFactory

if TYPE_CHECKING:
    pass

from .short_term_memory_service import ShortTermMemoryService


class MemoryServiceFactory:
    """记忆服务工厂类

    功能：
    1. 根据服务名称和配置创建对应的 ServiceFactory
    2. 支持多种记忆服务类型（短期、长期、混合等）
    3. 从配置中读取服务参数

    使用示例：
        # 在 YAML 配置中：
        services:
          register_memory_service: "short_term_memory"
          short_term_memory:
            max_dialog: 3

        # 在代码中（只需两行）：
        service_name = config.get("services.register_memory_service")
        env.register_service_factory(service_name, MemoryServiceFactory.create(service_name, config))
    """

    # 服务类型映射表
    SERVICE_CLASSES = {
        "short_term_memory": ShortTermMemoryService,
        # 未来可以添加其他服务：
        # "long_term_memory": LongTermMemoryService,
        # "hybrid_memory": HybridMemoryService,
        # "vector_memory": VectorMemoryService,
    }

    @staticmethod
    def create(service_name: str, config: Any) -> ServiceFactory:
        """创建记忆服务的 ServiceFactory

        Args:
            service_name: 服务名称（如 "short_term_memory"）
            config: RuntimeConfig 对象

        Returns:
            ServiceFactory 实例，可直接传给 env.register_service_factory()

        Raises:
            ValueError: 如果服务名称不支持或配置参数缺失

        Example:
            service_name = config.get("services.register_memory_service")
            factory = MemoryServiceFactory.create(service_name, config)
            env.register_service_factory(service_name, factory)
        """
        # 验证服务名称
        if service_name not in MemoryServiceFactory.SERVICE_CLASSES:
            supported = ", ".join(MemoryServiceFactory.SERVICE_CLASSES.keys())
            raise ValueError(f"不支持的服务类型: {service_name}。支持的类型: {supported}")

        # 根据服务类型读取配置并创建 ServiceFactory
        if service_name == "short_term_memory":
            return MemoryServiceFactory._create_short_term_memory(service_name, config)
        # 未来可以添加其他服务的创建逻辑
        # elif service_name == "long_term_memory":
        #     return MemoryServiceFactory._create_long_term_memory(service_name, config)

        raise NotImplementedError(f"未实现服务创建逻辑: {service_name}")

    @staticmethod
    def _create_short_term_memory(service_name: str, config: Any) -> ServiceFactory:
        """创建短期记忆服务的 ServiceFactory

        Args:
            service_name: 服务名称
            config: RuntimeConfig 对象

        Returns:
            ServiceFactory 实例

        Raises:
            ValueError: 如果 max_dialog 参数缺失
        """
        max_dialog = config.get(f"services.{service_name}.max_dialog")
        if max_dialog is None:
            raise ValueError(f"配置缺失: services.{service_name}.max_dialog")

        # 创建并返回 ServiceFactory
        return ServiceFactory(
            service_name=service_name,
            service_class=ShortTermMemoryService,
            service_kwargs={"max_dialog": max_dialog},
        )

    @staticmethod
    def get_service_class(service_name: str) -> type:
        """获取服务类

        Args:
            service_name: 服务名称

        Returns:
            服务类

        Raises:
            ValueError: 如果服务名称不支持
        """
        if service_name not in MemoryServiceFactory.SERVICE_CLASSES:
            supported = ", ".join(MemoryServiceFactory.SERVICE_CLASSES.keys())
            raise ValueError(f"不支持的服务类型: {service_name}。支持的类型: {supported}")

        return MemoryServiceFactory.SERVICE_CLASSES[service_name]

    @staticmethod
    def list_supported_services() -> list[str]:
        """列出所有支持的服务类型

        Returns:
            服务名称列表
        """
        return list(MemoryServiceFactory.SERVICE_CLASSES.keys())
