"""
Integration tests for multithreading scenarios
"""

import pytest
import time
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..utils import DataGenerator, ConcurrencyTester


def producer_thread(sage_queue, num_messages: int, message_prefix: str, results: list, errors: list):
    """Producer thread function"""
    try:
        for i in range(num_messages):
            message = f"{message_prefix}_{i}_{DataGenerator.string(20)}"
            sage_queue.put(message)
            results.append(message)
    except Exception as e:
        errors.append(f"Producer {message_prefix}: {str(e)}")


def consumer_thread(sage_queue, num_messages: int, consumer_id: str, results: list, errors: list, timeout: float = 10.0):
    """Consumer thread function"""
    try:
        consumed = 0
        start_time = time.time()
        
        while consumed < num_messages and (time.time() - start_time) < timeout:
            try:
                message = sage_queue.get(timeout=1.0)
                results.append(message)
                consumed += 1
            except queue.Empty:
                continue
    except Exception as e:
        errors.append(f"Consumer {consumer_id}: {str(e)}")


@pytest.mark.integration
@pytest.mark.threading
class TestMultithreadingBasic:
    """Basic multithreading integration tests"""
    
    def test_single_producer_single_consumer(self, medium_queue, thread_helper):
        """Test single producer, single consumer with threads"""
        num_messages = 100
        producer_results = []
        consumer_results = []
        errors = []
        
        # Start producer thread
        producer_thread_obj = thread_helper[0](
            producer_thread,
            args=(medium_queue, num_messages, "prod1", producer_results, errors)
        )
        
        # Start consumer thread
        consumer_thread_obj = thread_helper[0](
            consumer_thread,
            args=(medium_queue, num_messages, "cons1", consumer_results, errors)
        )
        
        # Wait for completion
        thread_helper[1](timeout=15)
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(producer_results) == num_messages
        assert len(consumer_results) == num_messages
        
        # All produced messages should be consumed (order may differ)
        assert set(producer_results) == set(consumer_results)
    
    def test_multiple_producers_single_consumer(self, large_queue, thread_helper):
        """Test multiple producers, single consumer"""
        num_producers = 4
        messages_per_producer = 25
        total_messages = num_producers * messages_per_producer
        
        producer_results = []
        consumer_results = []
        errors = []
        
        # Thread-safe lists
        producer_results_lock = threading.Lock()
        consumer_results_lock = threading.Lock()
        errors_lock = threading.Lock()
        
        def safe_producer(queue, num_msgs, prefix):
            results = []
            thread_errors = []
            producer_thread(queue, num_msgs, prefix, results, thread_errors)
            
            with producer_results_lock:
                producer_results.extend(results)
            with errors_lock:
                errors.extend(thread_errors)
        
        def safe_consumer(queue, num_msgs, consumer_id):
            results = []
            thread_errors = []
            consumer_thread(queue, num_msgs, consumer_id, results, thread_errors, timeout=15.0)
            
            with consumer_results_lock:
                consumer_results.extend(results)
            with errors_lock:
                errors.extend(thread_errors)
        
        # Start producer threads
        for i in range(num_producers):
            thread_helper[0](safe_producer, args=(large_queue, messages_per_producer, f"prod{i}"))
        
        # Start consumer thread
        thread_helper[0](safe_consumer, args=(large_queue, total_messages, "cons1"))
        
        # Wait for completion
        thread_helper[1](timeout=20)
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(producer_results) == total_messages
        assert len(consumer_results) == total_messages
        
        # All produced messages should be consumed
        assert set(producer_results) == set(consumer_results)
    
    def test_single_producer_multiple_consumers(self, large_queue, thread_helper):
        """Test single producer, multiple consumers"""
        num_consumers = 4
        total_messages = 100
        
        producer_results = []
        consumer_results = []
        errors = []
        
        # Thread-safe access
        consumer_results_lock = threading.Lock()
        errors_lock = threading.Lock()
        
        def safe_producer(queue, num_msgs, prefix):
            results = []
            thread_errors = []
            producer_thread(queue, num_msgs, prefix, results, thread_errors)
            
            producer_results.extend(results)
            with errors_lock:
                errors.extend(thread_errors)
        
        def safe_consumer(queue, max_msgs, consumer_id):
            results = []
            thread_errors = []
            consumer_thread(queue, max_msgs, consumer_id, results, thread_errors, timeout=15.0)
            
            with consumer_results_lock:
                consumer_results.extend(results)
            with errors_lock:
                errors.extend(thread_errors)
        
        # Start producer thread
        thread_helper[0](safe_producer, args=(large_queue, total_messages, "prod1"))
        
        # Start consumer threads
        for i in range(num_consumers):
            # Each consumer tries to get up to total_messages, but they'll compete
            thread_helper[0](safe_consumer, args=(large_queue, total_messages, f"cons{i}"))
        
        # Wait for completion
        thread_helper[1](timeout=20)
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(producer_results) == total_messages
        assert len(consumer_results) == total_messages  # Total consumed should equal produced
        
        # All produced messages should be consumed (no duplicates)
        assert len(set(consumer_results)) == len(consumer_results), "Duplicate messages consumed"
        assert set(producer_results) == set(consumer_results)


