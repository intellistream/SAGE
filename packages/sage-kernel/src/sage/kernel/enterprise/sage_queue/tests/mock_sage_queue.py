"""
Mock implementation for testing the test suite infrastructure
"""

import queue
import time
import threading
from typing import Any, Optional


class MockSageQueue:
    """Mock implementation of SageQueue for testing purposes"""
    
    def __init__(self, name: str, maxsize: int = 0, auto_cleanup: bool = True, 
                 namespace: Optional[str] = None, enable_multi_tenant: bool = True,
                 disable_signal_handlers: bool = False):
        if not isinstance(maxsize, int) or maxsize < 0:
            raise ValueError("maxsize must be a non-negative integer")
        self.name = name
        self.maxsize = maxsize
        self.auto_cleanup = auto_cleanup
        self.namespace = namespace
        self.enable_multi_tenant = enable_multi_tenant
        self._queue = queue.Queue(maxsize=maxsize)
        self._closed = False
        self._stats = {
            'put_count': 0,
            'get_count': 0,
            'created_time': time.time()
        }
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        if self._closed:
            raise RuntimeError("Queue is closed")
        # Simulate pickle validation for unpickleable objects
        try:
            import pickle
            pickle.dumps(item)
        except (pickle.PicklingError, TypeError) as e:
            raise e
        self._queue.put(item, block=block, timeout=timeout)
        self._stats['put_count'] += 1
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        if self._closed:
            raise RuntimeError("Queue is closed")
        item = self._queue.get(block=block, timeout=timeout)
        self._stats['get_count'] += 1
        return item
    
    def put_nowait(self, item: Any) -> None:
        self.put(item, block=False)
    
    def get_nowait(self) -> Any:
        return self.get(block=False)
    
    def empty(self) -> bool:
        return self._queue.empty()
    
    def full(self) -> bool:
        return self._queue.full()
    
    def qsize(self) -> int:
        return self._queue.qsize()
    
    def get_stats(self) -> dict:
        """获取队列统计信息"""
        return {
            'name': self.name,
            'maxsize': self.maxsize,
            'current_size': self.qsize(),
            'put_count': self._stats['put_count'],
            'get_count': self._stats['get_count'],
            'uptime': time.time() - self._stats['created_time'],
            'mock_queue': True
        }
    
    def close(self):
        self._closed = True
    
    def destroy(self):
        """销毁队列"""
        self._closed = True


class MockSageQueueManager:
    """Mock implementation of SageQueueManager for testing purposes"""
    
    def __init__(self):
        self._queues = {}
        self._lock = threading.Lock()
    
    def create_queue(self, name: str, maxsize: int = 0) -> MockSageQueue:
        # Validate parameters
        if not isinstance(maxsize, int) or maxsize < 0:
            raise ValueError("maxsize must be a non-negative integer")
        if not isinstance(name, str):
            raise TypeError("name must be a string")
            
        with self._lock:
            if name in self._queues:
                return self._queues[name]
            queue = MockSageQueue(name, maxsize)
            self._queues[name] = queue
            return queue
    
    def get_queue(self, name: str) -> MockSageQueue:
        with self._lock:
            if name not in self._queues:
                raise KeyError(f"Queue '{name}' not found")
            return self._queues[name]
    
    def cleanup_all(self):
        with self._lock:
            for queue in self._queues.values():
                queue.close()
            self._queues.clear()


# Set global variables for fallback
SageQueue = MockSageQueue
SageQueueManager = MockSageQueueManager
