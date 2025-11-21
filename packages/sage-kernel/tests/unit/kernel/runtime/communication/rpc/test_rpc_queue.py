"""
Unit tests for RPCQueue.

Tests the RPC queue implementation for remote process communication.
Note: Current implementation is a stub using local Queue.
"""

import time
from queue import Empty, Full

import pytest

from sage.kernel.runtime.communication.rpc.rpc_queue import RPCQueue

# Test Cases


@pytest.mark.unit
class TestRPCQueueInitialization:
    """Test RPCQueue initialization."""

    def test_initialization_with_defaults(self):
        """Test RPC queue initialization with default parameters."""
        queue = RPCQueue(queue_id="test_queue")

        assert queue.queue_id == "test_queue"
        assert queue.host == "localhost"
        assert queue.port == 50051
        assert queue.maxsize == 0
        assert not queue._connected
        assert queue._queue is not None

    def test_initialization_with_custom_parameters(self):
        """Test RPC queue initialization with custom parameters."""
        queue = RPCQueue(
            queue_id="custom_queue",
            host="192.168.1.100",
            port=8080,
            maxsize=100,
        )

        assert queue.queue_id == "custom_queue"
        assert queue.host == "192.168.1.100"
        assert queue.port == 8080
        assert queue.maxsize == 100
        assert not queue._connected

    def test_initialization_logs_stub_warning(self, caplog):
        """Test that initialization logs a stub implementation warning."""
        RPCQueue(queue_id="warning_test")

        assert "STUB" in caplog.text
        assert "warning_test" in caplog.text


@pytest.mark.unit
class TestRPCQueueConnection:
    """Test RPCQueue connection management."""

    def test_connect_first_time(self):
        """Test connecting to RPC server for the first time."""
        queue = RPCQueue(queue_id="connect_test")

        result = queue.connect()

        assert result is True
        assert queue._connected

    def test_connect_already_connected(self):
        """Test connecting when already connected."""
        queue = RPCQueue(queue_id="connect_test")
        queue.connect()

        # Connect again
        result = queue.connect()

        assert result is True
        assert queue._connected

    def test_close_connection(self):
        """Test closing RPC connection."""
        queue = RPCQueue(queue_id="close_test")
        queue.connect()
        assert queue._connected

        queue.close()

        assert not queue._connected

    def test_close_when_not_connected(self):
        """Test closing connection when not connected."""
        queue = RPCQueue(queue_id="close_test")
        assert not queue._connected

        # Should not raise error
        queue.close()

        assert not queue._connected


@pytest.mark.unit
class TestRPCQueuePutGet:
    """Test RPCQueue put and get operations."""

    def test_put_item(self):
        """Test putting an item into the queue."""
        queue = RPCQueue(queue_id="put_test")

        queue.put("test_item")

        assert queue.qsize() == 1
        assert queue._connected  # Auto-connect on put

    def test_put_multiple_items(self):
        """Test putting multiple items into the queue."""
        queue = RPCQueue(queue_id="multi_put_test")

        for i in range(5):
            queue.put(f"item_{i}")

        assert queue.qsize() == 5

    def test_get_item(self):
        """Test getting an item from the queue."""
        queue = RPCQueue(queue_id="get_test")
        queue.put("test_data")

        item = queue.get()

        assert item == "test_data"
        assert queue.qsize() == 0

    def test_get_multiple_items(self):
        """Test getting multiple items in order."""
        queue = RPCQueue(queue_id="multi_get_test")
        items = ["first", "second", "third"]

        for item in items:
            queue.put(item)

        retrieved = []
        for _ in range(3):
            retrieved.append(queue.get())

        assert retrieved == items

    def test_get_empty_queue_blocking_with_timeout(self):
        """Test getting from empty queue with timeout."""
        queue = RPCQueue(queue_id="empty_test")

        with pytest.raises(Empty):
            queue.get(block=True, timeout=0.1)

    def test_get_empty_queue_non_blocking(self):
        """Test getting from empty queue in non-blocking mode."""
        queue = RPCQueue(queue_id="empty_nonblock_test")

        with pytest.raises(Empty):
            queue.get(block=False)

    def test_put_with_maxsize_blocking(self):
        """Test putting into full queue with blocking."""
        queue = RPCQueue(queue_id="full_test", maxsize=2)

        # Fill the queue
        queue.put("item1")
        queue.put("item2")

        # This should timeout
        with pytest.raises(Full):
            queue.put("item3", block=True, timeout=0.1)

    def test_put_with_maxsize_non_blocking(self):
        """Test putting into full queue in non-blocking mode."""
        queue = RPCQueue(queue_id="full_nonblock_test", maxsize=1)

        queue.put("item1")

        with pytest.raises(Full):
            queue.put("item2", block=False)