@pytest.mark.integration
@pytest.mark.threading
class TestMultithreadingStress:
    """Stress tests for multithreading scenarios"""
    
    def test_many_producers_many_consumers(self, large_queue):
        """Test many producers and consumers"""
        num_producers = 6
        num_consumers = 6
        messages_per_producer = 20
        total_messages = num_producers * messages_per_producer
        
        producer_results = []
        consumer_results = []
        errors = []
        
        # Thread-safe data structures
        producer_lock = threading.Lock()
        consumer_lock = threading.Lock()
        error_lock = threading.Lock()
        
        def thread_safe_producer(thread_id):
            results = []
            thread_errors = []
            producer_thread(large_queue, messages_per_producer, f"prod{thread_id}", results, thread_errors)
            
            with producer_lock:
                producer_results.extend(results)
            with error_lock:
                errors.extend(thread_errors)
        
        def thread_safe_consumer(thread_id):
            results = []
            thread_errors = []
            # Each consumer tries to get a fair share, but they compete
            expected_share = total_messages // num_consumers + 5  # Add buffer
            consumer_thread(large_queue, expected_share, f"cons{thread_id}", results, thread_errors, timeout=20.0)
            
            with consumer_lock:
                consumer_results.extend(results)
            with error_lock:
                errors.extend(thread_errors)
        
        # Start all threads
        threads = []
        
        # Start producers
        for i in range(num_producers):
            thread = threading.Thread(target=thread_safe_producer, args=(i,))
            thread.start()
            threads.append(thread)
        
        # Start consumers
        for i in range(num_consumers):
            thread = threading.Thread(target=thread_safe_consumer, args=(i,))
            thread.start()
            threads.append(thread)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=25)
        
        # Verify all threads completed
        alive_threads = [t for t in threads if t.is_alive()]
        assert len(alive_threads) == 0, f"{len(alive_threads)} threads still alive"
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(producer_results) == total_messages
        
        # All produced messages should be consumed (no more, no less)
        assert len(consumer_results) == total_messages
        assert len(set(consumer_results)) == len(consumer_results), "Duplicate messages"
        assert set(producer_results) == set(consumer_results)
    
    @pytest.mark.slow
    def test_high_throughput_threading(self, large_queue):
        """Test high-throughput threading scenario"""
        num_producers = 4
        num_consumers = 4
        messages_per_producer = 100
        total_messages = num_producers * messages_per_producer
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_producers + num_consumers) as executor:
            # Submit producer tasks
            producer_futures = []
            for i in range(num_producers):
                future = executor.submit(
                    self._high_throughput_producer,
                    large_queue, messages_per_producer, f"prod{i}"
                )
                producer_futures.append(future)
            
            # Submit consumer tasks
            consumer_futures = []
            for i in range(num_consumers):
                expected = total_messages // num_consumers + (1 if i < (total_messages % num_consumers) else 0)
                future = executor.submit(
                    self._high_throughput_consumer,
                    large_queue, expected, f"cons{i}"
                )
                consumer_futures.append(future)
            
            # Collect results
            producer_results = []
            consumer_results = []
            
            for future in as_completed(producer_futures, timeout=30):
                result = future.result()
                if isinstance(result, list):
                    producer_results.extend(result)
            
            for future in as_completed(consumer_futures, timeout=30):
                result = future.result()
                if isinstance(result, list):
                    consumer_results.extend(result)
        
        duration = time.time() - start_time
        
        # Verify results
        assert len(producer_results) == total_messages
        assert len(consumer_results) == total_messages
        assert set(producer_results) == set(consumer_results)
        
        # Performance verification
        throughput = total_messages / duration
        assert throughput > 1000, f"Throughput too low: {throughput:.2f} msg/s"
        assert duration < 30, f"Test took too long: {duration:.2f}s"
    
    def _high_throughput_producer(self, queue, num_messages: int, prefix: str):
        """High-throughput producer helper"""
        results = []
        try:
            for i in range(num_messages):
                message = f"{prefix}_{i}"
                queue.put(message)
                results.append(message)
                
                # No delays for maximum throughput
        except Exception as e:
            raise RuntimeError(f"Producer {prefix} failed: {str(e)}")
        
        return results
    
    def _high_throughput_consumer(self, queue, num_messages: int, consumer_id: str):
        """High-throughput consumer helper"""
        results = []
        try:
            for _ in range(num_messages):
                message = queue.get(timeout=5.0)
                results.append(message)
        except Exception as e:
            raise RuntimeError(f"Consumer {consumer_id} failed: {str(e)}")
        
        return results


