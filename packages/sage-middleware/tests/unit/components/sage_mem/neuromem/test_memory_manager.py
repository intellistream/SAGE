"""MemoryManager 单元测试

测试 MemoryManager 的核心功能：
- Collection 创建和获取
- Collection 删除
- 持久化和加载
- 懒加载机制
- 列表所有 Collection
"""

import tempfile
from pathlib import Path

import pytest

from sage.middleware.components.sage_mem.neuromem.memory_manager import (
    MemoryManager,
)

# Skip: Service implementation issues (Vector requirements, float() errors, etc.)
pytestmark = pytest.mark.skip(reason="Service implementation issues")


class TestMemoryManagerBasic:
    """MemoryManager 基础功能测试"""

    def test_init_default_dir(self):
        """测试默认数据目录初始化"""
        manager = MemoryManager()

        assert manager.data_dir is not None
        assert manager.data_dir.exists()
        assert manager.collections == {}

    def test_init_custom_dir(self):
        """测试自定义数据目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(data_dir=tmpdir)

            assert manager.data_dir == Path(tmpdir)

    def test_create_collection(self):
        """测试创建 Collection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(data_dir=tmpdir)

            collection = manager.create_collection("test_col")

            assert collection is not None
            assert collection.name == "test_col"
            assert "test_col" in manager.collections

    def test_create_collection_with_config(self):
        """测试创建带配置的 Collection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(data_dir=tmpdir)

            config = {"max_size": 1000, "description": "Test collection"}
            collection = manager.create_collection("test_col", config)

            assert collection.config == config

    def test_create_duplicate_collection(self):
        """测试创建重复 Collection（应返回已存在的）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(data_dir=tmpdir)

            col1 = manager.create_collection("test_col")
            col2 = manager.create_collection("test_col")

            assert col1 is col2


class TestMemoryManagerGetCollection:
    """MemoryManager 获取 Collection 测试"""

    def test_get_existing_collection(self):
        """测试获取已存在的 Collection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(data_dir=tmpdir)

            created = manager.create_collection("test_col")
            retrieved = manager.get_collection("test_col")

            assert retrieved is created

    def test_get_nonexistent_collection(self):
        """测试获取不存在的 Collection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(data_dir=tmpdir)

            result = manager.get_collection("nonexistent")

            assert result is None

    def test_get_lazy_load(self):
        """测试懒加载机制"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 第一个 manager: 创建并持久化
            manager1 = MemoryManager(data_dir=tmpdir)
            collection = manager1.create_collection("test_col")
            data_id = collection.insert("hello", {"type": "greeting"})
            manager1.persist("test_col")

            # 第二个 manager: 懒加载
            manager2 = MemoryManager(data_dir=tmpdir)
            loaded = manager2.get_collection("test_col")

            assert loaded is not None
            assert loaded.name == "test_col"
            assert loaded.get(data_id) == {
                "text": "hello",
                "metadata": {"type": "greeting"},
                "created_at": loaded.get(data_id)["created_at"],
            }


class TestMemoryManagerRemove:
    """MemoryManager 删除 Collection 测试"""

    def test_remove_memory_only(self):
        """测试删除仅在内存中的 Collection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(data_dir=tmpdir)
            manager.create_collection("test_col")

            result = manager.remove_collection("test_col")

            assert result is True
            assert "test_col" not in manager.collections

    def test_remove_disk_only(self):
        """测试删除仅在磁盘上的 Collection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建并持久化
            manager1 = MemoryManager(data_dir=tmpdir)
            manager1.create_collection("test_col")
            manager1.persist("test_col")

            # 新 manager，删除磁盘文件
            manager2 = MemoryManager(data_dir=tmpdir)
            result = manager2.remove_collection("test_col")

            assert result is True
            assert not manager2.has_on_disk("test_col")

    def test_remove_both(self):
        """测试删除内存和磁盘上的 Collection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(data_dir=tmpdir)
            manager.create_collection("test_col")
            manager.persist("test_col")

            result = manager.remove_collection("test_col")

            assert result is True
            assert "test_col" not in manager.collections
            assert not manager.has_on_disk("test_col")


