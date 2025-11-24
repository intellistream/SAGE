"""
Unit tests for BaseServiceTask.

Tests the base class for service tasks providing unified service interface
and high-performance queue listening functionality.
"""

import queue
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from sage.kernel.runtime.service.base_service_task import BaseServiceTask

# Mock classes for testing


class MockServiceClass:
    """Mock service class for testing."""

    def __init__(self, ctx=None):
        self.ctx = ctx
        self.setup_called = False
        self.cleanup_called = False
        self.close_called = False
        self.started = False
        self.stopped = False

    def setup(self):
        """Mock setup method."""
        self.setup_called = True

    def cleanup(self):
        """Mock cleanup method."""
        self.cleanup_called = True

    def close(self):
        """Mock close method."""
        self.close_called = True

    def test_method(self, arg1, arg2=None):
        """Mock service method."""
        return f"result: {arg1}, {arg2}"

    def failing_method(self):
        """Mock method that raises an exception."""
        raise ValueError("Service method failed")

    @property
    def test_property(self):
        """Mock service property."""
        return "test_value"


class MockServiceFactory:
    """Mock service factory for testing."""

    def __init__(self, service_name="test_service", service_class=None):
        self.service_name = service_name
        self.service_class = service_class or MockServiceClass

    def create_service(self, ctx):
        """Create a mock service instance."""
        return self.service_class(ctx)


class MockServiceContext:
    """Mock service context for testing."""

    def __init__(self, enable_monitoring=False):
        self.name = "test_context"
        self.enable_monitoring = enable_monitoring
        self.metrics_window_size = 100
        self.enable_detailed_tracking = True
        self.resource_sampling_interval = 1.0
        self.enable_auto_report = False
        self.logger = MagicMock()

        # Queue descriptors
        self._request_queue = queue.Queue()
        self._response_queues = {}

    def get_request_queue_descriptor(self):
        """Get request queue descriptor."""
        descriptor = MagicMock()
        descriptor.queue_instance = self._request_queue
        descriptor.queue_id = "request_queue"
        descriptor.queue_type = "python_queue"
        return descriptor

    def get_service_response_queue_descriptor(self, node_name):
        """Get response queue descriptor for a node."""
        if node_name not in self._response_queues:
            self._response_queues[node_name] = queue.Queue()
        descriptor = MagicMock()
        descriptor.queue_instance = self._response_queues[node_name]
        descriptor.queue_id = f"response_queue_{node_name}"
        descriptor.queue_type = "python_queue"
        return descriptor

    def get_service_response_queue_descriptors(self):
        """Get all response queue descriptors."""
        return {
            name: self.get_service_response_queue_descriptor(name) for name in self._response_queues
        }

    def add_response_queue(self, node_name):
        """Add a response queue for a node."""
        self._response_queues[node_name] = queue.Queue()


