"""HierarchicalMemoryService 单元测试

测试 HierarchicalMemoryService 使用 NeuroMem HybridCollection 后端的功能。
"""

import pytest

from sage.middleware.components.sage_mem.services.hierarchical_memory_service import (
    HierarchicalMemoryService,
)


class TestHierarchicalMemoryServiceInit:
    """测试 HierarchicalMemoryService 初始化"""

    def test_default_init(self):
        """测试默认参数初始化"""
        service = HierarchicalMemoryService(collection_name="test_hier_init_default")
        assert service.tier_mode == "three_tier"
        assert service.migration_policy == "overflow"
        assert service.tier_names == ["stm", "mtm", "ltm"]

    def test_two_tier_mode_init(self):
        """测试两层模式初始化"""
        service = HierarchicalMemoryService(
            collection_name="test_hier_init_two", tier_mode="two_tier"
        )
        assert service.tier_mode == "two_tier"
        assert len(service.tier_names) == 2
        assert service.tier_names == ["stm", "ltm"]

    def test_functional_mode_init(self):
        """测试功能模式初始化"""
        service = HierarchicalMemoryService(
            collection_name="test_hier_init_func", tier_mode="functional"
        )
        assert service.tier_mode == "functional"

    def test_custom_capacities(self):
        """测试自定义容量"""
        service = HierarchicalMemoryService(
            collection_name="test_hier_init_cap",
            tier_capacities={"stm": 50, "mtm": 500, "ltm": -1},
        )
        assert service.tier_capacities["stm"] == 50
        assert service.tier_capacities["mtm"] == 500


class TestHierarchicalMemoryServiceInsert:
    """测试 HierarchicalMemoryService 插入功能"""

    @pytest.fixture
    def service(self):
        """创建测试用服务实例"""
        return HierarchicalMemoryService(
            collection_name="test_hier_insert",
            tier_capacities={"stm": 5, "mtm": 50, "ltm": -1},
        )

    def test_insert_basic(self, service):
        """测试基本插入（带 vector）"""
        import numpy as np

        vector = np.random.randn(384).astype(np.float32)
        entry_id = service.insert(entry="测试条目1", vector=vector, metadata={"type": "test"})

        assert entry_id is not None
        assert isinstance(entry_id, str)

    def test_insert_multiple(self, service):
        """测试多次插入"""
        import numpy as np

        for i in range(5):
            vector = np.random.randn(384).astype(np.float32)
            service.insert(entry=f"条目{i}", vector=vector, metadata={})

        stats = service.get_stats()
        assert stats.get("memory_count", 0) >= 5


class TestHierarchicalMemoryServiceRetrieve:
    """测试 HierarchicalMemoryService 检索功能"""

    @pytest.fixture
    def populated_service(self):
        """创建预填充数据的服务"""
        import numpy as np

        service = HierarchicalMemoryService(collection_name="test_hier_retrieve")
        # 插入测试数据（带 vector）
        for i in range(10):
            vector = np.random.randn(384).astype(np.float32)
            service.insert(
                entry=f"测试条目 {i}", vector=vector, metadata={"type": "test", "index": i}
            )
        return service

    def test_retrieve_basic(self, populated_service):
        """测试基本检索"""
        import numpy as np

        query_vector = np.random.randn(384).astype(np.float32)
        result = populated_service.retrieve(query="测试", vector=query_vector, metadata={})

        assert isinstance(result, list)

    def test_retrieve_with_limit(self, populated_service):
        """测试限制返回数量"""
        import numpy as np

        query_vector = np.random.randn(384).astype(np.float32)
        result = populated_service.retrieve(query="测试", vector=query_vector, metadata={}, top_k=3)

        assert isinstance(result, list)
        assert len(result) <= 3


class TestHierarchicalMemoryServiceMigration:
    """测试 HierarchicalMemoryService 迁移功能"""

    def test_overflow_migration(self):
        """测试溢出迁移"""
        import numpy as np

        service = HierarchicalMemoryService(
            collection_name="test_hier_overflow",
            migration_policy="overflow",
            tier_capacities={"stm": 3, "mtm": 10, "ltm": -1},
        )

        # 插入超过 STM 容量的条目（带 vector）
        for i in range(5):
            vector = np.random.randn(384).astype(np.float32)
            service.insert(entry=f"条目{i}", vector=vector, metadata={})

        # 服务应该正常工作，数据可能迁移到其他层
        stats = service.get_stats()
        assert stats.get("memory_count", 0) >= 5

    def test_manual_migration(self):
        """测试手动迁移模式下的插入"""
        import numpy as np

        service = HierarchicalMemoryService(
            collection_name="test_hier_manual",
            migration_policy="manual",
            tier_capacities={"stm": 10, "mtm": 100, "ltm": -1},
        )

        # 插入条目（带 vector）
        for i in range(3):
            vector = np.random.randn(384).astype(np.float32)
            service.insert(entry=f"条目{i}", vector=vector, metadata={})

        # 验证条目已插入
        stats = service.get_stats()
        assert stats.get("memory_count", 0) >= 3


class TestHierarchicalMemoryServiceStatistics:
    """测试 HierarchicalMemoryService 统计功能"""

    def test_get_stats(self):
        """测试获取统计信息"""
        import numpy as np

        service = HierarchicalMemoryService(collection_name="test_hier_stats")

        for i in range(5):
            vector = np.random.randn(384).astype(np.float32)
            service.insert(entry=f"条目{i}", vector=vector, metadata={})

        stats = service.get_stats()

        assert isinstance(stats, dict)
        # 验证有条目被插入
        assert stats.get("memory_count", 0) >= 5
