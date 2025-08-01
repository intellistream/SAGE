"""
Ray Queue Descriptor - Ray队列描述符

用于管理Ray分布式计算环境中的队列
"""

import uuid
from typing import Any, Dict, Optional
from .base_descriptor import BaseQueueDescriptor, QueueLike, register_descriptor_class
import logging

logger = logging.getLogger(__name__)


class RayQueueDescriptor(BaseQueueDescriptor):
    """
    Ray队列描述符
    
    特点：
    - 支持Ray分布式环境
    - 可序列化
    - 支持Ray Actor模式
    - 支持懒加载
    """
    
    def __init__(self, queue_id: str, actor_name: Optional[str] = None,
                 max_size: int = 1000, **extra_metadata):
        """
        初始化Ray队列描述符
        
        Args:
            queue_id: 队列ID
            actor_name: Ray Actor名称，如果为None则自动生成
            max_size: 队列最大大小
            **extra_metadata: 额外的元数据
        """
        if actor_name is None:
            actor_name = f"queue_actor_{uuid.uuid4().hex[:8]}"
        
        metadata = {
            'actor_name': actor_name,
            'max_size': max_size,
            **extra_metadata
        }
        
        super().__init__(
            queue_id=queue_id,
            queue_type="ray",
            metadata=metadata,
            can_serialize=True
        )
        
        logger.info(f"RayQueueDescriptor '{queue_id}' created for actor '{actor_name}'")
    
    def _validate_descriptor(self):
        """验证Ray队列描述符"""
        super()._validate_descriptor()
        if not self.metadata.get('actor_name'):
            raise ValueError("actor_name is required for Ray queue")
    
    def create_queue(self) -> QueueLike:
        """创建Ray队列对象"""
        actor_name = self.metadata['actor_name']
        max_size = self.metadata.get('max_size', 1000)
        
        # 这里应该实现真正的Ray队列
        # 目前使用存根实现
        from ..queue_stubs.ray_queue_stub import RayQueueStub
        
        # 创建一个临时的描述符用于存根
        temp_descriptor = type('TempDescriptor', (), {
            'queue_id': self.queue_id,
            'queue_type': self.queue_type,
            'metadata': self.metadata
        })()
        
        queue_obj = RayQueueStub(temp_descriptor)
        
        logger.info(f"Created Ray queue '{self.queue_id}' "
                   f"with actor='{actor_name}', max_size={max_size}")
        return queue_obj
    
    def get_ray_info(self) -> Dict[str, Any]:
        """获取Ray相关信息"""
        return {
            'actor_name': self.metadata['actor_name'],
            'max_size': self.metadata.get('max_size', 1000),
            'queue_id': self.queue_id,
            'initialized': self._initialized
        }
    
    def __repr__(self) -> str:
        status = "initialized" if self._initialized else "lazy"
        actor_name = self.metadata.get('actor_name', 'unknown')
        return f"RayQueueDescriptor(id='{self.queue_id}', actor='{actor_name}', {status})"


class RayActorQueueDescriptor(RayQueueDescriptor):
    """
    Ray Actor队列描述符
    
    专门用于Ray Actor之间的通信队列，提供更丰富的Actor管理功能
    """
    
    def __init__(self, queue_id: str, actor_name: Optional[str] = None,
                 max_size: int = 1000, actor_resources: Optional[Dict[str, float]] = None,
                 **extra_metadata):
        """
        初始化Ray Actor队列描述符
        
        Args:
            queue_id: 队列ID
            actor_name: Ray Actor名称
            max_size: 队列最大大小
            actor_resources: Actor资源配置 (例如: {"num_cpus": 1, "num_gpus": 0})
            **extra_metadata: 额外的元数据
        """
        if actor_resources is None:
            actor_resources = {"num_cpus": 1}
        
        extra_metadata.update({
            'actor_resources': actor_resources,
            'is_actor_queue': True
        })
        
        super().__init__(
            queue_id=queue_id,
            actor_name=actor_name,
            max_size=max_size,
            **extra_metadata
        )
        
        self._actor_handle = None
    
    def get_actor_resources(self) -> Dict[str, float]:
        """获取Actor资源配置"""
        return self.metadata.get('actor_resources', {"num_cpus": 1})
    
    def set_actor_handle(self, actor_handle):
        """设置Actor句柄"""
        self._actor_handle = actor_handle
        logger.info(f"Set actor handle for queue '{self.queue_id}'")
    
    def get_actor_handle(self):
        """获取Actor句柄"""
        return self._actor_handle
    
    def __repr__(self) -> str:
        status = "initialized" if self._initialized else "lazy"
        actor_name = self.metadata.get('actor_name', 'unknown')
        has_handle = "with handle" if self._actor_handle else "no handle"
        return f"RayActorQueueDescriptor(id='{self.queue_id}', actor='{actor_name}', {has_handle}, {status})"


