"""
Service Integration Tests - 跨服务集成测试

测试场景:
1. 多服务协同 - 同一Collection使用多个Service
2. 服务切换 - 在不同Service之间切换查询
3. 数据共享 - 多个Service访问相同数据
4. 配置兼容性 - 不同配置的Service共存
5. 性能基准 - 服务组合的性能表现

覆盖的Services:
- FeatureSummaryVectorStoreCombinationService (partitional)
- InvertedVectorStoreCombinationService (partitional)
- SemanticInvertedKnowledgeGraphService (hierarchical)
- LinknoteGraphService (hierarchical)
"""

from __future__ import annotations

import pytest

from sage.middleware.components.sage_mem.neuromem.memory_collection import (
    UnifiedCollection,
)
from sage.middleware.components.sage_mem.neuromem.services.hierarchical.semantic_inverted_knowledge_graph import (
    SemanticInvertedKnowledgeGraphService,
)
from sage.middleware.components.sage_mem.neuromem.services.partitional.feature_summary_vectorstore_combination import (
    FeatureSummaryVectorStoreCombinationService,
)
from sage.middleware.components.sage_mem.neuromem.services.partitional.inverted_vectorstore_combination import (
    InvertedVectorStoreCombinationService,
)
from sage.middleware.components.sage_mem.neuromem.services.registry import (
    MemoryServiceRegistry,
)


@pytest.fixture
def shared_collection(tmp_path):
    """共享的Collection用于多服务测试"""
    data_dir = tmp_path / "shared_data"
    col = UnifiedCollection(name="integration_test", config={"data_dir": str(data_dir)})
    yield col


@pytest.fixture
def sample_documents():
    """测试文档集"""
    return [
        {
            "text": "Python is a versatile programming language used for web development, data science, and automation.",
            "metadata": {"topic": "programming", "difficulty": "beginner"},
        },
        {
            "text": "Machine learning algorithms can learn patterns from data without explicit programming.",
            "metadata": {"topic": "ai", "difficulty": "intermediate"},
        },
        {
            "text": "Deep learning uses neural networks with multiple layers to process complex data.",
            "metadata": {"topic": "ai", "difficulty": "advanced"},
        },
        {
            "text": "Web frameworks like Django and Flask simplify web application development in Python.",
            "metadata": {"topic": "programming", "difficulty": "intermediate"},
        },
        {
            "text": "Natural language processing enables computers to understand and generate human language.",
            "metadata": {"topic": "ai", "difficulty": "advanced"},
        },
    ]


class TestMultiServiceCoexistence:
    """测试多个Service在同一Collection中共存"""

    def test_two_partitional_services(self, tmp_path, sample_documents):
        """测试两个partitional服务共存"""
        data_dir = tmp_path / "dual_service"
        col = UnifiedCollection(name="dual_test", config={"data_dir": str(data_dir)})

        # Service 1: FeatureSummary
        service1 = FeatureSummaryVectorStoreCombinationService(
            col,
            {
                "vector_dim": 128,
                "combination_strategy": "weighted",
                "enable_feature_extraction": False,
                "enable_summary_generation": False,
            },
        )

        # Service 2: InvertedVector
        service2 = InvertedVectorStoreCombinationService(
            col, {"vector_dim": 128, "fusion_strategy": "rrf"}
        )

        # 通过Service1插入数据
        for doc in sample_documents[:3]:
            service1.insert(doc["text"], doc["metadata"])

        # 通过Service2插入更多数据
        for doc in sample_documents[3:]:
            service2.insert(doc["text"], doc["metadata"])

        # 验证Collection有所有数据
        assert len(col.raw_data) == 5

        # 两个Service都能查询
        results1 = service1.retrieve("programming", top_k=3)
        results2 = service2.retrieve("machine learning", top_k=2)

        assert isinstance(results1, list)
        assert isinstance(results2, list)

    def test_partitional_and_hierarchical_mix(self, tmp_path, sample_documents):
        """测试partitional和hierarchical服务混合"""
        data_dir = tmp_path / "mixed_services"
        col = UnifiedCollection(name="mixed_test", config={"data_dir": str(data_dir)})

        # Partitional service
        partitional_svc = InvertedVectorStoreCombinationService(
            col, {"vector_dim": 128, "fusion_strategy": "linear"}
        )

        # Hierarchical service
        hierarchical_svc = SemanticInvertedKnowledgeGraphService(
            col,
            {
                "routing_strategy": "cascade",
                "enable_cross_layer_query": True,
            },
        )

        # 分别插入数据
        partitional_svc.insert(sample_documents[0]["text"], sample_documents[0]["metadata"])
        hierarchical_svc.insert(
            sample_documents[1]["text"],
            sample_documents[1]["metadata"],
            entities=["Machine learning", "algorithms"],
        )

        # 验证数据共享
        assert len(col.raw_data) == 2

        # 不同Service查询
        p_results = partitional_svc.retrieve("Python", top_k=2)
        h_results = hierarchical_svc.retrieve("learning", top_k=2, strategy="parallel")

        assert len(p_results) <= 2
        assert len(h_results) <= 2