class ConcreteServiceTask(BaseServiceTask):
    """Concrete implementation of BaseServiceTask for testing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service_instance_started = False
        self.service_instance_stopped = False

    def _start_service_instance(self):
        """Start service instance (concrete implementation)."""
        self.service_instance_started = True
        if hasattr(self.service_instance, "started"):
            self.service_instance.started = True

    def _stop_service_instance(self):
        """Stop service instance (concrete implementation)."""
        self.service_instance_stopped = True
        if hasattr(self.service_instance, "stopped"):
            self.service_instance.stopped = True


# Fixtures


@pytest.fixture
def mock_service_factory():
    """Create a mock service factory."""
    return MockServiceFactory()


@pytest.fixture
def mock_service_context():
    """Create a mock service context."""
    return MockServiceContext()


@pytest.fixture
def service_task(mock_service_factory, mock_service_context):
    """Create a concrete service task instance."""
    task = ConcreteServiceTask(mock_service_factory, mock_service_context)
    yield task
    task.cleanup()


# Test Cases


@pytest.mark.unit
class TestBaseServiceTaskInitialization:
    """Test BaseServiceTask initialization."""

    def test_initialization_with_context(self, mock_service_factory, mock_service_context):
        """Test service task initialization with context."""
        task = ConcreteServiceTask(mock_service_factory, mock_service_context)

        assert task.service_factory == mock_service_factory
        assert task.service_name == "test_service"
        assert task.ctx == mock_service_context
        assert task.service_instance is not None
        assert task.service == task.service_instance
        assert not task.is_running
        assert task._request_count == 0
        assert task._error_count == 0

        task.cleanup()

    def test_initialization_without_context_raises_error(self, mock_service_factory):
        """Test service task initialization without context raises error."""
        with pytest.raises(ValueError, match="ServiceContext is required"):
            ConcreteServiceTask(mock_service_factory, None)

    def test_initialization_calls_service_setup(self, mock_service_factory, mock_service_context):
        """Test service task initialization calls service setup method."""
        task = ConcreteServiceTask(mock_service_factory, mock_service_context)

        assert task.service_instance.setup_called

        task.cleanup()

    def test_initialization_injects_context_to_service(
        self, mock_service_factory, mock_service_context
    ):
        """Test service task initialization injects context to service instance."""
        task = ConcreteServiceTask(mock_service_factory, mock_service_context)

        assert hasattr(task.service_instance, "ctx")
        assert task.service_instance.ctx == mock_service_context

        task.cleanup()

    def test_logger_property(self, service_task):
        """Test logger property returns context logger."""
        assert service_task.logger == service_task.ctx.logger

    def test_name_property(self, service_task):
        """Test name property returns context name."""
        assert service_task.name == service_task.ctx.name


@pytest.mark.unit
class TestBaseServiceTaskQueueManagement:
    """Test BaseServiceTask queue management."""

    def test_request_queue_descriptor_property(self, service_task):
        """Test request_queue_descriptor property."""
        descriptor = service_task.request_queue_descriptor

        assert descriptor is not None
        assert descriptor.queue_id == "request_queue"

    def test_request_queue_property(self, service_task):
        """Test request_queue property."""
        request_queue = service_task.request_queue

        assert request_queue is not None
        assert isinstance(request_queue, queue.Queue)

    def test_get_response_queue_descriptor(self, service_task, mock_service_context):
        """Test get_response_queue_descriptor method."""
        mock_service_context.add_response_queue("node1")
        descriptor = service_task.get_response_queue_descriptor("node1")

        assert descriptor is not None
        assert descriptor.queue_id == "response_queue_node1"

    def test_get_response_queue(self, service_task, mock_service_context):
        """Test get_response_queue method."""
        mock_service_context.add_response_queue("node1")
        response_queue = service_task.get_response_queue("node1")

        assert response_queue is not None
        assert isinstance(response_queue, queue.Queue)


@pytest.mark.unit
class TestBaseServiceTaskLifecycle:
    """Test BaseServiceTask lifecycle management."""

    def test_start_running(self, service_task):
        """Test start_running method."""
        service_task.start_running()

        assert service_task.is_running
        assert service_task.service_instance_started
        assert service_task._queue_listener_thread is not None
        assert service_task._queue_listener_running

    def test_start_running_already_running(self, service_task):
        """Test start_running when already running logs warning."""
        service_task.start_running()
        assert service_task.is_running

        # Start again
        service_task.start_running()
        # Should log warning but not fail
        assert service_task.is_running

    def test_stop(self, service_task):
        """Test stop method."""
        service_task.start_running()
        assert service_task.is_running

        service_task.stop()

        assert not service_task.is_running
        assert service_task.service_instance_stopped
        assert not service_task._queue_listener_running

    def test_stop_not_running(self, service_task):
        """Test stop when not running logs warning."""
        assert not service_task.is_running

        service_task.stop()
        # Should log warning but not fail
        assert not service_task.is_running

    def test_terminate(self, service_task):
        """Test terminate method."""
        service_task.start_running()

        service_task.terminate()

        assert not service_task.is_running


@pytest.mark.unit
class TestBaseServiceTaskMethodCalling:
    """Test BaseServiceTask method calling."""

    def test_call_method_success(self, service_task):
        """Test calling a service method successfully."""
        result = service_task.call_method("test_method", "arg1", arg2="value2")

        assert result == "result: arg1, value2"
        assert service_task._request_count == 1
        assert service_task._error_count == 0

    def test_call_method_failure(self, service_task):
        """Test calling a service method that raises an exception."""
        with pytest.raises(ValueError, match="Service method failed"):
            service_task.call_method("failing_method")

        assert service_task._request_count == 1
        assert service_task._error_count == 1

    def test_call_nonexistent_method(self, service_task):
        """Test calling a method that doesn't exist."""
        with pytest.raises(AttributeError, match="does not have method"):
            service_task.call_method("nonexistent_method")

        assert service_task._error_count == 1

    def test_get_attribute(self, service_task):
        """Test getting a service attribute."""
        value = service_task.get_attribute("test_property")

        assert value == "test_value"

    def test_get_nonexistent_attribute(self, service_task):
        """Test getting an attribute that doesn't exist."""
        with pytest.raises(AttributeError, match="does not have attribute"):
            service_task.get_attribute("nonexistent_attr")

    def test_set_attribute(self, service_task):
        """Test setting a service attribute."""
        service_task.set_attribute("new_attr", "new_value")

        assert service_task.service_instance.new_attr == "new_value"


