"""
SemanticInvertedKnowledgeGraphService 单元测试

测试场景:
1. 服务初始化和索引配置
2. 三层数据插入
3. 单层查询（semantic/inverted/kg）
4. 级联策略（cascade）
5. 并行策略（parallel）
6. 自适应策略（adaptive）
7. 跨层查询
8. 统计信息
"""

from __future__ import annotations

import pytest

from sage.middleware.components.sage_mem.neuromem.memory_collection import (
    UnifiedCollection,
)
from sage.middleware.components.sage_mem.neuromem.services.hierarchical.semantic_inverted_knowledge_graph import (
    SemanticInvertedKnowledgeGraphService,
)
from sage.middleware.components.sage_mem.neuromem.services.registry import (
    MemoryServiceRegistry,
)


@pytest.fixture
def service_config():
    """Service配置"""
    return {
        "hierarchy_levels": 3,
        "routing_strategy": "cascade",
        "enable_cross_layer_query": True,
        "max_hops": 3,
        "default_index": "semantic_index",
    }


@pytest.fixture
def collection(tmp_path, service_config):
    """创建Collection并初始化Service"""
    data_dir = tmp_path / "data"
    col = UnifiedCollection(name="test_semantic_inverted_kg", config={"data_dir": str(data_dir)})

    # 使用Service初始化（会自动setup索引）
    SemanticInvertedKnowledgeGraphService(col, service_config)

    yield col
    # Note: UnifiedCollection doesn't have close() method


@pytest.fixture
def populated_collection(collection):
    """填充测试数据的Collection"""
    # 插入示例数据
    test_data = [
        {
            "text": "Python is a high-level programming language.",
            "metadata": {
                "entities": ["Python", "programming"],
                "relations": [("Python", "is", "language")],
                "segment_id": "tech",
            },
        },
        {
            "text": "Machine learning uses algorithms to learn from data.",
            "metadata": {
                "entities": ["Machine learning", "algorithms", "data"],
                "relations": [("ML", "uses", "algorithms")],
                "segment_id": "tech",
            },
        },
        {
            "text": "Deep learning is a subset of machine learning.",
            "metadata": {
                "entities": ["Deep learning", "Machine learning"],
                "relations": [("DL", "subset_of", "ML")],
                "segment_id": "tech",
            },
        },
        {
            "text": "Natural language processing analyzes human language.",
            "metadata": {
                "entities": ["NLP", "language"],
                "relations": [("NLP", "analyzes", "language")],
                "segment_id": "nlp",
            },
        },
        {
            "text": "Computer vision focuses on image processing.",
            "metadata": {
                "entities": ["Computer vision", "image"],
                "relations": [("CV", "focuses_on", "image")],
                "segment_id": "cv",
            },
        },
    ]

    for item in test_data:
        collection.insert(
            text=item["text"],
            metadata=item["metadata"],
        )

    return collection


class TestServiceInitialization:
    """测试服务初始化"""

    def test_service_registered(self):
        """测试服务已注册到Registry"""
        service_type = "hierarchical.semantic_inverted_knowledge_graph"
        service_cls = MemoryServiceRegistry.get_service_class(service_type)
        assert service_cls is SemanticInvertedKnowledgeGraphService

    def test_service_creation(self, tmp_path, service_config):
        """测试通过Registry创建服务"""
        data_dir = tmp_path / "data"
        col = UnifiedCollection(name="test_create", config={"data_dir": str(data_dir)})

        service = MemoryServiceRegistry.create(
            "hierarchical.semantic_inverted_knowledge_graph",
            collection=col,
            config=service_config,
        )

        assert isinstance(service, SemanticInvertedKnowledgeGraphService)
        assert service.hierarchy_levels == 3
        assert service.routing_strategy == "cascade"
        assert service.enable_cross_layer_query is True
        assert service.max_hops == 3

    def test_indexes_setup(self, collection):
        """测试三层索引已正确配置"""
        # 检查索引是否存在
        assert "semantic_index" in collection.indexes
        assert "inverted_index" in collection.indexes
        assert "kg_index" in collection.indexes

        # 检查索引类型
        semantic_idx = collection.indexes["semantic_index"]
        inverted_idx = collection.indexes["inverted_index"]
        kg_idx = collection.indexes["kg_index"]

        assert semantic_idx.__class__.__name__ == "FAISSIndex"
        assert inverted_idx.__class__.__name__ == "BM25Index"
        assert kg_idx.__class__.__name__ == "SegmentIndex"

    def test_default_config(self, tmp_path):
        """测试默认配置"""
        data_dir = tmp_path / "data"
        col = UnifiedCollection(name="test_default", config={"data_dir": str(data_dir)})
        service = SemanticInvertedKnowledgeGraphService(col)

        assert service.hierarchy_levels == 3
        assert service.routing_strategy == "cascade"
        assert service.enable_cross_layer_query is True
        assert service.max_hops == 3
        assert service.default_index == "semantic_index"