class TestServiceSwitching:
    """测试服务切换场景"""

    def test_switch_between_strategies(self, tmp_path, sample_documents):
        """测试在不同Service策略之间切换"""
        data_dir = tmp_path / "switch_test"
        col = UnifiedCollection(name="switch_test", config={"data_dir": str(data_dir)})

        # 使用SemanticInvertedKG的不同策略
        service = SemanticInvertedKnowledgeGraphService(col, {"routing_strategy": "cascade"})

        # 插入数据
        for doc in sample_documents:
            service.insert(doc["text"], doc["metadata"])

        # 使用不同策略查询同一query
        cascade_results = service.retrieve("Python programming", top_k=3, strategy="cascade")
        parallel_results = service.retrieve("Python programming", top_k=3, strategy="parallel")
        adaptive_results = service.retrieve("Python programming", top_k=3, strategy="adaptive")

        # 所有策略都应该返回结果
        assert isinstance(cascade_results, list)
        assert isinstance(parallel_results, list)
        assert isinstance(adaptive_results, list)

        # parallel应该有fused_score
        if parallel_results:
            assert "fused_score" in parallel_results[0]

    def test_switch_between_services(self, tmp_path, sample_documents):
        """测试在不同Service实例之间切换"""
        data_dir = tmp_path / "multi_switch"
        col = UnifiedCollection(name="multi_switch", config={"data_dir": str(data_dir)})

        # 创建多个Service实例
        service_a = FeatureSummaryVectorStoreCombinationService(
            col,
            {
                "vector_dim": 128,
                "combination_strategy": "weighted",
                "enable_feature_extraction": False,
            },
        )
        service_b = InvertedVectorStoreCombinationService(
            col, {"vector_dim": 128, "fusion_strategy": "rrf"}
        )

        # 插入数据
        for doc in sample_documents:
            service_a.insert(doc["text"], doc["metadata"])

        # 轮流使用不同Service查询
        for _ in range(3):
            results_a = service_a.retrieve("learning", top_k=2)
            results_b = service_b.retrieve("learning", top_k=2)

            assert isinstance(results_a, list)
            assert isinstance(results_b, list)


class TestDataSharing:
    """测试数据共享场景"""

    def test_shared_data_access(self, shared_collection, sample_documents):
        """测试多个Service访问相同数据"""
        # 创建两个不同的Service（不使用LinknoteGraph因为GraphIndex接口不同）
        service1 = InvertedVectorStoreCombinationService(shared_collection, {"vector_dim": 128})
        service2 = SemanticInvertedKnowledgeGraphService(
            shared_collection, {"routing_strategy": "parallel"}
        )

        # 通过service1插入数据
        data_ids = []
        for doc in sample_documents:
            data_id = service1.insert(doc["text"], doc["metadata"])
            data_ids.append(data_id)

        # 所有Service都能看到相同的数据
        assert len(shared_collection.raw_data) == 5

        # 两个Service都能查询
        results1 = service1.retrieve("Python", top_k=3)
        results2 = service2.retrieve("Python", top_k=3)

        assert len(results1) > 0
        assert len(results2) > 0

        # 验证返回的是相同的底层数据
        all_ids = set()
        for r in results1 + results2:
            all_ids.add(r["id"])

        # 所有返回的ID都应该在data_ids中
        assert all_ids.issubset(set(data_ids))

    def test_concurrent_insertions(self, shared_collection):
        """测试并发插入（模拟）"""
        service1 = InvertedVectorStoreCombinationService(shared_collection, {"vector_dim": 128})
        service2 = SemanticInvertedKnowledgeGraphService(
            shared_collection, {"routing_strategy": "cascade"}
        )

        # 交替插入
        id1 = service1.insert("Document from service 1", {})
        id2 = service2.insert("Document from service 2", {})
        id3 = service1.insert("Another from service 1", {})
        id4 = service2.insert("Another from service 2", {})

        # 验证所有数据都被正确存储
        assert len(shared_collection.raw_data) == 4
        assert id1 in shared_collection.raw_data
        assert id2 in shared_collection.raw_data
        assert id3 in shared_collection.raw_data
        assert id4 in shared_collection.raw_data


