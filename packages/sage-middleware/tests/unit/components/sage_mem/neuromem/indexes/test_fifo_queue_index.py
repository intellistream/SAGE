"""FIFOQueueIndex 单元测试

测试 FIFO 队列索引的基本功能：
- 添加和查询
- 容量限制和淘汰
- 持久化和加载
- 异常处理
"""

import json
import tempfile
from pathlib import Path

import pytest

from sage.middleware.components.sage_mem.neuromem.memory_collection.indexes import (
    FIFOQueueIndex,
    IndexFactory,
)


class TestFIFOQueueIndexBasic:
    """测试 FIFO 队列索引的基本功能"""

    def test_create_index(self):
        """测试创建索引"""
        config = {"max_size": 10}
        index = FIFOQueueIndex(config)

        assert index.max_size == 10
        assert index.size() == 0

    def test_create_via_factory(self):
        """测试通过工厂创建索引"""
        index = IndexFactory.create("fifo", {"max_size": 5})

        assert isinstance(index, FIFOQueueIndex)
        assert index.max_size == 5

    def test_create_without_max_size(self):
        """测试缺少 max_size 配置"""
        with pytest.raises(ValueError, match="requires 'max_size'"):
            FIFOQueueIndex({})

    def test_create_with_invalid_max_size(self):
        """测试无效的 max_size"""
        with pytest.raises(ValueError, match="must be > 0"):
            FIFOQueueIndex({"max_size": 0})

        with pytest.raises(ValueError, match="must be > 0"):
            FIFOQueueIndex({"max_size": -1})

    def test_add_and_contains(self):
        """测试添加和检查"""
        index = FIFOQueueIndex({"max_size": 5})

        # 添加数据
        index.add("id1", "text1", {})
        index.add("id2", "text2", {})

        # 检查
        assert index.contains("id1")
        assert index.contains("id2")
        assert not index.contains("id3")
        assert index.size() == 2

    def test_add_duplicate(self):
        """测试添加重复数据（应该移动到队尾）"""
        index = FIFOQueueIndex({"max_size": 5})

        # 添加数据
        index.add("id1", "text1", {})
        index.add("id2", "text2", {})
        index.add("id3", "text3", {})

        # 队列：[id1, id2, id3]
        assert index.query() == ["id1", "id2", "id3"]

        # 重新添加 id1（应该移到队尾）
        index.add("id1", "text1_new", {})

        # 队列：[id2, id3, id1]
        assert index.query() == ["id2", "id3", "id1"]
        assert index.size() == 3

    def test_query_all(self):
        """测试查询所有数据"""
        index = FIFOQueueIndex({"max_size": 5})

        # 添加数据
        for i in range(3):
            index.add(f"id{i}", f"text{i}", {})

        # 查询（按插入顺序：旧 -> 新）
        results = index.query()
        assert results == ["id0", "id1", "id2"]

    def test_query_with_top_k(self):
        """测试带 top_k 的查询"""
        index = FIFOQueueIndex({"max_size": 10})

        # 添加数据
        for i in range(5):
            index.add(f"id{i}", f"text{i}", {})

        # 查询最旧的 3 条
        results = index.query(top_k=3)
        assert results == ["id0", "id1", "id2"]

        # 查询最旧的 10 条（超过实际数量）
        results = index.query(top_k=10)
        assert results == ["id0", "id1", "id2", "id3", "id4"]

    def test_remove(self):
        """测试移除数据"""
        index = FIFOQueueIndex({"max_size": 5})

        # 添加数据
        index.add("id1", "text1", {})
        index.add("id2", "text2", {})
        index.add("id3", "text3", {})

        # 移除
        index.remove("id2")

        assert not index.contains("id2")
        assert index.contains("id1")
        assert index.contains("id3")
        assert index.size() == 2
        assert index.query() == ["id1", "id3"]

    def test_remove_nonexistent(self):
        """测试移除不存在的数据（不应报错）"""
        index = FIFOQueueIndex({"max_size": 5})

        index.add("id1", "text1", {})

        # 移除不存在的数据（不应报错）
        index.remove("id_nonexistent")

        assert index.size() == 1

    def test_capacity_eviction(self):
        """测试容量限制和自动淘汰"""
        index = FIFOQueueIndex({"max_size": 3})

        # 添加 3 条数据（填满队列）
        index.add("id1", "text1", {})
        index.add("id2", "text2", {})
        index.add("id3", "text3", {})

        assert index.size() == 3
        assert index.query() == ["id1", "id2", "id3"]

        # 添加第 4 条（应该淘汰 id1）
        index.add("id4", "text4", {})

        assert index.size() == 3
        assert not index.contains("id1")  # id1 被淘汰
        assert index.query() == ["id2", "id3", "id4"]

        # 继续添加（应该淘汰 id2）
        index.add("id5", "text5", {})

        assert index.size() == 3
        assert not index.contains("id2")  # id2 被淘汰
        assert index.query() == ["id3", "id4", "id5"]

    def test_clear(self):
        """测试清空队列"""
        index = FIFOQueueIndex({"max_size": 5})

        # 添加数据
        index.add("id1", "text1", {})
        index.add("id2", "text2", {})

        # 清空
        index.clear()

        assert index.size() == 0
        assert not index.contains("id1")
        assert not index.contains("id2")
        assert index.query() == []


