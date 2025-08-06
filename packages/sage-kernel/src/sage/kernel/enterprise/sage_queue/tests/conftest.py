"""
pytest fixtures and configuration for SAGE Queue tests
"""

import os
import sys
import pytest
import tempfile
import shutil
import threading
import time
import multiprocessing
from pathlib import Path
from typing import Generator, Optional, List, Dict, Any

# Add parent directory to path
current_dir = Path(__file__).parent
sage_queue_dir = current_dir.parent
sys.path.insert(0, str(sage_queue_dir))


from sage.extensions.sage_queue import SageQueue
print("✓ Using real SageQueue implementation")

from . import TEST_CONFIG


class QueueContext:
    """Context manager for SageQueue instances"""
    
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.kwargs = kwargs
        self.queue = None
        self._closed = False
    
    def __enter__(self):
        self.queue = SageQueue(self.name, **self.kwargs)
        return self.queue
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.queue and not self._closed:
            try:
                self.queue.close()
                self._closed = True
            except Exception:
                pass  # Ignore cleanup errors


@pytest.fixture(scope="session")
def temp_dir():
    """Create a temporary directory for test artifacts"""
    temp_path = tempfile.mkdtemp(prefix="sage_queue_tests_")
    yield temp_path
    # Cleanup
    try:
        shutil.rmtree(temp_path)
    except Exception:
        pass  # Ignore cleanup errors


@pytest.fixture
def queue_name():
    """Generate unique queue name for each test"""
    import uuid
    return f"{TEST_CONFIG['temp_queue_prefix']}{uuid.uuid4().hex[:8]}_{int(time.time() * 1000)}"


@pytest.fixture
def small_queue(queue_name):
    """Create a small queue for basic tests"""
    with QueueContext(queue_name, maxsize=1024) as queue:
        yield queue


@pytest.fixture
def medium_queue(queue_name):
    """Create a medium queue for performance tests"""
    with QueueContext(queue_name, maxsize=64 * 1024) as queue:
        yield queue


@pytest.fixture
def large_queue(queue_name):
    """Create a large queue for stress tests"""
    with QueueContext(queue_name, maxsize=1024 * 1024) as queue:
        yield queue


@pytest.fixture
def queue_manager():
    """Create a queue manager instance"""
    manager = SageQueueManager()
    yield manager
    # Cleanup all queues managed by this manager
    try:
        manager.cleanup_all()
    except Exception:
        pass


@pytest.fixture(params=[1024, 64*1024, 256*1024])
def queue_with_various_sizes(request, queue_name):
    """Parametrized fixture for queues with different sizes"""
    with QueueContext(queue_name, maxsize=request.param) as queue:
        yield queue, request.param


@pytest.fixture
def performance_data():
    """Storage for performance metrics during tests"""
    return {
        "throughput": [],
        "latency": [],
        "memory_usage": [],
        "cpu_usage": []
    }


class ProcessHelper:
    """Helper class for multiprocess testing"""
    
    def __init__(self, method="spawn"):
        self.method = method
        self.processes: List[multiprocessing.Process] = []
    
    def start_process(self, target, args=(), kwargs=None):
        """Start a new process"""
        if kwargs is None:
            kwargs = {}
        
        ctx = multiprocessing.get_context(self.method)
        process = ctx.Process(target=target, args=args, kwargs=kwargs)
        process.start()
        self.processes.append(process)
        return process
    
    def wait_all(self, timeout=None):
        """Wait for all processes to complete"""
        for process in self.processes:
            process.join(timeout=timeout)
    
    def terminate_all(self):
        """Terminate all processes"""
        for process in self.processes:
            if process.is_alive():
                process.terminate()
        self.wait_all(timeout=5)
        
        # Force kill if needed
        for process in self.processes:
            if process.is_alive():
                process.kill()
    
    def cleanup(self):
        """Cleanup all processes"""
        self.terminate_all()
        self.processes.clear()


@pytest.fixture
def process_helper():
    """Create a process helper for multiprocess tests"""
    helper = ProcessHelper(method=TEST_CONFIG["multiprocess_method"])
    yield helper
    # Cleanup
    helper.cleanup()


@pytest.fixture
def thread_helper():
    """Helper for multithreading tests"""
    threads = []
    
    def start_thread(target, args=(), kwargs=None):
        if kwargs is None:
            kwargs = {}
        thread = threading.Thread(target=target, args=args, kwargs=kwargs)
        thread.start()
        threads.append(thread)
        return thread
    
    def wait_all(timeout=None):
        for thread in threads:
            thread.join(timeout=timeout)
    
    yield start_thread, wait_all
    
    # Cleanup
    for thread in threads:
        if thread.is_alive():
            thread.join(timeout=5)


@pytest.fixture
def performance_monitor():
    """Monitor system performance during tests"""
    try:
        import psutil
    except ImportError:
        pytest.skip("psutil required for performance monitoring")
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.start_memory = None
            self.end_memory = None
            self.start_cpu = None
            self.end_cpu = None
            self.process = psutil.Process()
        
        def start(self):
            self.start_time = time.time()
            self.start_memory = self.process.memory_info().rss
            self.start_cpu = self.process.cpu_percent()
        
        def stop(self):
            self.end_time = time.time()
            self.end_memory = self.process.memory_info().rss
            self.end_cpu = self.process.cpu_percent()
        
        @property
        def duration(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
        
        @property
        def memory_delta(self):
            if self.start_memory and self.end_memory:
                return self.end_memory - self.start_memory
            return None
        
        @property
        def avg_cpu(self):
            if self.start_cpu and self.end_cpu:
                return (self.start_cpu + self.end_cpu) / 2
            return None
    
    return PerformanceMonitor()


# Test markers
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "unit: Unit tests for individual components"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests for component interaction"
    )
    config.addinivalue_line(
        "markers", "performance: Performance and benchmark tests"
    )
    config.addinivalue_line(
        "markers", "stress: Stress tests with high load"
    )
    config.addinivalue_line(
        "markers", "multiprocess: Tests requiring multiple processes"
    )
    config.addinivalue_line(
        "markers", "threading: Tests with multiple threads"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take a long time to run"
    )
    config.addinivalue_line(
        "markers", "ray: Tests requiring Ray framework"
    )


# Custom pytest hooks
def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    # Skip Ray tests if Ray is not available
    try:
        import ray
    except ImportError:
        ray_skip = pytest.mark.skip(reason="Ray not available")
        for item in items:
            if "ray" in item.keywords:
                item.add_marker(ray_skip)
    
    # Add slow marker to performance tests
    slow_marker = pytest.mark.slow
    for item in items:
        if "performance" in item.keywords or "stress" in item.keywords:
            item.add_marker(slow_marker)


# Session fixtures for one-time setup
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment"""
    # Set environment variables for testing
    os.environ["SAGE_TEST_MODE"] = "1"
    
    yield
    
    # Cleanup
    os.environ.pop("SAGE_TEST_MODE", None)
