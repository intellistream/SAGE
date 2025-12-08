"""MemoryServiceFactory 单元测试

测试 MemoryServiceFactory 创建各种 Memory Service 的功能。
"""

import pytest

from sage.middleware.components.sage_mem.services.graph_memory_service import (
    GraphMemoryService,
)
from sage.middleware.components.sage_mem.services.hierarchical_memory_service import (
    HierarchicalMemoryService,
)
from sage.middleware.components.sage_mem.services.hybrid_memory_service import (
    HybridMemoryService,
)
from sage.middleware.components.sage_mem.services.key_value_memory_service import (
    KeyValueMemoryService,
)
from sage.middleware.components.sage_mem.services.memory_service_factory import (
    MemoryServiceFactory,
)
from sage.middleware.components.sage_mem.services.short_term_memory_service import (
    ShortTermMemoryService,
)
from sage.middleware.components.sage_mem.services.vector_hash_memory_service import (
    VectorHashMemoryService,
)


class TestMemoryServiceFactoryServiceClasses:
    """测试 MemoryServiceFactory 服务类映射"""

    def test_all_services_registered(self):
        """测试所有服务都已注册"""
        expected_services = [
            "short_term_memory",
            "vector_hash_memory",
            "graph_memory",
            "hierarchical_memory",
            "hybrid_memory",
            "key_value_memory",
        ]

        for service_name in expected_services:
            assert service_name in MemoryServiceFactory.SERVICE_CLASSES

    def test_service_class_mapping(self):
        """测试服务类映射正确"""
        assert MemoryServiceFactory.SERVICE_CLASSES["short_term_memory"] == ShortTermMemoryService
        assert MemoryServiceFactory.SERVICE_CLASSES["vector_hash_memory"] == VectorHashMemoryService
        assert MemoryServiceFactory.SERVICE_CLASSES["graph_memory"] == GraphMemoryService
        assert (
            MemoryServiceFactory.SERVICE_CLASSES["hierarchical_memory"] == HierarchicalMemoryService
        )
        assert MemoryServiceFactory.SERVICE_CLASSES["hybrid_memory"] == HybridMemoryService
        assert MemoryServiceFactory.SERVICE_CLASSES["key_value_memory"] == KeyValueMemoryService


class TestMemoryServiceFactoryGetServiceClass:
    """测试 MemoryServiceFactory.get_service_class 方法"""

    def test_get_existing_service_class(self):
        """测试获取已存在的服务类"""
        service_class = MemoryServiceFactory.get_service_class("graph_memory")
        assert service_class == GraphMemoryService

    def test_get_nonexistent_service_class(self):
        """测试获取不存在的服务类"""
        with pytest.raises(ValueError):
            MemoryServiceFactory.get_service_class("nonexistent")


class TestMemoryServiceFactoryListSupportedServices:
    """测试 MemoryServiceFactory.list_supported_services 方法"""

    def test_list_supported_services(self):
        """测试列出支持的服务"""
        services = MemoryServiceFactory.list_supported_services()

        assert isinstance(services, list)
        assert len(services) == 6
        assert "short_term_memory" in services
        assert "vector_hash_memory" in services
        assert "graph_memory" in services
        assert "hierarchical_memory" in services
        assert "hybrid_memory" in services
        assert "key_value_memory" in services


class TestMemoryServiceFactoryCreateInstance:
    """测试 MemoryServiceFactory.create_instance 方法"""

    def test_create_short_term_instance(self):
        """测试创建短期记忆实例"""
        instance = MemoryServiceFactory.create_instance(
            "short_term_memory", max_dialog=5, collection_name="test_factory_stm"
        )

        assert isinstance(instance, ShortTermMemoryService)

    def test_create_graph_memory_instance(self):
        """测试创建图记忆实例"""
        instance = MemoryServiceFactory.create_instance(
            "graph_memory", graph_type="link_graph", collection_name="test_factory_graph"
        )

        assert isinstance(instance, GraphMemoryService)
        assert instance.graph_type == "link_graph"

    def test_create_hierarchical_memory_instance(self):
        """测试创建分层记忆实例"""
        instance = MemoryServiceFactory.create_instance(
            "hierarchical_memory", tier_mode="two_tier", collection_name="test_factory_hier"
        )

        assert isinstance(instance, HierarchicalMemoryService)
        assert instance.tier_mode == "two_tier"

    def test_create_hybrid_memory_instance(self):
        """测试创建混合记忆实例"""
        instance = MemoryServiceFactory.create_instance(
            "hybrid_memory", fusion_strategy="rrf", collection_name="test_factory_hybrid"
        )

        assert isinstance(instance, HybridMemoryService)
        assert instance.fusion_strategy == "rrf"

    def test_create_key_value_memory_instance(self):
        """测试创建键值记忆实例"""
        instance = MemoryServiceFactory.create_instance(
            "key_value_memory", collection_name="test_factory_kv"
        )

        assert isinstance(instance, KeyValueMemoryService)

    def test_create_instance_unsupported(self):
        """测试创建不支持的服务实例"""
        with pytest.raises(ValueError):
            MemoryServiceFactory.create_instance("unsupported_memory")
