"""
Unit tests for SAGE Queue Manager functionality
"""

import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor

from ..utils import DataGenerator, validate_queue_interface


@pytest.mark.unit
class TestSageQueueManager:
    """Test queue manager functionality"""
    
    def test_manager_creation(self, queue_manager):
        """Test queue manager creation"""
        assert queue_manager is not None
        assert hasattr(queue_manager, 'create_queue')
        assert hasattr(queue_manager, 'get_queue')
        assert hasattr(queue_manager, 'cleanup_all')
    
    def test_create_single_queue(self, queue_manager, queue_name):
        """Test creating a single queue through manager"""
        queue = queue_manager.create_queue(queue_name, maxsize=1024)
        
        validate_queue_interface(queue)
        assert queue.empty()
        assert queue.qsize() == 0
    
    def test_create_multiple_queues(self, queue_manager):
        """Test creating multiple queues through manager"""
        queue_names = [f"test_queue_{i}_{int(time.time())}" for i in range(3)]
        queues = []
        
        for name in queue_names:
            queue = queue_manager.create_queue(name, maxsize=1024)
            queues.append(queue)
            validate_queue_interface(queue)
        
        # Test that queues are independent
        for i, queue in enumerate(queues):
            queue.put(f"message_{i}")
        
        for i, queue in enumerate(queues):
            result = queue.get()
            assert result == f"message_{i}"
    
    def test_get_existing_queue(self, queue_manager, queue_name):
        """Test getting reference to existing queue"""
        # Create queue
        original_queue = queue_manager.create_queue(queue_name, maxsize=1024)
        original_queue.put("test_message")
        
        # Get reference to same queue
        retrieved_queue = queue_manager.get_queue(queue_name)
        
        # Should be able to retrieve message
        result = retrieved_queue.get()
        assert result == "test_message"
    
    def test_get_nonexistent_queue(self, queue_manager):
        """Test getting reference to non-existent queue"""
        with pytest.raises(Exception):  # Should raise KeyError or similar
            queue_manager.get_queue("nonexistent_queue")
    
    def test_queue_isolation(self, queue_manager):
        """Test that queues are properly isolated"""
        queue1_name = f"queue1_{int(time.time())}"
        queue2_name = f"queue2_{int(time.time())}"
        
        queue1 = queue_manager.create_queue(queue1_name, maxsize=1024)
        queue2 = queue_manager.create_queue(queue2_name, maxsize=1024)
        
        # Put different data in each queue
        queue1.put("data_for_queue1")
        queue2.put("data_for_queue2")
        
        # Verify isolation
        assert queue1.get() == "data_for_queue1"
        assert queue2.get() == "data_for_queue2"
        
        assert queue1.empty()
        assert queue2.empty()
    
    def test_cleanup_all_queues(self, queue_manager):
        """Test cleanup of all managed queues"""
        queue_names = [f"cleanup_test_{i}_{int(time.time())}" for i in range(3)]
        
        # Create multiple queues
        for name in queue_names:
            queue = queue_manager.create_queue(name, maxsize=1024)
            queue.put(f"data_for_{name}")
        
        # Cleanup all
        queue_manager.cleanup_all()
        
        # Verify queues are cleaned up (behavior depends on implementation)
        for name in queue_names:
            with pytest.raises(Exception):
                queue_manager.get_queue(name)


