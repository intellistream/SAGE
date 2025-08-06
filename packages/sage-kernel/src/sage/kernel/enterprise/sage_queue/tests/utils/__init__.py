"""
Test utilities for SAGE Queue tests
"""

import time
import threading
import multiprocessing
import queue
import random
import string
import json
from typing import Any, List, Dict, Optional, Union, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed


@dataclass
class MessageData:
    """Test message with metadata"""
    id: str
    payload: Any
    timestamp: float
    size: int
    
    @classmethod
    def create(cls, payload: Any, message_id: Optional[str] = None):
        """Create a test message"""
        if message_id is None:
            message_id = f"msg_{int(time.time() * 1000000)}"
        
        # Calculate size
        if isinstance(payload, (str, bytes)):
            size = len(payload)
        else:
            try:
                size = len(json.dumps(payload).encode('utf-8'))
            except:
                size = 0
        
        return cls(
            id=message_id,
            payload=payload,
            timestamp=time.time(),
            size=size
        )


class DataGenerator:
    """Generate test data of various types and sizes"""
    
    @staticmethod
    def string(size: int) -> str:
        """Generate a string of specified size"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=size))
    
    @staticmethod
    def bytes_data(size: int) -> bytes:
        """Generate bytes data of specified size"""
        return bytes(random.getrandbits(8) for _ in range(size))
    
    @staticmethod
    def dict_data(keys: int = 10, value_size: int = 100) -> Dict[str, Any]:
        """Generate dictionary with specified number of keys"""
        return {
            f"key_{i}": DataGenerator.string(value_size)
            for i in range(keys)
        }
    
    @staticmethod
    def list_data(items: int = 10, item_size: int = 100) -> List[str]:
        """Generate list with specified number of items"""
        return [DataGenerator.string(item_size) for _ in range(items)]
    
    @staticmethod
    def nested_data(depth: int = 3, width: int = 5) -> Dict[str, Any]:
        """Generate nested data structure"""
        if depth == 0:
            return DataGenerator.string(50)
        
        return {
            f"level_{depth}_item_{i}": DataGenerator.nested_data(depth - 1, width)
            for i in range(width)
        }
    
    @staticmethod
    def mixed_types() -> List[Any]:
        """Generate data with mixed types"""
        return [
            "string_value",
            42,
            3.14159,
            True,
            None,
            [1, 2, 3],
            {"nested": "dict"},
            (1, 2, 3)
        ]


class PerformanceCollector:
    """Collect and analyze performance metrics"""
    
    def __init__(self):
        self.metrics = {
            "latency": [],
            "throughput": [],
            "memory": [],
            "errors": []
        }
        self._lock = threading.Lock()
    
    def record_latency(self, operation: str, duration: float):
        """Record operation latency"""
        with self._lock:
            self.metrics["latency"].append({
                "operation": operation,
                "duration": duration,
                "timestamp": time.time()
            })
    
    def record_throughput(self, operation: str, count: int, duration: float):
        """Record throughput metrics"""
        rate = count / duration if duration > 0 else 0
        with self._lock:
            self.metrics["throughput"].append({
                "operation": operation,
                "count": count,
                "duration": duration,
                "rate": rate,
                "timestamp": time.time()
            })
    
    def record_memory(self, usage_bytes: int):
        """Record memory usage"""
        with self._lock:
            self.metrics["memory"].append({
                "usage_bytes": usage_bytes,
                "timestamp": time.time()
            })
    
    def record_error(self, operation: str, error: str):
        """Record error"""
        with self._lock:
            self.metrics["errors"].append({
                "operation": operation,
                "error": error,
                "timestamp": time.time()
            })
    
    def get_stats(self, metric_type: str) -> Dict[str, Any]:
        """Get statistics for a metric type"""
        if metric_type not in self.metrics:
            return {}
        
        data = self.metrics[metric_type]
        if not data:
            return {}
        
        if metric_type == "latency":
            durations = [m["duration"] for m in data]
            return {
                "count": len(durations),
                "min": min(durations),
                "max": max(durations),
                "avg": sum(durations) / len(durations),
                "p50": sorted(durations)[len(durations) // 2],
                "p95": sorted(durations)[int(len(durations) * 0.95)],
                "p99": sorted(durations)[int(len(durations) * 0.99)]
            }
        elif metric_type == "throughput":
            rates = [m["rate"] for m in data]
            return {
                "count": len(rates),
                "min_rate": min(rates),
                "max_rate": max(rates),
                "avg_rate": sum(rates) / len(rates),
                "total_operations": sum(m["count"] for m in data)
            }
        elif metric_type == "memory":
            usages = [m["usage_bytes"] for m in data]
            return {
                "count": len(usages),
                "min_usage": min(usages),
                "max_usage": max(usages),
                "avg_usage": sum(usages) / len(usages)
            }
        
        return {"count": len(data)}


class ConcurrencyTester:
    """Helper for concurrent testing scenarios"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.results = []
        self._lock = threading.Lock()
    
    def add_result(self, result: Any):
        """Thread-safe result collection"""
        with self._lock:
            self.results.append(result)
    
    def run_threaded(self, func: Callable, args_list: List[tuple], timeout: Optional[float] = None):
        """Run function concurrently with threading"""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(func, *args) for args in args_list]
            
            results = []
            errors = []
            
            for future in as_completed(futures, timeout=timeout):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    errors.append(str(e))
            
            return results, errors
    
    def run_multiprocess(self, func: Callable, args_list: List[tuple], timeout: Optional[float] = None):
        """Run function concurrently with multiprocessing"""
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(func, *args) for args in args_list]
            
            results = []
            errors = []
            
            for future in as_completed(futures, timeout=timeout):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    errors.append(str(e))
            
            return results, errors


