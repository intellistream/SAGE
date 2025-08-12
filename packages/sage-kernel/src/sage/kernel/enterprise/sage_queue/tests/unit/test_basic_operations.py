"""
Unit tests for SAGE Queue basic functionality
"""

import pytest
import time
import pickle
from queue import Empty, Full

from ..utils import DataGenerator, MessageData, validate_queue_interface


@pytest.mark.unit
class TestSageQueueBasics:
    """Test basic queue operations"""
    
    def test_queue_creation(self, small_queue):
        """Test queue creation and initial state"""
        validate_queue_interface(small_queue)
        assert small_queue.empty()
        assert small_queue.qsize() == 0
        assert not small_queue.full()
    
    def test_put_get_string(self, small_queue):
        """Test putting and getting string data"""
        test_string = "Hello, SAGE Queue!"
        
        small_queue.put(test_string)
        assert not small_queue.empty()
        assert small_queue.qsize() == 1
        
        result = small_queue.get()
        assert result == test_string
        assert small_queue.empty()
        assert small_queue.qsize() == 0
    
    def test_put_get_dict(self, small_queue):
        """Test putting and getting dictionary data"""
        test_dict = {"key": "value", "number": 42, "nested": {"inner": "data"}}
        
        small_queue.put(test_dict)
        result = small_queue.get()
        assert result == test_dict
    
    def test_put_get_list(self, small_queue):
        """Test putting and getting list data"""
        test_list = [1, 2, 3, "string", {"nested": "dict"}]
        
        small_queue.put(test_list)
        result = small_queue.get()
        assert result == test_list
    
    def test_put_get_tuple(self, small_queue):
        """Test putting and getting tuple data"""
        test_tuple = ("tuple", "data", 123, [1, 2, 3])
        
        small_queue.put(test_tuple)
        result = small_queue.get()
        assert result == test_tuple
    
    def test_put_get_bytes(self, small_queue):
        """Test putting and getting bytes data"""
        test_bytes = b"binary data \x00\x01\x02"
        
        small_queue.put(test_bytes)
        result = small_queue.get()
        assert result == test_bytes
    
    def test_put_get_none(self, small_queue):
        """Test putting and getting None"""
        small_queue.put(None)
        result = small_queue.get()
        assert result is None
    
    def test_multiple_items_fifo(self, small_queue):
        """Test FIFO ordering with multiple items"""
        items = ["first", "second", "third", "fourth"]
        
        # Put all items
        for item in items:
            small_queue.put(item)
        
        assert small_queue.qsize() == len(items)
        
        # Get all items and verify FIFO order
        results = []
        for _ in range(len(items)):
            results.append(small_queue.get())
        
        assert results == items
        assert small_queue.empty()
    
    def test_nowait_operations(self, small_queue):
        """Test non-blocking operations"""
        # Test get_nowait on empty queue
        with pytest.raises(Empty):
            small_queue.get_nowait()
        
        # Test put_nowait and get_nowait
        test_item = "nowait_test"
        small_queue.put_nowait(test_item)
        assert small_queue.qsize() == 1
        
        result = small_queue.get_nowait()
        assert result == test_item
        assert small_queue.empty()
    
    def test_queue_size_tracking(self, small_queue):
        """Test queue size tracking accuracy"""
        assert small_queue.qsize() == 0
        
        # Add items one by one
        for i in range(5):
            small_queue.put(f"item_{i}")
            assert small_queue.qsize() == i + 1
        
        # Remove items one by one
        for i in range(5):
            small_queue.get()
            assert small_queue.qsize() == 4 - i
    
    def test_empty_full_states(self, small_queue):
        """Test empty and full state detection"""
        # Initially empty
        assert small_queue.empty()
        assert not small_queue.full()
        
        # Add one item
        small_queue.put("item")
        assert not small_queue.empty()
        
        # Fill to capacity (assuming small queue has limited capacity)
        # This test depends on the actual queue size implementation
        small_queue.get()  # Remove the test item first
        
        # Test with known small capacity
        for i in range(10):  # Add several items
            small_queue.put(f"item_{i}")
        
        assert not small_queue.empty()
        # Note: full() behavior depends on queue implementation


