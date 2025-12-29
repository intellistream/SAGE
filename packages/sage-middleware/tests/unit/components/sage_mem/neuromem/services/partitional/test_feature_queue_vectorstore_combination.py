"""
测试 FeatureQueueVectorstoreCombinationService

测试点:
1. Service 初始化和索引配置（需要embedder）
2. 数据插入
3. 五种检索策略（weighted、voting、rrf、linear、recent）
4. 融合算法正确性
5. 分数归一化
6. 边界条件和错误处理
"""

import pytest

from sage.middleware.components.sage_mem.neuromem.memory_collection import UnifiedCollection
from sage.middleware.components.sage_mem.neuromem.services.partitional.feature_queue_vectorstore_combination import (
    FeatureQueueVectorstoreCombinationService,
)
from sage.middleware.components.sage_mem.neuromem.services.registry import (
    MemoryServiceRegistry,
)


class MockEmbedder:
    """Mock Embedding 模型"""

    def __init__(self, dim: int = 768):
        self.dim = dim

    def encode(self, text: str) -> list[float]:
        """生成简单的 mock embedding (单文本)"""
        import hashlib

        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        vector = [(hash_val >> i) % 100 / 100.0 for i in range(self.dim)]
        return vector

    def embed(self, texts: list[str] | str) -> list[list[float]]:
        """批量embedding，与服务代码兼容"""
        if isinstance(texts, str):
            texts = [texts]
        return [self.encode(text) for text in texts]


@pytest.fixture
def embedder():
    """创建 Mock Embedder"""
    return MockEmbedder(dim=128)


@pytest.fixture
def temp_data_dir(tmp_path):
    """临时数据目录"""
    return tmp_path / "test_feature_queue_vectorstore_service"


@pytest.fixture
def collection(temp_data_dir):
    """创建 UnifiedCollection"""
    col = UnifiedCollection(name="test_collection", config={"data_dir": str(temp_data_dir)})
    yield col


@pytest.fixture
def service(collection, embedder):
    """创建 FeatureQueueVectorstoreCombinationService"""
    config = {
        "vector_dim": 128,
        "fifo_max_size": 20,
        "combination_strategy": "weighted",
        "weights": {
            "feature_index": 0.3,
            "fifo_index": 0.3,
            "vector_index": 0.4,
        },
        "fusion_method": "rrf",
        "rrf_k": 60,
        "embedder": embedder,
    }
    return FeatureQueueVectorstoreCombinationService(collection, config)


class TestServiceRegistration:
    """测试 Service 注册"""

    def test_service_registered(self):
        """测试 Service 已注册到 Registry"""
        service_cls = MemoryServiceRegistry.get_service_class(
            "partitional.feature_queue_vectorstore_combination"
        )
        assert service_cls is FeatureQueueVectorstoreCombinationService


class TestServiceInitialization:
    """测试 Service 初始化"""

    def test_init_requires_embedder(self, collection):
        """测试必须提供 embedder"""
        config = {"vector_dim": 128}

        with pytest.raises(ValueError, match="Embedder is required"):
            FeatureQueueVectorstoreCombinationService(collection, config)

    def test_init_with_config(self, collection, embedder):
        """测试使用配置初始化"""
        config = {
            "vector_dim": 256,
            "fifo_max_size": 50,
            "combination_strategy": "rrf",
            "fusion_method": "linear",
            "embedder": embedder,
        }
        service = FeatureQueueVectorstoreCombinationService(collection, config)

        assert service.vector_dim == 256
        assert service.fifo_max_size == 50
        assert service.combination_strategy == "rrf"
        assert service.fusion_method == "linear"

    def test_init_without_config(self, collection, embedder):
        """测试带最小配置初始化"""
        config = {"embedder": embedder}
        service = FeatureQueueVectorstoreCombinationService(collection, config)

        assert service.vector_dim == 768
        assert service.fifo_max_size == 100
        assert service.combination_strategy == "weighted"
        assert service.fusion_method == "rrf"

    def test_indexes_setup(self, service):
        """测试索引配置正确"""
        assert "feature_index" in service.collection.indexes
        assert "fifo_index" in service.collection.indexes
        assert "vector_index" in service.collection.indexes


