"""KeyValueMemoryService 单元测试"""

import pytest

from sage.middleware.components.sage_mem.services.key_value_memory_service import (
    KeyValueMemoryService,
)


class TestKeyValueMemoryServiceInit:
    """测试 KeyValueMemoryService 初始化"""

    def test_default_init(self):
        """测试默认参数初始化"""
        service = KeyValueMemoryService()
        assert service.match_type == "exact"
        assert service.fuzzy_threshold == 0.8
        assert service.semantic_threshold == 0.7
        assert service.embedding_dim == 768

    def test_fuzzy_mode_init(self):
        """测试模糊匹配模式初始化"""
        service = KeyValueMemoryService(match_type="fuzzy")
        assert service.match_type == "fuzzy"

    def test_semantic_mode_init(self):
        """测试语义匹配模式初始化"""
        service = KeyValueMemoryService(match_type="semantic")
        assert service.match_type == "semantic"

    def test_custom_thresholds(self):
        """测试自定义阈值"""
        service = KeyValueMemoryService(fuzzy_threshold=0.9, semantic_threshold=0.8)
        assert service.fuzzy_threshold == 0.9
        assert service.semantic_threshold == 0.8


class TestKeyValueMemoryServiceInsert:
    """测试 KeyValueMemoryService 插入功能"""

    @pytest.fixture
    def service(self):
        """创建测试用服务实例"""
        return KeyValueMemoryService()

    def test_insert_with_key(self, service):
        """测试带键的插入"""
        result = service.insert(
            entry="用户喜欢蓝色", metadata={"key": "favorite_color", "value": "blue"}
        )

        assert result is not None

    def test_insert_via_set(self, service):
        """测试使用 set 方法"""
        service.set("test_key", "test_value")

        result = service.get("test_key")
        assert result is not None

    def test_insert_with_vector(self, service):
        """测试带向量的插入"""
        import numpy as np

        vector = np.random.randn(768).astype(np.float32)
        result = service.insert(
            entry="测试条目", vector=vector, metadata={"key": "test_key"}
        )

        assert result is not None


class TestKeyValueMemoryServiceRetrieve:
    """测试 KeyValueMemoryService 检索功能"""

    @pytest.fixture
    def populated_service(self):
        """创建预填充数据的服务"""
        service = KeyValueMemoryService()

        # 插入测试数据
        service.set("favorite_color", "blue")
        service.set("favorite_food", "pizza")
        service.set("user_name", "张三")
        service.set("user_age", "25")

        return service

    def test_exact_match(self, populated_service):
        """测试精确匹配"""
        result = populated_service.get("favorite_color")

        assert result is not None
        assert "blue" in str(result)

    def test_retrieve_with_metadata(self, populated_service):
        """测试使用 metadata 检索"""
        result = populated_service.retrieve(
            query="favorite_color", metadata={"match_type": "exact"}
        )

        assert isinstance(result, list)
        assert len(result) > 0

    def test_fuzzy_match(self):
        """测试模糊匹配"""
        service = KeyValueMemoryService(match_type="fuzzy", fuzzy_threshold=0.7)

        service.set("color_preference", "blue")

        # 使用相似的键
        result = service.retrieve(query="colour_preference", metadata={})

        assert isinstance(result, list)


class TestKeyValueMemoryServiceUpdate:
    """测试 KeyValueMemoryService 更新功能"""

    @pytest.fixture
    def service(self):
        """创建测试用服务实例"""
        return KeyValueMemoryService()

    def test_update_existing_key(self, service):
        """测试更新已存在的键"""
        # 首次设置
        service.set("test_key", "old_value")

        # 更新
        service.set("test_key", "new_value")

        result = service.get("test_key")

        assert "new_value" in str(result)


class TestKeyValueMemoryServiceDelete:
    """测试 KeyValueMemoryService 删除功能"""

    @pytest.fixture
    def service(self):
        """创建测试用服务实例"""
        service = KeyValueMemoryService()
        service.set("to_delete", "value")
        return service

    def test_delete_by_key(self, service):
        """测试按键删除"""
        result = service.delete("to_delete")

        # delete 返回删除的数量
        assert result >= 1
        assert service.get("to_delete") is None


class TestKeyValueMemoryServiceStatistics:
    """测试 KeyValueMemoryService 统计功能"""

    def test_get_stats(self):
        """测试获取统计信息"""
        service = KeyValueMemoryService()

        for i in range(5):
            service.set(f"key_{i}", f"value_{i}")

        stats = service.get_stats()

        assert "total_keys" in stats
        assert stats["total_keys"] >= 5

    def test_get_all_keys(self):
        """测试获取所有键"""
        service = KeyValueMemoryService()

        for i in range(3):
            service.set(f"key_{i}", f"value_{i}")

        keys = service.get_all_keys()

        assert len(keys) >= 3
        assert "key_0" in keys
        assert "key_1" in keys
        assert "key_2" in keys
