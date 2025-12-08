"""GraphMemoryService 单元测试

测试 GraphMemoryService 使用 NeuroMem GraphMemoryCollection 后端的功能。
"""

import pytest

from sage.middleware.components.sage_mem.services.graph_memory_service import (
    GraphMemoryService,
)


class TestGraphMemoryServiceInit:
    """测试 GraphMemoryService 初始化"""

    def test_default_init(self):
        """测试默认参数初始化"""
        service = GraphMemoryService(collection_name="test_graph_init_default")
        assert service.graph_type == "knowledge_graph"
        assert service.node_embedding_dim == 768
        assert service.link_policy == "bidirectional"

    def test_link_graph_mode_init(self):
        """测试 link_graph 模式初始化"""
        service = GraphMemoryService(
            collection_name="test_graph_init_link", graph_type="link_graph"
        )
        assert service.graph_type == "link_graph"

    def test_custom_params_init(self):
        """测试自定义参数初始化"""
        service = GraphMemoryService(
            collection_name="test_graph_init_custom",
            graph_type="knowledge_graph",
            node_embedding_dim=1024,
            synonymy_threshold=0.9,
            damping=0.8,
        )
        assert service.node_embedding_dim == 1024
        assert service.synonymy_threshold == 0.9
        assert service.damping == 0.8


class TestGraphMemoryServiceInsert:
    """测试 GraphMemoryService 插入功能"""

    @pytest.fixture
    def service(self):
        """创建测试用服务实例"""
        return GraphMemoryService(collection_name="test_graph_insert")

    def test_insert_basic(self, service):
        """测试基本插入"""
        entry = "北京是中国的首都"

        node_id = service.insert(entry=entry)

        assert node_id is not None

    def test_insert_with_triples(self, service):
        """测试使用三元组插入"""
        entry = "北京是中国的首都"
        # 使用元组格式的三元组: (subject, relation, object)
        metadata = {"triples": [("北京", "是...的首都", "中国")]}

        node_id = service.insert(entry=entry, metadata=metadata)

        assert node_id is not None

    def test_insert_with_list_triples(self, service):
        """测试使用列表格式三元组插入"""
        entry = "上海是中国最大城市"
        # 两元素元组格式: (subject, object)
        metadata = {"triples": [("上海", "中国最大城市")]}

        node_id = service.insert(entry=entry, metadata=metadata)

        assert node_id is not None

    def test_insert_link_graph_mode(self):
        """测试 link_graph 模式插入"""
        service = GraphMemoryService(
            collection_name="test_graph_link_insert", graph_type="link_graph"
        )
        entry = "测试笔记内容"
        metadata = {"id": "note1"}

        node_id = service.insert(entry=entry, metadata=metadata)

        assert node_id is not None


class TestGraphMemoryServiceRetrieve:
    """测试 GraphMemoryService 检索功能"""

    @pytest.fixture
    def populated_service(self):
        """创建预填充数据的服务"""
        import numpy as np

        service = GraphMemoryService(collection_name="test_graph_retrieve")
        # 插入一些测试数据（使用元组格式的三元组）
        service.insert(
            entry="北京是中国的首都",
            vector=np.random.randn(768).astype(np.float32),
            metadata={"triples": [("北京", "是...的首都", "中国")]},
        )
        service.insert(
            entry="上海是中国最大的城市",
            vector=np.random.randn(768).astype(np.float32),
            metadata={"triples": [("上海", "是...最大的城市", "中国")]},
        )
        return service

    def test_retrieve_basic(self, populated_service):
        """测试基本检索"""
        result = populated_service.retrieve(query="北京", metadata={})

        assert isinstance(result, list)

    def test_retrieve_knn(self, populated_service):
        """测试 KNN 检索"""
        import numpy as np

        query_vec = np.random.randn(768).astype(np.float32)
        result = populated_service.retrieve(
            query="北京", vector=query_vec, metadata={"method": "knn"}
        )

        assert isinstance(result, list)

    def test_retrieve_ppr(self, populated_service):
        """测试 PPR 检索"""
        result = populated_service.retrieve(
            query="中国", metadata={"method": "ppr", "seed_nodes": []}
        )

        assert isinstance(result, list)


class TestGraphMemoryServiceStatistics:
    """测试 GraphMemoryService 统计功能"""

    def test_get_stats(self):
        """测试获取统计信息"""
        service = GraphMemoryService(collection_name="test_graph_stats")
        # 使用元组格式的三元组
        service.insert(
            entry="测试",
            metadata={"triples": [("A", "关联", "B")]},
        )

        stats = service.get_stats()

        assert isinstance(stats, dict)