class RayClusterQueueDescriptor(RayQueueDescriptor):
    """
    Ray集群队列描述符
    
    用于管理跨Ray集群节点的队列通信
    """
    
    def __init__(self, queue_id: str, cluster_address: str,
                 actor_name: Optional[str] = None, max_size: int = 1000,
                 **extra_metadata):
        """
        初始化Ray集群队列描述符
        
        Args:
            queue_id: 队列ID
            cluster_address: Ray集群地址
            actor_name: Ray Actor名称
            max_size: 队列最大大小
            **extra_metadata: 额外的元数据
        """
        extra_metadata.update({
            'cluster_address': cluster_address,
            'is_cluster_queue': True
        })
        
        super().__init__(
            queue_id=queue_id,
            actor_name=actor_name,
            max_size=max_size,
            **extra_metadata
        )
    
    def get_cluster_address(self) -> str:
        """获取集群地址"""
        return self.metadata['cluster_address']
    
    def __repr__(self) -> str:
        status = "initialized" if self._initialized else "lazy"
        actor_name = self.metadata.get('actor_name', 'unknown')
        cluster_addr = self.metadata.get('cluster_address', 'unknown')
        return f"RayClusterQueueDescriptor(id='{self.queue_id}', actor='{actor_name}', cluster='{cluster_addr}', {status})"


# 工厂函数
def create_ray_queue_descriptor(queue_id: Optional[str] = None,
                               actor_name: Optional[str] = None,
                               max_size: int = 1000,
                               **extra_metadata) -> RayQueueDescriptor:
    """
    创建Ray队列描述符
    
    Args:
        queue_id: 队列ID，如果为None则自动生成
        actor_name: Ray Actor名称
        max_size: 队列最大大小
        **extra_metadata: 额外的元数据
        
    Returns:
        Ray队列描述符
    """
    if queue_id is None:
        queue_id = f"ray_{uuid.uuid4().hex[:8]}"
    
    return RayQueueDescriptor(
        queue_id=queue_id,
        actor_name=actor_name,
        max_size=max_size,
        **extra_metadata
    )


def create_ray_actor_queue_descriptor(queue_id: Optional[str] = None,
                                     actor_name: Optional[str] = None,
                                     max_size: int = 1000,
                                     actor_resources: Optional[Dict[str, float]] = None,
                                     **extra_metadata) -> RayActorQueueDescriptor:
    """
    创建Ray Actor队列描述符
    
    Args:
        queue_id: 队列ID，如果为None则自动生成
        actor_name: Ray Actor名称
        max_size: 队列最大大小
        actor_resources: Actor资源配置
        **extra_metadata: 额外的元数据
        
    Returns:
        Ray Actor队列描述符
    """
    if queue_id is None:
        queue_id = f"ray_actor_{uuid.uuid4().hex[:8]}"
    
    return RayActorQueueDescriptor(
        queue_id=queue_id,
        actor_name=actor_name,
        max_size=max_size,
        actor_resources=actor_resources,
        **extra_metadata
    )


def create_ray_cluster_queue_descriptor(cluster_address: str,
                                       queue_id: Optional[str] = None,
                                       actor_name: Optional[str] = None,
                                       max_size: int = 1000,
                                       **extra_metadata) -> RayClusterQueueDescriptor:
    """
    创建Ray集群队列描述符
    
    Args:
        cluster_address: Ray集群地址
        queue_id: 队列ID，如果为None则自动生成
        actor_name: Ray Actor名称
        max_size: 队列最大大小
        **extra_metadata: 额外的元数据
        
    Returns:
        Ray集群队列描述符
    """
    if queue_id is None:
        queue_id = f"ray_cluster_{uuid.uuid4().hex[:8]}"
    
    return RayClusterQueueDescriptor(
        queue_id=queue_id,
        cluster_address=cluster_address,
        actor_name=actor_name,
        max_size=max_size,
        **extra_metadata
    )


# 注册描述符类
register_descriptor_class("ray", RayQueueDescriptor)
register_descriptor_class("ray_actor", RayActorQueueDescriptor)
register_descriptor_class("ray_cluster", RayClusterQueueDescriptor)