@pytest.mark.unit
class TestBaseServiceTaskQueueListener:
    """Test BaseServiceTask queue listener."""

    def test_queue_listener_starts_with_service(self, service_task):
        """Test queue listener thread starts when service starts."""
        service_task.start_running()

        assert service_task._queue_listener_thread is not None
        assert service_task._queue_listener_thread.is_alive()
        assert service_task._queue_listener_running

    def test_queue_listener_stops_with_service(self, service_task):
        """Test queue listener thread stops when service stops."""
        service_task.start_running()
        thread = service_task._queue_listener_thread

        service_task.stop()

        # Give thread time to stop
        time.sleep(0.2)
        assert not service_task._queue_listener_running
        assert not thread.is_alive()

    def test_queue_listener_processes_request(self, service_task, mock_service_context):
        """Test queue listener processes requests from queue."""
        service_task.start_running()

        # Add response queue
        mock_service_context.add_response_queue("node1")
        response_queue = mock_service_context._response_queues["node1"]

        # Send a request
        request_data = {
            "request_id": "req_001",
            "method_name": "test_method",
            "args": ("arg1",),
            "kwargs": {"arg2": "value2"},
            "response_queue": response_queue,
            "response_queue_name": "node1",
            "timeout": 10.0,
        }
        service_task.request_queue.put(request_data)

        # Wait for processing
        time.sleep(0.3)

        # Check response was sent
        assert not response_queue.empty()
        response = response_queue.get(timeout=1.0)

        assert response["request_id"] == "req_001"
        assert response["success"]
        assert response["result"] == "result: arg1, value2"

    def test_queue_listener_handles_failing_request(self, service_task, mock_service_context):
        """Test queue listener handles failing requests gracefully."""
        service_task.start_running()

        # Add response queue
        mock_service_context.add_response_queue("node1")
        response_queue = mock_service_context._response_queues["node1"]

        # Send a failing request
        request_data = {
            "request_id": "req_002",
            "method_name": "failing_method",
            "args": (),
            "kwargs": {},
            "response_queue": response_queue,
            "response_queue_name": "node1",
            "timeout": 10.0,
        }
        service_task.request_queue.put(request_data)

        # Wait for processing
        time.sleep(0.3)

        # Check error response was sent
        assert not response_queue.empty()
        response = response_queue.get(timeout=1.0)

        assert response["request_id"] == "req_002"
        assert not response["success"]
        assert "Service method failed" in response["error"]


@pytest.mark.unit
class TestBaseServiceTaskDirectRequestHandling:
    """Test BaseServiceTask direct request handling (handle_request)."""

    def test_handle_request_success(self, service_task, mock_service_context):
        """Test direct request handling succeeds."""
        # Add response queue
        mock_service_context.add_response_queue("node1")
        response_queue = mock_service_context._response_queues["node1"]

        request_data = {
            "request_id": "req_003",
            "method_name": "test_method",
            "args": ("direct_arg",),
            "kwargs": {},
            "response_queue": response_queue,
            "timeout": 10.0,
        }

        service_task.handle_request(request_data)

        # Check response
        assert not response_queue.empty()
        response = response_queue.get(timeout=1.0)

        assert response["request_id"] == "req_003"
        assert response["success"]
        assert "direct_arg" in response["result"]

    def test_handle_request_failure(self, service_task, mock_service_context):
        """Test direct request handling with failure."""
        # Add response queue
        mock_service_context.add_response_queue("node1")
        response_queue = mock_service_context._response_queues["node1"]

        request_data = {
            "request_id": "req_004",
            "method_name": "failing_method",
            "args": (),
            "kwargs": {},
            "response_queue": response_queue,
            "timeout": 10.0,
        }

        service_task.handle_request(request_data)

        # Check error response
        assert not response_queue.empty()
        response = response_queue.get(timeout=1.0)

        assert response["request_id"] == "req_004"
        assert not response["success"]


@pytest.mark.unit
class TestBaseServiceTaskStatistics:
    """Test BaseServiceTask statistics."""

    def test_get_statistics(self, service_task):
        """Test get_statistics returns correct information."""
        stats = service_task.get_statistics()

        assert stats["service_name"] == "test_service"
        assert stats["service_type"] == "ConcreteServiceTask"
        assert not stats["is_running"]
        assert stats["request_count"] == 0
        assert stats["error_count"] == 0
        assert stats["service_class"] == "MockServiceClass"
        assert stats["has_service_context"]

    def test_statistics_after_requests(self, service_task):
        """Test statistics are updated after processing requests."""
        # Call some methods
        service_task.call_method("test_method", "arg1")
        try:
            service_task.call_method("failing_method")
        except ValueError:
            pass

        stats = service_task.get_statistics()

        assert stats["request_count"] == 2
        assert stats["error_count"] == 1


