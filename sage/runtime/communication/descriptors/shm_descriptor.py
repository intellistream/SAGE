"""
Shared Memory Queue Descriptor - 共享内存队列描述符

用于管理跨进程的共享内存队列
"""

import uuid
from typing import Any, Dict, Optional
from .base_descriptor import BaseQueueDescriptor, QueueLike, register_descriptor_class
import logging

logger = logging.getLogger(__name__)


class ShmQueueDescriptor(BaseQueueDescriptor):
    """
    共享内存队列描述符
    
    特点：
    - 支持跨进程通信
    - 可序列化
    - 使用共享内存进行高效数据交换
    - 支持懒加载
    """
    
    def __init__(self, queue_id: str, shm_name: str, maxsize: int = 1000, 
                 **extra_metadata):
        """
        初始化共享内存队列描述符
        
        Args:
            queue_id: 队列ID
            shm_name: 共享内存名称
            maxsize: 队列最大大小
            **extra_metadata: 额外的元数据
        """
        metadata = {
            'shm_name': shm_name,
            'maxsize': maxsize,
            **extra_metadata
        }
        
        super().__init__(
            queue_id=queue_id,
            queue_type="shm",
            metadata=metadata,
            can_serialize=True
        )
        
        logger.info(f"ShmQueueDescriptor '{queue_id}' created for shm '{shm_name}'")
    
    def _validate_descriptor(self):
        """验证共享内存队列描述符"""
        super()._validate_descriptor()
        if not self.metadata.get('shm_name'):
            raise ValueError("shm_name is required for shared memory queue")
    
    def create_queue(self) -> QueueLike:
        """创建共享内存队列对象"""
        shm_name = self.metadata['shm_name']
        maxsize = self.metadata.get('maxsize', 1000)
        
        # 这里应该实现真正的共享内存队列
        # 目前使用存根实现
        from ..queue_stubs.shm_queue_stub import ShmQueueStub
        
        # 创建一个临时的描述符用于存根
        temp_descriptor = type('TempDescriptor', (), {
            'queue_id': self.queue_id,
            'queue_type': self.queue_type,
            'metadata': self.metadata
        })()
        
        queue_obj = ShmQueueStub(temp_descriptor)
        
        logger.info(f"Created shared memory queue '{self.queue_id}' "
                   f"with shm_name='{shm_name}', maxsize={maxsize}")
        return queue_obj
    
    def get_shm_info(self) -> Dict[str, Any]:
        """获取共享内存相关信息"""
        return {
            'shm_name': self.metadata['shm_name'],
            'maxsize': self.metadata.get('maxsize', 1000),
            'queue_id': self.queue_id,
            'initialized': self._initialized
        }
    
    def __repr__(self) -> str:
        status = "initialized" if self._initialized else "lazy"
        shm_name = self.metadata.get('shm_name', 'unknown')
        return f"ShmQueueDescriptor(id='{self.queue_id}', shm='{shm_name}', {status})"


class MultiProcessShmQueueDescriptor(ShmQueueDescriptor):
    """
    多进程共享内存队列描述符
    
    专门用于多进程环境的共享内存队列，增加了进程管理功能
    """
    
    def __init__(self, queue_id: str, shm_name: str, process_count: int = 2,
                 maxsize: int = 1000, **extra_metadata):
        """
        初始化多进程共享内存队列描述符
        
        Args:
            queue_id: 队列ID
            shm_name: 共享内存名称
            process_count: 预期的进程数量
            maxsize: 队列最大大小
            **extra_metadata: 额外的元数据
        """
        extra_metadata.update({
            'process_count': process_count,
            'multiprocess': True
        })
        
        super().__init__(
            queue_id=queue_id,
            shm_name=shm_name,
            maxsize=maxsize,
            **extra_metadata
        )
        
        self._process_registry = {}
    
    def register_process(self, process_id: str, process_info: Dict[str, Any]):
        """注册使用此队列的进程"""
        self._process_registry[process_id] = process_info
        logger.info(f"Registered process '{process_id}' for queue '{self.queue_id}'")
    
    def unregister_process(self, process_id: str):
        """注销进程"""
        if process_id in self._process_registry:
            del self._process_registry[process_id]
            logger.info(f"Unregistered process '{process_id}' from queue '{self.queue_id}'")
    
    def get_registered_processes(self) -> Dict[str, Any]:
        """获取已注册的进程列表"""
        return self._process_registry.copy()
    
    def __repr__(self) -> str:
        status = "initialized" if self._initialized else "lazy"
        shm_name = self.metadata.get('shm_name', 'unknown')
        proc_count = len(self._process_registry)
        return f"MultiProcessShmQueueDescriptor(id='{self.queue_id}', shm='{shm_name}', processes={proc_count}, {status})"


# 工厂函数
def create_shm_queue_descriptor(shm_name: str, 
                               queue_id: Optional[str] = None,
                               maxsize: int = 1000,
                               **extra_metadata) -> ShmQueueDescriptor:
    """
    创建共享内存队列描述符
    
    Args:
        shm_name: 共享内存名称
        queue_id: 队列ID，如果为None则自动生成
        maxsize: 队列最大大小
        **extra_metadata: 额外的元数据
        
    Returns:
        共享内存队列描述符
    """
    if queue_id is None:
        queue_id = f"shm_{uuid.uuid4().hex[:8]}"
    
    return ShmQueueDescriptor(
        queue_id=queue_id,
        shm_name=shm_name,
        maxsize=maxsize,
        **extra_metadata
    )


def create_multiprocess_shm_queue_descriptor(shm_name: str,
                                           process_count: int = 2,
                                           queue_id: Optional[str] = None,
                                           maxsize: int = 1000,
                                           **extra_metadata) -> MultiProcessShmQueueDescriptor:
    """
    创建多进程共享内存队列描述符
    
    Args:
        shm_name: 共享内存名称
        process_count: 预期的进程数量
        queue_id: 队列ID，如果为None则自动生成
        maxsize: 队列最大大小
        **extra_metadata: 额外的元数据
        
    Returns:
        多进程共享内存队列描述符
    """
    if queue_id is None:
        queue_id = f"mp_shm_{uuid.uuid4().hex[:8]}"
    
    return MultiProcessShmQueueDescriptor(
        queue_id=queue_id,
        shm_name=shm_name,
        process_count=process_count,
        maxsize=maxsize,
        **extra_metadata
    )


# 注册描述符类
register_descriptor_class("shm", ShmQueueDescriptor)
register_descriptor_class("multiprocess_shm", MultiProcessShmQueueDescriptor)
