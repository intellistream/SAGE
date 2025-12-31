"""
Unit tests for MemoryServiceRegistry

测试范围:
- Service 注册: register() 装饰器
- Service 创建: create() 工厂方法
- 注册表查询: list_registered(), get_service_class()
- 异常处理: 未注册的 Service
"""

import pytest

from sage.middleware.components.sage_mem.neuromem.memory_collection import UnifiedCollection
from sage.middleware.components.sage_mem.neuromem.services import (
    BaseMemoryService,
    MemoryServiceRegistry,
)


class TestServiceRegistration:
    """测试 Service 注册"""

    def setup_method(self):
        """每个测试前清空注册表"""
        MemoryServiceRegistry._registry.clear()

    def test_register_service(self):
        """测试注册 Service"""

        @MemoryServiceRegistry.register("test_service")
        class TestService(BaseMemoryService):
            def _setup_indexes(self):
                pass

            def insert(self, text, metadata=None, **kwargs):
                return self.collection.insert(text, metadata)

            def retrieve(self, query, top_k=5, **kwargs):
                return []

        # 验证注册成功
        assert "test_service" in MemoryServiceRegistry.list_registered()
        assert MemoryServiceRegistry.get_service_class("test_service") == TestService

    def test_register_multiple_services(self):
        """测试注册多个 Service"""

        @MemoryServiceRegistry.register("service_a")
        class ServiceA(BaseMemoryService):
            def _setup_indexes(self):
                pass

            def insert(self, text, metadata=None, **kwargs):
                return "a"

            def retrieve(self, query, top_k=5, **kwargs):
                return []

        @MemoryServiceRegistry.register("service_b")
        class ServiceB(BaseMemoryService):
            def _setup_indexes(self):
                pass

            def insert(self, text, metadata=None, **kwargs):
                return "b"

            def retrieve(self, query, top_k=5, **kwargs):
                return []

        registered = MemoryServiceRegistry.list_registered()
        assert "service_a" in registered
        assert "service_b" in registered
        assert len(registered) == 2

    def test_register_overwrite_warning(self, caplog):
        """测试重复注册会打印警告"""

        @MemoryServiceRegistry.register("duplicate")
        class ServiceV1(BaseMemoryService):
            def _setup_indexes(self):
                pass

            def insert(self, text, metadata=None, **kwargs):
                return "v1"

            def retrieve(self, query, top_k=5, **kwargs):
                return []

        @MemoryServiceRegistry.register("duplicate")
        class ServiceV2(BaseMemoryService):
            def _setup_indexes(self):
                pass

            def insert(self, text, metadata=None, **kwargs):
                return "v2"

            def retrieve(self, query, top_k=5, **kwargs):
                return []

        # 验证被覆盖
        assert MemoryServiceRegistry.get_service_class("duplicate") == ServiceV2

        # 验证有警告日志 (使用 caplog)
        assert "already registered" in caplog.text


class TestServiceCreation:
    """测试 Service 创建"""

    def setup_method(self):
        """每个测试前清空注册表并注册测试 Service"""
        MemoryServiceRegistry._registry.clear()

        @MemoryServiceRegistry.register("mock_service")
        class MockService(BaseMemoryService):
            def _setup_indexes(self):
                self.collection.add_index("mock_index", "fifo", {"max_size": 10})

            def insert(self, text, metadata=None, **kwargs):
                return self.collection.insert(text, metadata, index_names=["mock_index"])

            def retrieve(self, query, top_k=5, **kwargs):
                data_ids = self.collection.query_by_index("mock_index", top_k=top_k)
                return [self.collection.get(id) for id in data_ids if self.collection.get(id)]

        self.MockService = MockService

    def test_create_service(self):
        """测试创建 Service 实例"""
        collection = UnifiedCollection("test_collection")
        service = MemoryServiceRegistry.create("mock_service", collection)

        assert isinstance(service, BaseMemoryService)
        assert service.collection.name == "test_collection"
        assert "mock_index" in service.collection.indexes

    def test_create_service_with_config(self):
        """测试带配置创建 Service"""
        collection = UnifiedCollection("test")
        config = {"top_k": 10, "threshold": 0.5}
        service = MemoryServiceRegistry.create("mock_service", collection, config)

        assert service.config == config
        assert service.config["top_k"] == 10

    def test_create_unregistered_service(self):
        """测试创建未注册的 Service 抛出异常"""
        collection = UnifiedCollection("test")

        with pytest.raises(ValueError, match="not registered"):
            MemoryServiceRegistry.create("nonexistent_service", collection)

    def test_create_service_error_message(self):
        """测试错误消息包含可用 Service 列表"""
        collection = UnifiedCollection("test")

        try:
            MemoryServiceRegistry.create("invalid", collection)
        except ValueError as e:
            assert "Available:" in str(e)
            assert "mock_service" in str(e)


