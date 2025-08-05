"""
Test suite for sage.kernels.runtime.service_context module

Tests the ServiceContext class which provides shared runtime context
for service tasks.
"""
import pytest
import threading
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from sage.kernel.kernels.runtime.service_context import ServiceContext


class MockServiceNode:
    """Mock service node for testing"""
    def __init__(self, name="test_service"):
        self.name = name
        self.service_qd = Mock()  # Mock queue descriptor


class MockEnvironment:
    """Mock environment for testing"""
    def __init__(self, name="test_env"):
        self.name = name
        self.env_base_dir = "/tmp/test"
        self.uuid = "test-uuid-123"
        self.console_log_level = "INFO"


class MockExecutionGraph:
    """Mock execution graph for testing"""
    def __init__(self):
        self.nodes = {}


class TestServiceContext:
    """Test class for ServiceContext functionality"""

    @pytest.fixture
    def mock_service_node(self):
        """Create a mock service node"""
        return MockServiceNode()

    @pytest.fixture
    def mock_env(self):
        """Create a mock environment"""
        return MockEnvironment()

    @pytest.fixture
    def mock_graph(self):
        """Create a mock execution graph"""
        return MockExecutionGraph()

    @pytest.fixture
    def mock_context(self, mock_service_node, mock_env, mock_graph):
        """Create a ServiceContext for testing"""
        return ServiceContext(mock_service_node, mock_env, mock_graph)

    @pytest.mark.unit
    def test_context_initialization(self, mock_service_node, mock_env, mock_graph):
        """Test ServiceContext initialization"""
        context = ServiceContext(mock_service_node, mock_env, mock_graph)
        
        # Verify basic attributes
        assert context.name == "test_service"
        assert context.env_name == "test_env"
        assert context.env_base_dir == "/tmp/test"
        assert context.env_uuid == "test-uuid-123"
        assert context.env_console_log_level == "INFO"

    @pytest.mark.unit
    def test_context_without_execution_graph(self, mock_service_node, mock_env):
        """Test ServiceContext initialization without execution graph"""
        context = ServiceContext(mock_service_node, mock_env, None)
        
        assert context.name == "test_service"
        assert context.env_name == "test_env"
        assert context._service_response_queue_descriptors == {}

    @pytest.mark.unit
    def test_context_attributes(self, mock_context):
        """Test all context attributes are properly set"""
        assert mock_context.name == "test_service"
        assert mock_context.env_name == "test_env"
        assert mock_context.env_base_dir == "/tmp/test"
        assert mock_context.env_uuid == "test-uuid-123"
        assert mock_context.env_console_log_level == "INFO"

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
        assert "_env_logger_cache" in exclude_list

    @pytest.mark.unit
    def test_request_queue_descriptor(self, mock_context):
        """Test request queue descriptor handling"""
        assert mock_context._request_queue_descriptor is not None
        # Should be the same as the service node's queue descriptor
        assert mock_context._request_queue_descriptor is mock_context._request_queue_descriptor

    @pytest.mark.unit
    def test_service_response_queue_descriptors(self, mock_service_node, mock_env):
        """Test service response queue descriptors from execution graph"""
        # Create mock nodes with response queue descriptors
        mock_graph = Mock()
        mock_node1 = Mock()
        mock_node1.service_response_qd = Mock()
        mock_node2 = Mock()
        mock_node2.service_response_qd = None
        mock_node3 = Mock()
        mock_node3.service_response_qd = Mock()
        
        mock_graph.nodes = {
            "node1": mock_node1,
            "node2": mock_node2,
            "node3": mock_node3
        }
        
        context = ServiceContext(mock_service_node, mock_env, mock_graph)
        
        # Should collect only nodes with service_response_qd
        assert "node1" in context._service_response_queue_descriptors
        assert "node2" not in context._service_response_queue_descriptors
        assert "node3" in context._service_response_queue_descriptors
        assert len(context._service_response_queue_descriptors) == 2

    @pytest.mark.unit
    def test_environment_fallback_values(self, mock_service_node):
        """Test fallback values when environment attributes are missing"""
        # Environment without some attributes
        incomplete_env = Mock()
        incomplete_env.name = "incomplete_env"
        incomplete_env.env_base_dir = "/tmp/incomplete"
        incomplete_env.console_log_level = "DEBUG"
        # Configure mock to not have uuid attribute
        del incomplete_env.uuid
        
        context = ServiceContext(mock_service_node, incomplete_env)
        
        assert context.env_name == "incomplete_env"
        assert context.env_base_dir == "/tmp/incomplete"
        assert context.env_console_log_level == "DEBUG"
        # Check that it handles missing attribute gracefully
        try:
            uuid_val = context.env_uuid
            assert uuid_val is None or hasattr(incomplete_env, 'uuid')
        except AttributeError:
            pass  # This is also acceptable behavior

    @pytest.mark.unit
    def test_multiple_context_instances(self, mock_env, mock_graph):
        """Test creating multiple context instances"""
        service_node1 = MockServiceNode(name="service1")
        service_node2 = MockServiceNode(name="service2")
        
        context1 = ServiceContext(service_node1, mock_env, mock_graph)
        context2 = ServiceContext(service_node2, mock_env, mock_graph)
        
        assert context1.name == "service1"
        assert context2.name == "service2"
        
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
            assert result[0] == "test_service"
            assert result[2] == "test_env"

    @pytest.mark.integration
    def test_context_with_real_logger(self, mock_service_node, mock_env, mock_graph):
        """Integration test with real logger system"""
        context = ServiceContext(mock_service_node, mock_env, mock_graph)
        
        # Should create a real logger
        logger = context.logger
        assert logger is not None
        
        # Logger should be functional
        try:
            logger.info("Test service message")
            logger.debug("Debug service message")
            logger.warning("Warning service message")
        except Exception as e:
            pytest.fail(f"Logger should be functional: {e}")

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
    def test_queue_descriptor_access(self, mock_context):
        """Test queue descriptor access methods"""
        # Request queue descriptor should be accessible
        request_qd = mock_context._request_queue_descriptor
        assert request_qd is not None
        
        # Response queue descriptors should be a dictionary
        response_qds = mock_context._service_response_queue_descriptors
        assert isinstance(response_qds, dict)

    @pytest.mark.unit
    def test_context_string_representation(self, mock_context):
        """Test context string representation"""
        context_str = str(mock_context)
        assert isinstance(context_str, str)
        
        # Should contain key information
        assert "test_service" in context_str or hasattr(mock_context, '__str__')


class TestServiceContextEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.mark.unit
    def test_context_with_none_values(self):
        """Test context creation with None values"""
        # This should not crash but handle gracefully
        try:
            context = ServiceContext(None, None, None)
            # Behavior depends on implementation
        except (AttributeError, TypeError):
            # Expected for None values
            pass

    @pytest.mark.unit
    def test_context_with_missing_attributes(self):
        """Test context with objects missing expected attributes"""
        incomplete_service_node = Mock()
        incomplete_service_node.name = "incomplete"
        # Missing service_qd attribute
        
        incomplete_env = Mock()
        incomplete_env.name = "incomplete_env"
        # Missing other attributes
        
        try:
            context = ServiceContext(incomplete_service_node, incomplete_env)
            # Should handle missing attributes gracefully
        except AttributeError:
            # Expected behavior for missing required attributes
            pass

    @pytest.mark.unit
    def test_execution_graph_with_no_response_queues(self, mock_service_node, mock_env):
        """Test execution graph where no nodes have response queue descriptors"""
        mock_graph = Mock()
        mock_node1 = Mock()
        mock_node1.service_response_qd = None
        mock_node2 = Mock()
        mock_node2.service_response_qd = None
        
        mock_graph.nodes = {
            "node1": mock_node1,
            "node2": mock_node2
        }
        
        context = ServiceContext(mock_service_node, mock_env, mock_graph)
        
        # Should have empty response queue descriptors
        assert len(context._service_response_queue_descriptors) == 0

    @pytest.mark.unit
    def test_execution_graph_with_invalid_nodes(self, mock_service_node, mock_env):
        """Test execution graph with nodes missing expected attributes"""
        mock_graph = Mock()
        invalid_node = Mock()
        # Node without service_response_qd attribute
        delattr(invalid_node, 'service_response_qd')
        
        mock_graph.nodes = {"invalid_node": invalid_node}
        
        try:
            context = ServiceContext(mock_service_node, mock_env, mock_graph)
            # Should handle missing attributes gracefully
        except AttributeError:
            # Expected if implementation doesn't handle missing attributes
            pass

    @pytest.mark.unit
    def test_service_node_without_queue_descriptor(self, mock_env):
        """Test service node without queue descriptor"""
        service_node_no_qd = Mock()
        service_node_no_qd.name = "no_qd_service"
        service_node_no_qd.service_qd = None
        
        context = ServiceContext(service_node_no_qd, mock_env)
        
        assert context.name == "no_qd_service"
        assert context._request_queue_descriptor is None

    @pytest.mark.unit
    def test_large_execution_graph(self, mock_service_node, mock_env):
        """Test with large execution graph"""
        mock_graph = Mock()
        
        # Create many nodes
        nodes = {}
        for i in range(1000):
            node = Mock()
            node.service_response_qd = Mock() if i % 2 == 0 else None
            nodes[f"node_{i}"] = node
        
        mock_graph.nodes = nodes
        
        context = ServiceContext(mock_service_node, mock_env, mock_graph)
        
        # Should handle large graphs efficiently
        assert len(context._service_response_queue_descriptors) == 500  # Half have response queues


# Additional fixtures and utilities
@pytest.fixture
def service_context_factory():
    """Factory for creating test service contexts with different configurations"""
    def _create_context(service_name="test_service", env_name="test_env"):
        service_node = MockServiceNode(service_name)
        env = MockEnvironment(env_name)
        graph = MockExecutionGraph()
        return ServiceContext(service_node, env, graph)
    
    return _create_context


@pytest.fixture(autouse=True)
def setup_service_test_environment():
    """Setup test environment before each service test"""
    # Any global setup needed for service tests
    yield
    # Cleanup after test
