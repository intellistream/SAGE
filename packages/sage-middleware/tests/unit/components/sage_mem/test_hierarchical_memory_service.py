"""HierarchicalMemoryService 单元测试"""

import pytest

from sage.middleware.components.sage_mem.services.hierarchical_memory_service import (
    HierarchicalMemoryService,
)


class TestHierarchicalMemoryServiceInit:
    """测试 HierarchicalMemoryService 初始化"""

    def test_default_init(self):
        """测试默认参数初始化"""
        service = HierarchicalMemoryService()
        assert service.tier_mode == "three_tier"
        assert service.migration_policy == "overflow"
        assert service.tier_names == ["stm", "mtm", "ltm"]

    def test_two_tier_mode_init(self):
        """测试两层模式初始化"""
        service = HierarchicalMemoryService(tier_mode="two_tier")
        assert service.tier_mode == "two_tier"
        assert len(service.tier_names) == 2
        assert service.tier_names == ["stm", "ltm"]

    def test_functional_mode_init(self):
        """测试功能模式初始化"""
        service = HierarchicalMemoryService(tier_mode="functional")
        assert service.tier_mode == "functional"

    def test_custom_capacities(self):
        """测试自定义容量"""
        service = HierarchicalMemoryService(tier_capacities={"stm": 50, "mtm": 500, "ltm": -1})
        assert service.tier_capacities["stm"] == 50
        assert service.tier_capacities["mtm"] == 500


class TestHierarchicalMemoryServiceInsert:
    """测试 HierarchicalMemoryService 插入功能"""

    @pytest.fixture
    def service(self):
        """创建测试用服务实例"""
        return HierarchicalMemoryService(tier_capacities={"stm": 5, "mtm": 50, "ltm": -1})

    def test_insert_to_stm(self, service):
        """测试插入到 STM"""
        entry_id = service.insert(entry="测试条目1", metadata={"type": "test"})

        assert entry_id is not None
        # STM 应该有数据
        assert len(service.tiers.get("stm", [])) >= 1

    def test_insert_multiple(self, service):
        """测试多次插入"""
        for i in range(5):
            service.insert(entry=f"条目{i}", metadata={})

        # STM 应该有数据（可能迁移到 MTM）
        total = sum(len(t.get("data", [])) for t in service.tiers.values())
        assert total == 5


class TestHierarchicalMemoryServiceRetrieve:
    """测试 HierarchicalMemoryService 检索功能"""

    @pytest.fixture
    def populated_service(self):
        """创建预填充数据的服务"""
        service = HierarchicalMemoryService()
        # 插入测试数据
        for i in range(10):
            service.insert(entry=f"测试条目 {i}", metadata={"type": "test", "index": i})
        return service

    def test_retrieve_basic(self, populated_service):
        """测试基本检索"""
        result = populated_service.retrieve(query="测试", metadata={})

        assert isinstance(result, list)

    def test_retrieve_with_limit(self, populated_service):
        """测试限制返回数量"""
        # top_k 是 retrieve 的参数，不是 metadata
        result = populated_service.retrieve(query="测试", metadata={}, top_k=3)

        assert isinstance(result, list)
        assert len(result) <= 3


class TestHierarchicalMemoryServiceMigration:
    """测试 HierarchicalMemoryService 迁移功能"""

    def test_overflow_migration(self):
        """测试溢出迁移"""
        service = HierarchicalMemoryService(
            migration_policy="overflow",
            tier_capacities={"stm": 3, "mtm": 10, "ltm": -1},
        )

        # 插入超过 STM 容量的条目
        for i in range(5):
            service.insert(entry=f"条目{i}", metadata={})

        # STM 应该不超过容量 (deque 自动限制 maxlen)
        stm_data = service.tiers.get("stm", {}).get("data", [])
        assert len(stm_data) <= 3

    def test_manual_migration(self):
        """测试手动迁移模式下的插入"""
        service = HierarchicalMemoryService(
            migration_policy="manual",
            tier_capacities={"stm": 10, "mtm": 100, "ltm": -1},
        )

        # 插入条目
        entry_ids = []
        for i in range(3):
            entry_id = service.insert(entry=f"条目{i}", metadata={})
            entry_ids.append(entry_id)

        # 验证条目已插入到 STM
        stm_data = service.tiers.get("stm", {}).get("data", [])
        assert len(stm_data) == 3


class TestHierarchicalMemoryServiceStatistics:
    """测试 HierarchicalMemoryService 统计功能"""

    def test_tier_counts(self):
        """测试获取各层条目数量"""
        service = HierarchicalMemoryService()

        for i in range(5):
            service.insert(entry=f"条目{i}", metadata={})

        # 直接检查 tiers 中的数据
        total = 0
        for tier_name in service.tier_names:
            tier_data = service.tiers.get(tier_name, {}).get("data", [])
            total += len(tier_data)

        assert total >= 5