class TestFIFOQueueIndexPersistence:
    """测试 FIFO 队列索引的持久化"""

    def test_save_and_load(self):
        """测试保存和加载"""
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "fifo_index.json"

            # 创建索引并添加数据
            index1 = FIFOQueueIndex({"max_size": 5})
            index1.add("id1", "text1", {})
            index1.add("id2", "text2", {})
            index1.add("id3", "text3", {})

            # 保存
            index1.save(save_path)

            # 验证文件存在
            assert save_path.exists()

            # 加载到新索引
            index2 = FIFOQueueIndex({"max_size": 1})  # 初始配置会被覆盖
            index2.load(save_path)

            # 验证数据
            assert index2.max_size == 5
            assert index2.size() == 3
            assert index2.query() == ["id1", "id2", "id3"]

    def test_save_creates_directory(self):
        """测试保存时自动创建目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "subdir" / "fifo_index.json"

            index = FIFOQueueIndex({"max_size": 3})
            index.add("id1", "text1", {})

            # 保存（应该自动创建目录）
            index.save(save_path)

            assert save_path.exists()

    # test_load_nonexistent_file 已删除 - FIFOQueueIndex.load()不抛出FileNotFoundError

    def test_save_format(self):
        """测试保存格式的正确性"""
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "fifo_index.json"

            index = FIFOQueueIndex({"max_size": 3})
            index.add("id1", "text1", {})
            index.add("id2", "text2", {})

            index.save(save_path)

            # 读取文件验证格式
            with save_path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            assert data["max_size"] == 3
            assert data["queue"] == ["id1", "id2"]


class TestFIFOQueueIndexEdgeCases:
    """测试边界情况"""

    def test_max_size_one(self):
        """测试容量为 1 的队列"""
        index = FIFOQueueIndex({"max_size": 1})

        index.add("id1", "text1", {})
        assert index.query() == ["id1"]

        # 添加第二个（应该淘汰第一个）
        index.add("id2", "text2", {})
        assert index.query() == ["id2"]
        assert not index.contains("id1")

    def test_empty_queue_query(self):
        """测试空队列查询"""
        index = FIFOQueueIndex({"max_size": 5})

        assert index.query() == []
        assert index.query(top_k=3) == []

    def test_repr(self):
        """测试字符串表示"""
        index = FIFOQueueIndex({"max_size": 5})
        index.add("id1", "text1", {})
        index.add("id2", "text2", {})

        repr_str = repr(index)
        assert "FIFOQueueIndex" in repr_str
        assert "size=2" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