@pytest.mark.unit
class TestBaseServiceTaskCleanup:
    """Test BaseServiceTask cleanup."""

    def test_cleanup_calls_service_cleanup(self, mock_service_factory, mock_service_context):
        """Test cleanup calls service instance cleanup method."""
        task = ConcreteServiceTask(mock_service_factory, mock_service_context)

        task.cleanup()

        assert task.service_instance.cleanup_called

    def test_cleanup_stops_running_service(self, service_task):
        """Test cleanup stops running service first."""
        service_task.start_running()
        assert service_task.is_running

        service_task.cleanup()

        assert not service_task.is_running

    def test_cleanup_with_close_method(self, mock_service_context):
        """Test cleanup calls close method if cleanup not available."""

        class ServiceWithClose:
            def __init__(self, ctx):
                self.ctx = ctx
                self.close_called = False

            def setup(self):
                pass

            def close(self):
                self.close_called = True

        factory = MockServiceFactory(service_class=ServiceWithClose)
        task = ConcreteServiceTask(factory, mock_service_context)

        task.cleanup()

        assert task.service_instance.close_called


@pytest.mark.unit
class TestBaseServiceTaskConcurrency:
    """Test BaseServiceTask concurrency and thread safety."""

    def test_concurrent_method_calls(self, service_task):
        """Test concurrent method calls are thread-safe."""
        results = []
        errors = []

        def call_method(thread_id):
            try:
                result = service_task.call_method("test_method", f"thread_{thread_id}")
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=call_method, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5.0)

        # Verify all calls succeeded
        assert len(results) == 10
        assert len(errors) == 0
        assert service_task._request_count == 10

    def test_concurrent_queue_processing(self, service_task, mock_service_context):
        """Test concurrent request processing through queue."""
        service_task.start_running()

        # Add response queues
        for i in range(5):
            mock_service_context.add_response_queue(f"node{i}")

        # Send multiple requests
        for i in range(5):
            response_queue = mock_service_context._response_queues[f"node{i}"]
            request_data = {
                "request_id": f"req_{i:03d}",
                "method_name": "test_method",
                "args": (f"arg{i}",),
                "kwargs": {},
                "response_queue": response_queue,
                "response_queue_name": f"node{i}",
                "timeout": 10.0,
            }
            service_task.request_queue.put(request_data)

        # Wait for all to process
        time.sleep(0.5)

        # Verify all responses received
        for i in range(5):
            response_queue = mock_service_context._response_queues[f"node{i}"]
            assert not response_queue.empty()
            response = response_queue.get(timeout=1.0)
            assert response["success"]


@pytest.mark.unit
class TestBaseServiceTaskMonitoring:
    """Test BaseServiceTask performance monitoring."""

    @patch("sage.kernel.runtime.service.base_service_task.RESOURCE_MONITOR_AVAILABLE", True)
    @patch("sage.kernel.runtime.service.base_service_task.MetricsCollector")
    def test_monitoring_enabled(self, mock_metrics_collector, mock_service_factory):
        """Test monitoring is enabled when configured."""
        ctx = MockServiceContext(enable_monitoring=True)
        task = ConcreteServiceTask(mock_service_factory, ctx)

        assert task._enable_monitoring
        assert mock_metrics_collector.called

        task.cleanup()

    def test_monitoring_disabled_by_default(self, service_task):
        """Test monitoring is disabled by default."""
        assert not service_task._enable_monitoring
        assert service_task.metrics_collector is None

    @patch("sage.kernel.runtime.service.base_service_task.RESOURCE_MONITOR_AVAILABLE", True)
    @patch("sage.kernel.runtime.service.base_service_task.MetricsCollector")
    def test_get_current_metrics_when_disabled(self, mock_metrics_collector, service_task):
        """Test get_current_metrics returns None when disabled."""
        metrics = service_task.get_current_metrics()

        assert metrics is None


@pytest.mark.unit
class TestBaseServiceTaskContextManager:
    """Test BaseServiceTask context manager protocol."""

    def test_context_manager_enter_exit(self, mock_service_factory, mock_service_context):
        """Test service task can be used as context manager."""
        with ConcreteServiceTask(mock_service_factory, mock_service_context) as task:
            assert task is not None
            assert task.service_instance is not None

        # Cleanup should be called on exit
        assert task.service_instance.cleanup_called


@pytest.mark.unit
class TestBaseServiceTaskRepr:
    """Test BaseServiceTask string representation."""

    def test_repr(self, service_task):
        """Test __repr__ method."""
        repr_str = repr(service_task)

        assert "ConcreteServiceTask" in repr_str
        assert "test_service" in repr_str
        assert "MockServiceClass" in repr_str
