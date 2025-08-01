"""
Ray Queue Descriptor - Ray分布式队列描述符

支持Ray分布式队列和Ray Actor队列
"""

from typing import Any, Dict, Optional
import logging
from .base_queue_descriptor import BaseQueueDescriptor

logger = logging.getLogger(__name__)


class RayQueueDescriptor(BaseQueueDescriptor):
    """
    Ray分布式队列描述符
    
    支持：
    - ray.util.Queue (Ray原生分布式队列)
    """
    
    def __init__(self, maxsize: int = 0, queue_id: Optional[str] = None):
        """
        初始化Ray队列描述符
        
        Args:
            maxsize: 队列最大大小，0表示无限制
            queue_id: 队列唯一标识符
        """
        self.maxsize = maxsize
        super().__init__(queue_id=queue_id)
    
    @property
    def queue_type(self) -> str:
        """队列类型标识符"""
        return "ray_queue"
    
    @property
    def can_serialize(self) -> bool:
        """Ray队列可以序列化"""
        return self._queue_instance is None
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """元数据字典"""
        return {"maxsize": self.maxsize}
    
    def _create_queue_instance(self) -> Any:
        """创建Ray队列实例"""
        try:
            import ray
            
            if not ray.is_initialized():
                logger.warning("Ray is not initialized, attempting to initialize...")
                ray.init()
            
            # Ray原生分布式队列
            queue_instance = ray.util.Queue(maxsize=self.maxsize if self.maxsize > 0 else None)
            logger.info(f"Successfully initialized Ray Queue: {self.queue_id}")
            return queue_instance
                
        except ImportError as e:
            logger.error(f"Failed to import Ray: {e}")
            raise RuntimeError(f"Ray not available: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize Ray queue: {e}")
            raise
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RayQueueDescriptor':
        """从字典创建实例"""
        metadata = data.get('metadata', {})
        instance = cls(
            maxsize=metadata.get('maxsize', 0),
            queue_id=data['queue_id']
        )
        instance.created_timestamp = data.get('created_timestamp', instance.created_timestamp)
        return instance


# 便利函数
def create_ray_queue(queue_id: Optional[str] = None, maxsize: int = 0) -> RayQueueDescriptor:
    """创建Ray分布式队列描述符"""
    return RayQueueDescriptor(maxsize=maxsize, queue_id=queue_id)
