"""
Python Queue Descriptor - Python标准库队列描述符

支持本地进程内队列（queue.Queue）和多进程队列（multiprocessing.Queue）
"""

from typing import Any, Dict, Optional
import logging
from queue import Queue
from .base_queue_descriptor import BaseQueueDescriptor

logger = logging.getLogger(__name__)


class PythonQueueDescriptor(BaseQueueDescriptor):
    """
    Python标准库队列描述符
    
    只支持 queue.Queue (本地进程内队列)
    """
    
    def __init__(self, maxsize: int = 0, queue_id: Optional[str] = None):
        """
        初始化Python队列描述符
        
        Args:
            maxsize: 队列最大大小，0表示无限制
            use_multiprocessing: 是否使用multiprocessing.Queue
            queue_id: 队列唯一标识符
            queue_instance: 可选的队列实例
        """
        self.maxsize = maxsize
        self._initialized = False  # 是否已初始化队列实例
        super().__init__(queue_id=queue_id)
    
    @property
    def queue_type(self) -> str:
        """队列类型标识符"""
        return "python"
    
    @property
    def can_serialize(self) -> bool:
        return False  # queue.Queue 不能序列化
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """元数据字典"""
        base_metadata = {
            "maxsize": self.maxsize,
            "queue_instance": self.queue_instance,  # 包含队列实例引用
        }
        
        return base_metadata
    
    @property
    def queue_instance(self) -> Any:
        """获取队列实例，如果未初始化则创建"""
        if not self._initialized:
            self._queue_instance = Queue(maxsize=self.maxsize)
            self._initialized = True
        return self._queue_instance
    