@pytest.mark.unit
class TestSageQueueManagerConcurrency:
    """Test queue manager under concurrent access"""
    
    def test_concurrent_queue_creation(self, queue_manager):
        """Test concurrent queue creation"""
        num_threads = 4
        queues_per_thread = 5
        created_queues = []
        errors = []
        lock = threading.Lock()
        
        def create_queues(thread_id):
            try:
                for i in range(queues_per_thread):
                    queue_name = f"concurrent_{thread_id}_{i}_{int(time.time())}"
                    queue = queue_manager.create_queue(queue_name, maxsize=1024)
                    
                    with lock:
                        created_queues.append((queue_name, queue))
            except Exception as e:
                with lock:
                    errors.append(str(e))
        
        # Start threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=create_queues, args=(i,))
            thread.start()
            threads.append(thread)
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Errors during concurrent creation: {errors}"
        assert len(created_queues) == num_threads * queues_per_thread
        
        # Verify all queues are functional
        for queue_name, queue in created_queues:
            queue.put(f"test_{queue_name}")
            result = queue.get()
            assert result == f"test_{queue_name}"
    
    def test_concurrent_queue_access(self, queue_manager, queue_name):
        """Test concurrent access to same queue"""
        queue = queue_manager.create_queue(queue_name, maxsize=10000)
        
        num_threads = 4
        items_per_thread = 100
        sent_items = []
        received_items = []
        errors = []
        lock = threading.Lock()
        
        def producer(thread_id):
            try:
                for i in range(items_per_thread):
                    item = f"item_{thread_id}_{i}"
                    queue.put(item)
                    with lock:
                        sent_items.append(item)
            except Exception as e:
                with lock:
                    errors.append(f"Producer {thread_id}: {str(e)}")
        
        def consumer(thread_id):
            try:
                for _ in range(items_per_thread):
                    item = queue.get(timeout=5.0)
                    with lock:
                        received_items.append(item)
            except Exception as e:
                with lock:
                    errors.append(f"Consumer {thread_id}: {str(e)}")
        
        # Start producers and consumers
        threads = []
        
        # Start producers
        for i in range(num_threads // 2):
            thread = threading.Thread(target=producer, args=(f"p{i}",))
            thread.start()
            threads.append(thread)
        
        # Start consumers
        for i in range(num_threads // 2):
            thread = threading.Thread(target=consumer, args=(f"c{i}",))
            thread.start()
            threads.append(thread)
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify results
        assert len(errors) == 0, f"Errors during concurrent access: {errors}"
        assert len(sent_items) == (num_threads // 2) * items_per_thread
        assert len(received_items) == (num_threads // 2) * items_per_thread
        
        # Verify all sent items were received (order may differ)
        assert set(sent_items) == set(received_items)


@pytest.mark.unit
class TestSageQueueManagerErrorHandling:
    """Test queue manager error handling"""
    
    def test_create_queue_with_invalid_params(self, queue_manager, queue_name):
        """Test queue creation with invalid parameters"""
        # Test with invalid maxsize
        with pytest.raises((ValueError, TypeError)):
            queue_manager.create_queue(queue_name, maxsize=-1)
        
        with pytest.raises((ValueError, TypeError)):
            queue_manager.create_queue(queue_name, maxsize="invalid")
    
    def test_create_duplicate_queue(self, queue_manager, queue_name):
        """Test creating queue with duplicate name"""
        # Create first queue
        queue1 = queue_manager.create_queue(queue_name, maxsize=1024)
        
        # Attempt to create another queue with same name
        # Behavior depends on implementation - might return same queue or raise error
        try:
            queue2 = queue_manager.create_queue(queue_name, maxsize=2048)
            # If no error, should be same queue or updated queue
            assert queue2 is not None
        except Exception:
            # If error is raised, that's also acceptable behavior
            pass
    
    def test_cleanup_with_active_operations(self, queue_manager):
        """Test cleanup while operations are active"""
        queue_name = f"active_test_{int(time.time())}"
        queue = queue_manager.create_queue(queue_name, maxsize=1024)
        
        # Start a background operation
        def background_operation():
            try:
                for i in range(100):
                    queue.put(f"item_{i}")
                    time.sleep(0.01)
            except Exception:
                pass  # Expected when queue is cleaned up
        
        thread = threading.Thread(target=background_operation)
        thread.start()
        
        time.sleep(0.1)  # Let it start
        
        # Cleanup should handle active operations gracefully
        queue_manager.cleanup_all()
        
        thread.join(timeout=2)  # Should terminate quickly after cleanup
        
        # Thread should have finished (either completed or interrupted)
        assert not thread.is_alive()
    
    def test_manager_operations_after_cleanup(self, queue_manager, queue_name):
        """Test manager operations after cleanup"""
        # Create and cleanup
        queue = queue_manager.create_queue(queue_name, maxsize=1024)
        queue_manager.cleanup_all()
        
        # Operations after cleanup should work (create new queues)
        new_queue = queue_manager.create_queue(f"{queue_name}_new", maxsize=1024)
        assert new_queue is not None
        
        new_queue.put("test")
        result = new_queue.get()
        assert result == "test"