@pytest.mark.unit
class TestSageQueueDataTypes:
    """Test queue with various data types"""
    
    @pytest.mark.parametrize("data", [
        42,
        3.14159,
        True,
        False,
        "",
        [],
        {},
        set(),
    ])
    def test_primitive_types(self, small_queue, data):
        """Test queue with primitive data types"""
        small_queue.put(data)
        result = small_queue.get()
        assert result == data
        assert type(result) == type(data)
    
    def test_complex_nested_data(self, small_queue):
        """Test queue with complex nested data structures"""
        complex_data = {
            "level1": {
                "level2": {
                    "level3": [
                        {"item": i, "data": f"value_{i}"}
                        for i in range(10)
                    ]
                }
            },
            "metadata": {
                "timestamp": time.time(),
                "version": "1.0.0",
                "flags": [True, False, None]
            }
        }
        
        small_queue.put(complex_data)
        result = small_queue.get()
        assert result == complex_data
    
    def test_large_string_data(self, medium_queue):
        """Test queue with large string data"""
        large_string = DataGenerator.string(10000)  # 10KB string
        
        medium_queue.put(large_string)
        result = medium_queue.get()
        assert result == large_string
    
    def test_large_dict_data(self, medium_queue):
        """Test queue with large dictionary data"""
        large_dict = DataGenerator.dict_data(keys=100, value_size=100)
        
        medium_queue.put(large_dict)
        result = medium_queue.get()
        assert result == large_dict
    
    def test_mixed_type_sequence(self, small_queue):
        """Test queue with mixed data types in sequence"""
        mixed_data = DataGenerator.mixed_types()
        
        # Put all items
        for item in mixed_data:
            small_queue.put(item)
        
        # Get all items and verify
        results = []
        for _ in range(len(mixed_data)):
            results.append(small_queue.get())
        
        assert results == mixed_data


@pytest.mark.unit
class TestSageQueueSerialization:
    """Test queue serialization/deserialization"""
    
    def test_pickle_serialization(self, small_queue):
        """Test that data survives pickle serialization"""
        # Test various pickle protocols
        test_data = {
            "string": "test",
            "number": 42,
            "list": [1, 2, 3],
            "nested": {"inner": "value"}
        }
        
        # Simulate what happens internally
        serialized = pickle.dumps(test_data)
        deserialized = pickle.loads(serialized)
        
        assert deserialized == test_data
        
        # Test through queue
        small_queue.put(test_data)
        result = small_queue.get()
        assert result == test_data
    
    def test_custom_objects(self, small_queue):
        """Test queue with custom objects"""
        from ..utils import MessageData
        
        test_obj = MessageData.create({"test": "value"}, "custom_msg")
        
        small_queue.put(test_obj)
        result = small_queue.get()
        assert result == test_obj
        assert result.id == "custom_msg"
        assert result.payload == {"test": "value"}
    
    def test_unpickleable_objects(self, small_queue):
        """Test handling of unpickleable objects"""
        # Lambda functions cannot be pickled
        unpickleable = lambda x: x + 1
        
        with pytest.raises(Exception):  # Could be pickle.PicklingError or similar
            small_queue.put(unpickleable)


@pytest.mark.unit
class TestSageQueueErrorHandling:
    """Test queue error handling"""
    
    def test_get_from_empty_queue_blocking(self, small_queue):
        """Test getting from empty queue with timeout"""
        start_time = time.time()
        
        with pytest.raises(Empty):
            small_queue.get(timeout=0.1)
        
        elapsed = time.time() - start_time
        assert 0.08 <= elapsed <= 0.15  # Allow some timing variance
    
    def test_get_from_empty_queue_nowait(self, small_queue):
        """Test get_nowait from empty queue"""
        with pytest.raises(Empty):
            small_queue.get_nowait()
    
    def test_queue_operations_after_close(self, queue_name):
        """Test queue operations after closing"""
        # Use the same import mechanism as fixtures
        from conftest import SageQueue
        
        queue = SageQueue(queue_name, maxsize=1024)
        queue.put("test")
        queue.close()
        
        # Operations after close should raise appropriate exceptions
        with pytest.raises(Exception):
            queue.put("should_fail")
        
        with pytest.raises(Exception):
            queue.get()
    
    def test_invalid_timeout_values(self, small_queue):
        """Test queue operations with invalid timeout values"""
        small_queue.put("test")
        
        # Negative timeout should be handled gracefully
        with pytest.raises((ValueError, TypeError)):
            small_queue.get(timeout=-1)
    
    def test_very_large_data(self, large_queue):
        """Test queue with very large data (stress serialization)"""
        # Create data that's close to memory limits
        large_data = DataGenerator.string(100000)  # 100KB string
        
        large_queue.put(large_data)
        result = large_queue.get()
        assert result == large_data
        assert len(result) == 100000
