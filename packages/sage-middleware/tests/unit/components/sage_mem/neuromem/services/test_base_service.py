"""
Unit tests for BaseMemoryService

测试范围:
- 抽象方法检查 (不能直接实例化)
- 公共方法: delete(), get(), list_indexes()
- 工具方法: _get_embeddings(), _summarize(), _filter_by_metadata()
- Mock Service 实现 (用于测试基类功能)
"""

import pytest

from sage.middleware.components.sage_mem.neuromem.memory_collection import UnifiedCollection
from sage.middleware.components.sage_mem.neuromem.services import BaseMemoryService


class TestAbstractMethods:
    """测试抽象方法 - 不能直接实例化 BaseMemoryService"""

    def test_cannot_instantiate_base_service(self):
        """BaseMemoryService 是抽象类，不能直接实例化"""
        collection = UnifiedCollection("test")

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseMemoryService(collection)  # type: ignore


# Mock Service 类定义 (模块级别，所有测试类共享)
class MockService(BaseMemoryService):
    """简单的 Mock Service 实现"""

    def _setup_indexes(self):
        # 创建一个简单的 FIFO 索引
        self.collection.add_index("test_index", "fifo", {"max_size": 10})

    def insert(self, text, metadata=None, **kwargs):
        return self.collection.insert(text, metadata, index_names=["test_index"])

    def retrieve(self, query, top_k=5, **kwargs):
        data_ids = self.collection.query_by_index("test_index", top_k=top_k)
        return self.collection.retrieve("test_index", query, top_k=top_k)


@pytest.fixture
def mock_service_class():
    """Mock Service 类 fixture"""
    return MockService


@pytest.fixture
def mock_service():
    """Mock Service 实例 fixture"""
    collection = UnifiedCollection("test_collection")
    return MockService(collection)


class TestConcreteService:
    """测试具体 Service 实现 (使用 Mock Service)"""

    def test_service_initialization(self, mock_service):
        """测试 Service 初始化"""
        assert mock_service.collection.name == "test_collection"
        assert mock_service.config == {}
        assert "test_index" in mock_service.collection.indexes

    def test_service_with_config(self, mock_service_class):
        """测试带配置的 Service 初始化"""
        collection = UnifiedCollection("test")
        config = {"top_k": 10, "threshold": 0.5}
        service = mock_service_class(collection, config)

        assert service.config == config
        assert service.config["top_k"] == 10

    def test_setup_indexes_called(self, mock_service):
        """测试 _setup_indexes() 在 __init__ 中被调用"""
        # 索引应该已经创建
        indexes = mock_service.collection.list_indexes()
        assert len(indexes) == 1
        assert indexes[0]["name"] == "test_index"
        assert indexes[0]["type"] == "fifo"


class TestPublicMethods:
    """测试公共方法"""

    def test_get_data(self, mock_service_class):
        """测试 get() 方法"""
        collection = UnifiedCollection("test")
        service = mock_service_class(collection)

        # 插入测试数据
        data_id = service.insert("Hello, world!", {"type": "greeting"})
        data = service.get(data_id)

        assert data is not None
        assert data["text"] == "Hello, world!"
        assert data["metadata"]["type"] == "greeting"

    def test_get_nonexistent_data(self, mock_service_class):
        """测试获取不存在的数据"""
        collection = UnifiedCollection("test")
        service = mock_service_class(collection)

        data = service.get("nonexistent_id")
        assert data is None

    def test_delete_data(self, mock_service_class):
        """测试 delete() 方法"""
        collection = UnifiedCollection("test")
        service = mock_service_class(collection)

        # 插入测试数据
        data_id = service.insert("Hello, world!", {"type": "greeting"})

        # 删除数据
        result = service.delete(data_id)
        assert result is True

        # 验证数据已删除
        data = service.get(data_id)
        assert data is None

    def test_delete_nonexistent_data(self, mock_service_class):
        """测试删除不存在的数据"""
        collection = UnifiedCollection("test")
        service = mock_service_class(collection)

        result = service.delete("nonexistent_id")
        assert result is False

    def test_list_indexes(self, mock_service_class):
        """测试 list_indexes() 方法"""
        collection = UnifiedCollection("test")
        service = mock_service_class(collection)

        indexes = service.list_indexes()
        assert len(indexes) == 1
        assert indexes[0]["name"] == "test_index"