class ProducerConsumerScenario:
    """Producer-Consumer test scenario"""
    
    def __init__(self, queue_factory: Callable, num_producers: int = 2, num_consumers: int = 2):
        self.queue_factory = queue_factory
        self.num_producers = num_producers
        self.num_consumers = num_consumers
        self.results = {
            "produced": multiprocessing.Manager().list(),
            "consumed": multiprocessing.Manager().list(),
            "errors": multiprocessing.Manager().list()
        }
    
    def producer_worker(self, queue_name: str, messages: List[Any], worker_id: int):
        """Producer worker function"""
        try:
            queue = self.queue_factory(queue_name)
            for i, message in enumerate(messages):
                test_msg = MessageData.create(message, f"p{worker_id}_m{i}")
                queue.put(test_msg.payload)
                self.results["produced"].append(test_msg.id)
                time.sleep(0.001)  # Small delay to simulate work
        except Exception as e:
            self.results["errors"].append(f"Producer {worker_id}: {str(e)}")
    
    def consumer_worker(self, queue_name: str, expected_count: int, worker_id: int, timeout: float = 10.0):
        """Consumer worker function"""
        try:
            queue = self.queue_factory(queue_name)
            consumed = 0
            start_time = time.time()
            
            while consumed < expected_count and (time.time() - start_time) < timeout:
                try:
                    message = queue.get(timeout=1.0)
                    self.results["consumed"].append(f"c{worker_id}_item{consumed}")
                    consumed += 1
                except queue.Empty:
                    continue
                    
        except Exception as e:
            self.results["errors"].append(f"Consumer {worker_id}: {str(e)}")
    
    def run(self, messages_per_producer: int = 100, timeout: float = 30.0):
        """Run the producer-consumer scenario"""
        import uuid
        queue_name = f"test_pc_{uuid.uuid4().hex[:8]}"
        
        # Generate test messages
        all_messages = []
        for i in range(self.num_producers):
            producer_messages = [
                DataGenerator.string(random.randint(10, 100))
                for _ in range(messages_per_producer)
            ]
            all_messages.append(producer_messages)
        
        total_messages = self.num_producers * messages_per_producer
        messages_per_consumer = total_messages // self.num_consumers
        
        processes = []
        
        # Start producers
        for i, messages in enumerate(all_messages):
            p = multiprocessing.Process(
                target=self.producer_worker,
                args=(queue_name, messages, i)
            )
            p.start()
            processes.append(p)
        
        # Start consumers
        for i in range(self.num_consumers):
            expected = messages_per_consumer + (1 if i < (total_messages % self.num_consumers) else 0)
            p = multiprocessing.Process(
                target=self.consumer_worker,
                args=(queue_name, expected, i, timeout)
            )
            p.start()
            processes.append(p)
        
        # Wait for completion
        for p in processes:
            p.join(timeout=timeout)
        
        # Cleanup any remaining processes
        for p in processes:
            if p.is_alive():
                p.terminate()
                p.join(timeout=1)
        
        return {
            "produced_count": len(self.results["produced"]),
            "consumed_count": len(self.results["consumed"]),
            "error_count": len(self.results["errors"]),
            "expected_count": total_messages,
            "success_rate": len(self.results["consumed"]) / total_messages if total_messages > 0 else 0,
            "errors": list(self.results["errors"])
        }


def measure_time(func: Callable) -> tuple:
    """Measure execution time of a function"""
    start_time = time.time()
    result = func()
    end_time = time.time()
    return result, end_time - start_time


def generate_test_data_sizes() -> List[int]:
    """Generate various data sizes for testing"""
    return [
        64,      # Small
        256,     # Medium-small
        1024,    # 1KB
        4096,    # 4KB
        16384,   # 16KB
        65536,   # 64KB
    ]


def validate_queue_interface(queue_instance):
    """Validate that queue instance implements expected interface"""
    required_methods = [
        'put', 'get', 'put_nowait', 'get_nowait',
        'empty', 'full', 'qsize', 'close'
    ]
    
    for method in required_methods:
        if not hasattr(queue_instance, method):
            raise AssertionError(f"Queue missing required method: {method}")
        if not callable(getattr(queue_instance, method)):
            raise AssertionError(f"Queue method not callable: {method}")


def assert_performance_within_bounds(metric_value: float, expected_min: float, expected_max: float, metric_name: str):
    """Assert that performance metric is within expected bounds"""
    if metric_value < expected_min:
        raise AssertionError(f"{metric_name} too low: {metric_value} < {expected_min}")
    if metric_value > expected_max:
        raise AssertionError(f"{metric_name} too high: {metric_value} > {expected_max}")
