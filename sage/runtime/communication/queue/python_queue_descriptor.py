"""
Python Queue Descriptor - Python标准库队列描述符

支持本地进程内队列和多进程共享内存队列
"""

from typing import Any, Dict, Optional
import logging
from .queue_descriptor import QueueDescriptor

logger = logging.getLogger(__name__)


class PythonQueueDescriptor(QueueDescriptor):
    """
    Python标准库队列描述符
    
    支持：
    - queue.Queue (本地进程内队列)
    - multiprocessing.Queue (多进程共享内存队列)
    """
    
    def __init__(self, maxsize: int = 0, use_multiprocessing: bool = False,
                 queue_id: Optional[str] = None, queue_instance: Optional[Any] = None):
        """
        初始化Python队列描述符
        
        Args:
            maxsize: 队列最大大小，0表示无限制
            use_multiprocessing: 是否使用多进程队列
            queue_id: 队列唯一标识符
            queue_instance: 可选的队列实例
        """
        self.maxsize = maxsize
        self.use_multiprocessing = use_multiprocessing
        super().__init__(queue_id=queue_id, queue_instance=queue_instance)
    
    @property
    def queue_type(self) -> str:
        """队列类型标识符"""
        return "multiprocessing" if self.use_multiprocessing else "local"
    
    @property
    def can_serialize(self) -> bool:
        """Python队列可以序列化"""
        return self._queue_instance is None
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """元数据字典"""
        return {
            "maxsize": self.maxsize,
            "use_multiprocessing": self.use_multiprocessing
        }
    
    def _create_queue_instance(self) -> Any:
        """创建Python队列实例"""
        if self.use_multiprocessing:
            try:
                import multiprocessing as mp
                queue_instance = mp.Queue(maxsize=self.maxsize)
                logger.info(f"Successfully initialized multiprocessing Queue: {self.queue_id}")
                return queue_instance
            except Exception as e:
                logger.warning(f"Failed to create multiprocessing queue, falling back to local: {e}")
                # 回退到本地队列
                self.use_multiprocessing = False
        
        # 创建本地队列
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
def create_local_queue(queue_id: Optional[str] = None, maxsize: int = 0) -> PythonQueueDescriptor:
    """创建本地队列描述符"""
    return PythonQueueDescriptor(maxsize=maxsize, use_multiprocessing=False, queue_id=queue_id)


def create_multiprocessing_queue(queue_id: Optional[str] = None, maxsize: int = 0) -> PythonQueueDescriptor:
    """创建多进程队列描述符"""
    return PythonQueueDescriptor(maxsize=maxsize, use_multiprocessing=True, queue_id=queue_id)
