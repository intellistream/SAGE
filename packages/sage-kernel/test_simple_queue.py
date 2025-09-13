#!/usr/bin/env python3
"""
Ray Actor测试用的简单队列实现，避开ray.util.queue的async actor限制
"""

import queue
import threading
import time


class SimpleTestQueue:
    """用于测试的简单队列实现，模拟Ray队列的接口"""
    
    def __init__(self, maxsize=0):
        self.maxsize = maxsize
        self._queue = queue.Queue(maxsize=maxsize)
        self._lock = threading.Lock()
        
    def put(self, item, timeout=None):
        """向队列添加项目"""
        return self._queue.put(item, timeout=timeout)
    
    def get(self, timeout=None):
        """从队列获取项目"""
        return self._queue.get(timeout=timeout)
    
    def qsize(self):
        """获取队列大小"""
        return self._queue.qsize()
    
    def empty(self):
        """检查队列是否为空"""
        return self._queue.empty()
    
    def full(self):
        """检查队列是否已满"""
        return self._queue.full()