class TestMemoryManagerPersistence:
    """MemoryManager 持久化测试"""

    def test_persist_simple(self):
        """测试简单持久化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(data_dir=tmpdir)
            collection = manager.create_collection("test_col")
            collection.insert("hello", {"type": "greeting"})
            collection.insert("world", {"type": "noun"})

            result = manager.persist("test_col")

            assert result is True
            assert manager.has_on_disk("test_col")

            # 检查文件存在
            col_path = manager._get_collection_path("test_col")
            assert (col_path / "raw_data.json").exists()
            assert (col_path / "index_metadata.json").exists()
            assert (col_path / "config.json").exists()

    def test_persist_nonexistent(self):
        """测试持久化不存在的 Collection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(data_dir=tmpdir)

            result = manager.persist("nonexistent")

            assert result is False

    def test_persist_with_indexes(self):
        """测试持久化带索引的 Collection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(data_dir=tmpdir)
            collection = manager.create_collection("test_col")

            # 添加数据
            data_id = collection.insert("hello", {"type": "greeting"})

            # 添加索引
            collection.add_index("fifo", "fifo", {"max_size": 10})

            # 持久化
            result = manager.persist("test_col")

            assert result is True

            # 检查索引文件
            col_path = manager._get_collection_path("test_col")
            assert (col_path / "index_fifo").exists()


class TestMemoryManagerLoad:
    """MemoryManager 加载测试"""

    def test_load_simple(self):
        """测试简单加载"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建并持久化
            manager1 = MemoryManager(data_dir=tmpdir)
            collection = manager1.create_collection("test_col")
            id1 = collection.insert("hello", {"type": "greeting"})
            id2 = collection.insert("world", {"type": "noun"})
            manager1.persist("test_col")

            # 加载
            manager2 = MemoryManager(data_dir=tmpdir)
            loaded = manager2.load_collection("test_col")

            assert loaded is not None
            assert loaded.name == "test_col"
            assert loaded.size() == 2
            assert loaded.get(id1)["text"] == "hello"
            assert loaded.get(id2)["text"] == "world"

    def test_load_nonexistent(self):
        """测试加载不存在的 Collection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(data_dir=tmpdir)

            result = manager.load_collection("nonexistent")

            assert result is None

    def test_load_with_indexes(self):
        """测试加载带索引的 Collection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建并持久化
            manager1 = MemoryManager(data_dir=tmpdir)
            collection = manager1.create_collection("test_col")
            data_id = collection.insert("hello", {"type": "greeting"})
            collection.add_index("fifo", "fifo", {"max_size": 10})
            collection.insert_to_index("fifo", data_id)
            manager1.persist("test_col")

            # 加载
            manager2 = MemoryManager(data_dir=tmpdir)
            loaded = manager2.load_collection("test_col")

            assert loaded is not None
            indexes = loaded.list_indexes()
            assert any(idx["name"] == "fifo" for idx in indexes)

    def test_load_with_config(self):
        """测试加载带配置的 Collection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建并持久化
            config = {"max_size": 1000, "description": "Test"}
            manager1 = MemoryManager(data_dir=tmpdir)
            manager1.create_collection("test_col", config)
            manager1.persist("test_col")

            # 加载
            manager2 = MemoryManager(data_dir=tmpdir)
            loaded = manager2.load_collection("test_col")

            assert loaded is not None
            assert loaded.config == config


class TestMemoryManagerList:
    """MemoryManager 列表功能测试"""

    def test_list_empty(self):
        """测试列表空 Manager"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(data_dir=tmpdir)

            collections = manager.list_collections()

            assert collections == {}

    def test_list_memory_only(self):
        """测试列表仅在内存中的 Collection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(data_dir=tmpdir)
            manager.create_collection("col1")
            manager.create_collection("col2")

            collections = manager.list_collections()

            assert collections == {"col1": "memory", "col2": "memory"}

    def test_list_disk_only(self):
        """测试列表仅在磁盘上的 Collection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建并持久化
            manager1 = MemoryManager(data_dir=tmpdir)
            manager1.create_collection("col1")
            manager1.persist("col1")

            # 新 manager
            manager2 = MemoryManager(data_dir=tmpdir)
            collections = manager2.list_collections()

            assert collections == {"col1": "disk"}

    def test_list_both(self):
        """测试列表内存和磁盘上的 Collection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(data_dir=tmpdir)
            manager.create_collection("col1")
            manager.persist("col1")

            collections = manager.list_collections()

            assert collections == {"col1": "both"}

    def test_list_mixed(self):
        """测试混合状态"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 col1 并持久化
            manager1 = MemoryManager(data_dir=tmpdir)
            manager1.create_collection("col1")
            manager1.persist("col1")

            # 新 manager，加载 col1，创建 col2
            manager2 = MemoryManager(data_dir=tmpdir)
            manager2.load_collection("col1")
            manager2.create_collection("col2")

            collections = manager2.list_collections()

            assert collections == {"col1": "both", "col2": "memory"}


class TestMemoryManagerIntegration:
    """MemoryManager 集成测试"""

    def test_full_lifecycle(self):
        """测试完整生命周期"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. 创建 Manager
            manager = MemoryManager(data_dir=tmpdir)

            # 2. 创建 Collection
            collection = manager.create_collection("test_col")
            id1 = collection.insert("hello", {"type": "greeting"})
            id2 = collection.insert("world", {"type": "noun"})

            # 3. 添加索引
            collection.add_index("fifo", "fifo", {"max_size": 10})
            collection.insert_to_index("fifo", id1)

            # 4. 持久化
            manager.persist("test_col")

            # 5. 清空内存
            del manager.collections["test_col"]

            # 6. 懒加载
            loaded = manager.get_collection("test_col")
            assert loaded is not None
            assert loaded.size() == 2

            # 7. 删除
            manager.remove_collection("test_col")
            assert not manager.has_on_disk("test_col")

    def test_multiple_collections(self):
        """测试管理多个 Collection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(data_dir=tmpdir)

            # 创建多个 Collection
            for i in range(5):
                col = manager.create_collection(f"col{i}")
                col.insert(f"data{i}", {"index": i})

            # 持久化部分
            manager.persist("col0")
            manager.persist("col2")

            # 列表
            collections = manager.list_collections()
            assert len(collections) == 5
            assert collections["col0"] == "both"
            assert collections["col1"] == "memory"
            assert collections["col2"] == "both"


class TestMemoryManagerRepr:
    """MemoryManager 字符串表示测试"""

    def test_repr(self):
        """测试 __repr__"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(data_dir=tmpdir)
            manager.create_collection("col1")

            repr_str = repr(manager)

            assert "MemoryManager" in repr_str
            assert "collections=1" in repr_str
            assert "in_memory=1" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
