"""MemoryService Registry 单元测试

测试 Registry 的基本功能：
- 注册/注销 Service
- 获取 Service 类
- 列出服务
- 类别管理
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

# 直接导入，避免触发 sage_flow C++ 扩展
sys.path.insert(0, str(Path(__file__).parents[5] / "src"))
from sage.middleware.components.sage_mem.memory_service.base_service import BaseMemoryService
from sage.middleware.components.sage_mem.memory_service.registry import MemoryServiceRegistry


class MockVectorMemoryService(BaseMemoryService):
    """Mock VectorMemoryService for testing"""

    @classmethod
    def from_config(cls, service_name: str, config: Any):
        from sage.kernel.runtime.factory.service_factory import ServiceFactory

        return ServiceFactory(service_name=service_name, service_class=cls, dim=768)

    def __init__(self, dim: int = 768):
        super().__init__()
        self.dim = dim

    def insert(
        self,
        entry: str,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        *,
        insert_mode: str = "passive",
        insert_params: dict[str, Any] | None = None,
    ) -> str:
        return "mock_id_123"

    def retrieve(
        self,
        query: str | None = None,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        return [{"text": "mock result", "metadata": {}, "score": 0.95}]

    def delete(self, item_id: str) -> bool:
        return True

    def get_stats(self) -> dict[str, Any]:
        return {"total_count": 0, "index_type": "MockIndex"}


class MockGraphMemoryService(BaseMemoryService):
    """Mock GraphMemoryService for testing"""

    @classmethod
    def from_config(cls, service_name: str, config: Any):
        from sage.kernel.runtime.factory.service_factory import ServiceFactory

        return ServiceFactory(service_name=service_name, service_class=cls)

    def insert(
        self,
        entry: str,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        *,
        insert_mode: str = "passive",
        insert_params: dict[str, Any] | None = None,
    ) -> str:
        return "mock_graph_id"

    def retrieve(
        self,
        query: str | None = None,
        vector: np.ndarray | list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        return []

    def delete(self, item_id: str) -> bool:
        return True

    def get_stats(self) -> dict[str, Any]:
        return {"total_count": 0}


@pytest.fixture(autouse=True)
def clear_registry():
    """自动清空 Registry（每个测试前后）"""
    MemoryServiceRegistry.clear()
    yield
    MemoryServiceRegistry.clear()


class TestMemoryServiceRegistry:
    """测试 MemoryServiceRegistry"""

    def test_register_and_get(self):
        """测试注册和获取 Service"""
        # 注册
        MemoryServiceRegistry.register("partitional.vector_memory", MockVectorMemoryService)

        # 获取
        service_class = MemoryServiceRegistry.get("partitional.vector_memory")
        assert service_class == MockVectorMemoryService

    def test_register_duplicate_raises_error(self):
        """测试重复注册会抛出异常"""
        MemoryServiceRegistry.register("partitional.vector_memory", MockVectorMemoryService)

        with pytest.raises(ValueError, match="already registered"):
            MemoryServiceRegistry.register("partitional.vector_memory", MockVectorMemoryService)

    def test_get_nonexistent_raises_error(self):
        """测试获取不存在的 Service 会抛出异常"""
        with pytest.raises(ValueError, match="Unknown MemoryService"):
            MemoryServiceRegistry.get("nonexistent.service")

    def test_list_services_all(self):
        """测试列出所有服务"""
        MemoryServiceRegistry.register("partitional.vector_memory", MockVectorMemoryService)
        MemoryServiceRegistry.register("hierarchical.graph_memory", MockGraphMemoryService)

        services = MemoryServiceRegistry.list_services()
        assert set(services) == {"partitional.vector_memory", "hierarchical.graph_memory"}

    def test_list_services_by_category(self):
        """测试按类别列出服务"""
        MemoryServiceRegistry.register("partitional.vector_memory", MockVectorMemoryService)
        MemoryServiceRegistry.register("partitional.key_value_memory", MockVectorMemoryService)
        MemoryServiceRegistry.register("hierarchical.graph_memory", MockGraphMemoryService)

        # 列出 partitional 类服务
        partitional_services = MemoryServiceRegistry.list_services(category="partitional")
        assert set(partitional_services) == {
            "partitional.vector_memory",
            "partitional.key_value_memory",
        }

        # 列出 hierarchical 类服务
        hierarchical_services = MemoryServiceRegistry.list_services(category="hierarchical")
        assert hierarchical_services == ["hierarchical.graph_memory"]

    def test_is_registered(self):
        """测试检查服务是否已注册"""
        MemoryServiceRegistry.register("partitional.vector_memory", MockVectorMemoryService)

        assert MemoryServiceRegistry.is_registered("partitional.vector_memory") is True
        assert MemoryServiceRegistry.is_registered("nonexistent.service") is False

    def test_get_category(self):
        """测试获取服务类别"""
        assert MemoryServiceRegistry.get_category("partitional.vector_memory") == "partitional"
        assert MemoryServiceRegistry.get_category("hierarchical.graph_memory") == "hierarchical"
        assert MemoryServiceRegistry.get_category("vector_memory") is None

    def test_list_categories(self):
        """测试列出所有类别"""
        MemoryServiceRegistry.register("partitional.vector_memory", MockVectorMemoryService)
        MemoryServiceRegistry.register("hierarchical.graph_memory", MockGraphMemoryService)
        MemoryServiceRegistry.register("hybrid.multi_index", MockVectorMemoryService)

        categories = MemoryServiceRegistry.list_categories()
        assert set(categories) == {"partitional", "hierarchical", "hybrid"}

    def test_unregister(self):
        """测试注销服务"""
        MemoryServiceRegistry.register("partitional.vector_memory", MockVectorMemoryService)

        # 注销成功
        success = MemoryServiceRegistry.unregister("partitional.vector_memory")
        assert success is True
        assert MemoryServiceRegistry.is_registered("partitional.vector_memory") is False

        # 注销不存在的服务
        success = MemoryServiceRegistry.unregister("nonexistent.service")
        assert success is False

    def test_clear(self):
        """测试清空所有注册"""
        MemoryServiceRegistry.register("partitional.vector_memory", MockVectorMemoryService)
        MemoryServiceRegistry.register("hierarchical.graph_memory", MockGraphMemoryService)

        MemoryServiceRegistry.clear()

        assert MemoryServiceRegistry.list_services() == []

    def test_register_non_base_service_raises_error(self):
        """测试注册非 BaseMemoryService 子类会抛出异常"""

        class NotAMemoryService:
            pass

        with pytest.raises(ValueError, match="must inherit from BaseMemoryService"):
            MemoryServiceRegistry.register("invalid.service", NotAMemoryService)  # type: ignore


class TestBaseMemoryService:
    """测试 BaseMemoryService"""

    def test_mock_service_creation(self):
        """测试 Mock Service 创建"""
        service = MockVectorMemoryService(dim=1024)
        assert service.dim == 1024

    def test_insert(self):
        """测试 insert 方法"""
        service = MockVectorMemoryService()
        memory_id = service.insert("Hello, world!")
        assert memory_id == "mock_id_123"

    def test_retrieve(self):
        """测试 retrieve 方法"""
        service = MockVectorMemoryService()
        results = service.retrieve(query="test", top_k=5)
        assert len(results) == 1
        assert results[0]["text"] == "mock result"
        assert results[0]["score"] == 0.95

    def test_delete(self):
        """测试 delete 方法"""
        service = MockVectorMemoryService()
        success = service.delete("mock_id_123")
        assert success is True

    def test_get_stats(self):
        """测试 get_stats 方法"""
        service = MockVectorMemoryService()
        stats = service.get_stats()
        assert stats["total_count"] == 0
        assert stats["index_type"] == "MockIndex"

    def test_from_config(self):
        """测试 from_config 方法"""
        from unittest.mock import MagicMock

        config = MagicMock()
        factory = MockVectorMemoryService.from_config("test_service", config)

        assert factory.service_name == "test_service"
        assert factory.service_class == MockVectorMemoryService
        assert factory.service_kwargs["dim"] == 768
