"""
Performance benchmark tests for SAGE Queue
"""

import pytest
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from .. import PERFORMANCE_BENCHMARKS
from ..utils import DataGenerator, PerformanceCollector, measure_time, generate_test_data_sizes


@pytest.mark.performance
class TestThroughputBenchmarks:
    """Throughput performance benchmarks"""
    
    @pytest.mark.parametrize("message_size", generate_test_data_sizes())
    def test_single_thread_throughput(self, large_queue, message_size, performance_monitor):
        """Benchmark single-threaded throughput for various message sizes"""
        num_messages = 1000
        message_data = DataGenerator.string(message_size)
        
        performance_monitor.start()
        
        # Measure put throughput
        start_time = time.time()
        for i in range(num_messages):
            large_queue.put(f"{i}_{message_data}")
        put_duration = time.time() - start_time
        
        # Measure get throughput
        start_time = time.time()
        for i in range(num_messages):
            large_queue.get()
        get_duration = time.time() - start_time
        
        performance_monitor.stop()
        
        # Calculate throughput
        put_throughput = num_messages / put_duration
        get_throughput = num_messages / get_duration
        
        # Assert minimum performance requirements
        min_throughput = PERFORMANCE_BENCHMARKS["min_throughput_msg_per_sec"]
        assert put_throughput >= min_throughput, f"Put throughput too low: {put_throughput:.2f} msg/s"
        assert get_throughput >= min_throughput, f"Get throughput too low: {get_throughput:.2f} msg/s"
        
        # Log performance metrics
        print(f"\nMessage size: {message_size} bytes")
        print(f"Put throughput: {put_throughput:.2f} msg/s")
        print(f"Get throughput: {get_throughput:.2f} msg/s")
        print(f"Total duration: {performance_monitor.duration:.3f}s")
    
    def test_multithreaded_throughput(self, large_queue, performance_monitor):
        """Benchmark multithreaded throughput"""
        num_threads = 4
        messages_per_thread = 250
        total_messages = num_threads * messages_per_thread
        message_data = DataGenerator.string(100)
        
        def producer_worker(thread_id):
            results = []
            for i in range(messages_per_thread):
                message = f"t{thread_id}_m{i}_{message_data}"
                start = time.time()
                large_queue.put(message)
                duration = time.time() - start
                results.append(duration)
            return results
        
        def consumer_worker():
            results = []
            for _ in range(messages_per_thread):
                start = time.time()
                large_queue.get(timeout=10.0)
                duration = time.time() - start
                results.append(duration)
            return results
        
        performance_monitor.start()
        
        with ThreadPoolExecutor(max_workers=num_threads * 2) as executor:
            # Start producers
            producer_futures = [
                executor.submit(producer_worker, i) for i in range(num_threads)
            ]
            
            # Start consumers
            consumer_futures = [
                executor.submit(consumer_worker) for _ in range(num_threads)
            ]
            
            # Wait for completion
            all_put_times = []
            for future in producer_futures:
                all_put_times.extend(future.result())
            
            all_get_times = []
            for future in consumer_futures:
                all_get_times.extend(future.result())
        
        performance_monitor.stop()
        
        # Calculate aggregate throughput
        total_duration = performance_monitor.duration
        aggregate_throughput = total_messages / total_duration
        
        # Calculate average latencies
        avg_put_latency = statistics.mean(all_put_times)
        avg_get_latency = statistics.mean(all_get_times)
        
        # Performance assertions
        min_throughput = PERFORMANCE_BENCHMARKS["min_throughput_msg_per_sec"]
        max_latency = PERFORMANCE_BENCHMARKS["max_latency_ms"] / 1000  # Convert to seconds
        
        assert aggregate_throughput >= min_throughput, f"Aggregate throughput too low: {aggregate_throughput:.2f} msg/s"
        assert avg_put_latency <= max_latency, f"Put latency too high: {avg_put_latency:.6f}s"
        assert avg_get_latency <= max_latency, f"Get latency too high: {avg_get_latency:.6f}s"
        
        # Log results
        print(f"\nMultithreaded throughput: {aggregate_throughput:.2f} msg/s")
        print(f"Average put latency: {avg_put_latency:.6f}s")
        print(f"Average get latency: {avg_get_latency:.6f}s")
        print(f"Total test duration: {total_duration:.3f}s")