class TestDataInsertion:
    """测试数据插入"""

    def test_insert_basic(self, service):
        """测试基本插入"""
        data_id = service.insert("这是一条测试消息")
        assert data_id is not None
        assert isinstance(data_id, str)

    def test_insert_with_vector(self, service):
        """测试向量生成"""
        text = "这是一条测试消息"
        data_id = service.insert(text)

        data = service.collection.get(data_id)
        assert data is not None
        assert "vector" in data.get("metadata", {})
        vector = data["metadata"]["vector"]
        assert isinstance(vector, list)
        assert len(vector) == 128

    def test_insert_with_metadata(self, service):
        """测试带元数据插入"""
        metadata = {"source": "test", "priority": 1}
        data_id = service.insert("测试消息", metadata)

        data = service.collection.get(data_id)
        assert data["metadata"]["source"] == "test"
        assert data["metadata"]["priority"] == 1

    def test_insert_multiple(self, service):
        """测试批量插入"""
        ids = []
        for i in range(5):
            data_id = service.insert(f"消息 {i}")
            ids.append(data_id)

        assert len(ids) == 5
        assert len(set(ids)) == 5


class TestRetrieveWeighted:
    """测试加权检索"""

    def test_retrieve_weighted_basic(self, service):
        """测试基本加权检索"""
        service.insert("Python 编程语言")
        service.insert("Java 开发")
        service.insert("JavaScript 前端")

        results = service.retrieve("Python", top_k=2, strategy="weighted")
        assert len(results) <= 2
        if results:
            assert "fused_score" in results[0]

    def test_retrieve_weighted_with_precomputed_vector(self, service, embedder):
        """测试使用预计算向量检索"""
        service.insert("机器学习")
        service.insert("深度学习")

        query_vector = embedder.embed(["学习"])[0]  # 批量API返回list[list[float]]，取第一个元素
        results = service.retrieve("学习", top_k=2, strategy="weighted", query_vector=query_vector)
        assert len(results) <= 2


class TestRetrieveVoting:
    """测试投票检索"""

    def test_retrieve_voting(self, service):
        """测试投票检索"""
        service.insert("数据库设计")
        service.insert("SQL查询")
        service.insert("NoSQL存储")

        results = service.retrieve("数据库", top_k=2, strategy="voting")
        assert len(results) <= 2


class TestRetrieveRRF:
    """测试RRF检索"""

    def test_retrieve_rrf_basic(self, service):
        """测试RRF融合检索"""
        service.insert("自然语言处理")
        service.insert("计算机视觉")
        service.insert("语音识别")

        results = service.retrieve("语言", top_k=2, strategy="rrf")
        assert len(results) <= 2
        if results:
            assert "rrf_score" in results[0]


class TestRetrieveLinear:
    """测试线性融合检索"""

    def test_retrieve_linear_basic(self, service):
        """测试线性融合检索"""
        service.insert("云计算平台")
        service.insert("边缘计算")
        service.insert("分布式系统")

        results = service.retrieve("计算", top_k=2, strategy="linear")
        assert len(results) <= 2
        if results:
            assert "linear_score" in results[0]

    def test_retrieve_linear_different_alpha(self, service):
        """测试不同alpha值的线性融合"""
        service.insert("区块链技术")
        service.insert("加密货币")

        results = service.retrieve("技术", top_k=2, strategy="linear", alpha=0.7)
        assert len(results) <= 2


class TestRetrieveRecent:
    """测试最近检索"""

    def test_retrieve_recent(self, service):
        """测试最近消息检索"""
        service.insert("旧消息1")
        service.insert("旧消息2")
        service.insert("新消息1")
        service.insert("新消息2")

        results = service.retrieve("消息", top_k=2, strategy="recent")
        assert len(results) <= 2


class TestQueueOperations:
    """测试队列操作"""

    def test_get_recent_items(self, service):
        """测试获取最近项目"""
        service.insert("消息A")
        service.insert("消息B")
        service.insert("消息C")

        recent = service.get_recent_items(count=2)
        assert len(recent) <= 2


class TestRRFFusion:
    """测试RRF融合方法"""

    def test_rrf_fusion_basic(self, service):
        """测试基本RRF融合"""
        result_lists = [
            [{"id": "1", "text": "文本1"}, {"id": "2", "text": "文本2"}],
            [{"id": "2", "text": "文本2"}, {"id": "3", "text": "文本3"}],
            [{"id": "1", "text": "文本1"}, {"id": "3", "text": "文本3"}],
        ]

        fused = service._rrf_fusion(result_lists, k=60, top_k=3)
        assert len(fused) == 3
        assert all("rrf_score" in item for item in fused)

    def test_rrf_fusion_no_overlap(self, service):
        """测试无重叠的RRF融合"""
        result_lists = [
            [{"id": "1", "text": "文本1"}],
            [{"id": "2", "text": "文本2"}],
            [{"id": "3", "text": "文本3"}],
        ]

        fused = service._rrf_fusion(result_lists, k=60, top_k=3)
        assert len(fused) == 3

    def test_rrf_fusion_complete_overlap(self, service):
        """测试完全重叠的RRF融合"""
        result_lists = [
            [{"id": "1", "text": "文本1"}, {"id": "2", "text": "文本2"}],
            [{"id": "1", "text": "文本1"}, {"id": "2", "text": "文本2"}],
            [{"id": "1", "text": "文本1"}, {"id": "2", "text": "文本2"}],
        ]

        fused = service._rrf_fusion(result_lists, k=60, top_k=2)
        assert len(fused) == 2
        # ID "1" 应该得分更高（在所有列表中排名第一）
        assert fused[0]["id"] == "1"


