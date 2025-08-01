"""
Python Queue Descriptor - Python标准库队列描述符

支持本地进程内队列（queue.Queue）和多进程队列（multiprocessing.Queue）
"""

from typing import Any, Dict, Optional
import logging
from .base_queue_descriptor import BaseQueueDescriptor

logger = logging.getLogger(__name__)


class PythonQueueDescriptor(BaseQueueDescriptor):
    """
    Python标准库队列描述符
    
    支持：
    - queue.Queue (本地进程内队列)
    - multiprocessing.Queue (跨进程队列)
    """
    
    def __init__(self, maxsize: int = 0, use_multiprocessing: bool = False, 
                 queue_id: Optional[str] = None, queue_instance: Optional[Any] = None):
        """
        初始化Python队列描述符
        
        Args:
            maxsize: 队列最大大小，0表示无限制
            use_multiprocessing: 是否使用multiprocessing.Queue
            queue_id: 队列唯一标识符
            queue_instance: 可选的队列实例
        """
        self.maxsize = maxsize
        self.use_multiprocessing = use_multiprocessing
        super().__init__(queue_id=queue_id, queue_instance=queue_instance)
    
    @property
    def queue_type(self) -> str:
        """队列类型标识符"""
        return "python"
    
    @property
    def can_serialize(self) -> bool:
        """
        序列化支持：
        - multiprocessing.Queue 可以序列化
        - queue.Queue 不能序列化
        """
        if self.use_multiprocessing:
            return self._queue_instance is None  # 只有未初始化的multiprocessing队列可以序列化
        else:
            return False  # queue.Queue 不能序列化
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """元数据字典"""
        base_metadata = {
            "maxsize": self.maxsize,
            "use_multiprocessing": self.use_multiprocessing
        }
        
        # 对于不可序列化的队列，包含队列实例引用
        if not self.can_serialize:
            base_metadata["queue_instance"] = self._queue_instance
        
        return base_metadata
    
    def _create_queue_instance(self) -> Any:
        """创建Python队列实例"""
        if self.use_multiprocessing:
            import multiprocessing
            queue_instance = multiprocessing.Queue(maxsize=self.maxsize if self.maxsize > 0 else None)
            logger.info(f"Successfully initialized multiprocessing Queue: {self.queue_id}")
        else:
            import queue
            queue_instance = queue.Queue(maxsize=self.maxsize)
            logger.info(f"Successfully initialized local Queue: {self.queue_id}")
        
        return queue_instance
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PythonQueueDescriptor':
        """从字典创建实例"""
        metadata = data.get('metadata', {})
        instance = cls(
            maxsize=metadata.get('maxsize', 0),
            use_multiprocessing=metadata.get('use_multiprocessing', False),
            queue_id=data['queue_id']
        )
        instance.created_timestamp = data.get('created_timestamp', instance.created_timestamp)
        return instance


# 便利函数
def create_python_queue(queue_id: Optional[str] = None, maxsize: int = 0, 
                       use_multiprocessing: bool = False) -> PythonQueueDescriptor:
    """创建Python队列描述符"""
    return PythonQueueDescriptor(
        maxsize=maxsize, 
        use_multiprocessing=use_multiprocessing, 
        queue_id=queue_id
    )


def create_local_queue(queue_id: Optional[str] = None, maxsize: int = 0) -> PythonQueueDescriptor:
    """创建本地队列描述符（仅线程内使用）"""
    return PythonQueueDescriptor(
        maxsize=maxsize, 
        use_multiprocessing=False, 
        queue_id=queue_id
    )


def create_multiprocessing_queue(queue_id: Optional[str] = None, maxsize: int = 0) -> PythonQueueDescriptor:
    """创建多进程队列描述符"""
    return PythonQueueDescriptor(
        maxsize=maxsize, 
        use_multiprocessing=True, 
        queue_id=queue_id
    )
