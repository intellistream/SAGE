"""T1.2 - UnifiedCollection 索引管理测试

验收标准：8个测试全部通过
- test_add_index: 添加索引
- test_remove_index: 删除索引
- test_list_indexes: 列出所有索引
- test_insert_to_index: 将数据加入索引
- test_remove_from_index: 从索引移除数据
- test_query_by_index: 通过索引查询
- test_retrieve: 检索完整数据
- test_auto_index_on_insert: 插入时自动加入索引
"""

import pytest

from sage.middleware.components.sage_mem.neuromem.memory_collection.unified_collection import (
    UnifiedCollection,
)


class TestUnifiedCollectionIndexes:
    """T1.2 - UnifiedCollection 索引管理测试"""

    def test_add_index(self):
        """测试添加索引"""
        collection = UnifiedCollection(name="test", config={})

        # 添加第一个索引
        success1 = collection.add_index("fifo", "fifo", {"max_size": 100})
        assert success1 is True
        assert "fifo" in collection.indexes
        assert collection.indexes["fifo"].index_type == "fifo"

        # 添加第二个索引
        success2 = collection.add_index("vector", "faiss", {"dim": 128})
        assert success2 is True
        assert len(collection.indexes) == 2

        # 添加重复索引（应该失败）
        success3 = collection.add_index("fifo", "fifo", {})
        assert success3 is False

    def test_remove_index(self):
        """测试删除索引"""
        collection = UnifiedCollection(name="test", config={})

        # 添加索引
        collection.add_index("idx1", "fifo", {})
        collection.add_index("idx2", "faiss", {})
        assert len(collection.indexes) == 2

        # 删除存在的索引
        success1 = collection.remove_index("idx1")
        assert success1 is True
        assert "idx1" not in collection.indexes
        assert len(collection.indexes) == 1

        # 删除不存在的索引
        success2 = collection.remove_index("nonexistent")
        assert success2 is False

    def test_list_indexes(self):
        """测试列出所有索引"""
        collection = UnifiedCollection(name="test", config={})

        # 空索引列表
        indexes = collection.list_indexes()
        assert indexes == []

        # 添加索引后查看
        collection.add_index("fifo", "fifo", {"max_size": 100})
        collection.add_index("vector", "faiss", {"dim": 128})

        indexes = collection.list_indexes()
        assert len(indexes) == 2
        assert any(idx["name"] == "fifo" and idx["type"] == "fifo" for idx in indexes)
        assert any(
            idx["name"] == "vector" and idx["type"] == "faiss" for idx in indexes
        )

    def test_insert_to_index(self):
        """测试将数据加入索引"""
        collection = UnifiedCollection(name="test", config={})

        # 先插入数据（不加入索引）
        data_id = collection.insert("Test text", {"key": "value"}, index_names=[])
        assert collection.size() == 1

        # 添加索引
        collection.add_index("idx1", "fifo", {})

        # 将数据加入索引
        success = collection.insert_to_index(data_id, "idx1")
        assert success is True
        assert collection.indexes["idx1"].contains(data_id)

        # 尝试加入不存在的索引
        success2 = collection.insert_to_index(data_id, "nonexistent")
        assert success2 is False

        # 尝试加入不存在的数据
        success3 = collection.insert_to_index("fake_id", "idx1")
        assert success3 is False

    def test_remove_from_index(self):
        """测试从索引移除数据"""
        collection = UnifiedCollection(name="test", config={})

        # 添加索引并插入数据
        collection.add_index("idx1", "fifo", {})
        data_id = collection.insert("Test text", {})

        # 验证数据在索引中
        assert collection.indexes["idx1"].contains(data_id)

        # 从索引移除
        success = collection.remove_from_index(data_id, "idx1")
        assert success is True
        assert not collection.indexes["idx1"].contains(data_id)

        # 原始数据应该还在
        assert collection.get(data_id) is not None

        # 尝试从不存在的索引移除
        success2 = collection.remove_from_index(data_id, "nonexistent")
        assert success2 is False

    def test_query_by_index(self):
        """测试通过索引查询"""
        collection = UnifiedCollection(name="test", config={})

        # 添加索引并插入数据
        collection.add_index("idx1", "fifo", {})
        id1 = collection.insert("Text 1", {})
        id2 = collection.insert("Text 2", {})
        id3 = collection.insert("Text 3", {})

        # 查询所有数据
        results = collection.query_by_index("idx1", query=None)
        assert len(results) == 3
        assert id1 in results
        assert id2 in results

        # 使用 top_k 参数
        results_top2 = collection.query_by_index("idx1", query=None, top_k=2)
        assert len(results_top2) == 2

        # 查询不存在的索引
        with pytest.raises(ValueError):
            collection.query_by_index("nonexistent", query=None)

    def test_retrieve(self):
        """测试检索完整数据"""
        collection = UnifiedCollection(name="test", config={})

        # 添加索引并插入数据
        collection.add_index("idx1", "fifo", {})
        id1 = collection.insert("Text 1", {"idx": 0})
        id2 = collection.insert("Text 2", {"idx": 1})

        # 检索完整数据
        results = collection.retrieve("idx1", query=None)
        assert len(results) == 2
        assert all("text" in r and "metadata" in r for r in results)
        assert any(r["text"] == "Text 1" and r["metadata"]["idx"] == 0 for r in results)

        # 使用 top_k
        results_top1 = collection.retrieve("idx1", query=None, top_k=1)
        assert len(results_top1) == 1

    def test_auto_index_on_insert(self):
        """测试插入时自动加入索引"""
        collection = UnifiedCollection(name="test", config={})

        # 添加两个索引
        collection.add_index("idx1", "fifo", {})
        collection.add_index("idx2", "faiss", {})

        # 插入数据（默认加入所有索引）
        data_id = collection.insert("Test text", {})

        # 验证数据在所有索引中
        assert collection.indexes["idx1"].contains(data_id)
        assert collection.indexes["idx2"].contains(data_id)

        # 插入数据（只加入指定索引）
        data_id2 = collection.insert("Text 2", {}, index_names=["idx1"])
        assert collection.indexes["idx1"].contains(data_id2)
        assert not collection.indexes["idx2"].contains(data_id2)
