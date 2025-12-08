"""KeyValueMemoryService 单元测试

测试 KeyValueMemoryService 使用 NeuroMem KVMemoryCollection 后端的功能。
"""

import pytest

from sage.middleware.components.sage_mem.services.key_value_memory_service import (
    KeyValueMemoryService,
)


class TestKeyValueMemoryServiceInit:
    """测试 KeyValueMemoryService 初始化"""

    def test_default_init(self):
        """测试默认参数初始化"""
        service = KeyValueMemoryService()
        assert service.collection_name == "kv_memory"
        assert service.index_name == "default_index"
        assert service.index_type == "bm25s"
        assert service.default_topk == 5

    def test_custom_collection_name(self):
        """测试自定义 collection 名称"""
        service = KeyValueMemoryService(collection_name="custom_kv")
        assert service.collection_name == "custom_kv"

    def test_custom_index_name(self):
        """测试自定义索引名称"""
        service = KeyValueMemoryService(index_name="my_index")
        assert service.index_name == "my_index"

    def test_custom_topk(self):
        """测试自定义 topk"""
        service = KeyValueMemoryService(default_topk=10)
        assert service.default_topk == 10


class TestKeyValueMemoryServiceInsert:
    """测试 KeyValueMemoryService 插入功能"""

    @pytest.fixture
    def service(self):
        """创建测试用服务实例"""
        return KeyValueMemoryService(collection_name="test_kv_insert")

    def test_insert_basic(self, service):
        """测试基本插入"""
        entry_id = service.insert(entry="用户喜欢蓝色")

        assert entry_id is not None
        assert isinstance(entry_id, str)

    def test_insert_with_metadata(self, service):
        """测试带元数据的插入"""
        entry_id = service.insert(
            entry="用户喜欢蓝色", metadata={"key": "favorite_color", "value": "blue"}
        )

        assert entry_id is not None

    def test_insert_with_priority(self, service):
        """测试带优先级的插入（active 模式）"""
        entry_id = service.insert(
            entry="重要信息",
            metadata={"type": "important"},
            insert_mode="active",
            insert_params={"priority": 10},
        )

        assert entry_id is not None

    def test_insert_invalid_entry(self, service):
        """测试插入无效类型"""
        with pytest.raises(TypeError):
            service.insert(entry=123)  # type: ignore


class TestKeyValueMemoryServiceRetrieve:
    """测试 KeyValueMemoryService 检索功能"""

    @pytest.fixture
    def populated_service(self):
        """创建预填充数据的服务"""
        service = KeyValueMemoryService(collection_name="test_kv_retrieve")

        # 插入测试数据
        service.insert(entry="用户喜欢蓝色", metadata={"type": "preference"})
        service.insert(entry="用户喜欢吃披萨", metadata={"type": "food"})
        service.insert(entry="用户名是张三", metadata={"type": "info"})
        service.insert(entry="用户年龄是25岁", metadata={"type": "info"})

        return service

    def test_retrieve_basic(self, populated_service):
        """测试基本检索"""
        result = populated_service.retrieve(query="蓝色", metadata={})

        assert isinstance(result, list)

    def test_retrieve_with_topk(self, populated_service):
        """测试指定返回数量"""
        result = populated_service.retrieve(query="用户", metadata={}, top_k=2)

        assert isinstance(result, list)
        assert len(result) <= 2

    def test_retrieve_empty_query(self, populated_service):
        """测试空查询"""
        result = populated_service.retrieve(query=None, metadata={})

        assert result == []


class TestKeyValueMemoryServiceDelete:
    """测试 KeyValueMemoryService 删除功能"""

    @pytest.fixture
    def service(self):
        """创建测试用服务实例"""
        service = KeyValueMemoryService(collection_name="test_kv_delete")
        return service

    def test_delete_existing(self, service):
        """测试删除已存在的条目"""
        entry_id = service.insert(entry="待删除的内容")

        result = service.delete(entry_id)

        # delete 返回 bool
        assert isinstance(result, bool)


class TestKeyValueMemoryServiceStatistics:
    """测试 KeyValueMemoryService 统计功能"""

    def test_get_stats(self):
        """测试获取统计信息"""
        service = KeyValueMemoryService(collection_name="test_kv_stats")

        for i in range(3):
            service.insert(entry=f"条目 {i}")

        stats = service.get_stats()

        assert "memory_count" in stats
        assert "index_count" in stats
        assert "collection_name" in stats
        assert stats["memory_count"] >= 3

    def test_clear(self):
        """测试清空所有记忆"""
        service = KeyValueMemoryService(collection_name="test_kv_clear")

        for i in range(3):
            service.insert(entry=f"条目 {i}")

        result = service.clear()

        assert result is True