@pytest.mark.performance
class TestLatencyBenchmarks:
    """Latency performance benchmarks"""
    
    def test_roundtrip_latency(self, medium_queue):
        """Benchmark round-trip latency"""
        num_operations = 1000
        message = DataGenerator.string(100)
        
        latencies = []
        
        for i in range(num_operations):
            start_time = time.time()
            medium_queue.put(f"{i}_{message}")
            result = medium_queue.get()
            end_time = time.time()
            
            latency = end_time - start_time
            latencies.append(latency)
        
        # Calculate statistics
        avg_latency = statistics.mean(latencies)
        p50_latency = statistics.median(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
        
        # Performance assertions
        max_latency = PERFORMANCE_BENCHMARKS["max_latency_ms"] / 1000
        assert avg_latency <= max_latency, f"Average latency too high: {avg_latency:.6f}s"
        assert p95_latency <= max_latency * 2, f"P95 latency too high: {p95_latency:.6f}s"
        
        # Log results
        print(f"\nLatency statistics:")
        print(f"Average: {avg_latency:.6f}s ({avg_latency*1000:.3f}ms)")
        print(f"P50: {p50_latency:.6f}s ({p50_latency*1000:.3f}ms)")
        print(f"P95: {p95_latency:.6f}s ({p95_latency*1000:.3f}ms)")
        print(f"P99: {p99_latency:.6f}s ({p99_latency*1000:.3f}ms)")
    
    def test_concurrent_latency(self, large_queue):
        """Benchmark latency under concurrent load"""
        num_threads = 4
        operations_per_thread = 100
        message = DataGenerator.string(50)
        
        all_latencies = []
        latency_lock = threading.Lock()
        
        def latency_worker(thread_id):
            thread_latencies = []
            for i in range(operations_per_thread):
                start_time = time.time()
                large_queue.put(f"t{thread_id}_m{i}_{message}")
                large_queue.get()
                end_time = time.time()
                
                latency = end_time - start_time
                thread_latencies.append(latency)
            
            with latency_lock:
                all_latencies.extend(thread_latencies)
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=latency_worker, args=(i,))
            thread.start()
            threads.append(thread)
        
        for thread in threads:
            thread.join()
        
        # Calculate statistics
        avg_latency = statistics.mean(all_latencies)
        p95_latency = sorted(all_latencies)[int(len(all_latencies) * 0.95)]
        
        # Under concurrent load, allow higher latency
        max_concurrent_latency = PERFORMANCE_BENCHMARKS["max_latency_ms"] / 1000 * 3
        assert avg_latency <= max_concurrent_latency, f"Concurrent average latency too high: {avg_latency:.6f}s"
        
        print(f"\nConcurrent latency (threads={num_threads}):")
        print(f"Average: {avg_latency:.6f}s ({avg_latency*1000:.3f}ms)")
        print(f"P95: {p95_latency:.6f}s ({p95_latency*1000:.3f}ms)")