class TestDataInsertion:
    """测试数据插入"""

    def test_insert_basic(self, tmp_path, service_config):
        """测试基本插入"""
        data_dir = tmp_path / "data"
        col = UnifiedCollection(name="test_insert", config={"data_dir": str(data_dir)})
        service = SemanticInvertedKnowledgeGraphService(col, service_config)

        data_id = service.insert(
            text="Test document about AI",
            metadata={"topic": "ai"},
        )

        assert isinstance(data_id, str)
        assert data_id in col.raw_data

    def test_insert_with_entities(self, tmp_path, service_config):
        """测试带实体的插入"""
        data_dir = tmp_path / "data"
        col = UnifiedCollection(name="test_entities", config={"data_dir": str(data_dir)})
        service = SemanticInvertedKnowledgeGraphService(col, service_config)

        data_id = service.insert(
            text="Python is a programming language",
            metadata={},
            entities=["Python", "programming"],
            relations=[("Python", "is", "language")],
            segment_id="tech",
        )

        # 检查元数据是否正确保存
        data = col.raw_data[data_id]
        assert "entities" in data["metadata"]
        assert "relations" in data["metadata"]
        assert "segment_id" in data["metadata"]
        assert data["metadata"]["entities"] == ["Python", "programming"]

    def test_insert_multiple(self, populated_collection):
        """测试批量插入（通过fixture）"""
        assert len(populated_collection.raw_data) == 5


class TestSingleLayerRetrieval:
    """测试单层检索"""

    def test_retrieve_semantic_layer(self, tmp_path, service_config):
        """测试语义层查询"""
        data_dir = tmp_path / "data"
        col = UnifiedCollection(name="test_semantic", config={"data_dir": str(data_dir)})
        service = SemanticInvertedKnowledgeGraphService(col, service_config)

        # 插入数据
        service.insert("Machine learning is amazing", metadata={})
        service.insert("Deep learning is powerful", metadata={})

        # 语义层查询
        results = service.retrieve(query="AI and ML", top_k=2, layer="semantic")

        assert isinstance(results, list)
        # Note: 可能返回空（因为没有真实的embedding）

    def test_retrieve_inverted_layer(self, populated_collection, service_config):
        """测试倒排层查询"""
        service = SemanticInvertedKnowledgeGraphService(
            populated_collection, service_config
        )

        results = service.retrieve(query="machine learning", top_k=3, layer="inverted")

        assert isinstance(results, list)
        assert len(results) <= 3

        # 检查结果结构
        if results:
            assert "id" in results[0]
            assert "text" in results[0]
            assert "metadata" in results[0]

    def test_retrieve_kg_layer(self, populated_collection, service_config):
        """测试KG层查询"""
        service = SemanticInvertedKnowledgeGraphService(
            populated_collection, service_config
        )

        results = service.retrieve(
            query="", top_k=5, layer="kg", segment_id="tech"
        )

        assert isinstance(results, list)
        # KG层通过segment查询

    def test_invalid_layer(self, populated_collection, service_config):
        """测试无效层级"""
        service = SemanticInvertedKnowledgeGraphService(
            populated_collection, service_config
        )

        with pytest.raises(ValueError, match="Unknown layer"):
            service.retrieve(query="test", layer="invalid_layer")


class TestCascadeStrategy:
    """测试级联策略"""

    def test_cascade_retrieval(self, populated_collection, service_config):
        """测试级联检索"""
        service = SemanticInvertedKnowledgeGraphService(
            populated_collection, service_config
        )

        results = service.retrieve(
            query="machine learning algorithms", top_k=3, strategy="cascade"
        )

        assert isinstance(results, list)
        assert len(results) <= 3

        # 检查结果应包含inverted_score
        if results:
            # cascade策略会添加倒排分数
            assert "inverted_score" in results[0]

    def test_cascade_without_cross_layer(self, populated_collection, service_config):
        """测试级联但禁用跨层查询"""
        service = SemanticInvertedKnowledgeGraphService(
            populated_collection, service_config
        )

        results = service.retrieve(
            query="deep learning", top_k=2, strategy="cascade", enable_cross_layer=False
        )

        assert isinstance(results, list)
        assert len(results) <= 2


