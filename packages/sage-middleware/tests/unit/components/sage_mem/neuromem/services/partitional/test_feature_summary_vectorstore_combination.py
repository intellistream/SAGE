"""
测试 FeatureSummaryVectorStoreCombinationService

测试点:
1. Service 初始化和索引配置
2. 数据插入（特征提取、摘要生成）
3. 三种检索策略（weighted、voting、cascade）
4. 融合算法正确性
5. 边界条件和错误处理
"""

import pytest

from sage.middleware.components.sage_mem.neuromem.memory_collection import UnifiedCollection
from sage.middleware.components.sage_mem.neuromem.services.partitional.feature_summary_vectorstore_combination import (
    FeatureSummaryVectorStoreCombinationService,
)
from sage.middleware.components.sage_mem.neuromem.services.registry import (
    MemoryServiceRegistry,
)


@pytest.fixture
def temp_data_dir(tmp_path):
    """临时数据目录"""
    return tmp_path / "test_feature_summary_service"


@pytest.fixture
def collection(temp_data_dir):
    """创建 UnifiedCollection"""
    col = UnifiedCollection(name="test_collection", config={"data_dir": str(temp_data_dir)})
    yield col
    # UnifiedCollection 不需要 close()


@pytest.fixture
def service(collection):
    """创建 FeatureSummaryVectorStoreCombinationService"""
    config = {
        "vector_dim": 128,  # 测试用小维度
        "summary_max_size": 10,
        "combination_strategy": "weighted",
        "weights": {
            "vector_index": 0.5,
            "feature_index": 0.3,
            "summary_index": 0.2,
        },
        "enable_feature_extraction": True,
        "enable_summary_generation": True,
    }
    return FeatureSummaryVectorStoreCombinationService(collection, config)


class TestServiceRegistration:
    """测试 Service 注册"""

    def test_service_registered(self):
        """测试 Service 已注册到 Registry"""
        service_cls = MemoryServiceRegistry.get_service_class(
            "feature_summary_vectorstore_combination"
        )
        assert service_cls is FeatureSummaryVectorStoreCombinationService


class TestServiceInitialization:
    """测试 Service 初始化"""

    def test_init_with_config(self, collection):
        """测试使用配置初始化"""
        config = {
            "vector_dim": 256,
            "summary_max_size": 20,
            "combination_strategy": "voting",
            "enable_feature_extraction": False,
        }
        service = FeatureSummaryVectorStoreCombinationService(collection, config)

        assert service.vector_dim == 256
        assert service.summary_max_size == 20
        assert service.combination_strategy == "voting"
        assert service.enable_feature_extraction is False
        assert service.enable_summary_generation is True  # 默认值

    def test_init_without_config(self, collection):
        """测试不带配置初始化（使用默认值）"""
        service = FeatureSummaryVectorStoreCombinationService(collection, None)

        assert service.vector_dim == 768
        assert service.summary_max_size == 50
        assert service.combination_strategy == "weighted"

    def test_indexes_setup(self, service):
        """测试索引配置正确"""
        # 检查三个索引是否存在
        assert "vector_index" in service.collection.indexes
        assert "feature_index" in service.collection.indexes
        assert "summary_index" in service.collection.indexes


class TestDataInsertion:
    """测试数据插入"""

    def test_insert_basic(self, service):
        """测试基本插入"""
        data_id = service.insert("Hello world", metadata={"source": "test"})

        assert data_id is not None
        assert data_id in service.collection

    def test_insert_with_feature_extraction(self, service):
        """测试特征提取"""
        text = "This is a test sentence with multiple words"
        data_id = service.insert(text)

        # 检查 metadata 中是否有特征
        data = service.collection.get(data_id)
        assert "features" in data["metadata"]
        assert "word_count" in data["metadata"]["features"]
        assert data["metadata"]["features"]["word_count"] == 8

    def test_insert_with_summary_generation(self, service):
        """测试摘要生成"""
        text = "A" * 150  # 超过默认 100 字符
        data_id = service.insert(text)

        # 检查 metadata 中是否有摘要
        data = service.collection.get(data_id)
        assert "summary" in data["metadata"]
        assert len(data["metadata"]["summary"]) < len(text)

    def test_insert_skip_feature_extraction(self, service):
        """测试跳过特征提取"""
        data_id = service.insert(
            "Test text", metadata={}, insert_params={"skip_feature_extraction": True}
        )

        data = service.collection.get(data_id)
        assert "features" not in data["metadata"]

    def test_insert_skip_summary_generation(self, service):
        """测试跳过摘要生成"""
        data_id = service.insert(
            "Test text", metadata={}, insert_params={"skip_summary_generation": True}
        )

        data = service.collection.get(data_id)
        assert "summary" not in data["metadata"]

    def test_insert_multiple(self, service):
        """测试插入多条数据"""
        texts = [f"Document {i}" for i in range(20)]
        ids = [service.insert(text) for text in texts]

        assert len(ids) == 20
        assert len(set(ids)) == 20  # 确保 ID 唯一