@pytest.mark.performance
class TestMemoryEfficiency:
    """Memory efficiency benchmarks"""
    
    def test_memory_usage_scaling(self, performance_monitor):
        """Test memory usage with increasing queue sizes"""
        try:
            import psutil
        except ImportError:
            pytest.skip("psutil required for memory testing")
        
        try:
            from sage.extensions.sage_queue.python.sage_queue import SageQueue
        except ImportError:
            pytest.skip("Real SageQueue module required for memory testing")
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        queue_sizes = [1024, 4096, 16384, 65536]  # Various sizes
        memory_usage = []
        
        for size in queue_sizes:
            queue_name = f"memory_test_{size}_{int(time.time())}"
            queue = SageQueue(queue_name, maxsize=size)
            
            # Fill queue to capacity
            message = DataGenerator.string(100)
            items_added = 0
            try:
                while items_added < size // 200:  # Don't completely fill to avoid blocking
                    queue.put(f"{items_added}_{message}")
                    items_added += 1
            except:
                pass  # Queue might be full
            
            current_memory = process.memory_info().rss
            memory_used = current_memory - initial_memory
            memory_usage.append((size, memory_used, items_added))
            
            queue.close()
            
            # Allow garbage collection
            import gc
            gc.collect()
            time.sleep(0.1)
        
        # Analyze memory efficiency
        for size, memory_used, items in memory_usage:
            memory_mb = memory_used / (1024 * 1024)
            memory_per_item = memory_used / items if items > 0 else 0
            
            print(f"\nQueue size {size}: {memory_mb:.2f}MB, {items} items, {memory_per_item:.0f} bytes/item")
            
            # Assert reasonable memory usage
            max_memory_mb = PERFORMANCE_BENCHMARKS["max_memory_usage_mb"]
            assert memory_mb <= max_memory_mb, f"Memory usage too high: {memory_mb:.2f}MB"
    
    @pytest.mark.slow
    def test_memory_leak_detection(self, performance_monitor):
        """Test for memory leaks during extended operation"""
        try:
            import psutil
        except ImportError:
            pytest.skip("psutil required for memory leak testing")
        
        try:
            from sage.extensions.sage_queue.python.sage_queue import SageQueue
        except ImportError:
            pytest.skip("Real SageQueue module required for memory leak testing")
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Run multiple cycles of queue creation/usage/cleanup
        num_cycles = 50
        messages_per_cycle = 100
        
        memory_samples = []
        
        for cycle in range(num_cycles):
            queue_name = f"leak_test_{cycle}_{int(time.time())}"
            queue = SageQueue(queue_name, maxsize=10000)
            
            # Use the queue intensively
            message = DataGenerator.string(200)
            for i in range(messages_per_cycle):
                queue.put(f"cycle{cycle}_msg{i}_{message}")
            
            for i in range(messages_per_cycle):
                queue.get()
            
            # Close and cleanup
            queue.close()
            
            # Sample memory every 10 cycles
            if cycle % 10 == 0:
                import gc
                gc.collect()  # Force garbage collection
                current_memory = process.memory_info().rss
                memory_samples.append(current_memory - initial_memory)
        
        # Analyze memory growth trend
        if len(memory_samples) >= 3:
            # Check if memory is growing significantly
            first_half = memory_samples[:len(memory_samples)//2]
            second_half = memory_samples[len(memory_samples)//2:]
            
            avg_first_half = statistics.mean(first_half)
            avg_second_half = statistics.mean(second_half)
            
            memory_growth = avg_second_half - avg_first_half
            memory_growth_mb = memory_growth / (1024 * 1024)
            
            print(f"\nMemory leak test:")
            print(f"Initial memory baseline: {initial_memory / (1024 * 1024):.2f}MB")
            print(f"Memory growth over {num_cycles} cycles: {memory_growth_mb:.2f}MB")
            
            # Allow some growth but not excessive
            max_growth_mb = 20  # 20MB growth limit
            assert memory_growth_mb <= max_growth_mb, f"Potential memory leak: {memory_growth_mb:.2f}MB growth"


@pytest.mark.performance
@pytest.mark.slow
class TestStressBenchmarks:
    """Stress test benchmarks"""
    
    def test_sustained_high_load(self, large_queue, performance_monitor):
        """Test sustained high-load performance"""
        duration_seconds = 30
        num_producers = 2
        num_consumers = 2
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        stats = {
            "messages_produced": 0,
            "messages_consumed": 0,
            "errors": []
        }
        stats_lock = threading.Lock()
        
        def sustained_producer(producer_id):
            message = DataGenerator.string(100)
            count = 0
            while time.time() < end_time:
                try:
                    large_queue.put(f"p{producer_id}_m{count}_{message}", timeout=1.0)
                    count += 1
                except:
                    with stats_lock:
                        stats["errors"].append(f"Producer {producer_id} put failed")
                    time.sleep(0.001)  # Brief pause on error
            
            with stats_lock:
                stats["messages_produced"] += count
        
        def sustained_consumer(consumer_id):
            count = 0
            while time.time() < end_time:
                try:
                    large_queue.get(timeout=1.0)
                    count += 1
                except:
                    time.sleep(0.001)  # Brief pause if queue empty
            
            with stats_lock:
                stats["messages_consumed"] += count
        
        performance_monitor.start()
        
        # Start workers
        threads = []
        
        for i in range(num_producers):
            thread = threading.Thread(target=sustained_producer, args=(i,))
            thread.start()
            threads.append(thread)
        
        for i in range(num_consumers):
            thread = threading.Thread(target=sustained_consumer, args=(i,))
            thread.start()
            threads.append(thread)
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        performance_monitor.stop()
        
        # Analyze results
        actual_duration = performance_monitor.duration
        avg_throughput = (stats["messages_produced"] + stats["messages_consumed"]) / (2 * actual_duration)
        error_rate = len(stats["errors"]) / (stats["messages_produced"] + len(stats["errors"]))
        
        print(f"\nSustained load test ({actual_duration:.1f}s):")
        print(f"Messages produced: {stats['messages_produced']}")
        print(f"Messages consumed: {stats['messages_consumed']}")
        print(f"Average throughput: {avg_throughput:.2f} msg/s")
        print(f"Error rate: {error_rate:.3%}")
        print(f"Errors: {len(stats['errors'])}")
        
        # Performance assertions
        min_sustained_throughput = PERFORMANCE_BENCHMARKS["min_throughput_msg_per_sec"] * 0.8  # Allow 20% reduction under stress
        assert avg_throughput >= min_sustained_throughput, f"Sustained throughput too low: {avg_throughput:.2f} msg/s"
        assert error_rate <= 0.05, f"Error rate too high: {error_rate:.3%}"  # Max 5% error rate
    
    def test_burst_load_handling(self, large_queue):
        """Test handling of burst loads"""
        burst_size = 2000
        num_bursts = 5
        burst_interval = 2.0  # seconds between bursts
        
        message = DataGenerator.string(50)
        total_sent = 0
        total_received = 0
        
        def burst_producer():
            nonlocal total_sent
            for burst in range(num_bursts):
                # Send burst
                for i in range(burst_size):
                    large_queue.put(f"burst{burst}_msg{i}_{message}")
                    total_sent += 1
                
                # Wait before next burst
                if burst < num_bursts - 1:
                    time.sleep(burst_interval)
        
        def burst_consumer():
            nonlocal total_received
            expected_total = burst_size * num_bursts
            while total_received < expected_total:
                try:
                    large_queue.get(timeout=5.0)
                    total_received += 1
                except:
                    break  # Timeout or other error
        
        import threading
        
        start_time = time.time()
        
        # Start producer and consumer
        producer_thread = threading.Thread(target=burst_producer)
        consumer_thread = threading.Thread(target=burst_consumer)
        
        producer_thread.start()
        consumer_thread.start()
        
        producer_thread.join()
        consumer_thread.join()
        
        duration = time.time() - start_time
        
        print(f"\nBurst load test:")
        print(f"Bursts: {num_bursts} x {burst_size} messages")
        print(f"Total sent: {total_sent}")
        print(f"Total received: {total_received}")
        print(f"Duration: {duration:.2f}s")
        print(f"Success rate: {total_received/total_sent:.3%}")
        
        # Verify successful handling
        assert total_sent == burst_size * num_bursts, "Not all messages were sent"
        assert total_received >= total_sent * 0.95, f"Too many messages lost: {total_received}/{total_sent}"