class TestLinearFusion:
    """测试线性融合方法"""

    def test_linear_fusion_basic(self, service):
        """测试基本线性融合"""
        feature_results = [
            {"id": "1", "text": "文本1"},
            {"id": "2", "text": "文本2"},
        ]
        vector_results = [
            {"id": "2", "text": "文本2"},
            {"id": "3", "text": "文本3"},
        ]

        fused = service._linear_fusion(feature_results, vector_results, alpha=0.5, top_k=3)
        assert len(fused) == 3
        assert all("linear_score" in item for item in fused)

    def test_linear_fusion_alpha_zero(self, service):
        """测试alpha=0（只用vector）"""
        feature_results = [{"id": "1", "text": "文本1"}]
        vector_results = [{"id": "2", "text": "文本2"}]

        fused = service._linear_fusion(feature_results, vector_results, alpha=0.0, top_k=2)
        # alpha=0 意味着 100% vector weight
        assert fused[0]["id"] == "2"

    def test_linear_fusion_alpha_one(self, service):
        """测试alpha=1（只用feature）"""
        feature_results = [{"id": "1", "text": "文本1"}]
        vector_results = [{"id": "2", "text": "文本2"}]

        fused = service._linear_fusion(feature_results, vector_results, alpha=1.0, top_k=2)
        # alpha=1 意味着 100% feature weight
        assert fused[0]["id"] == "1"


class TestScoreNormalization:
    """测试分数归一化"""

    def test_normalize_scores_basic(self, service):
        """测试基本归一化"""
        results = [
            {"id": "1", "text": "文本1"},
            {"id": "2", "text": "文本2"},
            {"id": "3", "text": "文本3"},
        ]

        normalized = service._normalize_scores(results)
        assert len(normalized) == 3
        # 分数应该在 [0, 1] 范围内
        for score in normalized.values():
            assert 0.0 <= score <= 1.0

    def test_normalize_scores_same_value(self, service):
        """测试所有得分相同时的归一化"""
        results = [
            {"id": "1", "text": "文本1"},
        ]

        normalized = service._normalize_scores(results)
        assert normalized["1"] == 1.0

    def test_normalize_scores_empty(self, service):
        """测试空结果归一化"""
        normalized = service._normalize_scores([])
        assert normalized == {}


class TestWeightedFusion:
    """测试加权融合方法"""

    def test_weighted_fusion(self, service):
        """测试加权融合"""
        result_sets = {
            "feature_index": [
                {"id": "1", "text": "文本1"},
                {"id": "2", "text": "文本2"},
            ],
            "fifo_index": [
                {"id": "2", "text": "文本2"},
                {"id": "3", "text": "文本3"},
            ],
            "vector_index": [
                {"id": "1", "text": "文本1"},
                {"id": "3", "text": "文本3"},
            ],
        }

        weights = {
            "feature_index": 0.3,
            "fifo_index": 0.3,
            "vector_index": 0.4,
        }

        fused = service._weighted_fusion(result_sets, weights, top_k=3)
        assert len(fused) == 3
        assert all("fused_score" in item for item in fused)


class TestErrorHandling:
    """测试错误处理"""

    def test_retrieve_unknown_strategy(self, service):
        """测试未知检索策略"""
        service.insert("测试消息")

        with pytest.raises(ValueError, match="Unknown strategy"):
            service.retrieve("测试", strategy="unknown_strategy")


class TestEdgeCases:
    """测试边界情况"""

    def test_retrieve_empty_collection(self, service):
        """测试空Collection检索"""
        results = service.retrieve("查询文本", top_k=5)
        assert isinstance(results, list)

    def test_large_top_k(self, service):
        """测试超大top_k"""
        service.insert("消息1")
        service.insert("消息2")

        results = service.retrieve("消息", top_k=1000)
        assert len(results) <= 1000
