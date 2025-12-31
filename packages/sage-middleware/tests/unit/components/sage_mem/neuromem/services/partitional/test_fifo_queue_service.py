"""
测试 FIFOQueueService
"""

import pytest

from sage.middleware.components.sage_mem.neuromem.memory_collection import (
    UnifiedCollection,
)
from sage.middleware.components.sage_mem.neuromem.services.partitional import (
    FIFOQueueService,
)


class TestFIFOQueueServiceBasic:
    """基础功能测试"""

    def test_init_default_config(self):
        """测试默认配置初始化"""
        collection = UnifiedCollection("test_collection")
        service = FIFOQueueService(collection)

        assert service.collection is collection
        assert service.config["max_size"] == 100  # 默认值

    def test_init_custom_config(self):
        """测试自定义配置"""
        collection = UnifiedCollection("test_collection")
        service = FIFOQueueService(collection, {"max_size": 50})

        assert service.config["max_size"] == 50

    def test_setup_indexes(self):
        """测试索引创建"""
        collection = UnifiedCollection("test_collection")
        service = FIFOQueueService(collection, {"max_size": 10})

        # 检查索引是否创建
        assert "fifo_queue" in collection.indexes
        assert collection.indexes["fifo_queue"].max_size == 10


class TestFIFOQueueServiceInsert:
    """插入功能测试"""

    def test_insert_single_item(self):
        """测试插入单条数据"""
        collection = UnifiedCollection("test_collection")
        service = FIFOQueueService(collection, {"max_size": 5})

        data_id = service.insert("测试消息1")

        assert data_id is not None
        item = service.get(data_id)
        assert item["text"] == "测试消息1"

    def test_insert_with_metadata(self):
        """测试插入带元数据的数据"""
        collection = UnifiedCollection("test_collection")
        service = FIFOQueueService(collection)

        metadata = {"user": "Alice", "timestamp": "2024-01-01"}
        data_id = service.insert("Hello", metadata=metadata)

        item = service.get(data_id)
        assert item["metadata"]["user"] == "Alice"
        assert item["metadata"]["timestamp"] == "2024-01-01"

    def test_insert_auto_eviction(self):
        """测试自动淘汰功能"""
        collection = UnifiedCollection("test_collection")
        service = FIFOQueueService(collection, {"max_size": 3})

        # 插入3条数据
        id1 = service.insert("消息1")
        id2 = service.insert("消息2")
        id3 = service.insert("消息3")

        # 检查队列已满
        results = service.get_recent(limit=10)
        assert len(results) == 3

        # 插入第4条，应该淘汰第1条
        id4 = service.insert("消息4")

        results = service.get_recent(limit=10)
        assert len(results) == 3

        # 第1条应该不在队列中（但可能仍在collection的raw_data中）
        # 队列检索不应该返回id1
        result_ids = [r["id"] for r in results]
        assert id1 not in result_ids
        # 其他3条应该在队列中
        assert id2 in result_ids
        assert id3 in result_ids
        assert id4 in result_ids


class TestFIFOQueueServiceRetrieve:
    """检索功能测试"""

    def test_retrieve_recent_items(self):
        """测试检索最近数据"""
        collection = UnifiedCollection("test_collection")
        service = FIFOQueueService(collection, {"max_size": 10})

        # 插入5条数据
        for i in range(5):
            service.insert(f"消息{i+1}")

        results = service.retrieve(query=None, top_k=3)

        assert len(results) == 3
        # FIFO：最早的3条
        assert results[0]["text"] == "消息1"
        assert results[1]["text"] == "消息2"
        assert results[2]["text"] == "消息3"

    def test_retrieve_all_items(self):
        """测试检索所有数据"""
        collection = UnifiedCollection("test_collection")
        service = FIFOQueueService(collection, {"max_size": 10})

        for i in range(5):
            service.insert(f"消息{i+1}")

        results = service.retrieve(query=None, top_k=100)

        assert len(results) == 5

    def test_retrieve_with_metadata_filter(self):
        """测试带元数据过滤的检索"""
        collection = UnifiedCollection("test_collection")
        service = FIFOQueueService(collection)

        service.insert("消息1", metadata={"type": "question"})
        service.insert("消息2", metadata={"type": "answer"})
        service.insert("消息3", metadata={"type": "question"})

        # 过滤只要 question 类型
        results = service.retrieve(
            query=None, top_k=10, filters={"type": "question"}
        )

        assert len(results) == 2
        assert all(r["metadata"]["type"] == "question" for r in results)


