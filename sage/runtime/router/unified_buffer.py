"""
统一的进程间通信缓冲区接口
支持本地进程间通信和Ray分布式通信
"""

from abc import ABC, abstractmethod
from typing import Any, Union
import ray
from ray.util.queue import Queue as RayQueue
from sage.utils.mmap_queue.sage_queue import SageQueue

class UnifiedBuffer(ABC):
    """统一的缓冲区接口"""
    
    @abstractmethod
    def put(self, item: Any) -> bool:
        """放入数据"""
        pass
    
    @abstractmethod
    def get(self, timeout: float = None) -> Any:
        """获取数据"""
        pass
    
    @abstractmethod
    def qsize(self) -> int:
        """获取队列大小"""
        pass
    
    @abstractmethod
    def empty(self) -> bool:
        """检查队列是否为空"""
        pass


class LocalBuffer(UnifiedBuffer):
    """本地缓冲区实现（基于SageQueue）"""
    
    def __init__(self, name: str, maxsize: int = 1000):
        self.buffer = SageQueue(name=name, maxsize=maxsize)
    
    def put(self, item: Any) -> bool:
        try:
            self.buffer.put(item, block=False)
            return True
        except:
            return False
    
    def get(self, timeout: float = None) -> Any:
        return self.buffer.get(timeout=timeout)
    
    def qsize(self) -> int:
        return self.buffer.qsize()
    
    def empty(self) -> bool:
        return self.buffer.empty()


class RemoteBuffer(UnifiedBuffer):
    """远程缓冲区实现（基于Ray Queue）"""
    
    def __init__(self, name: str, maxsize: int = 1000):
        self.buffer = RayQueue(maxsize=maxsize)
    
    def put(self, item: Any) -> bool:
        try:
            self.buffer.put(item, block=False)
            return True
        except:
            return False
    
    def get(self, timeout: float = None) -> Any:
        return self.buffer.get(timeout=timeout)
    
    def qsize(self) -> int:
        return self.buffer.qsize()
    
    def empty(self) -> bool:
        return self.buffer.empty()


def create_unified_buffer(name: str, is_remote: bool = False, maxsize: int = 1000) -> UnifiedBuffer:
    """
    创建统一缓冲区
    
    Args:
        name: 缓冲区名称
        is_remote: 是否为远程缓冲区
        maxsize: 最大大小
        
    Returns:
        UnifiedBuffer实例
    """
    if is_remote:
        return RemoteBuffer(name, maxsize)
    else:
        return LocalBuffer(name, maxsize)
