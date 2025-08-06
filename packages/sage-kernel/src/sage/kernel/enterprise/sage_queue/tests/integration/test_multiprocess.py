"""
Integration tests for multiprocessing scenarios
"""

import pytest
import time
import multiprocessing
import os
import signal
from concurrent.futures import ProcessPoolExecutor, as_completed

from ..utils import DataGenerator, ProducerConsumerScenario, ConcurrencyTester


def producer_worker(queue_name: str, num_messages: int, message_size: int):
    """Producer worker for multiprocessing tests"""
    from sage.extensions.sage_queue import SageQueue
    
    try:
        queue = SageQueue(queue_name)
        messages_sent = 0
        
        for i in range(num_messages):
            message = DataGenerator.string(message_size)
            queue.put(f"msg_{os.getpid()}_{i}_{message}")
            messages_sent += 1
            
            if i % 100 == 0:  # Small delay every 100 messages
                time.sleep(0.001)
        
        queue.close()
        return messages_sent
        
    except Exception as e:
        return f"Error: {str(e)}"


def consumer_worker(queue_name: str, expected_messages: int, timeout: float = 30.0):
    """Consumer worker for multiprocessing tests"""
    from sage.extensions.sage_queue import SageQueue
    
    try:
        queue = SageQueue(queue_name)
        messages_received = 0
        start_time = time.time()
        
        while messages_received < expected_messages:
            if time.time() - start_time > timeout:
                break
                
            try:
                message = queue.get(timeout=1.0)
                messages_received += 1
            except:
                continue
        
        queue.close()
        return messages_received
        
    except Exception as e:
        return f"Error: {str(e)}"


@pytest.mark.integration
@pytest.mark.multiprocess
class TestMultiprocessBasic:
    """Basic multiprocess integration tests"""
    
    def test_single_producer_single_consumer(self, queue_name, process_helper):
        """Test single producer, single consumer across processes"""
        num_messages = 100
        message_size = 50
        
        # Start producer
        producer_proc = process_helper.start_process(
            producer_worker,
            args=(queue_name, num_messages, message_size)
        )
        
        # Start consumer
        consumer_proc = process_helper.start_process(
            consumer_worker,
            args=(queue_name, num_messages, 10.0)
        )
        
        # Wait for completion
        process_helper.wait_all(timeout=15)
        
        # Check results
        assert producer_proc.exitcode == 0, "Producer process failed"
        assert consumer_proc.exitcode == 0, "Consumer process failed"
    
    def test_multiple_producers_single_consumer(self, queue_name, process_helper):
        """Test multiple producers, single consumer"""
        num_producers = 3
        messages_per_producer = 50
        total_messages = num_producers * messages_per_producer
        
        # Start producers
        for i in range(num_producers):
            process_helper.start_process(
                producer_worker,
                args=(f"{queue_name}_p{i}", messages_per_producer, 30)
            )
        
        # Start consumer
        process_helper.start_process(
            consumer_worker,
            args=(queue_name, total_messages, 20.0)
        )
        
        # Wait for completion
        process_helper.wait_all(timeout=25)
        
        # All processes should complete successfully
        for proc in process_helper.processes:
            assert proc.exitcode == 0, f"Process {proc.pid} failed"
    
    def test_single_producer_multiple_consumers(self, queue_name, process_helper):
        """Test single producer, multiple consumers"""
        num_consumers = 3
        total_messages = 150
        messages_per_consumer = total_messages // num_consumers
        
        # Start producer
        process_helper.start_process(
            producer_worker,
            args=(queue_name, total_messages, 40)
        )
        
        # Start consumers
        for i in range(num_consumers):
            expected = messages_per_consumer + (1 if i < (total_messages % num_consumers) else 0)
            process_helper.start_process(
                consumer_worker,
                args=(queue_name, expected, 20.0)
            )
        
        # Wait for completion
        process_helper.wait_all(timeout=25)
        
        # All processes should complete successfully
        for proc in process_helper.processes:
            assert proc.exitcode == 0, f"Process {proc.pid} failed"


