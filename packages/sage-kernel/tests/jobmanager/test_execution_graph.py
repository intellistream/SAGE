"""
ExecutionGraph 执行图测试
测试 ExecutionGraph 及其相关组件的所有功能，包括图构建、节点管理、边管理等
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock

from sage.kernels.jobmanager.execution_graph.execution_graph import ExecutionGraph
from sage.kernels.jobmanager.execution_graph.graph_node import GraphNode  
from sage.kernels.jobmanager.execution_graph.service_node import ServiceNode
from sage.kernels.jobmanager.execution_graph.graph_edge import GraphEdge


@pytest.mark.unit
class TestExecutionGraphInitialization:
    """测试ExecutionGraph初始化"""

    @pytest.fixture
    def mock_environment(self):
        """创建模拟环境"""
        env = Mock()
        env.name = "test_env"
        env.console_log_level = "INFO"
        env.env_base_dir = "/tmp/test_env"
        env.pipeline = Mock()
        env.pipeline.transformations = []
        return env

    def test_basic_initialization(self, mock_environment):
        """测试基本初始化"""
        with patch.object(ExecutionGraph, '_build_graph_from_pipeline'), \
             patch.object(ExecutionGraph, '_build_service_nodes'), \
             patch.object(ExecutionGraph, 'generate_runtime_contexts'), \
             patch.object(ExecutionGraph, 'setup_logging_system'):
            
            graph = ExecutionGraph(mock_environment)
            
            assert graph.env is mock_environment
            assert isinstance(graph.nodes, dict)
            assert isinstance(graph.service_nodes, dict)
            assert isinstance(graph.edges, dict)

    def test_initialization_with_pipeline(self, mock_environment):
        """测试使用流水线初始化"""
        # 模拟流水线中的转换
        mock_transform1 = Mock()
        mock_transform1.name = "transform1"
        mock_transform2 = Mock()
        mock_transform2.name = "transform2"
        
        mock_environment.pipeline.transformations = [mock_transform1, mock_transform2]
        
        with patch.object(ExecutionGraph, '_build_graph_from_pipeline') as mock_build, \
             patch.object(ExecutionGraph, '_build_service_nodes'), \
             patch.object(ExecutionGraph, 'generate_runtime_contexts'), \
             patch.object(ExecutionGraph, 'setup_logging_system'):
            
            graph = ExecutionGraph(mock_environment)
            
            mock_build.assert_called_once_with(mock_environment)

    def test_logging_system_setup(self, mock_environment):
        """测试日志系统设置"""
        with patch.object(ExecutionGraph, '_build_graph_from_pipeline'), \
             patch.object(ExecutionGraph, '_build_service_nodes'), \
             patch.object(ExecutionGraph, 'generate_runtime_contexts'), \
             patch('sage.utils.logging.custom_logger.CustomLogger') as mock_logger:
            
            graph = ExecutionGraph(mock_environment)
            
            # 验证CustomLogger被正确调用
            mock_logger.assert_called_once()
            call_args = mock_logger.call_args
            
            # 验证日志配置
            log_configs = call_args[0][0]
            assert len(log_configs) == 3  # console, debug, error
            assert log_configs[0][0] == "console"
            assert "ExecutionGraph.log" in log_configs[1][0]
            assert "Error.log" in log_configs[2][0]


@pytest.mark.unit
class TestExecutionGraphNodeManagement:
    """测试节点管理功能"""

    @pytest.fixture
    def execution_graph(self):
        """创建ExecutionGraph实例"""
        mock_env = Mock()
        mock_env.name = "test_env"
        mock_env.console_log_level = "INFO"
        mock_env.env_base_dir = "/tmp/test"
        mock_env.pipeline = Mock()
        mock_env.pipeline.transformations = []
        
        with patch.object(ExecutionGraph, '_build_graph_from_pipeline'), \
             patch.object(ExecutionGraph, '_build_service_nodes'), \
             patch.object(ExecutionGraph, 'generate_runtime_contexts'), \
             patch.object(ExecutionGraph, 'setup_logging_system'):
            
            return ExecutionGraph(mock_env)

    def test_add_node(self, execution_graph):
        """测试添加节点"""
        mock_transformation = Mock()
        mock_transformation.name = "test_transform"
        
        node = GraphNode(
            transformation=mock_transformation,
            name="test_node",
            is_source=True,
            is_sink=False
        )
        
        execution_graph.nodes["test_node"] = node
        
        assert "test_node" in execution_graph.nodes
        assert execution_graph.nodes["test_node"] is node

    def test_add_service_node(self, execution_graph):
        """测试添加服务节点"""
        service_node = ServiceNode(
            service_name="test_service",
            service_type="ML_SERVICE"
        )
        
        execution_graph.service_nodes["test_service"] = service_node
        
        assert "test_service" in execution_graph.service_nodes
        assert execution_graph.service_nodes["test_service"] is service_node

    def test_get_node_by_name(self, execution_graph):
        """测试按名称获取节点"""
        mock_transformation = Mock()
        mock_transformation.name = "test_transform"
        
        node = GraphNode(
            transformation=mock_transformation,
            name="lookup_node",
            is_source=True,
            is_sink=False
        )
        
        execution_graph.nodes["lookup_node"] = node
        
        found_node = execution_graph.get_node("lookup_node")
        assert found_node is node

    def test_get_nonexistent_node(self, execution_graph):
        """测试获取不存在的节点"""
        result = execution_graph.get_node("nonexistent")
        assert result is None

    def test_list_source_nodes(self, execution_graph):
        """测试列出源节点"""
        # 创建多个节点
        for i in range(3):
            mock_transform = Mock()
            mock_transform.name = f"transform_{i}"
            
            node = GraphNode(
                transformation=mock_transform,
                name=f"node_{i}",
                is_source=(i == 0),  # 只有第一个是源节点
                is_sink=False
            )
            execution_graph.nodes[f"node_{i}"] = node
        
        source_nodes = execution_graph.get_source_nodes()
        assert len(source_nodes) == 1
        assert source_nodes[0].name == "node_0"

    def test_list_sink_nodes(self, execution_graph):
        """测试列出汇点节点"""
        # 创建多个节点
        for i in range(3):
            mock_transform = Mock()
            mock_transform.name = f"transform_{i}"
            
            node = GraphNode(
                transformation=mock_transform,
                name=f"node_{i}",
                is_source=False,
                is_sink=(i == 2)  # 只有最后一个是汇点
            )
            execution_graph.nodes[f"node_{i}"] = node
        
        sink_nodes = execution_graph.get_sink_nodes()
        assert len(sink_nodes) == 1
        assert sink_nodes[0].name == "node_2"


@pytest.mark.unit
class TestExecutionGraphEdgeManagement:
    """测试边管理功能"""

    @pytest.fixture
    def execution_graph_with_nodes(self):
        """创建带有节点的ExecutionGraph"""
        mock_env = Mock()
        mock_env.name = "test_env"
        mock_env.console_log_level = "INFO"
        mock_env.env_base_dir = "/tmp/test"
        mock_env.pipeline = Mock()
        mock_env.pipeline.transformations = []
        
        with patch.object(ExecutionGraph, '_build_graph_from_pipeline'), \
             patch.object(ExecutionGraph, '_build_service_nodes'), \
             patch.object(ExecutionGraph, 'generate_runtime_contexts'), \
             patch.object(ExecutionGraph, 'setup_logging_system'):
            
            graph = ExecutionGraph(mock_env)
            
            # 添加测试节点
            for i in range(3):
                mock_transform = Mock()
                mock_transform.name = f"transform_{i}"
                
                node = GraphNode(
                    transformation=mock_transform,
                    name=f"node_{i}",
                    is_source=(i == 0),
                    is_sink=(i == 2)
                )
                graph.nodes[f"node_{i}"] = node
            
            return graph

    def test_add_edge(self, execution_graph_with_nodes):
        """测试添加边"""
        graph = execution_graph_with_nodes
        
        edge = GraphEdge(
            from_node=graph.nodes["node_0"],
            to_node=graph.nodes["node_1"],
            edge_type="DATA_FLOW"
        )
        
        graph.edges["edge_0_1"] = edge
        
        assert "edge_0_1" in graph.edges
        assert graph.edges["edge_0_1"] is edge

    def test_create_edge_between_nodes(self, execution_graph_with_nodes):
        """测试在节点间创建边"""
        graph = execution_graph_with_nodes
        
        edge = graph.create_edge("node_0", "node_1", "DATA_FLOW")
        
        assert edge.from_node is graph.nodes["node_0"]
        assert edge.to_node is graph.nodes["node_1"]
        assert edge.edge_type == "DATA_FLOW"

    def test_create_edge_with_invalid_nodes(self, execution_graph_with_nodes):
        """测试使用无效节点创建边"""
        graph = execution_graph_with_nodes
        
        with pytest.raises(ValueError, match="Source node not found"):
            graph.create_edge("nonexistent", "node_1", "DATA_FLOW")
        
        with pytest.raises(ValueError, match="Target node not found"):
            graph.create_edge("node_0", "nonexistent", "DATA_FLOW")

    def test_get_node_connections(self, execution_graph_with_nodes):
        """测试获取节点连接"""
        graph = execution_graph_with_nodes
        
        # 创建连接
        edge1 = graph.create_edge("node_0", "node_1", "DATA_FLOW")
        edge2 = graph.create_edge("node_1", "node_2", "DATA_FLOW")
        
        graph.edges["edge_0_1"] = edge1
        graph.edges["edge_1_2"] = edge2
        
        # 测试输出连接
        outgoing = graph.get_outgoing_edges("node_0")
        assert len(outgoing) == 1
        assert outgoing[0] is edge1
        
        # 测试输入连接
        incoming = graph.get_incoming_edges("node_2")
        assert len(incoming) == 1
        assert incoming[0] is edge2

    def test_remove_edge(self, execution_graph_with_nodes):
        """测试删除边"""
        graph = execution_graph_with_nodes
        
        edge = graph.create_edge("node_0", "node_1", "DATA_FLOW")
        graph.edges["edge_0_1"] = edge
        
        # 删除边
        del graph.edges["edge_0_1"]
        
        assert "edge_0_1" not in graph.edges


@pytest.mark.unit
class TestExecutionGraphRuntimeContext:
    """测试运行时上下文生成"""

    @pytest.fixture
    def execution_graph(self):
        """创建ExecutionGraph实例"""
        mock_env = Mock()
        mock_env.name = "test_env"
        mock_env.console_log_level = "INFO"
        mock_env.env_base_dir = "/tmp/test"
        mock_env.pipeline = Mock()
        mock_env.pipeline.transformations = []
        
        with patch.object(ExecutionGraph, '_build_graph_from_pipeline'), \
             patch.object(ExecutionGraph, '_build_service_nodes'), \
             patch.object(ExecutionGraph, 'generate_runtime_contexts'), \
             patch.object(ExecutionGraph, 'setup_logging_system'):
            
            return ExecutionGraph(mock_env)

    def test_generate_runtime_contexts_for_nodes(self, execution_graph):
        """测试为节点生成运行时上下文"""
        # 添加测试节点
        mock_transform = Mock()
        mock_transform.name = "test_transform"
        
        node = GraphNode(
            transformation=mock_transform,
            name="test_node",
            is_source=True,
            is_sink=False
        )
        
        execution_graph.nodes["test_node"] = node
        
        with patch('sage.kernels.runtime.task_context.TaskContext') as mock_task_context:
            mock_context_instance = Mock()
            mock_task_context.return_value = mock_context_instance
            
            execution_graph.generate_runtime_contexts()
            
            # 验证TaskContext被创建
            mock_task_context.assert_called_once_with(
                node, mock_transform, execution_graph.env, execution_graph=execution_graph
            )
            
            # 验证上下文被分配给节点
            assert node.ctx is mock_context_instance

    def test_generate_runtime_contexts_for_service_nodes(self, execution_graph):
        """测试为服务节点生成运行时上下文"""
        service_node = ServiceNode(
            service_name="test_service",
            service_type="ML_SERVICE"
        )
        
        execution_graph.service_nodes["test_service"] = service_node
        
        with patch('sage.kernels.runtime.service_context.ServiceContext') as mock_service_context:
            mock_context_instance = Mock()
            mock_service_context.return_value = mock_context_instance
            
            execution_graph.generate_runtime_contexts()
            
            # 验证ServiceContext被创建
            mock_service_context.assert_called_once()
            
            # 验证上下文被分配给服务节点
            assert service_node.ctx is mock_context_instance

    def test_generate_runtime_contexts_error_handling(self, execution_graph):
        """测试运行时上下文生成错误处理"""
        mock_transform = Mock()
        mock_transform.name = "error_transform"
        
        node = GraphNode(
            transformation=mock_transform,
            name="error_node",
            is_source=True,
            is_sink=False
        )
        
        execution_graph.nodes["error_node"] = node
        
        with patch('sage.kernels.runtime.task_context.TaskContext') as mock_task_context, \
             patch.object(execution_graph, 'logger') as mock_logger:
            
            # 模拟TaskContext创建失败
            mock_task_context.side_effect = Exception("Context creation failed")
            
            # 应该优雅处理错误，不抛出异常
            execution_graph.generate_runtime_contexts()
            
            # 验证错误被记录
            mock_logger.error.assert_called()
            error_call = mock_logger.error.call_args[0][0]
            assert "Failed to generate runtime context" in error_call
            assert "error_node" in error_call


@pytest.mark.unit
class TestExecutionGraphStopSignals:
    """测试停止信号计算"""

    @pytest.fixture
    def execution_graph(self):
        """创建ExecutionGraph实例"""
        mock_env = Mock()
        mock_env.name = "test_env"
        mock_env.console_log_level = "INFO"
        mock_env.env_base_dir = "/tmp/test"
        mock_env.pipeline = Mock()
        mock_env.pipeline.transformations = []
        
        with patch.object(ExecutionGraph, '_build_graph_from_pipeline'), \
             patch.object(ExecutionGraph, '_build_service_nodes'), \
             patch.object(ExecutionGraph, 'generate_runtime_contexts'), \
             patch.object(ExecutionGraph, 'setup_logging_system'):
            
            return ExecutionGraph(mock_env)

    def test_calculate_total_stop_signals_basic(self, execution_graph):
        """测试基本停止信号计算"""
        # 添加汇点节点
        for i in range(3):
            mock_transform = Mock()
            mock_transform.name = f"sink_transform_{i}"
            
            node = GraphNode(
                transformation=mock_transform,
                name=f"sink_node_{i}",
                is_source=False,
                is_sink=True
            )
            node.stop_signal_num = i + 1  # 1, 2, 3
            execution_graph.nodes[f"sink_node_{i}"] = node
        
        total_signals = execution_graph.calculate_total_stop_signals()
        assert total_signals == 6  # 1 + 2 + 3

    def test_calculate_total_stop_signals_no_sinks(self, execution_graph):
        """测试没有汇点节点时的停止信号计算"""
        # 添加非汇点节点
        mock_transform = Mock()
        mock_transform.name = "source_transform"
        
        node = GraphNode(
            transformation=mock_transform,
            name="source_node",
            is_source=True,
            is_sink=False
        )
        node.stop_signal_num = 5
        execution_graph.nodes["source_node"] = node
        
        total_signals = execution_graph.calculate_total_stop_signals()
        assert total_signals == 0

    def test_calculate_source_dependencies(self, execution_graph):
        """测试源依赖计算"""
        # 创建源节点
        mock_source_transform = Mock()
        mock_source_transform.name = "source_transform"
        
        source_node = GraphNode(
            transformation=mock_source_transform,
            name="source_node",
            is_source=True,
            is_sink=False
        )
        execution_graph.nodes["source_node"] = source_node
        
        # 创建中间节点
        mock_middle_transform = Mock()
        mock_middle_transform.name = "middle_transform"
        
        middle_node = GraphNode(
            transformation=mock_middle_transform,
            name="middle_node",
            is_source=False,
            is_sink=False
        )
        execution_graph.nodes["middle_node"] = middle_node
        
        # 模拟依赖关系
        with patch.object(execution_graph, '_calculate_source_dependencies') as mock_calc:
            execution_graph._calculate_source_dependencies()
            mock_calc.assert_called_once()


@pytest.mark.unit
class TestExecutionGraphUtilities:
    """测试工具功能"""

    @pytest.fixture
    def execution_graph(self):
        """创建ExecutionGraph实例"""
        mock_env = Mock()
        mock_env.name = "test_env"
        mock_env.console_log_level = "INFO"
        mock_env.env_base_dir = "/tmp/test"
        mock_env.pipeline = Mock()
        mock_env.pipeline.transformations = []
        
        with patch.object(ExecutionGraph, '_build_graph_from_pipeline'), \
             patch.object(ExecutionGraph, '_build_service_nodes'), \
             patch.object(ExecutionGraph, 'generate_runtime_contexts'), \
             patch.object(ExecutionGraph, 'setup_logging_system'):
            
            return ExecutionGraph(mock_env)

    def test_get_graph_statistics(self, execution_graph):
        """测试获取图统计信息"""
        # 添加节点
        for i in range(3):
            mock_transform = Mock()
            mock_transform.name = f"transform_{i}"
            
            node = GraphNode(
                transformation=mock_transform,
                name=f"node_{i}",
                is_source=(i == 0),
                is_sink=(i == 2)
            )
            execution_graph.nodes[f"node_{i}"] = node
        
        # 添加服务节点
        for i in range(2):
            service_node = ServiceNode(
                service_name=f"service_{i}",
                service_type="TEST_SERVICE"
            )
            execution_graph.service_nodes[f"service_{i}"] = service_node
        
        stats = execution_graph.get_graph_statistics()
        
        assert stats["total_nodes"] == 3
        assert stats["total_service_nodes"] == 2
        assert stats["source_nodes"] == 1
        assert stats["sink_nodes"] == 1

    def test_validate_graph_structure(self, execution_graph):
        """测试验证图结构"""
        # 添加有效的图结构
        mock_source = Mock()
        mock_source.name = "source"
        source_node = GraphNode(
            transformation=mock_source,
            name="source_node",
            is_source=True,
            is_sink=False
        )
        
        mock_sink = Mock()
        mock_sink.name = "sink"
        sink_node = GraphNode(
            transformation=mock_sink,
            name="sink_node",
            is_source=False,
            is_sink=True
        )
        
        execution_graph.nodes["source_node"] = source_node
        execution_graph.nodes["sink_node"] = sink_node
        
        # 创建连接
        edge = GraphEdge(
            from_node=source_node,
            to_node=sink_node,
            edge_type="DATA_FLOW"
        )
        execution_graph.edges["source_to_sink"] = edge
        
        # 验证应该通过
        is_valid = execution_graph.validate_graph_structure()
        assert is_valid is True

    def test_validate_invalid_graph_structure(self, execution_graph):
        """测试验证无效图结构"""
        # 只添加源节点，没有汇点
        mock_source = Mock()
        mock_source.name = "source"
        source_node = GraphNode(
            transformation=mock_source,
            name="source_node",
            is_source=True,
            is_sink=False
        )
        execution_graph.nodes["source_node"] = source_node
        
        # 验证应该失败
        is_valid = execution_graph.validate_graph_structure()
        assert is_valid is False

    def test_export_graph_description(self, execution_graph):
        """测试导出图描述"""
        # 添加节点和边
        for i in range(2):
            mock_transform = Mock()
            mock_transform.name = f"transform_{i}"
            
            node = GraphNode(
                transformation=mock_transform,
                name=f"node_{i}",
                is_source=(i == 0),
                is_sink=(i == 1)
            )
            execution_graph.nodes[f"node_{i}"] = node
        
        edge = GraphEdge(
            from_node=execution_graph.nodes["node_0"],
            to_node=execution_graph.nodes["node_1"],
            edge_type="DATA_FLOW"
        )
        execution_graph.edges["edge_0_1"] = edge
        
        description = execution_graph.export_graph_description()
        
        assert "nodes" in description
        assert "edges" in description
        assert len(description["nodes"]) == 2
        assert len(description["edges"]) == 1

    def test_clone_graph(self, execution_graph):
        """测试克隆图"""
        # 添加原始节点
        mock_transform = Mock()
        mock_transform.name = "original_transform"
        
        original_node = GraphNode(
            transformation=mock_transform,
            name="original_node",
            is_source=True,
            is_sink=False
        )
        execution_graph.nodes["original_node"] = original_node
        
        # 克隆图
        cloned_graph = execution_graph.clone()
        
        # 验证克隆结果
        assert cloned_graph is not execution_graph
        assert len(cloned_graph.nodes) == len(execution_graph.nodes)
        assert "original_node" in cloned_graph.nodes
        assert cloned_graph.nodes["original_node"] is not original_node  # 不是同一个对象


@pytest.mark.integration
class TestExecutionGraphIntegration:
    """ExecutionGraph集成测试"""

    def test_complete_graph_construction(self):
        """测试完整的图构建过程"""
        # 创建模拟环境和流水线
        mock_env = Mock()
        mock_env.name = "integration_test"
        mock_env.console_log_level = "INFO"
        mock_env.env_base_dir = "/tmp/integration"
        mock_env.pipeline = Mock()
        
        # 创建模拟转换
        transforms = []
        for i in range(3):
            transform = Mock()
            transform.name = f"transform_{i}"
            transform.get_input_channels = Mock(return_value=[f"input_{i}"] if i > 0 else [])
            transform.get_output_channels = Mock(return_value=[f"output_{i}"] if i < 2 else [])
            transforms.append(transform)
        
        mock_env.pipeline.transformations = transforms
        
        with patch('sage.utils.logging.custom_logger.CustomLogger'), \
             patch('sage.kernels.runtime.task_context.TaskContext'), \
             patch('sage.kernels.runtime.service_context.ServiceContext'):
            
            graph = ExecutionGraph(mock_env)
            
            # 验证图构建
            assert graph.env is mock_env
            assert isinstance(graph.nodes, dict)
            assert isinstance(graph.service_nodes, dict)
            assert isinstance(graph.edges, dict)

    def test_graph_execution_simulation(self):
        """测试图执行模拟"""
        mock_env = Mock()
        mock_env.name = "execution_test"
        mock_env.console_log_level = "INFO"
        mock_env.env_base_dir = "/tmp/execution"
        mock_env.pipeline = Mock()
        mock_env.pipeline.transformations = []
        
        with patch.object(ExecutionGraph, '_build_graph_from_pipeline'), \
             patch.object(ExecutionGraph, '_build_service_nodes'), \
             patch.object(ExecutionGraph, 'generate_runtime_contexts'), \
             patch.object(ExecutionGraph, 'setup_logging_system'):
            
            graph = ExecutionGraph(mock_env)
            
            # 添加节点模拟执行流程
            source_transform = Mock()
            source_transform.name = "data_source"
            
            source_node = GraphNode(
                transformation=source_transform,
                name="source",
                is_source=True,
                is_sink=False
            )
            source_node.ctx = Mock()
            
            sink_transform = Mock()
            sink_transform.name = "data_sink"
            
            sink_node = GraphNode(
                transformation=sink_transform,
                name="sink",
                is_source=False,
                is_sink=True
            )
            sink_node.ctx = Mock()
            
            graph.nodes["source"] = source_node
            graph.nodes["sink"] = sink_node
            
            # 创建连接
            edge = GraphEdge(
                from_node=source_node,
                to_node=sink_node,
                edge_type="DATA_FLOW"
            )
            graph.edges["source_to_sink"] = edge
            
            # 模拟执行
            execution_result = graph.simulate_execution()
            assert execution_result["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
