"""T1.3 - BaseIndex + IndexFactory 测试

验收标准：成功导入并基本功能测试
- 测试 IndexFactory 注册和创建
- 测试 BaseIndex 抽象接口
"""

import pytest

from sage.middleware.components.sage_mem.neuromem.memory_collection.indexes import (
    BaseIndex,
    IndexFactory,
    MockIndex,
)


class TestIndexFactory:
    """IndexFactory 功能测试"""

    def test_register_and_create(self):
        """测试注册和创建索引"""
        # 注册 MockIndex
        IndexFactory.register("mock", MockIndex)
        assert IndexFactory.is_registered("mock")

        # 创建索引
        index = IndexFactory.create("mock", {"test": "config"})
        assert isinstance(index, MockIndex)
        assert isinstance(index, BaseIndex)

    def test_list_types(self):
        """测试列出索引类型"""
        # 清空并重新注册
        IndexFactory.clear_registry()
        IndexFactory.register("mock", MockIndex)
        IndexFactory.register("test", MockIndex)

        types = IndexFactory.list_types()
        assert "mock" in types
        assert "test" in types
        assert types == sorted(types)  # 应该是排序的

    def test_create_unknown_type(self):
        """测试创建未知类型索引"""
        IndexFactory.clear_registry()

        with pytest.raises(ValueError) as exc_info:
            IndexFactory.create("unknown_type", {})

        assert "Unknown index type" in str(exc_info.value)
        assert "unknown_type" in str(exc_info.value)

    def test_unregister(self):
        """测试注销索引类型"""
        IndexFactory.clear_registry()
        IndexFactory.register("temp", MockIndex)
        assert IndexFactory.is_registered("temp")

        # 注销
        success = IndexFactory.unregister("temp")
        assert success is True
        assert not IndexFactory.is_registered("temp")

        # 注销不存在的类型
        success2 = IndexFactory.unregister("nonexistent")
        assert success2 is False


class TestBaseIndex:
    """BaseIndex 接口测试（通过 MockIndex）"""

    def test_mock_index_implements_base_index(self):
        """测试 MockIndex 实现了 BaseIndex 的所有方法"""
        index = MockIndex("test", {})

        # 验证继承关系
        assert isinstance(index, BaseIndex)

        # 验证所有抽象方法都已实现
        assert hasattr(index, "add")
        assert hasattr(index, "remove")
        assert hasattr(index, "query")
        assert hasattr(index, "contains")
        assert hasattr(index, "size")
        assert hasattr(index, "save")
        assert hasattr(index, "load")

    def test_base_index_operations(self):
        """测试基本索引操作"""
        index = MockIndex("test", {})

        # 初始状态
        assert index.size() == 0

        # 添加数据
        index.add("id1", "text1", {})
        assert index.size() == 1
        assert index.contains("id1")

        # 查询
        results = index.query(None)
        assert "id1" in results

        # 删除
        index.remove("id1")
        assert index.size() == 0
        assert not index.contains("id1")