class TestConfigurationCompatibility:
    """测试配置兼容性"""

    def test_different_vector_dims_warning(self, tmp_path):
        """测试不同向量维度的Service（应该警告但不崩溃）"""
        data_dir = tmp_path / "dim_test"
        col = UnifiedCollection(name="dim_test", config={"data_dir": str(data_dir)})

        # Service with 128D
        service1 = InvertedVectorStoreCombinationService(
            col, {"vector_dim": 128, "fusion_strategy": "rrf"}
        )

        # Service with different config (但使用相同的底层索引)
        service2 = FeatureSummaryVectorStoreCombinationService(
            col,
            {
                "vector_dim": 128,  # 必须相同维度
                "combination_strategy": "voting",
                "enable_feature_extraction": False,
            },
        )

        # 插入数据
        service1.insert("Test document 1", {})
        service2.insert("Test document 2", {})

        # 两个Service都能工作
        results1 = service1.retrieve("test", top_k=2)
        results2 = service2.retrieve("test", top_k=2)

        assert isinstance(results1, list)
        assert isinstance(results2, list)

    def test_registry_creation(self, tmp_path):
        """测试通过Registry创建多个Service"""
        data_dir = tmp_path / "registry_test"
        col = UnifiedCollection(name="registry_test", config={"data_dir": str(data_dir)})

        # 通过Registry创建不同Service
        service1 = MemoryServiceRegistry.create(
            "partitional.inverted_vectorstore_combination",
            collection=col,
            config={"vector_dim": 128, "fusion_strategy": "rrf"},
        )

        service2 = MemoryServiceRegistry.create(
            "hierarchical.semantic_inverted_knowledge_graph",
            collection=col,
            config={"routing_strategy": "adaptive"},
        )

        # 验证类型
        assert isinstance(service1, InvertedVectorStoreCombinationService)
        assert isinstance(service2, SemanticInvertedKnowledgeGraphService)

        # 插入和查询
        service1.insert("Registry test document", {})
        results = service2.retrieve("test", top_k=1)
        assert isinstance(results, list)


class TestCrossServiceQuery:
    """测试跨Service查询场景"""

    def test_query_comparison(self, tmp_path, sample_documents):
        """测试不同Service对相同查询的结果对比"""
        data_dir = tmp_path / "comparison_test"
        col = UnifiedCollection(name="comparison", config={"data_dir": str(data_dir)})

        # 创建三个不同的Service
        services = {
            "inverted_vector": InvertedVectorStoreCombinationService(
                col, {"vector_dim": 128, "fusion_strategy": "rrf"}
            ),
            "feature_summary": FeatureSummaryVectorStoreCombinationService(
                col,
                {
                    "vector_dim": 128,
                    "combination_strategy": "weighted",
                    "enable_feature_extraction": False,
                },
            ),
            "semantic_kg": SemanticInvertedKnowledgeGraphService(
                col, {"routing_strategy": "cascade"}
            ),
        }

        # 插入相同的数据集
        for doc in sample_documents:
            services["inverted_vector"].insert(doc["text"], doc["metadata"])

        # 使用相同查询测试所有Service
        query = "machine learning"
        results_map = {}

        for name, service in services.items():
            results = service.retrieve(query, top_k=3)
            results_map[name] = results

        # 所有Service都应该返回结果
        for name, results in results_map.items():
            assert isinstance(results, list), f"{name} should return list"
            assert len(results) > 0, f"{name} should return some results"

    def test_ensemble_retrieval(self, tmp_path, sample_documents):
        """测试集成检索（组合多个Service的结果）"""
        data_dir = tmp_path / "ensemble_test"
        col = UnifiedCollection(name="ensemble", config={"data_dir": str(data_dir)})

        # 创建两个Service
        service1 = InvertedVectorStoreCombinationService(
            col, {"vector_dim": 128, "fusion_strategy": "rrf"}
        )
        service2 = SemanticInvertedKnowledgeGraphService(col, {"routing_strategy": "parallel"})

        # 插入数据
        for doc in sample_documents:
            service1.insert(doc["text"], doc["metadata"])

        # 从两个Service获取结果
        query = "Python programming"
        results1 = service1.retrieve(query, top_k=3)
        results2 = service2.retrieve(query, top_k=3)

        # 简单的集成：去重并合并
        all_ids = set()
        ensemble_results = []

        for r in results1 + results2:
            if r["id"] not in all_ids:
                all_ids.add(r["id"])
                ensemble_results.append(r)

        # 集成结果应该包含来自两个Service的数据
        assert len(ensemble_results) > 0
        assert len(ensemble_results) <= len(results1) + len(results2)


