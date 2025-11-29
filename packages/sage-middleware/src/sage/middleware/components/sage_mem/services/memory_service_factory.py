"""记忆服务工厂 - 根据配置动态创建记忆服务的 ServiceFactory"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sage.kernel.runtime.factory.service_factory import ServiceFactory

if TYPE_CHECKING:
    pass

from .graph_memory_service import GraphMemoryService
from .hierarchical_memory_service import HierarchicalMemoryService
from .hybrid_memory_service import HybridMemoryService
from .key_value_memory_service import KeyValueMemoryService
from .short_term_memory_service import ShortTermMemoryService
from .vector_hash_memory_service import VectorHashMemoryService


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
        "vector_hash_memory": VectorHashMemoryService,
        "graph_memory": GraphMemoryService,
        "hierarchical_memory": HierarchicalMemoryService,
        "hybrid_memory": HybridMemoryService,
        "key_value_memory": KeyValueMemoryService,
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
        elif service_name == "vector_hash_memory":
            return MemoryServiceFactory._create_vector_hash_memory(service_name, config)
        elif service_name == "graph_memory":
            return MemoryServiceFactory._create_graph_memory(service_name, config)
        elif service_name == "hierarchical_memory":
            return MemoryServiceFactory._create_hierarchical_memory(service_name, config)
        elif service_name == "hybrid_memory":
            return MemoryServiceFactory._create_hybrid_memory(service_name, config)
        elif service_name == "key_value_memory":
            return MemoryServiceFactory._create_key_value_memory(service_name, config)

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
    def _create_vector_hash_memory(service_name: str, config: Any) -> ServiceFactory:
        """创建向量哈希记忆服务的 ServiceFactory

        Args:
            service_name: 服务名称
            config: RuntimeConfig 对象

        Returns:
            ServiceFactory 实例

        Raises:
            ValueError: 如果 dim 或 nbits 参数缺失
        """
        dim = config.get(f"services.{service_name}.dim")
        nbits = config.get(f"services.{service_name}.nbits")

        if dim is None:
            raise ValueError(f"配置缺失: services.{service_name}.dim")
        if nbits is None:
            raise ValueError(f"配置缺失: services.{service_name}.nbits")

        # 创建并返回 ServiceFactory
        return ServiceFactory(
            service_name=service_name,
            service_class=VectorHashMemoryService,
            service_kwargs={"dim": dim, "nbits": nbits},
        )

    @staticmethod
    def _create_graph_memory(service_name: str, config: Any) -> ServiceFactory:
        """创建图记忆服务的 ServiceFactory

        Args:
            service_name: 服务名称
            config: RuntimeConfig 对象

        Returns:
            ServiceFactory 实例
        """
        # 获取配置参数（均有默认值）
        graph_type = config.get(
            f"services.{service_name}.graph_type", "knowledge_graph"
        )
        node_embedding_dim = config.get(
            f"services.{service_name}.node_embedding_dim", 768
        )
        edge_types_raw = config.get(f"services.{service_name}.edge_types")
        edge_types = list(edge_types_raw) if edge_types_raw else None

        link_policy = config.get(
            f"services.{service_name}.link_policy", "bidirectional"
        )
        max_links_per_node = config.get(
            f"services.{service_name}.max_links_per_node", 50
        )
        link_weight_init = config.get(
            f"services.{service_name}.link_weight_init", 1.0
        )
        synonymy_threshold = config.get(
            f"services.{service_name}.synonymy_threshold", 0.8
        )
        damping = config.get(f"services.{service_name}.damping", 0.5)

        # 创建并返回 ServiceFactory
        return ServiceFactory(
            service_name=service_name,
            service_class=GraphMemoryService,
            service_kwargs={
                "graph_type": graph_type,
                "node_embedding_dim": node_embedding_dim,
                "edge_types": edge_types,
                "link_policy": link_policy,
                "max_links_per_node": max_links_per_node,
                "link_weight_init": link_weight_init,
                "synonymy_threshold": synonymy_threshold,
                "damping": damping,
            },
        )

    @staticmethod
    def _create_hierarchical_memory(service_name: str, config: Any) -> ServiceFactory:
        """创建分层记忆服务的 ServiceFactory

        Args:
            service_name: 服务名称
            config: RuntimeConfig 对象

        Returns:
            ServiceFactory 实例
        """
        # 获取配置参数（均有默认值）
        tier_mode = config.get(f"services.{service_name}.tier_mode", "three_tier")

        # 解析 tier_capacities
        tier_capacities_raw = config.get(f"services.{service_name}.tier_capacities")
        if tier_capacities_raw is not None:
            if isinstance(tier_capacities_raw, dict):
                tier_capacities = tier_capacities_raw
            else:
                tier_capacities = None
        else:
            tier_capacities = None

        migration_policy = config.get(
            f"services.{service_name}.migration_policy", "overflow"
        )
        migration_threshold = config.get(
            f"services.{service_name}.migration_threshold", 0.7
        )
        migration_interval = config.get(
            f"services.{service_name}.migration_interval", 3600
        )
        embedding_dim = config.get(f"services.{service_name}.embedding_dim", 768)
        heat_alpha = config.get(f"services.{service_name}.heat_alpha", 1.0)
        heat_beta = config.get(f"services.{service_name}.heat_beta", 1.0)
        heat_gamma = config.get(f"services.{service_name}.heat_gamma", 1.0)

        # 创建并返回 ServiceFactory
        return ServiceFactory(
            service_name=service_name,
            service_class=HierarchicalMemoryService,
            service_kwargs={
                "tier_mode": tier_mode,
                "tier_capacities": tier_capacities,
                "migration_policy": migration_policy,
                "migration_threshold": migration_threshold,
                "migration_interval": migration_interval,
                "embedding_dim": embedding_dim,
                "heat_alpha": heat_alpha,
                "heat_beta": heat_beta,
                "heat_gamma": heat_gamma,
            },
        )

    @staticmethod
    def _create_hybrid_memory(service_name: str, config: Any) -> ServiceFactory:
        """创建混合记忆服务的 ServiceFactory

        Args:
            service_name: 服务名称
            config: RuntimeConfig 对象

        Returns:
            ServiceFactory 实例
        """
        # 获取配置参数
        indexes_raw = config.get(f"services.{service_name}.indexes")
        indexes = indexes_raw if isinstance(indexes_raw, list) else None

        fusion_strategy = config.get(
            f"services.{service_name}.fusion_strategy", "weighted"
        )
        fusion_weights_raw = config.get(f"services.{service_name}.fusion_weights")
        if fusion_weights_raw:
            if isinstance(fusion_weights_raw, str):
                fusion_weights = [
                    float(x.strip()) for x in fusion_weights_raw.split(",")
                ]
            else:
                fusion_weights = list(fusion_weights_raw)
        else:
            fusion_weights = None

        rrf_k = config.get(f"services.{service_name}.rrf_k", 60)

        # 创建并返回 ServiceFactory
        return ServiceFactory(
            service_name=service_name,
            service_class=HybridMemoryService,
            service_kwargs={
                "indexes": indexes,
                "fusion_strategy": fusion_strategy,
                "fusion_weights": fusion_weights,
                "rrf_k": rrf_k,
            },
        )

    @staticmethod
    def _create_key_value_memory(service_name: str, config: Any) -> ServiceFactory:
        """创建键值记忆服务的 ServiceFactory

        Args:
            service_name: 服务名称
            config: RuntimeConfig 对象

        Returns:
            ServiceFactory 实例
        """
        # 获取配置参数（均有默认值）
        match_type = config.get(f"services.{service_name}.match_type", "exact")
        key_extractor = config.get(f"services.{service_name}.key_extractor", "entity")
        fuzzy_threshold = config.get(f"services.{service_name}.fuzzy_threshold", 0.8)
        semantic_threshold = config.get(
            f"services.{service_name}.semantic_threshold", 0.7
        )
        embedding_dim = config.get(f"services.{service_name}.embedding_dim", 768)
        case_sensitive = config.get(f"services.{service_name}.case_sensitive", False)

        # 创建并返回 ServiceFactory
        return ServiceFactory(
            service_name=service_name,
            service_class=KeyValueMemoryService,
            service_kwargs={
                "match_type": match_type,
                "key_extractor": key_extractor,
                "fuzzy_threshold": fuzzy_threshold,
                "semantic_threshold": semantic_threshold,
                "embedding_dim": embedding_dim,
                "case_sensitive": case_sensitive,
            },
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

    @staticmethod
    def create_instance(service_name: str, **kwargs: Any) -> Any:
        """直接创建记忆服务实例（用于非 Pipeline 环境）

        Args:
            service_name: 服务名称（如 "short_term_memory"）
            **kwargs: 服务构造参数

        Returns:
            服务实例

        Raises:
            ValueError: 如果服务名称不支持

        Example:
            # 创建短期记忆服务
            memory = MemoryServiceFactory.create_instance(
                "short_term_memory",
                max_dialog=10
            )
        """
        if service_name not in MemoryServiceFactory.SERVICE_CLASSES:
            supported = ", ".join(MemoryServiceFactory.SERVICE_CLASSES.keys())
            raise ValueError(f"不支持的服务类型: {service_name}。支持的类型: {supported}")

        service_class = MemoryServiceFactory.SERVICE_CLASSES[service_name]
        return service_class(**kwargs)
