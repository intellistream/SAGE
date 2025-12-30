"""
测试 LSHHashService
"""

import pytest

# Skip all LSH tests - LSH Index not yet registered in IndexFactory
pytestmark = pytest.mark.skip(reason="LSH Index not registered in IndexFactory")

from sage.middleware.components.sage_mem.neuromem.memory_collection import (
    UnifiedCollection,
)
from sage.middleware.components.sage_mem.neuromem.services.partitional import (
    LSHHashService,
)


class MockEmbedder:
    """Mock Embedding 模型"""

    def __init__(self, dim: int = 768):
        self.dim = dim

    def encode(self, texts: list[str]) -> list[list[float]]:
        """生成简单的 mock embedding"""
        import hashlib

        embeddings = []
        for text in texts:
            # 使用哈希生成伪向量（保证相同文本相同向量）
            hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
            vector = [(hash_val >> i) % 100 / 100.0 for i in range(self.dim)]
            embeddings.append(vector)
        return embeddings

    def embed(self, texts: list[str]) -> list[list[float]]:
        """别名方法，与BaseMemoryService的_get_embeddings()兼容"""
        return self.encode(texts)


class TestLSHHashServiceBasic:
    """基础功能测试"""

    def test_init_requires_embedder(self):
        """测试必须提供 embedder"""
        collection = UnifiedCollection("test_collection")

        with pytest.raises(ValueError, match="requires 'embedder'"):
            LSHHashService(collection)

    def test_init_with_embedder(self):
        """测试提供 embedder 的初始化"""
        collection = UnifiedCollection("test_collection")
        embedder = MockEmbedder(dim=384)

        service = LSHHashService(
            collection,
            {
                "embedder": embedder,
                "embedding_dim": 384,
            },
        )

        assert service.config["embedder"] is embedder
        assert service.config["embedding_dim"] == 384

    def test_setup_indexes(self):
        """测试 LSH 索引创建"""
        collection = UnifiedCollection("test_collection")
        embedder = MockEmbedder()

        service = LSHHashService(
            collection,
            {
                "embedder": embedder,
                "embedding_dim": 768,
                "num_tables": 10,
                "hash_size": 8,
            },
        )

        assert "lsh_index" in collection.indexes


class TestLSHHashServiceInsert:
    """插入功能测试"""

    def test_insert_single_item(self):
        """测试插入单条数据"""
        collection = UnifiedCollection("test_collection")
        embedder = MockEmbedder()

        service = LSHHashService(
            collection,
            {
                "embedder": embedder,
                "embedding_dim": 768,
            },
        )

        data_id = service.insert("这是一段测试文本")

        assert data_id is not None
        item = service.get(data_id)
        assert item["text"] == "这是一段测试文本"
        # 检查是否保存了 embedding
        assert "embedding" in item["metadata"]
        assert len(item["metadata"]["embedding"]) == 768

    def test_insert_with_metadata(self):
        """测试插入带元数据的数据"""
        collection = UnifiedCollection("test_collection")
        embedder = MockEmbedder()

        service = LSHHashService(
            collection,
            {
                "embedder": embedder,
                "embedding_dim": 768,
            },
        )

        metadata = {"category": "tech", "author": "Alice"}
        data_id = service.insert("技术文章", metadata=metadata)

        item = service.get(data_id)
        assert item["metadata"]["category"] == "tech"
        assert item["metadata"]["author"] == "Alice"
        assert "embedding" in item["metadata"]

    def test_insert_with_precomputed_vector(self):
        """测试插入预计算的向量"""
        collection = UnifiedCollection("test_collection")
        embedder = MockEmbedder()

        service = LSHHashService(
            collection,
            {
                "embedder": embedder,
                "embedding_dim": 768,
            },
        )

        # 预计算向量
        vector = [0.1] * 768

        data_id = service.insert("文本", vector=vector)

        item = service.get(data_id)
        assert item["metadata"]["embedding"] == vector