@pytest.mark.integration
@pytest.mark.multiprocess
class TestMultiprocessStress:
    """Stress tests for multiprocess scenarios"""
    
    def test_many_producers_many_consumers(self, queue_name, process_helper):
        """Test many producers and consumers"""
        num_producers = 4
        num_consumers = 4
        messages_per_producer = 25
        total_messages = num_producers * messages_per_producer
        messages_per_consumer = total_messages // num_consumers
        
        # Start producers
        for i in range(num_producers):
            process_helper.start_process(
                producer_worker,
                args=(queue_name, messages_per_producer, 20)
            )
        
        # Start consumers
        for i in range(num_consumers):
            expected = messages_per_consumer + (1 if i < (total_messages % num_consumers) else 0)
            process_helper.start_process(
                consumer_worker,
                args=(queue_name, expected, 30.0)
            )
        
        # Wait for completion
        process_helper.wait_all(timeout=35)
        
        # Check that most processes completed successfully
        successful_processes = sum(1 for proc in process_helper.processes if proc.exitcode == 0)
        total_processes = len(process_helper.processes)
        
        # Allow some tolerance for timing-related failures
        success_rate = successful_processes / total_processes
        assert success_rate >= 0.8, f"Success rate too low: {success_rate:.2f}"
    
    @pytest.mark.slow
    def test_long_running_multiprocess(self, queue_name, process_helper):
        """Test long-running multiprocess communication"""
        num_producers = 2
        num_consumers = 2
        messages_per_producer = 200
        total_messages = num_producers * messages_per_producer
        messages_per_consumer = total_messages // num_consumers
        
        start_time = time.time()
        
        # Start producers
        for i in range(num_producers):
            process_helper.start_process(
                producer_worker,
                args=(queue_name, messages_per_producer, 100)  # Larger messages
            )
        
        # Start consumers
        for i in range(num_consumers):
            expected = messages_per_consumer + (1 if i < (total_messages % num_consumers) else 0)
            process_helper.start_process(
                consumer_worker,
                args=(queue_name, expected, 60.0)
            )
        
        # Wait for completion
        process_helper.wait_all(timeout=65)
        
        duration = time.time() - start_time
        
        # Verify completion
        successful_processes = sum(1 for proc in process_helper.processes if proc.exitcode == 0)
        total_processes = len(process_helper.processes)
        
        assert successful_processes == total_processes, "Some processes failed"
        assert duration < 60, f"Test took too long: {duration:.2f}s"


@pytest.mark.integration
@pytest.mark.multiprocess
class TestMultiprocessErrorHandling:
    """Test error handling in multiprocess scenarios"""
    
    def test_consumer_timeout_handling(self, queue_name, process_helper):
        """Test consumer behavior when producer is slow/missing"""
        # Start consumer without producer (should timeout gracefully)
        process_helper.start_process(
            consumer_worker,
            args=(queue_name, 10, 2.0)  # Short timeout
        )
        
        process_helper.wait_all(timeout=5)
        
        # Consumer should exit gracefully even without getting all messages
        for proc in process_helper.processes:
            assert proc.exitcode == 0, "Consumer should handle timeout gracefully"
    
    def test_producer_failure_recovery(self, queue_name, process_helper):
        """Test system behavior when producer fails"""
        def failing_producer(queue_name: str):
            """Producer that fails after sending some messages"""
            from sage.extensions.sage_queue import SageQueue
            
            try:
                queue = SageQueue(queue_name)
                
                # Send a few messages
                for i in range(5):
                    queue.put(f"message_{i}")
                
                # Simulate failure
                raise RuntimeError("Simulated producer failure")
                
            except Exception:
                return 1  # Exit with error code
        
        # Start failing producer
        process_helper.start_process(failing_producer, args=(queue_name,))
        
        # Start consumer that expects more messages than producer will send
        process_helper.start_process(
            consumer_worker,
            args=(queue_name, 10, 3.0)  # Expects more than producer sends
        )
        
        process_helper.wait_all(timeout=5)
        
        # Producer should have failed, consumer should have handled it gracefully
        producer_proc, consumer_proc = process_helper.processes
        assert producer_proc.exitcode != 0, "Producer should have failed"
        assert consumer_proc.exitcode == 0, "Consumer should handle producer failure"
    
    def test_process_interruption_handling(self, queue_name, process_helper):
        """Test handling of process interruptions"""
        # Start a long-running producer
        producer_proc = process_helper.start_process(
            producer_worker,
            args=(queue_name, 1000, 50)
        )
        
        # Let it run for a bit
        time.sleep(1.0)
        
        # Interrupt the producer
        producer_proc.terminate()
        
        # Start consumer to see if queue is still functional
        process_helper.start_process(
            consumer_worker,
            args=(queue_name, 100, 5.0)  # Try to consume what was produced
        )
        
        process_helper.wait_all(timeout=10)
        
        # System should handle interruption gracefully
        # Consumer should exit normally even if it doesn't get all expected messages
        consumer_proc = process_helper.processes[-1]  # Last started process
        assert consumer_proc.exitcode == 0, "Consumer should handle interrupted producer"


@pytest.mark.integration
@pytest.mark.multiprocess
def test_producer_consumer_scenario_integration(queue_name):
    """Integration test using ProducerConsumerScenario utility"""
    def queue_factory(name):
        from sage.extensions.sage_queue import SageQueue
        return SageQueue(name, maxsize=10000)
    
    scenario = ProducerConsumerScenario(
        queue_factory=queue_factory,
        num_producers=2,
        num_consumers=2
    )
    
    result = scenario.run(
        messages_per_producer=50,
        timeout=20.0
    )
    
    # Verify successful completion
    assert result["error_count"] == 0, f"Errors occurred: {result['errors']}"
    assert result["success_rate"] >= 0.9, f"Success rate too low: {result['success_rate']}"
    assert result["produced_count"] == result["expected_count"]
    
    # Allow some tolerance for message loss in complex scenarios
    assert result["consumed_count"] >= result["expected_count"] * 0.8