class TestParallelStrategy:
    """测试并行策略"""

    def test_parallel_retrieval(self, populated_collection, service_config):
        """测试并行检索"""
        service = SemanticInvertedKnowledgeGraphService(
            populated_collection, service_config
        )

        results = service.retrieve(
            query="natural language processing", top_k=3, strategy="parallel"
        )

        assert isinstance(results, list)
        assert len(results) <= 3

        # 检查融合分数
        if results:
            assert "fused_score" in results[0]

    def test_parallel_with_custom_weights(self, populated_collection, service_config):
        """测试自定义权重的并行检索"""
        service = SemanticInvertedKnowledgeGraphService(
            populated_collection, service_config
        )

        custom_weights = {"semantic": 0.6, "inverted": 0.3, "kg": 0.1}

        results = service.retrieve(
            query="computer vision",
            top_k=2,
            strategy="parallel",
            weights=custom_weights,
        )

        assert isinstance(results, list)


class TestAdaptiveStrategy:
    """测试自适应策略"""

    def test_adaptive_with_entities(self, populated_collection, service_config):
        """测试带实体的自适应查询（应选择KG层）"""
        service = SemanticInvertedKnowledgeGraphService(
            populated_collection, service_config
        )

        results = service.retrieve(
            query="test",
            top_k=2,
            strategy="adaptive",
            entities=["Python", "ML"],
        )

        assert isinstance(results, list)
        # adaptive策略应该自动选择kg层

    def test_adaptive_long_query(self, populated_collection, service_config):
        """测试长查询（应选择语义层）"""
        service = SemanticInvertedKnowledgeGraphService(
            populated_collection, service_config
        )

        long_query = "This is a very long query with many words that should trigger semantic layer"

        results = service.retrieve(query=long_query, top_k=2, strategy="adaptive")

        assert isinstance(results, list)

    def test_adaptive_short_query(self, populated_collection, service_config):
        """测试短查询（应选择倒排层）"""
        service = SemanticInvertedKnowledgeGraphService(
            populated_collection, service_config
        )

        results = service.retrieve(query="learning", top_k=2, strategy="adaptive")

        assert isinstance(results, list)


class TestCrossLayerQuery:
    """测试跨层查询"""

    def test_cross_layer_enabled(self, populated_collection):
        """测试启用跨层查询"""
        config = {
            "hierarchy_levels": 3,
            "routing_strategy": "cascade",
            "enable_cross_layer_query": True,
            "max_hops": 3,
        }
        service = SemanticInvertedKnowledgeGraphService(populated_collection, config)

        results = service.retrieve(
            query="machine learning",
            top_k=3,
            entities=["Python", "algorithms"],
        )

        assert isinstance(results, list)

    def test_cross_layer_disabled(self, populated_collection):
        """测试禁用跨层查询"""
        config = {
            "hierarchy_levels": 3,
            "routing_strategy": "cascade",
            "enable_cross_layer_query": False,
            "max_hops": 0,
        }
        service = SemanticInvertedKnowledgeGraphService(populated_collection, config)

        results = service.retrieve(query="deep learning", top_k=2)

        assert isinstance(results, list)
        # 不应该有KG扩展


class TestStatistics:
    """测试统计信息"""

    def test_get_layer_stats(self, populated_collection, service_config):
        """测试获取层级统计"""
        service = SemanticInvertedKnowledgeGraphService(
            populated_collection, service_config
        )

        stats = service.get_layer_stats()

        assert isinstance(stats, dict)
        assert "semantic" in stats
        assert "inverted" in stats
        assert "kg" in stats

        # 检查统计结构
        for layer_name, layer_stats in stats.items():
            assert "size" in layer_stats
            assert "type" in layer_stats

    def test_stats_after_insertion(self, tmp_path, service_config):
        """测试插入后统计变化"""
        data_dir = tmp_path / "data"
        col = UnifiedCollection(name="test_stats", config={"data_dir": str(data_dir)})
        service = SemanticInvertedKnowledgeGraphService(col, service_config)

        # 初始统计
        stats_before = service.get_layer_stats()
        size_before = stats_before["inverted"]["size"]

        # 插入数据
        service.insert("Test document", metadata={})

        # 插入后统计
        stats_after = service.get_layer_stats()
        size_after = stats_after["inverted"]["size"]

        assert size_after == size_before + 1


class TestInvalidStrategy:
    """测试无效策略"""

    def test_unknown_routing_strategy(self, populated_collection, service_config):
        """测试未知路由策略"""
        service = SemanticInvertedKnowledgeGraphService(
            populated_collection, service_config
        )

        with pytest.raises(ValueError, match="Unknown routing strategy"):
            service.retrieve(query="test", strategy="unknown_strategy")
