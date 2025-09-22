"""
Ray Queue Descriptor - Ray分布式队列描述符

支持Ray分布式队列和Ray Actor队列
"""

from typing import Any, Dict, Optional
import logging
from ray.util.queue import Queue
from .base_queue_descriptor import BaseQueueDescriptor
import ray

logger = logging.getLogger(__name__)

# 全局队列管理器，用于在不同Actor之间共享队列实例
@ray.remote
class RayQueueManager:
    """Ray队列管理器，管理全局队列实例"""
    
    def __init__(self):
        self.queues = {}
    
    def get_or_create_queue(self, queue_id: str, maxsize: int):
        """获取或创建队列"""
        if queue_id not in self.queues:
            self.queues[queue_id] = Queue(maxsize=maxsize if maxsize > 0 else None)
            logger.debug(f"Created new Ray queue {queue_id}")
        else:
            logger.debug(f"Retrieved existing Ray queue {queue_id}")
        return self.queues[queue_id]
    
    def queue_exists(self, queue_id: str):
        """检查队列是否存在"""
        return queue_id in self.queues
    
    def delete_queue(self, queue_id: str):
        """删除队列"""
        if queue_id in self.queues:
            del self.queues[queue_id]
            return True
        return False

# 全局队列管理器实例
_global_queue_manager = None

def get_global_queue_manager():
    """获取全局队列管理器"""
    import time
    import random
    
    # 先尝试获取现有的命名Actor
    try:
        return ray.get_actor("global_ray_queue_manager")
    except ValueError:
        pass
    
    # 多次尝试创建命名Actor，处理并发冲突
    for attempt in range(3):
        try:
            # 如果不存在，创建新的命名Actor
            global _global_queue_manager
            _global_queue_manager = RayQueueManager.options(name="global_ray_queue_manager").remote()
            return _global_queue_manager
        except ValueError as e:
            # 如果Actor已存在，再次尝试获取
            if "already exists" in str(e):
                try:
                    return ray.get_actor("global_ray_queue_manager")
                except ValueError:
                    # 短暂等待后重试
                    time.sleep(random.uniform(0.1, 0.5))
                    continue
            else:
                raise
        except Exception as e:
            # 其他错误，短暂等待后重试
            time.sleep(random.uniform(0.1, 0.5))
            if attempt == 2:  # 最后一次尝试
                raise
    
    # 如果仍然失败，尝试最后一次获取
    return ray.get_actor("global_ray_queue_manager")

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
        self._queue = None  # 延迟初始化
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
        """获取队列实例 - 使用全局管理器确保同一队列ID共享同一实例"""
        if self._queue is None:
            manager = get_global_queue_manager()
            self._queue = ray.get(manager.get_or_create_queue.remote(self.queue_id, self.maxsize))
        return self._queue
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典，包含队列元信息"""
        return {
            'queue_type': self.queue_type,
            'queue_id': self.queue_id,
            'metadata': self.metadata,
            'created_timestamp': self.created_timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RayQueueDescriptor':
        """从字典反序列化"""
        instance = cls(
            maxsize=data['metadata'].get('maxsize', 1024*1024),
            queue_id=data['queue_id']
        )
        instance.created_timestamp = data.get('created_timestamp', instance.created_timestamp)
        return instance
