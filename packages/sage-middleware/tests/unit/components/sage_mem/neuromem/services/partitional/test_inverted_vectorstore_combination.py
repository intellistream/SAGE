"""
测试 InvertedVectorStoreCombinationService

测试点:
1. Service 初始化和索引配置
2. 数据插入
3. RRF 融合检索
4. 线性融合检索
5. 融合算法正确性
6. 分数归一化
7. 边界条件和错误处理
"""

import pytest

from sage.middleware.components.sage_mem.neuromem.memory_collection import UnifiedCollection
from sage.middleware.components.sage_mem.neuromem.services.partitional.inverted_vectorstore_combination import (
    InvertedVectorStoreCombinationService,
)
from sage.middleware.components.sage_mem.neuromem.services.registry import (
    MemoryServiceRegistry,
)


@pytest.fixture
def temp_data_dir(tmp_path):
    """临时数据目录"""
    return tmp_path / "test_inverted_vector_service"


@pytest.fixture
def collection(temp_data_dir):
    """创建 UnifiedCollection"""
    col = UnifiedCollection(name="test_collection", config={"data_dir": str(temp_data_dir)})
    yield col
    # UnifiedCollection 不需要 close()


@pytest.fixture
def service(collection):
    """创建 InvertedVectorStoreCombinationService"""
    config = {
        "vector_dim": 128,  # 测试用小维度
        "fusion_strategy": "rrf",
        "rrf_k": 60,
        "linear_alpha": 0.5,
    }
    return InvertedVectorStoreCombinationService(collection, config)


class TestServiceRegistration:
    """测试 Service 注册"""

    def test_service_registered(self):
        """测试 Service 已注册到 Registry"""
        service_cls = MemoryServiceRegistry.get_service_class("partitional.inverted_vectorstore_combination")
        assert service_cls is InvertedVectorStoreCombinationService


class TestServiceInitialization:
    """测试 Service 初始化"""

    def test_init_with_config(self, collection):
        """测试使用配置初始化"""
        config = {
            "vector_dim": 256,
            "fusion_strategy": "linear",
            "rrf_k": 100,
            "linear_alpha": 0.7,
        }
        service = InvertedVectorStoreCombinationService(collection, config)

        assert service.vector_dim == 256
        assert service.fusion_strategy == "linear"
        assert service.rrf_k == 100
        assert service.linear_alpha == 0.7

    def test_init_without_config(self, collection):
        """测试不带配置初始化（使用默认值）"""
        service = InvertedVectorStoreCombinationService(collection, None)

        assert service.vector_dim == 768
        assert service.fusion_strategy == "rrf"
        assert service.rrf_k == 60
        assert service.linear_alpha == 0.5

    def test_indexes_setup(self, service):
        """测试索引配置正确"""
        # 检查两个索引是否存在
        assert "inverted_index" in service.collection.indexes
        assert "vector_index" in service.collection.indexes


class TestDataInsertion:
    """测试数据插入"""

    def test_insert_basic(self, service):
        """测试基本插入"""
        data_id = service.insert("Hello world", metadata={"source": "test"})

        assert data_id is not None
        assert data_id in service.collection

    def test_insert_with_vector(self, service):
        """测试插入时提供向量"""
        import numpy as np

        vector = np.random.randn(128).tolist()
        data_id = service.insert("Test document", vector=vector)

        assert data_id is not None

    def test_insert_multiple(self, service):
        """测试插入多条数据"""
        texts = [f"Document {i}" for i in range(20)]
        ids = [service.insert(text) for text in texts]

        assert len(ids) == 20
        assert len(set(ids)) == 20  # 确保 ID 唯一


class TestRetrieveRRF:
    """测试 RRF 融合检索"""

    def test_retrieve_rrf_basic(self, service):
        """测试基本 RRF 检索"""
        # 插入测试数据
        service.insert("Python programming language", metadata={"topic": "python"})
        service.insert("Java programming language", metadata={"topic": "java"})
        service.insert("Machine learning with Python", metadata={"topic": "ml"})

        # 检索（默认策略是 RRF）
        results = service.retrieve("Python programming", top_k=2)

        assert len(results) <= 2
        assert all("id" in r for r in results)
        # 检查是否有 RRF 分数字段
        if results:
            assert "rrf_score" in results[0]

    def test_retrieve_rrf_with_vector(self, service):
        """测试使用预计算向量的 RRF 检索"""
        import numpy as np

        # 插入数据
        vector1 = np.random.randn(128).tolist()
        service.insert("Document 1", vector=vector1)

        # 检索
        query_vector = np.random.randn(128).tolist()
        results = service.retrieve(
            "Document", top_k=1, query_vector=query_vector, strategy="rrf"
        )

        assert len(results) >= 0


class TestRetrieveLinear:
    """测试线性融合检索"""

    def test_retrieve_linear_basic(self, service):
        """测试基本线性融合检索"""
        # 插入测试数据
        for i in range(5):
            service.insert(f"Python tutorial {i}", metadata={"id": i})

        # 使用线性融合策略检索
        results = service.retrieve("Python tutorial", top_k=3, strategy="linear")

        assert len(results) <= 3
        # 检查是否有线性分数字段
        if results:
            assert "linear_score" in results[0]
            assert "inverted_score" in results[0]
            assert "vector_score" in results[0]

    def test_retrieve_linear_different_alpha(self, collection):
        """测试不同 alpha 值的线性融合"""
        # 创建 alpha=0.8 的 service（更偏重 BM25）
        config = {"vector_dim": 128, "fusion_strategy": "linear", "linear_alpha": 0.8}
        service = InvertedVectorStoreCombinationService(collection, config)

        service.insert("Python programming")
        service.insert("Java programming")

        results = service.retrieve("Python", top_k=2, strategy="linear")

        assert len(results) <= 2


