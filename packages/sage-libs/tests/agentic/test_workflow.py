"""
Tests for agentic/workflow module

Tests cover:
- WorkflowNode: Basic node functionality
- WorkflowGraph: Workflow graph operations
"""

import pytest


@pytest.mark.unit
class TestWorkflowImports:
    """Test workflow module imports"""

    def test_import_workflow_graph(self):
        """测试能够导入WorkflowGraph"""
        from sage.libs.agentic.workflow.base import WorkflowGraph

        assert WorkflowGraph is not None
        assert hasattr(WorkflowGraph, "__init__")

    def test_import_workflow_node(self):
        """测试能够导入WorkflowNode"""
        from sage.libs.agentic.workflow.base import WorkflowNode

        assert WorkflowNode is not None

    def test_import_node_type(self):
        """测试能够导入NodeType"""
        from sage.libs.agentic.workflow.base import NodeType

        assert NodeType is not None
        assert hasattr(NodeType, "AGENT")


@pytest.mark.unit
class TestWorkflowNode:
    """Test WorkflowNode class"""

    def test_create_node(self):
        """测试创建节点"""
        from sage.libs.agentic.workflow.base import NodeType, WorkflowNode

        node = WorkflowNode(id="test_node", name="Test Node", node_type=NodeType.AGENT)

        assert node.id == "test_node"
        assert node.name == "Test Node"
        assert node.node_type == NodeType.AGENT

    def test_node_metrics(self):
        """测试节点指标"""
        from sage.libs.agentic.workflow.base import NodeType, WorkflowNode

        node = WorkflowNode(
            id="node1",
            name="Node 1",
            node_type=NodeType.TOOL,
            metrics={"cost": 10.0, "latency": 0.5},
        )

        assert node.cost == 10.0
        assert node.latency == 0.5
        assert node.quality == 1.0  # Default value


@pytest.mark.unit
class TestWorkflowGraph:
    """Test WorkflowGraph class"""

    def test_create_workflow(self):
        """测试创建工作流"""
        from sage.libs.agentic.workflow.base import WorkflowGraph

        workflow = WorkflowGraph(name="test_workflow")

        assert workflow.name == "test_workflow"
        assert isinstance(workflow.nodes, dict)
        assert isinstance(workflow.edges, dict)

    def test_add_node_to_workflow(self):
        """测试添加节点到工作流"""
        from sage.libs.agentic.workflow.base import NodeType, WorkflowGraph

        workflow = WorkflowGraph(name="test")

        node = workflow.add_node(node_id="node1", node_type=NodeType.AGENT)

        assert "node1" in workflow.nodes
        assert node.id == "node1"
        assert node.node_type == NodeType.AGENT

    def test_add_duplicate_node_raises_error(self):
        """测试添加重复节点会报错"""
        from sage.libs.agentic.workflow.base import NodeType, WorkflowGraph

        workflow = WorkflowGraph(name="test")
        workflow.add_node(node_id="node1", node_type=NodeType.AGENT)

        with pytest.raises(ValueError, match="already exists"):
            workflow.add_node(node_id="node1", node_type=NodeType.TOOL)