@pytest.mark.unit
class TestRPCQueueAutoConnect:
    """Test RPCQueue auto-connection behavior."""

    def test_put_auto_connects(self):
        """Test that put() auto-connects if not connected."""
        queue = RPCQueue(queue_id="auto_connect_put")
        assert not queue._connected

        queue.put("test")

        assert queue._connected

    def test_get_auto_connects(self):
        """Test that get() auto-connects if not connected."""
        queue = RPCQueue(queue_id="auto_connect_get")
        queue._queue.put("test")  # Put directly to internal queue
        assert not queue._connected

        queue.get()

        assert queue._connected


@pytest.mark.unit
class TestRPCQueueSizeChecks:
    """Test RPCQueue size and state checking methods."""

    def test_qsize_empty(self):
        """Test qsize() on empty queue."""
        queue = RPCQueue(queue_id="size_test")

        assert queue.qsize() == 0

    def test_qsize_with_items(self):
        """Test qsize() with items in queue."""
        queue = RPCQueue(queue_id="size_test")

        for i in range(3):
            queue.put(f"item_{i}")

        assert queue.qsize() == 3

    def test_empty_when_empty(self):
        """Test empty() returns True for empty queue."""
        queue = RPCQueue(queue_id="empty_check_test")

        assert queue.empty()

    def test_empty_when_not_empty(self):
        """Test empty() returns False when queue has items."""
        queue = RPCQueue(queue_id="empty_check_test")
        queue.put("item")

        assert not queue.empty()

    def test_full_when_not_full(self):
        """Test full() returns False when queue is not full."""
        queue = RPCQueue(queue_id="full_check_test", maxsize=5)
        queue.put("item")

        assert not queue.full()

    def test_full_when_full(self):
        """Test full() returns True when queue is full."""
        queue = RPCQueue(queue_id="full_check_test", maxsize=2)
        queue.put("item1")
        queue.put("item2")

        assert queue.full()

    def test_full_with_unlimited_size(self):
        """Test full() with unlimited size queue."""
        queue = RPCQueue(queue_id="unlimited_test", maxsize=0)

        for i in range(100):
            queue.put(f"item_{i}")

        assert not queue.full()


@pytest.mark.unit
class TestRPCQueueContextManager:
    """Test RPCQueue context manager protocol."""

    def test_context_manager_enters_and_exits(self):
        """Test RPCQueue can be used as context manager."""
        with RPCQueue(queue_id="context_test") as queue:
            assert queue._connected
            queue.put("test_item")
            item = queue.get()
            assert item == "test_item"

        # After exit, connection should be closed
        assert not queue._connected

    def test_context_manager_with_exception(self):
        """Test context manager properly closes on exception."""
        queue = None
        try:
            with RPCQueue(queue_id="exception_test") as q:
                queue = q
                assert queue._connected
                raise ValueError("Test exception")
        except ValueError:
            pass

        assert not queue._connected


@pytest.mark.unit
class TestRPCQueueRepr:
    """Test RPCQueue string representation."""

    def test_repr_disconnected(self):
        """Test __repr__ when disconnected."""
        queue = RPCQueue(queue_id="repr_test", host="testhost", port=9999)

        repr_str = repr(queue)

        assert "RPCQueue" in repr_str
        assert "repr_test" in repr_str
        assert "testhost" in repr_str
        assert "9999" in repr_str
        assert "disconnected" in repr_str

    def test_repr_connected(self):
        """Test __repr__ when connected."""
        queue = RPCQueue(queue_id="repr_test")
        queue.connect()

        repr_str = repr(queue)

        assert "connected" in repr_str

    def test_repr_with_items(self):
        """Test __repr__ shows queue size."""
        queue = RPCQueue(queue_id="repr_test")
        queue.put("item1")
        queue.put("item2")

        repr_str = repr(queue)

        assert "size=2" in repr_str


