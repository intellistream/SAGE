"""
Tests for PipelineBuilder - Visual Pipeline to SAGE Pipeline conversion
"""
import pytest

from sage.studio.models import VisualPipeline, VisualNode, VisualEdge
from sage.studio.services import PipelineBuilder


class TestPipelineBuilder:
    """测试 PipelineBuilder 功能"""
    
    def test_builder_initialization(self):
        """测试 Builder 初始化"""
        builder = PipelineBuilder()
        
        # 验证 Registry 已初始化
        assert builder.registry is not None
        assert len(builder.registry.list_types()) > 0
    
    def test_build_simple_pipeline(self):
        """测试构建简单的 Pipeline"""
        # 创建一个简单的 Visual Pipeline
        node1 = VisualNode(
            id="node1",
            node_type="retriever",
            config={
                "top_k": 5,
                "index_name": "test_index"
            },
            position={"x": 100, "y": 100}
        )
        
        visual_pipeline = VisualPipeline(
            id="test_pipeline",
            name="Test Pipeline",
            nodes=[node1],
            edges=[],
            metadata={}
        )
        
        # 构建 Pipeline
        builder = PipelineBuilder()
        sage_pipeline = builder.build(visual_pipeline)
        
        # 验证 Pipeline 创建成功
        assert sage_pipeline is not None
    
    def test_build_pipeline_with_edges(self):
        """测试构建带连接的 Pipeline"""
        # 创建两个节点
        node1 = VisualNode(
            id="node1",
            node_type="retriever",
            config={"top_k": 5},
            position={"x": 100, "y": 100}
        )
        
        node2 = VisualNode(
            id="node2",
            node_type="generator",
            config={"model": "gpt-3.5-turbo"},
            position={"x": 300, "y": 100}
        )
        
        # 创建边
        edge = VisualEdge(
            id="edge1",
            source="node1",
            target="node2"
        )
        
        visual_pipeline = VisualPipeline(
            id="test_pipeline",
            name="RAG Pipeline",
            nodes=[node1, node2],
            edges=[edge],
            metadata={}
        )
        
        # 构建 Pipeline
        builder = PipelineBuilder()
        sage_pipeline = builder.build(visual_pipeline)
        
        # 验证 Pipeline 创建成功
        assert sage_pipeline is not None
    
    def test_build_empty_pipeline(self):
        """测试构建空 Pipeline"""
        visual_pipeline = VisualPipeline(
            id="empty_pipeline",
            name="Empty Pipeline",
            nodes=[],
            edges=[],
            metadata={}
        )
        
        builder = PipelineBuilder()
        
        # 空 Pipeline 应该抛出异常或返回特定结果
        # 根据实际实现调整这里的断言
        with pytest.raises(Exception):
            builder.build(visual_pipeline)
    
    def test_topological_sort_simple(self):
        """测试简单的拓扑排序"""
        node1 = VisualNode(id="node1", node_type="retriever", config={}, position={})
        node2 = VisualNode(id="node2", node_type="generator", config={}, position={})
        edge = VisualEdge(id="edge1", source="node1", target="node2")
        
        pipeline = VisualPipeline(
            id="test",
            name="Test",
            nodes=[node2, node1],  # 故意打乱顺序
            edges=[edge],
            metadata={}
        )
        
        builder = PipelineBuilder()
        sorted_nodes = builder._topological_sort(pipeline)
        
        # 验证排序结果
        assert len(sorted_nodes) == 2
        assert sorted_nodes[0].id == "node1"
        assert sorted_nodes[1].id == "node2"
    
    def test_topological_sort_complex(self):
        """测试复杂的拓扑排序"""
        # 创建一个更复杂的依赖图
        # node1 -> node2 -> node4
        #       -> node3 -> node4
        
        node1 = VisualNode(id="node1", node_type="retriever", config={}, position={})
        node2 = VisualNode(id="node2", node_type="promptor", config={}, position={})
        node3 = VisualNode(id="node3", node_type="promptor", config={}, position={})
        node4 = VisualNode(id="node4", node_type="generator", config={}, position={})
        
        edges = [
            VisualEdge(id="e1", source="node1", target="node2"),
            VisualEdge(id="e2", source="node1", target="node3"),
            VisualEdge(id="e3", source="node2", target="node4"),
            VisualEdge(id="e4", source="node3", target="node4"),
        ]
        
        pipeline = VisualPipeline(
            id="test",
            name="Test",
            nodes=[node4, node3, node2, node1],  # 故意打乱顺序
            edges=edges,
            metadata={}
        )
        
        builder = PipelineBuilder()
        sorted_nodes = builder._topological_sort(pipeline)
        
        # 验证排序结果
        assert len(sorted_nodes) == 4
        assert sorted_nodes[0].id == "node1"
        # node2 和 node3 可以是任意顺序
        assert sorted_nodes[3].id == "node4"
    
    def test_topological_sort_cycle_detection(self):
        """测试检测循环依赖"""
        # 创建一个有循环的依赖图
        # node1 -> node2 -> node3 -> node1
        
        node1 = VisualNode(id="node1", node_type="retriever", config={}, position={})
        node2 = VisualNode(id="node2", node_type="promptor", config={}, position={})
        node3 = VisualNode(id="node3", node_type="generator", config={}, position={})
        
        edges = [
            VisualEdge(id="e1", source="node1", target="node2"),
            VisualEdge(id="e2", source="node2", target="node3"),
            VisualEdge(id="e3", source="node3", target="node1"),  # 形成循环
        ]
        
        pipeline = VisualPipeline(
            id="test",
            name="Test",
            nodes=[node1, node2, node3],
            edges=edges,
            metadata={}
        )
        
        builder = PipelineBuilder()
        
        # 应该抛出 ValueError
        with pytest.raises(ValueError, match="Cycle detected"):
            builder._topological_sort(pipeline)
    
    def test_get_operator_class(self):
        """测试获取 Operator 类"""
        builder = PipelineBuilder()
        
        # 测试获取有效的节点类型
        retriever_cls = builder._get_operator_class("retriever")
        assert retriever_cls is not None
        
        # 测试获取无效的节点类型
        with pytest.raises(ValueError, match="Unknown node type"):
            builder._get_operator_class("invalid_type")
    
    def test_create_source(self):
        """测试创建数据源"""
        node = VisualNode(
            id="source",
            node_type="file_source",
            config={"data": [{"input": "test1"}, {"input": "test2"}]},
            position={}
        )
        
        pipeline = VisualPipeline(
            id="test",
            name="Test",
            nodes=[node],
            edges=[],
            metadata={}
        )
        
        builder = PipelineBuilder()
        source = builder._create_source(node, pipeline)
        
        # 验证 Source 创建成功
        assert source is not None
    
    def test_create_sink(self):
        """测试创建数据接收器"""
        pipeline = VisualPipeline(
            id="test",
            name="Test",
            nodes=[],
            edges=[],
            metadata={}
        )
        
        builder = PipelineBuilder()
        sink = builder._create_sink(pipeline)
        
        # 验证 Sink 创建成功
        assert sink is not None
    
    def test_get_pipeline_builder_singleton(self):
        """测试获取 PipelineBuilder 单例"""
        from sage.studio.services import get_pipeline_builder
        
        builder1 = get_pipeline_builder()
        builder2 = get_pipeline_builder()
        
        # 验证是同一个实例
        assert builder1 is builder2