class TestUtilityMethods:
    """测试工具方法"""

    @pytest.fixture
    def mock_embedder(self):
        """创建 Mock Embedder"""

        class MockEmbedder:
            def embed(self, texts):
                return [[0.1, 0.2, 0.3] for _ in texts]

        return MockEmbedder()

    @pytest.fixture
    def mock_summarizer(self):
        """创建 Mock Summarizer"""

        class MockSummarizer:
            def summarize(self, texts):
                return f"Summary of {len(texts)} texts"

        return MockSummarizer()

    def test_get_embeddings(self, mock_service_class, mock_embedder):
        """测试 _get_embeddings() 方法"""
        collection = UnifiedCollection("test")
        config = {"embedder": mock_embedder}
        service = mock_service_class(collection, config)

        embeddings = service._get_embeddings(["text1", "text2"])
        assert len(embeddings) == 2
        assert embeddings[0] == [0.1, 0.2, 0.3]

    def test_get_embeddings_no_embedder(self, mock_service_class):
        """测试没有配置 embedder 时抛出异常"""
        collection = UnifiedCollection("test")
        service = mock_service_class(collection)

        with pytest.raises(ValueError, match="requires 'embedder'"):
            service._get_embeddings(["text"])

    def test_summarize_with_summarizer(self, mock_service_class, mock_summarizer):
        """测试 _summarize() 方法 (有 summarizer)"""
        collection = UnifiedCollection("test")
        config = {"summarizer": mock_summarizer}
        service = mock_service_class(collection, config)

        summary = service._summarize(["text1", "text2"])
        assert summary == "Summary of 2 texts"

    def test_summarize_fallback(self, mock_service_class):
        """测试 _summarize() fallback (无 summarizer)"""
        collection = UnifiedCollection("test")
        service = mock_service_class(collection)

        texts = [f"word{i}" for i in range(150)]  # 超过 100 个 token
        summary = service._summarize(texts)

        # Fallback 应该只取前 100 个 token
        tokens = summary.split()
        assert len(tokens) == 100

    def test_filter_by_metadata(self, mock_service_class):
        """测试 _filter_by_metadata() 方法"""
        collection = UnifiedCollection("test")
        service = mock_service_class(collection)

        results = [
            {"id": "1", "metadata": {"type": "doc", "lang": "en"}},
            {"id": "2", "metadata": {"type": "code", "lang": "python"}},
            {"id": "3", "metadata": {"type": "doc", "lang": "zh"}},
        ]

        # 过滤 type=doc
        filtered = service._filter_by_metadata(results, {"type": "doc"})
        assert len(filtered) == 2
        assert filtered[0]["id"] == "1"
        assert filtered[1]["id"] == "3"

        # 过滤 type=doc AND lang=en
        filtered = service._filter_by_metadata(results, {"type": "doc", "lang": "en"})
        assert len(filtered) == 1
        assert filtered[0]["id"] == "1"

    def test_filter_by_metadata_no_filters(self, mock_service_class):
        """测试不提供过滤条件时返回原始结果"""
        collection = UnifiedCollection("test")
        service = mock_service_class(collection)

        results = [{"id": "1"}, {"id": "2"}]
        filtered = service._filter_by_metadata(results, {})
        assert filtered == results


class TestServiceRepr:
    """测试字符串表示"""

    def test_repr(self, mock_service_class):
        """测试 __repr__() 方法"""
        collection = UnifiedCollection("my_collection")
        service = mock_service_class(collection)

        repr_str = repr(service)
        assert "MockService" in repr_str
        assert "my_collection" in repr_str
        assert "indexes=1" in repr_str
