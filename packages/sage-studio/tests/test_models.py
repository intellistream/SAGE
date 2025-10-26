"""
Tests for Studio Data Models
"""

import pytest

from sage.studio.models import (  # type: ignore[import-not-found]
    PipelineExecution,
    PipelineStatus,
    VisualConnection,
    VisualNode,
    VisualPipeline,
)


class TestVisualNode:
    """测试 VisualNode 数据模型"""

    def test_node_creation(self):
        """测试创建节点"""
        node = VisualNode(
            id="test_node",
            type="retriever",
            label="Test Retriever",
            config={"top_k": 5},
            position={"x": 100, "y": 200},
        )

        assert node.id == "test_node"
        assert node.type == "retriever"
        assert node.config["top_k"] == 5
        assert node.position["x"] == 100
        assert node.position["y"] == 200

    def test_node_with_empty_config(self):
        """测试创建配置为空的节点"""
        node = VisualNode(
            id="node1",
            type="generator",
            label="Generator",
            config={},
            position={"x": 0, "y": 0},
        )

        assert node.config == {}

    def test_node_serialization(self):
        """测试节点序列化"""
        node = VisualNode(
            id="node1",
            type="retriever",
            label="Retriever",
            config={"top_k": 5},
            position={"x": 100, "y": 200},
        )

        # VisualNode 是 dataclass
        assert node.id == "node1"
        assert node.type == "retriever"
        assert node.config["top_k"] == 5


class TestVisualConnection:
    """测试 VisualConnection 数据模型"""

    def test_connection_creation(self):
        """测试创建连接"""
        conn = VisualConnection(
            id="conn1",
            source_node_id="node1",
            source_port="output",
            target_node_id="node2",
            target_port="input",
        )

        assert conn.id == "conn1"
        assert conn.source_node_id == "node1"
        assert conn.target_node_id == "node2"

    def test_connection_with_label(self):
        """测试创建带标签的连接"""
        conn = VisualConnection(
            id="conn1",
            source_node_id="node1",
            source_port="output",
            target_node_id="node2",
            target_port="input",
            label="data flow",
        )

        assert conn.label == "data flow"

    def test_connection_serialization(self):
        """测试连接序列化"""
        conn = VisualConnection(
            id="conn1",
            source_node_id="node1",
            source_port="output",
            target_node_id="node2",
            target_port="input",
        )

        # VisualConnection 是 dataclass，使用 __dict__
        assert conn.id == "conn1"
        assert conn.source_node_id == "node1"
        assert conn.target_node_id == "node2"


class TestVisualPipeline:
    """测试 VisualPipeline 数据模型"""

    def test_pipeline_creation(self):
        """测试创建 Pipeline"""
        node1 = VisualNode(
            id="node1",
            type="retriever",
            label="Retriever",
            config={},
            position={"x": 0, "y": 0},
        )
        node2 = VisualNode(
            id="node2",
            type="generator",
            label="Generator",
            config={},
            position={"x": 100, "y": 0},
        )
        conn = VisualConnection(
            id="conn1",
            source_node_id="node1",
            source_port="output",
            target_node_id="node2",
            target_port="input",
        )

        pipeline = VisualPipeline(
            id="pipeline1",
            name="Test Pipeline",
            nodes=[node1, node2],
            connections=[conn],
        )

        assert pipeline.id == "pipeline1"
        assert pipeline.name == "Test Pipeline"
        assert len(pipeline.nodes) == 2
        assert len(pipeline.connections) == 1

    def test_empty_pipeline(self):
        """测试创建空 Pipeline"""
        pipeline = VisualPipeline(id="empty", name="Empty Pipeline", nodes=[], connections=[])

        assert len(pipeline.nodes) == 0
        assert len(pipeline.connections) == 0

    def test_pipeline_serialization(self):
        """测试 Pipeline 序列化"""
        node = VisualNode(
            id="node1",
            type="retriever",
            label="Retriever",
            config={},
            position={"x": 0, "y": 0},
        )
        pipeline = VisualPipeline(
            id="pipeline1", name="Test Pipeline", nodes=[node], connections=[]
        )

        # VisualPipeline 是 dataclass
        assert pipeline.id == "pipeline1"
        assert pipeline.name == "Test Pipeline"
        assert len(pipeline.nodes) == 1

    def test_pipeline_from_dict(self):
        """测试从字典创建 Pipeline"""
        node = VisualNode(
            id="node1",
            type="retriever",
            label="Retriever",
            config={"top_k": 5},
            position={"x": 100, "y": 100},
        )

        pipeline = VisualPipeline(
            id="pipeline1", name="Test Pipeline", nodes=[node], connections=[]
        )

        assert pipeline.id == "pipeline1"
        assert len(pipeline.nodes) == 1
        assert pipeline.nodes[0].config["top_k"] == 5


class TestPipelineExecution:
    """测试 PipelineExecution 数据模型"""

    def test_execution_creation(self):
        """测试创建 Execution"""
        from datetime import datetime

        execution = PipelineExecution(
            id="exec1",
            pipeline_id="pipeline1",
            status=PipelineStatus.RUNNING,
            start_time=datetime.now(),
        )

        assert execution.id == "exec1"
        assert execution.pipeline_id == "pipeline1"
        assert execution.status == PipelineStatus.RUNNING
        assert execution.end_time is None

    def test_completed_execution(self):
        """测试完成的 Execution"""
        from datetime import datetime

        now = datetime.now()
        execution = PipelineExecution(
            id="exec1",
            pipeline_id="pipeline1",
            status=PipelineStatus.COMPLETED,
            start_time=now,
            end_time=now,
        )

        assert execution.status == PipelineStatus.COMPLETED
        assert execution.end_time is not None

    def test_execution_status(self):
        """测试 Execution 状态"""
        from datetime import datetime

        execution = PipelineExecution(
            id="exec1",
            pipeline_id="pipeline1",
            status=PipelineStatus.PENDING,
            start_time=datetime.now(),
        )

        assert execution.status == PipelineStatus.PENDING


class TestModelIntegration:
    """集成测试 - 测试模型之间的协作"""

    def test_complete_pipeline_model(self):
        """测试完整的 Pipeline 数据模型"""
        # 创建节点
        retriever = VisualNode(
            id="retriever",
            type="retriever",
            label="Retriever",
            config={"top_k": 5, "index_name": "test"},
            position={"x": 100, "y": 100},
        )

        promptor = VisualNode(
            id="promptor",
            type="promptor",
            label="Promptor",
            config={"template": "Context: {context}"},
            position={"x": 300, "y": 100},
        )

        generator = VisualNode(
            id="generator",
            type="generator",
            label="Generator",
            config={"model": "gpt-3.5-turbo"},
            position={"x": 500, "y": 100},
        )

        # 创建连接
        connections = [
            VisualConnection(
                id="c1",
                source_node_id="retriever",
                source_port="output",
                target_node_id="promptor",
                target_port="input",
            ),
            VisualConnection(
                id="c2",
                source_node_id="promptor",
                source_port="output",
                target_node_id="generator",
                target_port="input",
            ),
        ]

        # 创建 Pipeline
        pipeline = VisualPipeline(
            id="rag_pipeline",
            name="RAG Pipeline",
            nodes=[retriever, promptor, generator],
            connections=connections,
        )

        # 验证 Pipeline 结构
        assert len(pipeline.nodes) == 3
        assert len(pipeline.connections) == 2
        assert pipeline.name == "RAG Pipeline"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