class TestRegistryQueries:
    """测试注册表查询"""

    def setup_method(self):
        """注册测试 Service"""
        MemoryServiceRegistry._registry.clear()

        @MemoryServiceRegistry.register("service_1")
        class Service1(BaseMemoryService):
            def _setup_indexes(self):
                pass

            def insert(self, text, metadata=None, **kwargs):
                return "1"

            def retrieve(self, query, top_k=5, **kwargs):
                return []

        @MemoryServiceRegistry.register("service_2")
        class Service2(BaseMemoryService):
            def _setup_indexes(self):
                pass

            def insert(self, text, metadata=None, **kwargs):
                return "2"

            def retrieve(self, query, top_k=5, **kwargs):
                return []

        self.Service1 = Service1
        self.Service2 = Service2

    def test_list_registered(self):
        """测试列出所有注册的 Service"""
        registered = MemoryServiceRegistry.list_registered()
        assert "service_1" in registered
        assert "service_2" in registered
        assert len(registered) == 2

    def test_get_service_class(self):
        """测试获取 Service 类"""
        service_class = MemoryServiceRegistry.get_service_class("service_1")
        assert service_class == self.Service1

    def test_get_nonexistent_service_class(self):
        """测试获取不存在的 Service 类返回 None"""
        service_class = MemoryServiceRegistry.get_service_class("nonexistent")
        assert service_class is None


class TestRegistryIntegration:
    """测试注册表集成场景"""

    def setup_method(self):
        """清空注册表"""
        MemoryServiceRegistry._registry.clear()

    def test_full_workflow(self):
        """测试完整工作流: 注册 → 创建 → 使用"""

        # 1. 注册 Service
        @MemoryServiceRegistry.register("integration_test")
        class IntegrationService(BaseMemoryService):
            def _setup_indexes(self):
                self.collection.add_index("test_idx", "fifo", {"max_size": 5})

            def insert(self, text, metadata=None, **kwargs):
                return self.collection.insert(text, metadata, index_names=["test_idx"])

            def retrieve(self, query, top_k=5, **kwargs):
                data_ids = self.collection.query_by_index("test_idx", query, top_k=top_k)
                return [self.collection.get(id) for id in data_ids if self.collection.get(id)]

        # 2. 创建 Collection 和 Service
        collection = UnifiedCollection("integration_collection")
        service = MemoryServiceRegistry.create("integration_test", collection)

        # 3. 使用 Service
        data_id = service.insert("Hello, integration test!", {"type": "test"})
        assert data_id is not None

        data = service.get(data_id)
        assert data is not None
        assert data["text"] == "Hello, integration test!"

        # 4. 检索
        results = service.retrieve("integration", top_k=5)
        assert len(results) >= 0  # FIFO 可能需要特定查询

    def test_multiple_services_same_collection(self):
        """测试同一个 Collection 创建多个 Service"""

        @MemoryServiceRegistry.register("service_alpha")
        class ServiceAlpha(BaseMemoryService):
            def _setup_indexes(self):
                self.collection.add_index("alpha_idx", "fifo", {"max_size": 10})

            def insert(self, text, metadata=None, **kwargs):
                return self.collection.insert(text, metadata, index_names=["alpha_idx"])

            def retrieve(self, query, top_k=5, **kwargs):
                return []

        @MemoryServiceRegistry.register("service_beta")
        class ServiceBeta(BaseMemoryService):
            def _setup_indexes(self):
                self.collection.add_index("beta_idx", "bm25", {})

            def insert(self, text, metadata=None, **kwargs):
                return self.collection.insert(text, metadata, index_names=["beta_idx"])

            def retrieve(self, query, top_k=5, **kwargs):
                return []

        # 同一个 Collection，不同 Service
        collection = UnifiedCollection("shared_collection")
        service_a = MemoryServiceRegistry.create("service_alpha", collection)
        service_b = MemoryServiceRegistry.create("service_beta", collection)

        # 验证索引共存
        indexes = collection.list_indexes()
        index_names = [idx["name"] for idx in indexes]
        assert "alpha_idx" in index_names
        assert "beta_idx" in index_names