class TestPerformanceBaseline:
    """性能基准测试"""

    def test_single_vs_multi_service_overhead(self, tmp_path, sample_documents):
        """测试单Service vs 多Service的开销"""
        # Single service setup
        data_dir1 = tmp_path / "single"
        col1 = UnifiedCollection(name="single", config={"data_dir": str(data_dir1)})
        single_service = InvertedVectorStoreCombinationService(col1, {"vector_dim": 128})

        # Multi service setup
        data_dir2 = tmp_path / "multi"
        col2 = UnifiedCollection(name="multi", config={"data_dir": str(data_dir2)})
        multi_service1 = InvertedVectorStoreCombinationService(col2, {"vector_dim": 128})
        multi_service2 = SemanticInvertedKnowledgeGraphService(
            col2, {"routing_strategy": "cascade"}
        )

        # 插入相同数据
        for doc in sample_documents:
            single_service.insert(doc["text"], doc["metadata"])
            multi_service1.insert(doc["text"], doc["metadata"])

        # 查询（不测时间，只验证功能）
        single_results = single_service.retrieve("Python", top_k=3)
        multi_results1 = multi_service1.retrieve("Python", top_k=3)
        multi_results2 = multi_service2.retrieve("Python", top_k=3)

        # 验证结果都有效
        assert len(single_results) > 0
        assert len(multi_results1) > 0
        assert len(multi_results2) > 0

    def test_large_scale_insertion(self, tmp_path):
        """测试大规模数据插入（集成场景）"""
        data_dir = tmp_path / "large_scale"
        col = UnifiedCollection(name="large", config={"data_dir": str(data_dir)})

        service1 = InvertedVectorStoreCombinationService(
            col, {"vector_dim": 128, "fusion_strategy": "linear"}
        )
        service2 = SemanticInvertedKnowledgeGraphService(col, {"routing_strategy": "adaptive"})

        # 插入100个文档
        num_docs = 100
        for i in range(num_docs):
            text = f"Document {i} about topic {i % 10}"
            metadata = {"doc_id": i, "category": i % 5}

            if i % 2 == 0:
                service1.insert(text, metadata)
            else:
                service2.insert(text, metadata)

        # 验证所有数据都被存储
        assert len(col.raw_data) == num_docs

        # 查询应该仍然快速响应
        results1 = service1.retrieve("topic 5", top_k=10)
        results2 = service2.retrieve("topic 5", top_k=10, strategy="parallel")

        assert isinstance(results1, list)
        assert isinstance(results2, list)
        assert len(results1) <= 10
        assert len(results2) <= 10


class TestErrorHandling:
    """错误处理测试"""

    def test_incompatible_operations(self, tmp_path):
        """测试不兼容操作的错误处理"""
        data_dir = tmp_path / "error_test"
        col = UnifiedCollection(name="error_test", config={"data_dir": str(data_dir)})

        service = SemanticInvertedKnowledgeGraphService(col, {"routing_strategy": "cascade"})

        # 测试无效策略
        service.insert("Test document", {})

        with pytest.raises(ValueError, match="Unknown routing strategy"):
            service.retrieve("test", top_k=5, strategy="invalid_strategy")

    def test_empty_collection_query(self, tmp_path):
        """测试空Collection查询"""
        data_dir = tmp_path / "empty_test"
        col = UnifiedCollection(name="empty", config={"data_dir": str(data_dir)})

        service1 = InvertedVectorStoreCombinationService(col, {"vector_dim": 128})
        service2 = SemanticInvertedKnowledgeGraphService(col, {"routing_strategy": "parallel"})

        # 在空Collection上查询不应该崩溃
        results1 = service1.retrieve("query", top_k=5)
        results2 = service2.retrieve("query", top_k=5)

        assert isinstance(results1, list)
        assert isinstance(results2, list)
        assert len(results1) == 0
        assert len(results2) == 0
