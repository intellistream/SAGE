"""
Ray Queue Descriptor - Ray分布式队列描述符

支持Ray分布式队列和Ray Actor队列
"""

from typing import Any, Dict, Optional
import logging
from .queue_descriptor import QueueDescriptor

logger = logging.getLogger(__name__)


class RayQueueDescriptor(QueueDescriptor):
    """
    Ray分布式队列描述符
    
    支持：
    - ray.util.Queue (Ray原生分布式队列)
    - Ray Actor Queue (基于Ray Actor的队列)
    """
    
    def __init__(self, maxsize: int = 0, actor_name: Optional[str] = None,
                 queue_id: Optional[str] = None, queue_instance: Optional[Any] = None):
        """
        初始化Ray队列描述符
        
        Args:
            maxsize: 队列最大大小，0表示无限制
            actor_name: Ray Actor名称，如果指定则使用Actor队列
            queue_id: 队列唯一标识符
            queue_instance: 可选的队列实例
        """
        self.maxsize = maxsize
        self.actor_name = actor_name
        super().__init__(queue_id=queue_id, queue_instance=queue_instance)
    
    @property
    def queue_type(self) -> str:
        """队列类型标识符"""
        return "ray_actor" if self.actor_name else "ray_queue"
    
    @property
    def can_serialize(self) -> bool:
        """Ray队列可以序列化"""
        return self._queue_instance is None
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """元数据字典"""
        metadata = {"maxsize": self.maxsize}
        if self.actor_name:
            metadata["actor_name"] = self.actor_name
        return metadata
    
    def _create_queue_instance(self) -> Any:
        """创建Ray队列实例"""
        try:
            import ray
            
            if not ray.is_initialized():
                logger.warning("Ray is not initialized, attempting to initialize...")
                ray.init()
            
            if self.actor_name:
                # Ray Actor队列
                try:
                    actor_handle = ray.get_actor(self.actor_name)
                    logger.info(f"Connected to existing Ray Actor: {self.actor_name}")
                    return actor_handle
                except ValueError:
                    logger.error(f"Ray Actor {self.actor_name} not found, please create it first")
                    raise RuntimeError(f"Ray Actor '{self.actor_name}' not found")
            else:
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
            actor_name=metadata.get('actor_name'),
            queue_id=data['queue_id']
        )
        instance.created_timestamp = data.get('created_timestamp', instance.created_timestamp)
        return instance


# 便利函数
def create_ray_queue(queue_id: Optional[str] = None, maxsize: int = 0) -> RayQueueDescriptor:
    """创建Ray分布式队列描述符"""
    return RayQueueDescriptor(maxsize=maxsize, queue_id=queue_id)


def create_ray_actor_queue(actor_name: str, queue_id: Optional[str] = None, 
                          maxsize: int = 0) -> RayQueueDescriptor:
    """创建Ray Actor队列描述符"""
    return RayQueueDescriptor(maxsize=maxsize, actor_name=actor_name, queue_id=queue_id)
