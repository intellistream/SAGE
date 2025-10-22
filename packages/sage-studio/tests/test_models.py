"""
Tests for Studio Data Models
"""
import pytest

from sage.studio.models import VisualNode, VisualConnection, VisualPipeline, PipelineExecution, PipelineStatus, NodeStatus


class TestVisualNode:
    """测试 VisualNode 数据模型"""
    
    def test_node_creation(self):
        """测试创建节点"""
        node = VisualNode(
            id="test_node",
            node_type="retriever",
            config={"top_k": 5},
            position={"x": 100, "y": 200}
        )
        
        assert node.id == "test_node"
        assert node.node_type == "retriever"
        assert node.config["top_k"] == 5
        assert node.position["x"] == 100
        assert node.position["y"] == 200
    
    def test_node_with_empty_config(self):
        """测试创建配置为空的节点"""
        node = VisualNode(
            id="node1",
            node_type="generator",
            config={},
            position={"x": 0, "y": 0}
        )
        
        assert node.config == {}
    
    def test_node_serialization(self):
        """测试节点序列化"""
        node = VisualNode(
            id="node1",
            node_type="retriever",
            config={"top_k": 5},
            position={"x": 100, "y": 200}
        )
        
        # 测试转换为字典
        node_dict = node.model_dump()
        
        assert node_dict["id"] == "node1"
        assert node_dict["node_type"] == "retriever"
        assert node_dict["config"]["top_k"] == 5


class TestVisualEdge:
    """测试 VisualEdge 数据模型"""
    
    def test_edge_creation(self):
        """测试创建边"""
        edge = VisualEdge(
            id="edge1",
            source="node1",
            target="node2"
        )
        
        assert edge.id == "edge1"
        assert edge.source == "node1"
        assert edge.target == "node2"
    
    def test_edge_with_label(self):
        """测试创建带标签的边"""
        edge = VisualEdge(
            id="edge1",
            source="node1",
            target="node2",
            label="output"
        )
        
        assert edge.label == "output"
    
    def test_edge_serialization(self):
        """测试边序列化"""
        edge = VisualEdge(
            id="edge1",
            source="node1",
            target="node2"
        )
        
        edge_dict = edge.model_dump()
        
        assert edge_dict["id"] == "edge1"
        assert edge_dict["source"] == "node1"
        assert edge_dict["target"] == "node2"


class TestVisualPipeline:
    """测试 VisualPipeline 数据模型"""
    
    def test_pipeline_creation(self):
        """测试创建 Pipeline"""
        node1 = VisualNode(id="node1", node_type="retriever", config={}, position={})
        node2 = VisualNode(id="node2", node_type="generator", config={}, position={})
        edge = VisualEdge(id="edge1", source="node1", target="node2")
        
        pipeline = VisualPipeline(
            id="pipeline1",
            name="Test Pipeline",
            nodes=[node1, node2],
            edges=[edge],
            metadata={"description": "A test pipeline"}
        )
        
        assert pipeline.id == "pipeline1"
        assert pipeline.name == "Test Pipeline"
        assert len(pipeline.nodes) == 2
        assert len(pipeline.edges) == 1
        assert pipeline.metadata["description"] == "A test pipeline"
    
    def test_empty_pipeline(self):
        """测试创建空 Pipeline"""
        pipeline = VisualPipeline(
            id="empty",
            name="Empty Pipeline",
            nodes=[],
            edges=[],
            metadata={}
        )
        
        assert len(pipeline.nodes) == 0
        assert len(pipeline.edges) == 0
    
    def test_pipeline_serialization(self):
        """测试 Pipeline 序列化"""
        node = VisualNode(id="node1", node_type="retriever", config={}, position={})
        pipeline = VisualPipeline(
            id="pipeline1",
            name="Test Pipeline",
            nodes=[node],
            edges=[],
            metadata={}
        )
        
        pipeline_dict = pipeline.model_dump()
        
        assert pipeline_dict["id"] == "pipeline1"
        assert pipeline_dict["name"] == "Test Pipeline"
        assert len(pipeline_dict["nodes"]) == 1
    
    def test_pipeline_from_json(self):
        """测试从 JSON 创建 Pipeline"""
        json_data = {
            "id": "pipeline1",
            "name": "Test Pipeline",
            "nodes": [
                {
                    "id": "node1",
                    "node_type": "retriever",
                    "config": {"top_k": 5},
                    "position": {"x": 100, "y": 100}
                }
            ],
            "edges": [],
            "metadata": {}
        }
        
        pipeline = VisualPipeline.model_validate(json_data)
        
        assert pipeline.id == "pipeline1"
        assert len(pipeline.nodes) == 1
        assert pipeline.nodes[0].config["top_k"] == 5


class TestPipelineResponse:
    """测试 PipelineResponse 数据模型"""
    
    def test_response_creation(self):
        """测试创建 Response"""
        response = PipelineResponse(
            pipeline_id="pipeline1",
            status="success",
            results=[{"output": "test"}],
            error=None
        )
        
        assert response.pipeline_id == "pipeline1"
        assert response.status == "success"
        assert len(response.results) == 1
        assert response.error is None
    
    def test_error_response(self):
        """测试创建错误 Response"""
        response = PipelineResponse(
            pipeline_id="pipeline1",
            status="error",
            results=[],
            error="Something went wrong"
        )
        
        assert response.status == "error"
        assert response.error == "Something went wrong"
    
    def test_response_serialization(self):
        """测试 Response 序列化"""
        response = PipelineResponse(
            pipeline_id="pipeline1",
            status="success",
            results=[{"output": "test"}],
            error=None
        )
        
        response_dict = response.model_dump()
        
        assert response_dict["pipeline_id"] == "pipeline1"
        assert response_dict["status"] == "success"


class TestModelIntegration:
    """集成测试 - 测试模型之间的协作"""
    
    def test_complete_pipeline_model(self):
        """测试完整的 Pipeline 数据模型"""
        # 创建节点
        retriever = VisualNode(
            id="retriever",
            node_type="retriever",
            config={"top_k": 5, "index_name": "test"},
            position={"x": 100, "y": 100}
        )
        
        promptor = VisualNode(
            id="promptor",
            node_type="promptor",
            config={"template": "Context: {context}"},
            position={"x": 300, "y": 100}
        )
        
        generator = VisualNode(
            id="generator",
            node_type="generator",
            config={"model": "gpt-3.5-turbo"},
            position={"x": 500, "y": 100}
        )
        
        # 创建边
        edges = [
            VisualEdge(id="e1", source="retriever", target="promptor"),
            VisualEdge(id="e2", source="promptor", target="generator"),
        ]
        
        # 创建 Pipeline
        pipeline = VisualPipeline(
            id="rag_pipeline",
            name="RAG Pipeline",
            nodes=[retriever, promptor, generator],
            edges=edges,
            metadata={"description": "A complete RAG pipeline"}
        )
        
        # 验证 Pipeline 结构
        assert len(pipeline.nodes) == 3
        assert len(pipeline.edges) == 2
        
        # 验证可以序列化和反序列化
        pipeline_dict = pipeline.model_dump()
        reconstructed = VisualPipeline.model_validate(pipeline_dict)
        
        assert reconstructed.id == pipeline.id
        assert len(reconstructed.nodes) == len(pipeline.nodes)
        assert len(reconstructed.edges) == len(pipeline.edges)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
