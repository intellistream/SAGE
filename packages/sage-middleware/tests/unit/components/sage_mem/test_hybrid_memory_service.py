"""HybridMemoryService 单元测试"""

import pytest

from sage.middleware.components.sage_mem.services.hybrid_memory_service import (
    HybridMemoryService,
)


class TestHybridMemoryServiceInit:
    """测试 HybridMemoryService 初始化"""

    def test_default_init(self):
        """测试默认参数初始化"""
        service = HybridMemoryService()
        assert service.fusion_strategy == "weighted"
        assert service.rrf_k == 60
        assert len(service.index_configs) == 2  # 默认 vector + bm25

    def test_custom_indexes(self):
        """测试自定义索引配置"""
        indexes = [
            {"name": "semantic", "type": "vector", "dim": 1024},
            {"name": "keyword", "type": "bm25"},
            {"name": "tag", "type": "keyword"},
        ]
        service = HybridMemoryService(indexes=indexes)
        assert len(service.index_configs) == 3

    def test_rrf_fusion_strategy(self):
        """测试 RRF 融合策略"""
        service = HybridMemoryService(fusion_strategy="rrf")
        assert service.fusion_strategy == "rrf"

    def test_custom_fusion_weights(self):
        """测试自定义融合权重"""
        service = HybridMemoryService(fusion_weights=[0.7, 0.3])
        assert service.fusion_weights == [0.7, 0.3]


class TestHybridMemoryServiceInsert:
    """测试 HybridMemoryService 插入功能"""

    @pytest.fixture
    def service(self):
        """创建测试用服务实例"""
        return HybridMemoryService()

    def test_insert_basic(self, service):
        """测试基本插入"""
        doc_id = service.insert(entry="这是一个测试文档", metadata={"type": "test"})

        assert doc_id is not None
        assert len(service.documents) == 1

    def test_insert_with_vector(self, service):
        """测试带向量的插入"""
        import numpy as np

        vector = np.random.randn(768).astype(np.float32)
        doc_id = service.insert(entry="测试文档", vector=vector, metadata={"type": "test"})

        assert doc_id is not None

    def test_insert_multiple(self, service):
        """测试多次插入"""
        for i in range(5):
            service.insert(entry=f"文档{i}", metadata={"index": i})

        assert len(service.documents) == 5


class TestHybridMemoryServiceRetrieve:
    """测试 HybridMemoryService 检索功能"""

    @pytest.fixture
    def populated_service(self):
        """创建预填充数据的服务"""
        service = HybridMemoryService()

        # 插入多条测试数据
        test_docs = [
            "人工智能是计算机科学的一个分支",
            "机器学习是人工智能的子领域",
            "深度学习是机器学习的一种方法",
            "自然语言处理处理文本数据",
            "计算机视觉处理图像数据",
        ]

        for i, text in enumerate(test_docs):
            service.insert(entry=text, metadata={"id": i})

        return service

    def test_retrieve_basic(self, populated_service):
        """测试基本检索"""
        result = populated_service.retrieve(query="人工智能", metadata={})

        assert isinstance(result, list)
        assert len(result) > 0

    def test_retrieve_with_vector(self, populated_service):
        """测试带向量的检索"""
        import numpy as np

        query_vector = np.random.randn(768).astype(np.float32)
        result = populated_service.retrieve(query="机器学习", vector=query_vector, metadata={})

        assert isinstance(result, list)

    def test_retrieve_with_top_k(self, populated_service):
        """测试指定返回数量"""
        # top_k 是 retrieve 的参数，不是 metadata
        result = populated_service.retrieve(query="学习", metadata={}, top_k=2)

        assert isinstance(result, list)
        assert len(result) <= 2


class TestHybridMemoryServiceFusion:
    """测试 HybridMemoryService 融合策略"""

    def test_weighted_fusion(self):
        """测试加权融合"""
        service = HybridMemoryService(fusion_strategy="weighted")

        service.insert(entry="测试文档1", metadata={})
        service.insert(entry="测试文档2", metadata={})

        result = service.retrieve(query="测试", metadata={})

        assert isinstance(result, list)

    def test_rrf_fusion(self):
        """测试 RRF 融合"""
        service = HybridMemoryService(fusion_strategy="rrf")

        service.insert(entry="测试文档1", metadata={})
        service.insert(entry="测试文档2", metadata={})

        result = service.retrieve(query="测试", metadata={})

        assert isinstance(result, list)


class TestHybridMemoryServiceStatistics:
    """测试 HybridMemoryService 统计功能"""

    def test_document_count(self):
        """测试文档数量统计"""
        service = HybridMemoryService()

        for i in range(3):
            service.insert(entry=f"文档{i}", metadata={})

        # 直接检查 documents 字典
        assert len(service.documents) == 3

    def test_index_info(self):
        """测试获取索引信息"""
        service = HybridMemoryService()

        service.insert(entry="测试", metadata={})

        # 验证索引已初始化
        assert len(service.indexes) > 0