@pytest.mark.unit
class TestRPCQueueConcurrency:
    """Test RPCQueue concurrency and thread safety."""

    def test_concurrent_put(self):
        """Test concurrent put operations."""
        import threading

        queue = RPCQueue(queue_id="concurrent_put_test")
        errors = []

        def put_items(thread_id):
            try:
                for i in range(10):
                    queue.put(f"thread_{thread_id}_item_{i}")
            except Exception as e:
                errors.append(e)

        # Start 5 threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=put_items, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join(timeout=5.0)

        assert len(errors) == 0
        assert queue.qsize() == 50

    def test_concurrent_get(self):
        """Test concurrent get operations."""
        import threading

        queue = RPCQueue(queue_id="concurrent_get_test")

        # Pre-fill queue
        for i in range(50):
            queue.put(f"item_{i}")

        results = []
        errors = []

        def get_items(thread_id):
            try:
                for _ in range(10):
                    item = queue.get(timeout=2.0)
                    results.append(item)
            except Exception as e:
                errors.append(e)

        # Start 5 threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=get_items, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join(timeout=5.0)

        assert len(errors) == 0
        assert len(results) == 50
        assert queue.empty()

    def test_concurrent_put_get(self):
        """Test concurrent put and get operations."""
        import threading

        queue = RPCQueue(queue_id="concurrent_put_get_test", maxsize=10)
        put_count = [0]
        get_count = [0]

        def producer():
            for i in range(20):
                queue.put(f"data_{i}", timeout=2.0)
                put_count[0] += 1
                time.sleep(0.01)

        def consumer():
            for _ in range(20):
                queue.get(timeout=2.0)
                get_count[0] += 1
                time.sleep(0.01)

        producer_thread = threading.Thread(target=producer)
        consumer_thread = threading.Thread(target=consumer)

        producer_thread.start()
        consumer_thread.start()

        producer_thread.join(timeout=5.0)
        consumer_thread.join(timeout=5.0)

        assert put_count[0] == 20
        assert get_count[0] == 20


@pytest.mark.unit
class TestRPCQueueDataTypes:
    """Test RPCQueue with different data types."""

    def test_with_string(self):
        """Test queue with string data."""
        queue = RPCQueue(queue_id="string_test")
        queue.put("test string")
        assert queue.get() == "test string"

    def test_with_integer(self):
        """Test queue with integer data."""
        queue = RPCQueue(queue_id="int_test")
        queue.put(42)
        assert queue.get() == 42

    def test_with_dict(self):
        """Test queue with dictionary data."""
        queue = RPCQueue(queue_id="dict_test")
        data = {"key": "value", "number": 123}
        queue.put(data)
        assert queue.get() == data

    def test_with_list(self):
        """Test queue with list data."""
        queue = RPCQueue(queue_id="list_test")
        data = [1, 2, 3, "four", {"five": 5}]
        queue.put(data)
        assert queue.get() == data

    def test_with_none(self):
        """Test queue with None value."""
        queue = RPCQueue(queue_id="none_test")
        queue.put(None)
        assert queue.get() is None

    def test_with_custom_object(self):
        """Test queue with custom object."""

        class CustomObject:
            def __init__(self, value):
                self.value = value

        queue = RPCQueue(queue_id="custom_test")
        obj = CustomObject(42)
        queue.put(obj)
        retrieved = queue.get()

        assert retrieved.value == 42


@pytest.mark.unit
class TestRPCQueueEdgeCases:
    """Test RPCQueue edge cases and error handling."""

    def test_multiple_close_calls(self):
        """Test multiple close() calls don't cause errors."""
        queue = RPCQueue(queue_id="multi_close_test")
        queue.connect()

        queue.close()
        queue.close()
        queue.close()

        assert not queue._connected

    def test_put_after_close_reconnects(self):
        """Test put after close auto-reconnects."""
        queue = RPCQueue(queue_id="reconnect_test")
        queue.connect()
        queue.close()
        assert not queue._connected

        queue.put("test")

        assert queue._connected

    def test_zero_timeout(self):
        """Test operations with zero timeout."""
        queue = RPCQueue(queue_id="zero_timeout_test")

        with pytest.raises(Empty):
            queue.get(block=True, timeout=0)

    def test_very_large_timeout(self):
        """Test operations with very large timeout."""
        queue = RPCQueue(queue_id="large_timeout_test")
        queue.put("test", timeout=999999)

        item = queue.get(timeout=999999)
        assert item == "test"
