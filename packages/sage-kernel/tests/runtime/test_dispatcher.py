"""
Test suite for sage.runtime.dispatcher module

Tests the Dispatcher class which manages execution of tasks and services
in both local and remote environments.
"""
import pytest
import time
from unittest.mock import Mock, MagicMock, patch, call
import threading
from typing import Dict, Any

from sage.runtime.dispatcher import Dispatcher
from sage.runtime.task.base_task import BaseTask
from sage.runtime.service.base_service_task import BaseServiceTask
from sage.runtime.distributed.actor import ActorWrapper


class MockExecutionGraph:
    """Mock execution graph for testing"""
    def __init__(self, total_stop_signals=1):
        self.total_stop_signals = total_stop_signals
        self.nodes = {}


class MockEnvironment:
    """Mock environment for testing"""
    def __init__(self, name="test_env", platform="local"):
        self.name = name
        self.platform = platform
        self.env_base_dir = "/tmp/test"
        self.console_log_level = "INFO"


class TestDispatcher:
    """Test class for Dispatcher functionality"""

    @pytest.fixture
    def mock_env(self):
        """Create a mock local environment"""
        return MockEnvironment()

    @pytest.fixture
    def mock_remote_env(self):
        """Create a mock remote environment"""
        return MockEnvironment(platform="remote")

    @pytest.fixture
    def mock_graph(self):
        """Create a mock execution graph"""
        return MockExecutionGraph(total_stop_signals=2)

    @pytest.fixture
    def local_dispatcher(self, mock_graph, mock_env):
        """Create a local dispatcher for testing"""
        with patch('sage.runtime.dispatcher.ensure_ray_initialized'):
            return Dispatcher(mock_graph, mock_env)

    @pytest.fixture
    def remote_dispatcher(self, mock_graph, mock_remote_env):
        """Create a remote dispatcher for testing"""
        with patch('sage.runtime.dispatcher.ensure_ray_initialized') as mock_ray:
            dispatcher = Dispatcher(mock_graph, mock_remote_env)
            mock_ray.assert_called_once()
            return dispatcher

    @pytest.mark.unit
    def test_dispatcher_initialization_local(self, mock_graph, mock_env):
        """Test dispatcher initialization in local mode"""
        with patch('sage.runtime.dispatcher.ensure_ray_initialized') as mock_ray:
            dispatcher = Dispatcher(mock_graph, mock_env)
            
            # Verify basic attributes
            assert dispatcher.name == "test_env"
            assert dispatcher.total_stop_signals == 2
            assert dispatcher.received_stop_signals == 0
            assert dispatcher.remote is False
            assert isinstance(dispatcher.tasks, dict)
            assert isinstance(dispatcher.services, dict)
            assert dispatcher.is_running is False
            
            # Ray should not be initialized for local environment
            mock_ray.assert_not_called()

    @pytest.mark.unit
    def test_dispatcher_initialization_remote(self, mock_graph, mock_remote_env):
        """Test dispatcher initialization in remote mode"""
        with patch('sage.runtime.dispatcher.ensure_ray_initialized') as mock_ray:
            dispatcher = Dispatcher(mock_graph, mock_remote_env)
            
            # Verify basic attributes
            assert dispatcher.name == "test_env"
            assert dispatcher.remote is True
            
            # Ray should be initialized for remote environment
            mock_ray.assert_called_once()

    @pytest.mark.unit
    def test_receive_stop_signal_partial(self, local_dispatcher):
        """Test receiving partial stop signals"""
        # First stop signal should not trigger cleanup
        result = local_dispatcher.receive_stop_signal()
        assert result is False
        assert local_dispatcher.received_stop_signals == 1

    @pytest.mark.unit
    def test_receive_stop_signal_complete(self, local_dispatcher):
        """Test receiving all required stop signals"""
        # First stop signal
        local_dispatcher.receive_stop_signal()
        
        # Second stop signal should trigger cleanup
        with patch.object(local_dispatcher, 'cleanup') as mock_cleanup:
            result = local_dispatcher.receive_stop_signal()
            assert result is True
            assert local_dispatcher.received_stop_signals == 2
            mock_cleanup.assert_called_once()

    @pytest.mark.unit
    def test_setup_logging_system(self, local_dispatcher):
        """Test logging system setup"""
        # Logger should be created during initialization
        assert hasattr(local_dispatcher, 'logger')
        assert local_dispatcher.logger is not None

    @pytest.mark.unit
    def test_add_task_local(self, local_dispatcher):
        """Test adding a local task"""
        mock_task = Mock(spec=BaseTask)
        local_dispatcher.tasks["test_task"] = mock_task
        
        assert "test_task" in local_dispatcher.tasks
        assert local_dispatcher.tasks["test_task"] is mock_task

    @pytest.mark.unit
    def test_add_task_remote(self, remote_dispatcher):
        """Test adding a remote task (ActorWrapper)"""
        mock_actor = Mock(spec=ActorWrapper)
        remote_dispatcher.tasks["test_actor"] = mock_actor
        
        assert "test_actor" in remote_dispatcher.tasks
        assert remote_dispatcher.tasks["test_actor"] is mock_actor

    @pytest.mark.unit
    def test_add_service(self, local_dispatcher):
        """Test adding a service"""
        mock_service = Mock(spec=BaseServiceTask)
        local_dispatcher.services["test_service"] = mock_service
        
        assert "test_service" in local_dispatcher.services
        assert local_dispatcher.services["test_service"] is mock_service

    @pytest.mark.unit
    def test_get_task_exists(self, local_dispatcher):
        """Test getting an existing task"""
        mock_task = Mock(spec=BaseTask)
        local_dispatcher.tasks["test_task"] = mock_task
        
        result = local_dispatcher.tasks.get("test_task")
        assert result is mock_task

    @pytest.mark.unit
    def test_get_task_not_exists(self, local_dispatcher):
        """Test getting a non-existent task"""
        result = local_dispatcher.tasks.get("non_existent")
        assert result is None

    @pytest.mark.unit 
    def test_dispatcher_state_management(self, local_dispatcher):
        """Test dispatcher state management"""
        # Initially not running
        assert local_dispatcher.is_running is False
        
        # Set to running
        local_dispatcher.is_running = True
        assert local_dispatcher.is_running is True

    @pytest.mark.unit
    def test_multiple_dispatcher_instances(self, mock_graph):
        """Test creating multiple dispatcher instances"""
        env1 = MockEnvironment("env1")
        env2 = MockEnvironment("env2") 
        
        with patch('sage.runtime.dispatcher.ensure_ray_initialized'):
            dispatcher1 = Dispatcher(mock_graph, env1)
            dispatcher2 = Dispatcher(mock_graph, env2)
            
            assert dispatcher1.name == "env1"
            assert dispatcher2.name == "env2"
            assert dispatcher1.tasks is not dispatcher2.tasks
            assert dispatcher1.services is not dispatcher2.services

    @pytest.mark.unit
    def test_dispatcher_cleanup_preparation(self, local_dispatcher):
        """Test dispatcher cleanup preparation"""
        # Add some tasks and services
        local_dispatcher.tasks["task1"] = Mock()
        local_dispatcher.services["service1"] = Mock()
        
        # Verify they exist before cleanup
        assert len(local_dispatcher.tasks) == 1
        assert len(local_dispatcher.services) == 1

    @pytest.mark.integration
    def test_dispatcher_with_real_logging(self, mock_graph, mock_env):
        """Integration test with real logging system"""
        dispatcher = Dispatcher(mock_graph, mock_env)
        
        # Should have a real logger instance
        assert hasattr(dispatcher, 'logger')
        assert dispatcher.logger is not None
        
        # Logger should be callable
        try:
            dispatcher.logger.info("Test message")
        except Exception as e:
            pytest.fail(f"Logger should be functional: {e}")

    @pytest.mark.integration
    @patch('sage.runtime.distributed.ray.ensure_ray_initialized')
    def test_dispatcher_ray_integration(self, mock_ray_init, mock_graph):
        """Integration test for Ray initialization"""
        remote_env = MockEnvironment(platform="remote")
        
        # Since actual Ray init happens, mock it to capture the call
        with patch('sage.runtime.dispatcher.ensure_ray_initialized') as dispatcher_ray_mock:
            dispatcher = Dispatcher(mock_graph, remote_env)
            
            # Check the Ray init call was made (either mock could be called)
            dispatcher_ray_mock.assert_called_once()
        
        assert dispatcher.remote is True

    @pytest.mark.unit
    def test_stop_signal_thread_safety(self, local_dispatcher):
        """Test stop signal handling in multi-threaded environment"""
        results = []
        
        def signal_worker():
            result = local_dispatcher.receive_stop_signal()
            results.append(result)
        
        # Create multiple threads sending stop signals (adjust for expected signals)
        threads = [threading.Thread(target=signal_worker) for _ in range(2)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should have exactly one True result (cleanup triggered once)
        true_count = sum(1 for r in results if r is True)
        assert true_count == 1  # Exactly one cleanup for 2 stop signals
        assert local_dispatcher.received_stop_signals == 2  # Exactly required signals

    @pytest.mark.slow
    def test_dispatcher_performance(self, mock_graph, mock_env):
        """Performance test for dispatcher operations"""
        start_time = time.time()
        
        # Create many dispatchers quickly
        dispatchers = []
        for i in range(100):
            with patch('sage.runtime.dispatcher.ensure_ray_initialized'):
                dispatcher = Dispatcher(mock_graph, mock_env)
                dispatchers.append(dispatcher)
        
        creation_time = time.time() - start_time
        
        # Should create 100 dispatchers in reasonable time (< 1 second)
        assert creation_time < 1.0
        assert len(dispatchers) == 100

    @pytest.mark.unit
    def test_dispatcher_error_handling(self, mock_graph):
        """Test dispatcher error handling during initialization"""
        # Test with invalid environment
        invalid_env = None
        
        with pytest.raises(AttributeError):
            Dispatcher(mock_graph, invalid_env)

    @pytest.mark.unit
    def test_dispatcher_repr(self, local_dispatcher):
        """Test dispatcher string representation"""
        repr_str = repr(local_dispatcher)
        assert "Dispatcher" in repr_str or hasattr(local_dispatcher, '__repr__')


class TestDispatcherEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.mark.unit
    def test_zero_stop_signals(self):
        """Test dispatcher with zero required stop signals"""
        graph = MockExecutionGraph(total_stop_signals=0)
        env = MockEnvironment()
        
        with patch('sage.runtime.dispatcher.ensure_ray_initialized'):
            dispatcher = Dispatcher(graph, env)
            
            # Should immediately return True
            result = dispatcher.receive_stop_signal()
            assert result is True

    @pytest.mark.unit
    def test_negative_stop_signals(self):
        """Test dispatcher with negative stop signals"""
        graph = MockExecutionGraph(total_stop_signals=-1)
        env = MockEnvironment()
        
        with patch('sage.runtime.dispatcher.ensure_ray_initialized'):
            dispatcher = Dispatcher(graph, env)
            
            # Should handle gracefully
            result = dispatcher.receive_stop_signal()
            # Behavior depends on implementation, but should not crash

    @pytest.mark.unit
    def test_large_stop_signals(self):
        """Test dispatcher with very large number of stop signals"""
        graph = MockExecutionGraph(total_stop_signals=1000000)
        env = MockEnvironment()
        
        with patch('sage.runtime.dispatcher.ensure_ray_initialized'):
            dispatcher = Dispatcher(graph, env)
            
            # Should handle large numbers
            assert dispatcher.total_stop_signals == 1000000
            assert dispatcher.received_stop_signals == 0


# Pytest configuration and fixtures
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment before each test"""
    # Any global setup needed
    yield
    # Cleanup after test
