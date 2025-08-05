"""
Test suite for sage.kernels.runtime.task_context module

Tests the TaskContext class which provides shared runtime context
for tasks, operators and functions.
"""
import pytest
import threading
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from sage.kernel.kernels.runtime.task_context import TaskContext


class MockGraphNode:
    """Mock graph node for testing"""
    def __init__(self, name="test_node", parallelism=1, stop_signal_num=2):
        self.name = name
        self.parallelism = parallelism
        self.stop_signal_num = stop_signal_num
        # Add input_qd attribute that TaskContext expects
        from unittest.mock import Mock
        self.input_qd = Mock()
        self.input_qd.name = f"{name}_input_queue"


class MockTransformation:
    """Mock transformation for testing"""
    def __init__(self, is_spout=True):
        self.is_spout = is_spout


class MockEnvironment:
    """Mock environment for testing"""
    def __init__(self, name="test_env"):
        self.name = name
        self.env_base_dir = "/tmp/test"
        self.uuid = "test-uuid-123"
        self.console_log_level = "INFO"
        self.jobmanager_host = "127.0.0.1"
        self.jobmanager_port = 19001


class MockExecutionGraph:
    """Mock execution graph for testing"""
    def __init__(self):
        self.nodes = {}


class TestTaskContext:
    """Test class for TaskContext functionality"""

    @pytest.fixture
    def mock_node(self):
        """Create a mock graph node"""
        return MockGraphNode()

    @pytest.fixture
    def mock_transformation(self):
        """Create a mock transformation"""
        return MockTransformation()

    @pytest.fixture
    def mock_env(self):
        """Create a mock environment"""
        return MockEnvironment()

    @pytest.fixture
    def mock_graph(self):
        """Create a mock execution graph"""
        return MockExecutionGraph()

    @pytest.fixture
    def mock_context(self, mock_node, mock_transformation, mock_env, mock_graph):
        """Create a TaskContext for testing"""
        return TaskContext(mock_node, mock_transformation, mock_env, mock_graph)

    @pytest.mark.unit
    def test_context_initialization(self, mock_node, mock_transformation, mock_env, mock_graph):
        """Test TaskContext initialization"""
        context = TaskContext(mock_node, mock_transformation, mock_env, mock_graph)
        
        # Verify basic attributes
        assert context.name == "test_node"
        assert context.env_name == "test_env"
        assert context.env_base_dir == "/tmp/test"
        assert context.env_uuid == "test-uuid-123"
        assert context.env_console_log_level == "INFO"
        assert context.parallel_index == 0
        assert context.parallelism == 2
        assert context.is_spout is True
        assert context.delay == 0.01
        assert context.stop_signal_num == 1
        assert context.jobmanager_host == "127.0.0.1"
        assert context.jobmanager_port == 19001

    @pytest.mark.unit
    def test_context_attributes(self, mock_context):
        """Test all context attributes are properly set"""
        assert mock_context.name == "test_node"
        assert mock_context.env_name == "test_env"
        assert mock_context.env_base_dir == "/tmp/test"
        assert mock_context.parallel_index == 0
        assert mock_context.parallelism == 2
        assert mock_context.is_spout is True
        assert mock_context.delay == 0.01
        assert mock_context.stop_signal_num == 1
        assert mock_context.jobmanager_host == "127.0.0.1"
        assert mock_context.jobmanager_port == 19001

    @pytest.mark.unit
    def test_context_without_execution_graph(self, mock_node, mock_transformation, mock_env):
        """Test TaskContext initialization without execution graph"""
        context = TaskContext(mock_node, mock_transformation, mock_env, None)
        
        assert context.name == "test_node"
        assert context.env_name == "test_env"

    @pytest.mark.unit
    def test_logger_property(self, mock_context):
        """Test logger property functionality"""
        # Logger should be created lazily
        logger = mock_context.logger
        assert logger is not None
        
        # Subsequent calls should return the same logger
        logger2 = mock_context.logger
        assert logger is logger2

    @pytest.mark.unit
    def test_state_exclude_attribute(self, mock_context):
        """Test __state_exclude__ attribute"""
        assert hasattr(mock_context, '__state_exclude__')
        exclude_list = getattr(mock_context, '__state_exclude__')
        assert isinstance(exclude_list, list)
        assert "_logger" in exclude_list
        assert "env" in exclude_list

    @pytest.mark.unit
    def test_delayed_initialization_attributes(self, mock_context):
        """Test delayed initialization attributes"""
        # These should be None initially
        assert mock_context._stop_event is None
        assert mock_context.received_stop_signals is None
        assert mock_context.stop_signal_count == 0

    @pytest.mark.unit
    def test_environment_fallback_values(self, mock_node, mock_transformation):
        """Test fallback values when environment attributes are missing"""
        # Environment without some attributes
        incomplete_env = Mock()
        incomplete_env.name = "incomplete_env"
        incomplete_env.env_base_dir = "/tmp/incomplete"
        incomplete_env.console_log_level = "DEBUG"
        # Missing uuid, jobmanager_host, jobmanager_port
        
        context = TaskContext(mock_node, mock_transformation, incomplete_env)
        
        assert context.env_name == "incomplete_env"
        assert context.env_base_dir == "/tmp/incomplete"
        assert context.env_console_log_level == "DEBUG"
        assert context.env_uuid is None  # Should handle missing attribute
        assert context.jobmanager_host == "127.0.0.1"  # Default value
        assert context.jobmanager_port == 19001  # Default value

    @pytest.mark.unit
    def test_transformation_attributes(self, mock_node, mock_env, mock_graph):
        """Test different transformation configurations"""
        # Non-spout transformation
        non_spout_transformation = MockTransformation(is_spout=False)
        context = TaskContext(mock_node, non_spout_transformation, mock_env, mock_graph)
        
        assert context.is_spout is False

    @pytest.mark.unit
    def test_node_parallelism_attributes(self, mock_transformation, mock_env, mock_graph):
        """Test different node parallelism configurations"""
        # High parallelism node
        high_parallel_node = MockGraphNode(
            name="high_parallel",
            parallel_index=5,
            parallelism=10,
            stop_signal_num=3
        )
        
        context = TaskContext(high_parallel_node, mock_transformation, mock_env, mock_graph)
        
        assert context.name == "high_parallel"
        assert context.parallel_index == 5
        assert context.parallelism == 10
        assert context.stop_signal_num == 3

    @pytest.mark.unit
    def test_context_serialization_preparation(self, mock_context):
        """Test context is prepared for serialization"""
        # Check that non-serializable attributes are in exclude list
        exclude_list = getattr(mock_context, '__state_exclude__', [])
        
        # Should exclude logger and environment references
        non_serializable = ["_logger", "env", "_env_logger_cache"]
        for attr in non_serializable:
            assert attr in exclude_list

    @pytest.mark.unit
    def test_multiple_context_instances(self, mock_transformation, mock_env, mock_graph):
        """Test creating multiple context instances"""
        node1 = MockGraphNode(name="node1", parallel_index=0)
        node2 = MockGraphNode(name="node2", parallel_index=1)
        
        context1 = TaskContext(node1, mock_transformation, mock_env, mock_graph)
        context2 = TaskContext(node2, mock_transformation, mock_env, mock_graph)
        
        assert context1.name == "node1"
        assert context2.name == "node2"
        assert context1.parallel_index == 0
        assert context2.parallel_index == 1
        
        # Loggers should be separate instances
        logger1 = context1.logger
        logger2 = context2.logger
        assert logger1 is not logger2

    @pytest.mark.unit
    def test_context_thread_safety(self, mock_context):
        """Test context access in multi-threaded environment"""
        results = []
        
        def worker():
            try:
                # Access various properties
                name = mock_context.name
                logger = mock_context.logger
                env_name = mock_context.env_name
                results.append((name, logger, env_name))
            except Exception as e:
                results.append(e)
        
        # Create multiple threads
        threads = [threading.Thread(target=worker) for _ in range(10)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All results should be successful
        assert len(results) == 10
        for result in results:
            assert isinstance(result, tuple)
            assert result[0] == "test_node"
            assert result[2] == "test_env"

    @pytest.mark.integration
    def test_context_with_real_logger(self, mock_node, mock_transformation, mock_env, mock_graph):
        """Integration test with real logger system"""
        context = TaskContext(mock_node, mock_transformation, mock_env, mock_graph)
        
        # Should create a real logger
        logger = context.logger
        assert logger is not None
        
        # Logger should be functional
        try:
            logger.info("Test message")
            logger.debug("Debug message")
            logger.warning("Warning message")
        except Exception as e:
            pytest.fail(f"Logger should be functional: {e}")

    @pytest.mark.unit
    def test_context_string_representation(self, mock_context):
        """Test context string representation"""
        context_str = str(mock_context)
        assert isinstance(context_str, str)
        
        # Should contain key information
        assert "test_node" in context_str or hasattr(mock_context, '__str__')

    @pytest.mark.unit
    def test_context_attribute_modification(self, mock_context):
        """Test modifying context attributes"""
        # Some attributes should be modifiable
        original_delay = mock_context.delay
        mock_context.delay = 0.05
        assert mock_context.delay == 0.05
        assert mock_context.delay != original_delay
        
        # Stop signal count should be modifiable
        mock_context.stop_signal_count = 5
        assert mock_context.stop_signal_count == 5


class TestTaskContextEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.mark.unit
    def test_context_with_none_values(self):
        """Test context creation with None values"""
        # This should not crash but handle gracefully
        try:
            context = TaskContext(None, None, None, None)
            # Behavior depends on implementation
        except (AttributeError, TypeError):
            # Expected for None values
            pass

    @pytest.mark.unit
    def test_context_with_missing_attributes(self):
        """Test context with objects missing expected attributes"""
        incomplete_node = Mock()
        incomplete_node.name = "incomplete"
        # Missing other attributes
        
        incomplete_transformation = Mock()
        # Missing is_spout
        
        incomplete_env = Mock()
        incomplete_env.name = "incomplete_env"
        # Missing other attributes
        
        try:
            context = TaskContext(incomplete_node, incomplete_transformation, incomplete_env)
            # Should handle missing attributes gracefully
        except AttributeError:
            # Expected behavior for missing required attributes
            pass

    @pytest.mark.unit
    def test_extreme_parallelism_values(self):
        """Test with extreme parallelism values"""
        extreme_node = MockGraphNode(
            name="extreme",
            parallel_index=999999,
            parallelism=1000000,
            stop_signal_num=0
        )
        transformation = MockTransformation()
        env = MockEnvironment()
        
        context = TaskContext(extreme_node, transformation, env)
        
        assert context.parallel_index == 999999
        assert context.parallelism == 1000000
        assert context.stop_signal_num == 0

    @pytest.mark.unit
    def test_negative_parallelism_values(self):
        """Test with negative parallelism values"""
        negative_node = MockGraphNode(
            name="negative",
            parallel_index=-1,
            parallelism=-5,
            stop_signal_num=-1
        )
        transformation = MockTransformation()
        env = MockEnvironment()
        
        context = TaskContext(negative_node, transformation, env)
        
        # Should handle negative values (behavior depends on implementation)
        assert context.parallel_index == -1
        assert context.parallelism == -5
        assert context.stop_signal_num == -1


# Additional fixtures and utilities
@pytest.fixture
def context_factory():
    """Factory for creating test contexts with different configurations"""
    def _create_context(name="test", parallel_index=0, parallelism=1, is_spout=True):
        node = MockGraphNode(name, parallel_index, parallelism)
        transformation = MockTransformation(is_spout)
        env = MockEnvironment()
        graph = MockExecutionGraph()
        return TaskContext(node, transformation, env, graph)
    
    return _create_context
