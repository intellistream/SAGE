"""
Python Queue Descriptor - Python标准库队列描述符

支持本地进程内队列（queue.Queue）和多进程队列（multiprocessing.Queue）
"""

from typing import Any, Dict, Optional
import logging
from queue import Queue
from .base_queue_descriptor import BaseQueueDescriptor


class PythonQueueDescriptor(BaseQueueDescriptor):
    """
    Python标准库队列描述符
    
    只支持 queue.Queue (本地进程内队列)
    """
    
    def __init__(self, maxsize: int = 0, use_multiprocessing: bool = False, queue_id: Optional[str] = None):
        """
        初始化Python队列描述符
        
        Args:
            maxsize: 队列最大大小，0表示无限制
            use_multiprocessing: 是否使用multiprocessing.Queue
            queue_id: 队列唯一标识符
        """
        self.maxsize = maxsize
        self.use_multiprocessing = use_multiprocessing
        self._initialized = False  # 是否已初始化队列实例
        super().__init__(queue_id=queue_id)
    
    @property
    def queue_type(self) -> str:
        """队列类型标识符"""
        return "python"
    
    @property
    def can_serialize(self) -> bool:
        return not self._initialized  # 未初始化时可以序列化
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """元数据字典"""
        base_metadata = {
            "maxsize": self.maxsize,
            "use_multiprocessing": self.use_multiprocessing,
        }
        
        # 只有在不可序列化时才包含队列实例引用
        if not self.can_serialize:
            base_metadata["queue_instance"] = self.queue_instance
        
        return base_metadata

    def clone(self, new_queue_id: Optional[str] = None) -> 'BaseQueueDescriptor':
        """克隆描述符（不包含队列实例）"""
        # 创建同类型的新实例
        return self

    @property
    def queue_instance(self) -> Any:
        """获取队列实例，如果未初始化则创建"""
        if not self._initialized:
            self._queue_instance = Queue(maxsize=self.maxsize)
            self._initialized = True
        return self._queue_instance
    