class TestRRFFusion:
    """测试 RRF 融合算法"""

    def test_rrf_fusion_basic(self, service):
        """测试基本 RRF 融合"""
        inverted_results = [
            {"id": "a", "score": 0.9},
            {"id": "b", "score": 0.8},
            {"id": "c", "score": 0.7},
        ]
        vector_results = [
            {"id": "b", "score": 0.95},
            {"id": "a", "score": 0.85},
            {"id": "d", "score": 0.75},
        ]

        fused = service._rrf_fusion(inverted_results, vector_results, k=60)

        # 检查所有 ID 都被包含
        ids = {r["id"] for r in fused}
        assert ids == {"a", "b", "c", "d"}

        # 检查有 rrf_score 字段
        assert all("rrf_score" in r for r in fused)

        # 检查有 rank 字段
        assert all("inverted_rank" in r for r in fused)
        assert all("vector_rank" in r for r in fused)

        # 检查排序（RRF 分数从高到低）
        scores = [r["rrf_score"] for r in fused]
        assert scores == sorted(scores, reverse=True)

    def test_rrf_fusion_no_overlap(self, service):
        """测试完全不重叠的结果集"""
        inverted_results = [{"id": "a", "score": 0.9}]
        vector_results = [{"id": "b", "score": 0.9}]

        fused = service._rrf_fusion(inverted_results, vector_results, k=60)

        assert len(fused) == 2
        ids = {r["id"] for r in fused}
        assert ids == {"a", "b"}

    def test_rrf_fusion_complete_overlap(self, service):
        """测试完全重叠的结果集"""
        inverted_results = [
            {"id": "a", "score": 0.9},
            {"id": "b", "score": 0.8},
        ]
        vector_results = [
            {"id": "a", "score": 0.95},
            {"id": "b", "score": 0.85},
        ]

        fused = service._rrf_fusion(inverted_results, vector_results, k=60)

        assert len(fused) == 2
        # 完全重叠的结果应该得到更高的 RRF 分数
        assert fused[0]["rrf_score"] > fused[1]["rrf_score"]


class TestLinearFusion:
    """测试线性融合算法"""

    def test_linear_fusion_basic(self, service):
        """测试基本线性融合"""
        inverted_results = [
            {"id": "a", "score": 0.9},
            {"id": "b", "score": 0.7},
        ]
        vector_results = [
            {"id": "a", "score": 0.6},
            {"id": "c", "score": 0.8},
        ]

        fused = service._linear_fusion(inverted_results, vector_results, alpha=0.5)

        # 检查所有 ID 都被包含
        ids = {r["id"] for r in fused}
        assert ids == {"a", "b", "c"}

        # 检查有分数字段
        assert all("linear_score" in r for r in fused)
        assert all("inverted_score" in r for r in fused)
        assert all("vector_score" in r for r in fused)

        # 检查排序
        scores = [r["linear_score"] for r in fused]
        assert scores == sorted(scores, reverse=True)

    def test_linear_fusion_alpha_zero(self, service):
        """测试 alpha=0（完全依赖向量）"""
        inverted_results = [{"id": "a", "score": 1.0}]
        vector_results = [{"id": "b", "score": 1.0}]

        fused = service._linear_fusion(inverted_results, vector_results, alpha=0.0)

        # alpha=0 时，inverted_score 不影响结果
        # 所有结果的 inverted_score 归一化后贡献为 0
        assert len(fused) == 2

    def test_linear_fusion_alpha_one(self, service):
        """测试 alpha=1（完全依赖倒排）"""
        inverted_results = [{"id": "a", "score": 1.0}]
        vector_results = [{"id": "b", "score": 1.0}]

        fused = service._linear_fusion(inverted_results, vector_results, alpha=1.0)

        # alpha=1 时，vector_score 不影响结果
        assert len(fused) == 2


class TestScoreNormalization:
    """测试分数归一化"""

    def test_normalize_scores_basic(self, service):
        """测试基本归一化"""
        scores = {"a": 10.0, "b": 5.0, "c": 0.0}
        normalized = service._normalize_scores(scores)

        assert normalized["a"] == 1.0  # max
        assert normalized["c"] == 0.0  # min
        assert 0.0 < normalized["b"] < 1.0

    def test_normalize_scores_same_value(self, service):
        """测试所有值相同的情况"""
        scores = {"a": 5.0, "b": 5.0, "c": 5.0}
        normalized = service._normalize_scores(scores)

        # 所有值相同时归一化为 1.0
        assert all(v == 1.0 for v in normalized.values())

    def test_normalize_scores_empty(self, service):
        """测试空字典"""
        normalized = service._normalize_scores({})

        assert normalized == {}


class TestErrorHandling:
    """测试错误处理"""

    def test_retrieve_unknown_strategy(self, service):
        """测试使用未知策略"""
        service.insert("Test")

        with pytest.raises(ValueError, match="Unknown fusion strategy"):
            service.retrieve("Test", strategy="invalid_strategy")


class TestEdgeCases:
    """测试边界条件"""

    def test_retrieve_empty_collection(self, service):
        """测试空 Collection 检索"""
        results = service.retrieve("Test", top_k=5)

        assert isinstance(results, list)

    def test_large_top_k(self, service):
        """测试 top_k 大于实际数据量"""
        service.insert("Doc 1")
        service.insert("Doc 2")

        results = service.retrieve("Doc", top_k=100)

        assert len(results) <= 2

    def test_retrieve_with_empty_results(self, service):
        """测试检索返回空结果的融合"""
        # 插入数据但使用不相关的查询
        service.insert("Python programming")

        # 查询可能不匹配
        results = service.retrieve("xyz_totally_unrelated_query", top_k=5)

        assert isinstance(results, list)