@pytest.mark.integration
@pytest.mark.threading
class TestThreadingErrorHandling:
    """Test error handling in threading scenarios"""
    
    def test_thread_safety_under_errors(self, medium_queue):
        """Test thread safety when errors occur"""
        num_threads = 8
        operations_per_thread = 50
        
        errors = []
        successful_operations = []
        lock = threading.Lock()
        
        def worker_with_errors(thread_id):
            """Worker that occasionally encounters errors"""
            for i in range(operations_per_thread):
                try:
                    if i % 10 == 0 and thread_id % 2 == 0:
                        # Occasionally try invalid operations
                        medium_queue.put(None, timeout=-1)  # Invalid timeout
                    else:
                        # Normal operations
                        medium_queue.put(f"msg_{thread_id}_{i}")
                        if not medium_queue.empty():
                            msg = medium_queue.get_nowait()
                            with lock:
                                successful_operations.append(msg)
                except Exception as e:
                    with lock:
                        errors.append(f"Thread {thread_id}: {str(e)}")
        
        # Start threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=worker_with_errors, args=(i,))
            thread.start()
            threads.append(thread)
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=15)
        
        # System should remain stable despite errors
        assert len(successful_operations) > 0, "No successful operations"
        assert len(errors) > 0, "Expected some errors to occur"
        
        # Queue should still be functional
        medium_queue.put("final_test")
        result = medium_queue.get()
        assert result == "final_test"
    
    def test_concurrent_queue_lifecycle(self, queue_name):
        """Test concurrent queue creation/destruction"""
        from sage.extensions.sage_queue.python.sage_queue import SageQueue
        
        num_threads = 4
        operations_per_thread = 10
        
        def lifecycle_worker(thread_id):
            """Worker that creates and destroys queues"""
            for i in range(operations_per_thread):
                local_queue_name = f"{queue_name}_{thread_id}_{i}"
                try:
                    # Create queue
                    queue = SageQueue(local_queue_name, maxsize=1024)
                    
                    # Use queue
                    queue.put(f"test_{thread_id}_{i}")
                    result = queue.get()
                    assert result == f"test_{thread_id}_{i}"
                    
                    # Close queue
                    queue.close()
                    
                except Exception as e:
                    pytest.fail(f"Thread {thread_id} operation {i} failed: {str(e)}")
        
        # Start threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=lifecycle_worker, args=(i,))
            thread.start()
            threads.append(thread)
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=20)
        
        # All threads should have completed successfully
        for thread in threads:
            assert not thread.is_alive(), "Thread did not complete"