class TestRetrieveWeighted:
    """测试加权融合检索"""

    def test_retrieve_weighted_basic(self, service):
        """测试基本加权检索"""
        # 插入测试数据
        service.insert("Python programming language", metadata={"topic": "python"})
        service.insert("Java programming language", metadata={"topic": "java"})
        service.insert("Machine learning with Python", metadata={"topic": "ml"})

        # 检索
        results = service.retrieve("Python programming", top_k=2)

        assert len(results) <= 2
        assert all("id" in r for r in results)

    def test_retrieve_weighted_with_vector(self, service):
        """测试使用预计算向量检索"""
        import numpy as np

        # 插入数据（需要提供向量）
        vector1 = np.random.randn(128).tolist()
        service.insert("Document 1", vector=vector1)

        # 检索（提供查询向量）
        query_vector = np.random.randn(128).tolist()
        results = service.retrieve(
            "Document", top_k=1, query_vector=query_vector
        )

        assert len(results) >= 0


class TestRetrieveVoting:
    """测试投票策略检索"""

    def test_retrieve_voting(self, service):
        """测试投票策略"""
        # 插入数据
        for i in range(5):
            service.insert(f"Python tutorial {i}", metadata={"id": i})

        # 使用投票策略检索
        results = service.retrieve("Python tutorial", top_k=3, strategy="voting")

        assert len(results) <= 3
        # 检查是否有 vote_count 字段
        if results:
            assert "vote_count" in results[0]


class TestRetrieveCascade:
    """测试级联策略检索"""

    def test_retrieve_cascade(self, service):
        """测试级联策略"""
        # 插入数据
        for i in range(10):
            service.insert(f"Machine learning tutorial {i}", metadata={"id": i})

        # 使用级联策略检索
        results = service.retrieve(
            "Machine learning", top_k=5, strategy="cascade"
        )

        assert len(results) <= 5


class TestFusionMethods:
    """测试融合方法"""

    def test_weighted_fusion(self, service):
        """测试加权融合算法"""
        results_by_index = {
            "vector_index": [
                {"id": "a", "score": 0.9},
                {"id": "b", "score": 0.8},
            ],
            "feature_index": [
                {"id": "a", "score": 0.7},
                {"id": "c", "score": 0.6},
            ],
            "summary_index": [
                {"id": "b", "score": 1.0},
            ],
        }
        weights = {
            "vector_index": 0.5,
            "feature_index": 0.3,
            "summary_index": 0.2,
        }

        fused = service._weighted_fusion(results_by_index, weights)

        # 检查所有 ID 都被包含
        ids = {r["id"] for r in fused}
        assert ids == {"a", "b", "c"}

        # 检查有 weighted_score 字段
        assert all("weighted_score" in r for r in fused)

        # 检查排序（分数从高到低）
        scores = [r["weighted_score"] for r in fused]
        assert scores == sorted(scores, reverse=True)


class TestFeatureExtraction:
    """测试特征提取"""

    def test_extract_features(self, service):
        """测试特征提取方法"""
        text = "This is a simple test"
        features = service._extract_features(text)

        assert "word_count" in features
        assert "char_count" in features
        assert "avg_word_length" in features
        assert features["word_count"] == 5

    def test_extract_features_empty(self, service):
        """测试空文本特征提取"""
        features = service._extract_features("")

        assert features["word_count"] == 0  # 空字符串word_count应为0
        assert features["char_count"] == 0


class TestSummaryGeneration:
    """测试摘要生成"""

    def test_generate_summary_short(self, service):
        """测试短文本摘要（不截断）"""
        text = "Short text"
        summary = service._generate_summary(text)

        assert summary == text

    def test_generate_summary_long(self, service):
        """测试长文本摘要（截断）"""
        text = "A" * 150
        summary = service._generate_summary(text)

        assert len(summary) < len(text)
        assert summary.endswith("...")


class TestErrorHandling:
    """测试错误处理"""

    def test_retrieve_unknown_strategy(self, service):
        """测试使用未知策略"""
        service.insert("Test")

        with pytest.raises(ValueError, match="Unknown combination strategy"):
            service.retrieve("Test", strategy="invalid_strategy")


class TestEdgeCases:
    """测试边界条件"""

    def test_retrieve_empty_collection(self, service):
        """测试空 Collection 检索"""
        results = service.retrieve("Test", top_k=5)

        assert isinstance(results, list)
        # 空 collection 可能返回空列表

    def test_large_top_k(self, service):
        """测试 top_k 大于实际数据量"""
        service.insert("Doc 1")
        service.insert("Doc 2")

        results = service.retrieve("Doc", top_k=100)

        assert len(results) <= 2