class TestFIFOQueueServiceGetRecent:
    """get_recent 方法测试"""

    def test_get_recent_default(self):
        """测试默认获取最近数据"""
        collection = UnifiedCollection("test_collection")
        service = FIFOQueueService(collection, {"max_size": 10})

        for i in range(5):
            service.insert(f"消息{i+1}")

        results = service.get_recent()

        assert len(results) == 5

    def test_get_recent_with_limit(self):
        """测试限制返回数量"""
        collection = UnifiedCollection("test_collection")
        service = FIFOQueueService(collection)

        for i in range(10):
            service.insert(f"消息{i+1}")

        results = service.get_recent(limit=3)

        assert len(results) == 3


class TestFIFOQueueServiceClear:
    """清空功能测试"""

    def test_clear_queue(self):
        """测试清空队列"""
        collection = UnifiedCollection("test_collection")
        service = FIFOQueueService(collection)

        # 插入数据
        for i in range(5):
            service.insert(f"消息{i+1}")

        assert len(service.get_recent()) == 5

        # 清空
        service.clear()

        assert len(service.get_recent()) == 0

    def test_clear_and_reinsert(self):
        """测试清空后重新插入"""
        collection = UnifiedCollection("test_collection")
        service = FIFOQueueService(collection, {"max_size": 3})

        # 插入数据
        service.insert("消息1")
        service.insert("消息2")

        # 清空
        service.clear()

        # 重新插入
        service.insert("新消息1")
        service.insert("新消息2")

        results = service.get_recent()
        assert len(results) == 2
        assert results[0]["text"] == "新消息1"


class TestFIFOQueueServiceDelete:
    """删除功能测试（继承自 BaseMemoryService）"""

    def test_delete_item(self):
        """测试删除单条数据"""
        collection = UnifiedCollection("test_collection")
        service = FIFOQueueService(collection)

        data_id = service.insert("测试消息")
        assert service.get(data_id) is not None

        service.delete(data_id)
        assert service.get(data_id) is None

    def test_delete_multiple_items(self):
        """测试删除多条数据"""
        collection = UnifiedCollection("test_collection")
        service = FIFOQueueService(collection)

        id1 = service.insert("消息1")
        id2 = service.insert("消息2")
        id3 = service.insert("消息3")

        service.delete(id1)
        service.delete(id3)

        results = service.get_recent()
        assert len(results) == 1
        assert results[0]["id"] == id2


class TestFIFOQueueServiceEdgeCases:
    """边界情况测试"""

    def test_empty_queue_retrieve(self):
        """测试空队列检索"""
        collection = UnifiedCollection("test_collection")
        service = FIFOQueueService(collection)

        results = service.retrieve(query=None, top_k=10)
        assert len(results) == 0

    def test_max_size_one(self):
        """测试队列大小为1"""
        collection = UnifiedCollection("test_collection")
        service = FIFOQueueService(collection, {"max_size": 1})

        id1 = service.insert("消息1")
        results = service.get_recent(limit=10)
        assert len(results) == 1
        assert results[0]["id"] == id1

        id2 = service.insert("消息2")
        # 队列只能保留1条，应该只有消息2
        results = service.get_recent(limit=10)
        assert len(results) == 1
        assert results[0]["id"] == id2

    def test_insert_empty_string(self):
        """测试插入空字符串"""
        collection = UnifiedCollection("test_collection")
        service = FIFOQueueService(collection)

        data_id = service.insert("")
        assert data_id is not None
        item = service.get(data_id)
        assert item["text"] == ""