class TestLSHHashServiceRetrieve:
    """检索功能测试"""

    def test_retrieve_similar_items(self):
        """测试检索相似数据"""
        collection = UnifiedCollection("test_collection")
        embedder = MockEmbedder(dim=128)

        service = LSHHashService(
            collection,
            {
                "embedder": embedder,
                "embedding_dim": 128,
                "num_tables": 5,
            },
        )

        # 插入数据
        service.insert("Python 编程语言")
        service.insert("Java 编程语言")
        service.insert("苹果水果")

        # 查询（使用较低阈值，因为"编程语言"与"Python 编程语言"的Jaccard相似度 < 0.5）
        results = service.retrieve("编程语言", top_k=2, threshold=0.3)

        # 应该返回结果（LSH 近似搜索）
        assert len(results) > 0
        assert all("score" in r for r in results)

    def test_retrieve_with_precomputed_query_vector(self):
        """测试使用预计算的查询向量"""
        collection = UnifiedCollection("test_collection")
        embedder = MockEmbedder(dim=128)

        service = LSHHashService(
            collection,
            {
                "embedder": embedder,
                "embedding_dim": 128,
            },
        )

        service.insert("测试文本")

        # 使用预计算向量查询
        query_vector = [0.5] * 128
        results = service.retrieve("查询", top_k=5, query_vector=query_vector)

        assert isinstance(results, list)

    def test_retrieve_with_metadata_filter(self):
        """测试带元数据过滤的检索"""
        collection = UnifiedCollection("test_collection")
        embedder = MockEmbedder(dim=128)

        service = LSHHashService(
            collection,
            {
                "embedder": embedder,
                "embedding_dim": 128,
            },
        )

        service.insert("文本1", metadata={"category": "A"})
        service.insert("文本2", metadata={"category": "B"})
        service.insert("文本3", metadata={"category": "A"})

        results = service.retrieve(
            "查询", top_k=10, filters={"category": "A"}
        )

        # 过滤后只应返回 category=A 的数据
        assert all(r["metadata"]["category"] == "A" for r in results)

    def test_retrieve_with_threshold(self):
        """测试相似度阈值过滤"""
        collection = UnifiedCollection("test_collection")
        embedder = MockEmbedder(dim=128)

        service = LSHHashService(
            collection,
            {
                "embedder": embedder,
                "embedding_dim": 128,
            },
        )

        service.insert("文本1")
        service.insert("文本2")

        # 设置高阈值
        results = service.retrieve("查询", top_k=10, threshold=0.95)

        # 所有结果应该满足阈值
        assert all(r["score"] >= 0.95 for r in results)


class TestLSHHashServiceFindDuplicates:
    """去重功能测试"""

    def test_find_duplicates_empty(self):
        """测试空数据库查找重复"""
        collection = UnifiedCollection("test_collection")
        embedder = MockEmbedder(dim=128)

        service = LSHHashService(
            collection,
            {
                "embedder": embedder,
                "embedding_dim": 128,
            },
        )

        duplicates = service.find_duplicates()
        assert len(duplicates) == 0

    def test_find_duplicates_with_data(self):
        """测试查找重复数据"""
        collection = UnifiedCollection("test_collection")
        embedder = MockEmbedder(dim=128)

        service = LSHHashService(
            collection,
            {
                "embedder": embedder,
                "embedding_dim": 128,
            },
        )

        # 插入一些数据
        service.insert("文本A")
        service.insert("文本B")
        service.insert("文本C")

        duplicates = service.find_duplicates(threshold=0.9)

        # 返回格式应该是 (id1, id2, similarity) 元组列表
        assert isinstance(duplicates, list)
        for dup in duplicates:
            assert len(dup) == 3
            assert isinstance(dup[2], float)  # similarity


class TestLSHHashServiceEdgeCases:
    """边界情况测试"""

    def test_empty_collection_retrieve(self):
        """测试空集合检索"""
        collection = UnifiedCollection("test_collection")
        embedder = MockEmbedder()

        service = LSHHashService(
            collection,
            {
                "embedder": embedder,
                "embedding_dim": 768,
            },
        )

        results = service.retrieve("查询", top_k=10)
        assert len(results) == 0

    def test_insert_empty_string(self):
        """测试插入空字符串"""
        collection = UnifiedCollection("test_collection")
        embedder = MockEmbedder()

        service = LSHHashService(
            collection,
            {
                "embedder": embedder,
                "embedding_dim": 768,
            },
        )

        data_id = service.insert("")
        assert data_id is not None

    def test_custom_num_tables(self):
        """测试自定义哈希表数量"""
        collection = UnifiedCollection("test_collection")
        embedder = MockEmbedder()

        service = LSHHashService(
            collection,
            {
                "embedder": embedder,
                "embedding_dim": 768,
                "num_tables": 20,
                "hash_size": 16,
            },
        )

        assert service.config["num_tables"] == 20
        assert service.config["hash_size"] == 16
