"""
Unit tests for RayServiceTask.

Tests the Ray distributed service task implementation that extends BaseServiceTask
with Ray actor support.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock Ray before importing
mock_ray = MagicMock()
mock_ray.remote = lambda cls: cls  # Make @ray.remote decorator a no-op
mock_ray_queue = MagicMock()

sys.modules["ray"] = mock_ray
sys.modules["ray.util"] = MagicMock()
sys.modules["ray.util.queue"] = mock_ray_queue

from sage.kernel.runtime.service.ray_service_task import RayServiceTask

# Mock classes for testing


class MockServiceClass:
    """Mock service class for testing."""

    def __init__(self, ctx=None):
        self.ctx = ctx
        self.setup_called = False
        self.cleanup_called = False
        self.started = False
        self.stopped = False

    def setup(self):
        """Mock setup method."""
        self.setup_called = True

    def cleanup(self):
        """Mock cleanup method."""
        self.cleanup_called = True

    def start_running(self):
        """Mock start_running method."""
        self.started = True

    def start(self):
        """Mock start method."""
        self.started = True

    def stop(self):
        """Mock stop method."""
        self.stopped = True

    def test_method(self, arg1, arg2=None):
        """Mock service method."""
        return f"ray_result: {arg1}, {arg2}"


class MockServiceFactory:
    """Mock service factory for testing."""

    def __init__(self, service_name="ray_test_service", service_class=None):
        self.service_name = service_name
        self.service_class = service_class or MockServiceClass

    def create_service(self, ctx):
        """Create a mock service instance."""
        return self.service_class(ctx)


class MockServiceContext:
    """Mock service context for testing."""

    def __init__(self, enable_monitoring=False):
        self.name = "ray_test_context"
        self.enable_monitoring = enable_monitoring
        self.metrics_window_size = 100
        self.enable_detailed_tracking = True
        self.resource_sampling_interval = 1.0
        self.enable_auto_report = False
        self.logger = MagicMock()

        # Queue descriptors
        self._request_queue_descriptor = None
        self._response_queue_descriptors = {}

    def get_request_queue_descriptor(self):
        """Get request queue descriptor."""
        return self._request_queue_descriptor

    def get_service_response_queue_descriptor(self, node_name):
        """Get response queue descriptor for a node."""
        return self._response_queue_descriptors.get(node_name)

    def get_service_response_queue_descriptors(self):
        """Get all response queue descriptors."""
        return self._response_queue_descriptors


# Fixtures


@pytest.fixture
def mock_ray():
    """Mock Ray module."""
    with patch("sage.kernel.runtime.service.ray_service_task.ray") as mock:
        mock.is_initialized.return_value = True
        mock_context = MagicMock()
        mock_context.node_id.hex.return_value = "test_node_123"
        mock.get_runtime_context.return_value = mock_context
        yield mock


@pytest.fixture
def mock_ray_queue():
    """Mock Ray Queue class."""
    with patch("sage.kernel.runtime.service.ray_service_task.RayQueue") as mock_queue_class:
        # Create a mock queue instance
        mock_queue_instance = MagicMock()
        mock_queue_instance.get.return_value = None
        mock_queue_instance.put.return_value = None
        mock_queue_class.return_value = mock_queue_instance
        yield mock_queue_class


@pytest.fixture
def mock_ray_queue_available():
    """Mock RAY_QUEUE_AVAILABLE flag."""
    with patch("sage.kernel.runtime.service.ray_service_task.RAY_QUEUE_AVAILABLE", True):
        yield


@pytest.fixture
def mock_service_factory():
    """Create a mock service factory."""
    return MockServiceFactory()


@pytest.fixture
def mock_service_context():
    """Create a mock service context."""
    return MockServiceContext()


# Test Cases


@pytest.mark.unit
class TestRayServiceTaskInitialization:
    """Test RayServiceTask initialization."""

    def test_initialization_with_context(
        self, mock_ray, mock_service_factory, mock_service_context
    ):
        """Test Ray service task initialization with context."""
        task = RayServiceTask(mock_service_factory, mock_service_context)

        assert task.service_factory == mock_service_factory
        assert task.service_name == "ray_test_service"
        assert task.ctx == mock_service_context
        assert task.service_instance is not None
        assert task.service == task.service_instance

        task.cleanup()

    def test_initialization_calls_service_setup(
        self, mock_ray, mock_service_factory, mock_service_context
    ):
        """Test Ray service task initialization calls service setup method."""
        task = RayServiceTask(mock_service_factory, mock_service_context)

        assert task.service_instance.setup_called

        task.cleanup()


@pytest.mark.unit
class TestRayServiceTaskServiceInstanceManagement:
    """Test RayServiceTask service instance management."""

    def test_start_service_instance_with_start_running(
        self, mock_ray, mock_service_factory, mock_service_context
    ):
        """Test _start_service_instance calls start_running if available."""
        task = RayServiceTask(mock_service_factory, mock_service_context)

        task._start_service_instance()

        assert task.service_instance.started

        task.cleanup()

    def test_start_service_instance_with_start(self, mock_ray, mock_service_context):
        """Test _start_service_instance calls start if start_running not available."""

        class ServiceWithStart:
            def __init__(self, ctx):
                self.ctx = ctx
                self.started = False

            def setup(self):
                pass

            def start(self):
                self.started = True

            def cleanup(self):
                pass

        factory = MockServiceFactory(service_class=ServiceWithStart)
        task = RayServiceTask(factory, mock_service_context)

        task._start_service_instance()

        assert task.service_instance.started

        task.cleanup()

    def test_stop_service_instance(self, mock_ray, mock_service_factory, mock_service_context):
        """Test _stop_service_instance calls stop method."""
        task = RayServiceTask(mock_service_factory, mock_service_context)

        task._stop_service_instance()

        assert task.service_instance.stopped

        task.cleanup()


@pytest.mark.unit
class TestRayServiceTaskQueueManagement:
    """Test RayServiceTask Ray queue management."""

    def test_create_request_queue(
        self,
        mock_ray,
        mock_ray_queue_available,
        mock_ray_queue,
        mock_service_factory,
        mock_service_context,
    ):
        """Test _create_request_queue creates Ray queue."""
        task = RayServiceTask(mock_service_factory, mock_service_context)

        queue = task._create_request_queue()

        assert queue is not None
        mock_ray_queue.assert_called_once_with(maxsize=10000)

        task.cleanup()

    def test_create_request_queue_without_ray_queue_raises_error(
        self, mock_ray, mock_service_factory, mock_service_context
    ):
        """Test _create_request_queue raises error when Ray queue not available."""
        with patch("sage.kernel.runtime.service.ray_service_task.RAY_QUEUE_AVAILABLE", False):
            task = RayServiceTask(mock_service_factory, mock_service_context)

            with pytest.raises(RuntimeError, match="Ray queue is not available"):
                task._create_request_queue()

            task.cleanup()

    def test_create_response_queue(
        self,
        mock_ray,
        mock_ray_queue_available,
        mock_ray_queue,
        mock_service_factory,
        mock_service_context,
    ):
        """Test _create_response_queue creates Ray queue."""
        task = RayServiceTask(mock_service_factory, mock_service_context)

        queue = task._create_response_queue("node1")

        assert queue is not None
        mock_ray_queue.assert_called_once_with(maxsize=10000)

        task.cleanup()

    def test_create_response_queue_without_ray_queue_raises_error(
        self, mock_ray, mock_service_factory, mock_service_context
    ):
        """Test _create_response_queue raises error when Ray queue not available."""
        with patch("sage.kernel.runtime.service.ray_service_task.RAY_QUEUE_AVAILABLE", False):
            task = RayServiceTask(mock_service_factory, mock_service_context)

            with pytest.raises(RuntimeError, match="Ray queue is not available"):
                task._create_response_queue("node1")

            task.cleanup()


@pytest.mark.unit
class TestRayServiceTaskQueueOperations:
    """Test RayServiceTask queue operations."""

    def test_queue_get(self, mock_ray, mock_service_factory, mock_service_context):
        """Test _queue_get retrieves data from Ray queue."""
        task = RayServiceTask(mock_service_factory, mock_service_context)

        mock_queue = MagicMock()
        mock_queue.get.return_value = {"data": "test"}

        result = task._queue_get(mock_queue, timeout=2.0)

        assert result == {"data": "test"}
        mock_queue.get.assert_called_once_with(timeout=2.0)

        task.cleanup()

    def test_queue_put(self, mock_ray, mock_service_factory, mock_service_context):
        """Test _queue_put sends data to Ray queue."""
        task = RayServiceTask(mock_service_factory, mock_service_context)

        mock_queue = MagicMock()
        data = {"request": "test"}

        task._queue_put(mock_queue, data, timeout=3.0)

        mock_queue.put.assert_called_once_with(data, timeout=3.0)

        task.cleanup()

    def test_queue_close_with_shutdown(self, mock_ray, mock_service_factory, mock_service_context):
        """Test _queue_close calls shutdown if available."""
        task = RayServiceTask(mock_service_factory, mock_service_context)

        mock_queue = MagicMock()
        mock_queue.shutdown = MagicMock()

        task._queue_close(mock_queue)

        mock_queue.shutdown.assert_called_once()

        task.cleanup()

    def test_queue_close_with_close(self, mock_ray, mock_service_factory, mock_service_context):
        """Test _queue_close calls close if shutdown not available."""
        task = RayServiceTask(mock_service_factory, mock_service_context)

        mock_queue = MagicMock()
        del mock_queue.shutdown
        mock_queue.close = MagicMock()

        task._queue_close(mock_queue)

        mock_queue.close.assert_called_once()

        task.cleanup()


@pytest.mark.unit
class TestRayServiceTaskStatistics:
    """Test RayServiceTask statistics."""

    def test_get_statistics_includes_ray_info(
        self, mock_ray, mock_service_factory, mock_service_context
    ):
        """Test get_statistics includes Ray-specific information."""
        mock_ray.is_initialized.return_value = True
        mock_context = MagicMock()
        mock_context.node_id.hex.return_value = "node_abc123"
        mock_ray.get_runtime_context.return_value = mock_context

        task = RayServiceTask(mock_service_factory, mock_service_context)

        stats = task.get_statistics()

        assert "actor_id" in stats
        assert stats["actor_id"] == "ray_actor_ray_test_service"
        assert "ray_node_id" in stats
        assert stats["ray_node_id"] == "node_abc123"
        assert stats["service_name"] == "ray_test_service"

        task.cleanup()

    def test_get_statistics_when_ray_not_initialized(
        self, mock_ray, mock_service_factory, mock_service_context
    ):
        """Test get_statistics when Ray is not initialized."""
        mock_ray.is_initialized.return_value = False

        task = RayServiceTask(mock_service_factory, mock_service_context)

        stats = task.get_statistics()

        assert "ray_node_id" in stats
        assert stats["ray_node_id"] == "unknown"

        task.cleanup()


@pytest.mark.unit
class TestRayServiceTaskMethodCalling:
    """Test RayServiceTask method calling (inherited from BaseServiceTask)."""

    def test_call_method_success(self, mock_ray, mock_service_factory, mock_service_context):
        """Test calling a service method successfully."""
        task = RayServiceTask(mock_service_factory, mock_service_context)

        result = task.call_method("test_method", "ray_arg1", arg2="ray_value2")

        assert result == "ray_result: ray_arg1, ray_value2"
        assert task._request_count == 1

        task.cleanup()


@pytest.mark.unit
class TestRayServiceTaskLifecycle:
    """Test RayServiceTask lifecycle (inherited from BaseServiceTask)."""

    def test_start_running(self, mock_ray, mock_service_factory, mock_service_context):
        """Test start_running method starts service instance."""
        # Set up queue descriptor
        mock_descriptor = MagicMock()
        mock_descriptor.queue_instance = MagicMock()
        mock_service_context._request_queue_descriptor = mock_descriptor

        task = RayServiceTask(mock_service_factory, mock_service_context)

        task.start_running()

        assert task.is_running
        assert task.service_instance.started

        task.cleanup()

    def test_stop(self, mock_ray, mock_service_factory, mock_service_context):
        """Test stop method stops service instance."""
        # Set up queue descriptor
        mock_descriptor = MagicMock()
        mock_descriptor.queue_instance = MagicMock()
        mock_service_context._request_queue_descriptor = mock_descriptor

        task = RayServiceTask(mock_service_factory, mock_service_context)
        task.start_running()

        task.stop()

        assert not task.is_running
        assert task.service_instance.stopped

        task.cleanup()


@pytest.mark.unit
class TestRayServiceTaskCleanup:
    """Test RayServiceTask cleanup."""

    def test_cleanup_calls_service_cleanup(
        self, mock_ray, mock_service_factory, mock_service_context
    ):
        """Test cleanup calls service instance cleanup method."""
        task = RayServiceTask(mock_service_factory, mock_service_context)

        task.cleanup()

        assert task.service_instance.cleanup_called


@pytest.mark.unit
class TestRayServiceTaskDecoratorUsage:
    """Test RayServiceTask with Ray remote decorator."""

    def test_ray_remote_decorator_is_mocked(self, mock_ray):
        """Test that Ray decorator is properly mocked for testing."""
        # In our test environment, @ray.remote is a no-op
        # This allows us to test the class directly
        assert RayServiceTask is not None
        assert RayServiceTask.__name__ == "RayServiceTask"

    def test_can_instantiate_for_testing(self, mock_service_factory, mock_service_context):
        """Test that we can instantiate the class for testing."""
        task = RayServiceTask(mock_service_factory, mock_service_context)

        assert task is not None
        assert isinstance(task, RayServiceTask)

        task.cleanup()
