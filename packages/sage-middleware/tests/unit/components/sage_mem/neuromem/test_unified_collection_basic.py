"""T1.1 - UnifiedCollection 基础数据管理测试

验收标准：5个测试全部通过
- test_init: 初始化配置
- test_insert_single: 单条数据插入
- test_insert_batch: 批量插入
- test_get_by_id: 按ID获取
- test_delete: 删除数据
"""

import pytest

from sage.middleware.components.sage_mem.neuromem.memory_collection.unified_collection import (
    UnifiedCollection,
)


class TestUnifiedCollectionBasic:
    """T1.1 - UnifiedCollection 基础功能测试"""

    def test_init(self):
        """测试初始化"""
        collection = UnifiedCollection(name="test_collection", config={})
        assert collection.name == "test_collection"
        assert collection.size() == 0

    def test_insert_single(self):
        """测试单条插入"""
        collection = UnifiedCollection(name="test", config={})

        # 插入数据
        id1 = collection.insert(text="Hello, world!", metadata={"type": "greeting"})
        assert id1 is not None
        assert collection.size() == 1

        # 验证数据
        data = collection.get(id1)
        assert data is not None
        assert data["text"] == "Hello, world!"
        assert data["metadata"]["type"] == "greeting"

    def test_insert_batch(self):
        """测试批量插入"""
        collection = UnifiedCollection(name="test", config={})

        # 批量插入
        texts = ["Text 1", "Text 2", "Text 3"]
        metadatas = [{"idx": i} for i in range(3)]
        ids = collection.insert_batch(texts=texts, metadatas=metadatas)

        assert len(ids) == 3
        assert collection.size() == 3

        # 验证每条数据
        for i, id_ in enumerate(ids):
            data = collection.get(id_)
            assert data["text"] == texts[i]
            assert data["metadata"]["idx"] == i

    def test_get_by_id(self):
        """测试按ID获取"""
        collection = UnifiedCollection(name="test", config={})

        # 插入数据
        id1 = collection.insert("Test text", {"key": "value"})

        # 获取存在的数据
        data = collection.get(id1)
        assert data is not None
        assert data["text"] == "Test text"

        # 获取不存在的数据
        data_none = collection.get("nonexistent_id")
        assert data_none is None

    def test_delete(self):
        """测试删除数据"""
        collection = UnifiedCollection(name="test", config={})

        # 插入数据
        id1 = collection.insert("To be deleted", {})
        assert collection.size() == 1

        # 删除数据
        success = collection.delete(id1)
        assert success is True
        assert collection.size() == 0
        assert collection.get(id1) is None

        # 删除不存在的数据
        success2 = collection.delete("nonexistent_id")
        assert success2 is False
