"""
Python Queue Descriptor - Python标准库队列描述符

支持本地进程内队列（queue.Queue）
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
    """
    
    def __init__(self, maxsize: int = 0, queue_id: Optional[str] = None, queue_instance: Optional[Any] = None):
        """
        初始化Python队列描述符
        
        Args:
            maxsize: 队列最大大小，0表示无限制
            queue_id: 队列唯一标识符
            queue_instance: 可选的队列实例
        """
        self.maxsize = maxsize
        super().__init__(queue_id=queue_id, queue_instance=queue_instance)
    
    @property
    def queue_type(self) -> str:
        """队列类型标识符"""
        return "local"
    
    @property
    def can_serialize(self) -> bool:
        """Python队列不支持序列化"""
        return False
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """元数据字典"""
        return {
            "maxsize": self.maxsize,
            "queue_instance": self._queue_instance  # 因为不支持序列化，可以包含队列实例
        }
    
    def _create_queue_instance(self) -> Any:
        """创建Python队列实例"""
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
            queue_id=data['queue_id']
        )
        instance.created_timestamp = data.get('created_timestamp', instance.created_timestamp)
        return instance


# 便利函数
def create_python_queue(queue_id: Optional[str] = None, maxsize: int = 0) -> PythonQueueDescriptor:
    """创建Python队列描述符"""
    return PythonQueueDescriptor(maxsize=maxsize, queue_id=queue_id)


def create_local_queue(queue_id: Optional[str] = None, maxsize: int = 0) -> PythonQueueDescriptor:
    """创建本地队列描述符"""
    return PythonQueueDescriptor(maxsize=maxsize, queue_id=queue_id)
