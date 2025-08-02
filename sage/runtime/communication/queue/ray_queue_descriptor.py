"""
Ray Queue Descriptor - Ray分布式队列描述符

支持Ray分布式队列和Ray Actor队列
"""

from typing import Any, Dict, Optional
import logging
from ray.util.queue import Queue
from .base_queue_descriptor import BaseQueueDescriptor

logger = logging.getLogger(__name__)


class RayQueueDescriptor(BaseQueueDescriptor):
    """
    Ray分布式队列描述符
    
    支持：
    - ray.util.Queue (Ray原生分布式队列)
    """
    
    def __init__(self, maxsize: int = 1024*1024, queue_id: Optional[str] = None):
        """
        初始化Ray队列描述符
        
        Args:
            maxsize: 队列最大大小，0表示无限制
            queue_id: 队列唯一标识符
        """
        self.maxsize = maxsize
        # 直接创建队列实例，不通过metadata
        self._queue = Queue(maxsize=self.maxsize if self.maxsize > 0 else None)
        super().__init__(queue_id=queue_id)
    
    @property
    def queue_type(self) -> str:
        """队列类型标识符"""
        return "ray_queue"
    
    @property
    def can_serialize(self) -> bool:
        """Ray队列可以序列化"""
        return True
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """元数据字典"""
        return {"maxsize": self.maxsize}
    
    @property
    def queue_instance(self) -> Any:
        """获取队列实例"""
        return self._queue