class TestPipelineBuilderIntegration:
    """集成测试 - 测试完整的 Pipeline 构建流程"""
    
    def test_full_rag_pipeline(self):
        """测试完整的 RAG Pipeline 构建"""
        # 创建完整的 RAG Pipeline
        retriever = VisualNode(
            id="retriever",
            node_type="retriever",
            config={"top_k": 5, "index_name": "test_index"},
            position={"x": 100, "y": 100}
        )
        
        promptor = VisualNode(
            id="promptor",
            node_type="promptor",
            config={"template": "Context: {context}\nQuestion: {question}"},
            position={"x": 300, "y": 100}
        )
        
        generator = VisualNode(
            id="generator",
            node_type="generator",
            config={"model": "gpt-3.5-turbo"},
            position={"x": 500, "y": 100}
        )
        
        edges = [
            VisualEdge(id="e1", source="retriever", target="promptor"),
            VisualEdge(id="e2", source="promptor", target="generator"),
        ]
        
        visual_pipeline = VisualPipeline(
            id="rag_pipeline",
            name="RAG Pipeline",
            nodes=[retriever, promptor, generator],
            edges=edges,
            metadata={"description": "A complete RAG pipeline"}
        )
        
        # 构建 Pipeline
        builder = PipelineBuilder()
        sage_pipeline = builder.build(visual_pipeline)
        
        # 验证 Pipeline 创建成功
        assert sage_pipeline is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
