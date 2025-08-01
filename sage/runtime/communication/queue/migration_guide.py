"""
Queue Architecture Migration Guide - 队列架构迁移指南

从分离的 queue_stubs 架构迁移到统一的 QueueDescriptor 架构
"""

import logging
from typing import Any, Dict, Optional
from .queue_descriptor import QueueDescriptor

logger = logging.getLogger(__name__)


class QueueMigrationHelper:
    """队列架构迁移助手"""
    
    @staticmethod
    def migrate_from_sage_queue_stub(sage_queue_stub) -> QueueDescriptor:
        """
        从 SageQueueStub 迁移到 QueueDescriptor
        
        Args:
            sage_queue_stub: 旧的 SageQueueStub 实例
            
        Returns:
            新的 QueueDescriptor 实例
        """
        if hasattr(sage_queue_stub, 'descriptor'):
            # 如果存在 descriptor 属性，直接返回
            return sage_queue_stub.descriptor
        
        # 否则从 sage_queue_stub 属性中重建
        if hasattr(sage_queue_stub, '_sage_queue') and sage_queue_stub._sage_queue:
            sage_queue = sage_queue_stub._sage_queue
            queue_id = getattr(sage_queue, 'name', f"migrated_sage_{id(sage_queue)}")
            
            return QueueDescriptor.create_sage_queue(
                queue_id=queue_id,
                maxsize=getattr(sage_queue, 'maxsize', 1024 * 1024),
                auto_cleanup=getattr(sage_queue, 'auto_cleanup', True),
                namespace=getattr(sage_queue, 'namespace', None),
                enable_multi_tenant=getattr(sage_queue, 'enable_multi_tenant', True)
            )
        
        raise ValueError("Unable to migrate SageQueueStub: missing required attributes")
    
    @staticmethod
    def migrate_from_local_queue_stub(local_queue_stub) -> QueueDescriptor:
        """
        从 LocalQueueStub 迁移到 QueueDescriptor
        
        Args:
            local_queue_stub: 旧的 LocalQueueStub 实例
            
        Returns:
            新的 QueueDescriptor 实例
        """
        if hasattr(local_queue_stub, 'descriptor'):
            return local_queue_stub.descriptor
        
        # 从队列实例中提取信息
        if hasattr(local_queue_stub, '_queue') and local_queue_stub._queue:
            queue = local_queue_stub._queue
            maxsize = getattr(queue, 'maxsize', 0)
            queue_id = f"migrated_local_{id(queue)}"
            
            return QueueDescriptor.create_local_queue(
                queue_id=queue_id,
                maxsize=maxsize
            )
        
        raise ValueError("Unable to migrate LocalQueueStub: missing queue instance")
    
    @staticmethod
    def migrate_from_shm_queue_stub(shm_queue_stub) -> QueueDescriptor:
        """
        从 SharedMemoryQueueStub 迁移到 QueueDescriptor
        
        Args:
            shm_queue_stub: 旧的 SharedMemoryQueueStub 实例
            
        Returns:
            新的 QueueDescriptor 实例
        """
        if hasattr(shm_queue_stub, 'descriptor'):
            return shm_queue_stub.descriptor
        
        # 尝试从实例中提取信息
        shm_name = f"migrated_shm_{id(shm_queue_stub)}"
        maxsize = 1000  # 默认值
        
        if hasattr(shm_queue_stub, '_mp_queue') and shm_queue_stub._mp_queue:
            # multiprocessing.Queue 没有直接的 maxsize 属性，使用默认值
            pass
        
        return QueueDescriptor.create_shm_queue(
            shm_name=shm_name,
            maxsize=maxsize
        )
    
    @staticmethod
    def migrate_from_ray_queue_stub(ray_queue_stub) -> QueueDescriptor:
        """
        从 RayQueueStub 迁移到 QueueDescriptor
        
        Args:
            ray_queue_stub: 旧的 RayQueueStub 实例
            
        Returns:
            新的 QueueDescriptor 实例
        """
        if hasattr(ray_queue_stub, 'descriptor'):
            return ray_queue_stub.descriptor
        
        # 根据队列类型创建对应的描述符
        if hasattr(ray_queue_stub, '_queue_type'):
            queue_type = ray_queue_stub._queue_type
            queue_id = f"migrated_{queue_type}_{id(ray_queue_stub)}"
            
            if queue_type == "ray_queue":
                return QueueDescriptor.create_ray_queue(queue_id=queue_id)
            elif queue_type == "ray_actor":
                # 尝试提取 actor_name
                actor_name = getattr(ray_queue_stub, '_actor_name', f"actor_{id(ray_queue_stub)}")
                return QueueDescriptor.create_ray_actor_queue(
                    actor_name=actor_name,
                    queue_id=queue_id
                )
        
        # 默认创建 ray_queue
        return QueueDescriptor.create_ray_queue(queue_id=f"migrated_ray_{id(ray_queue_stub)}")
    
    @staticmethod
    def auto_migrate(queue_stub) -> QueueDescriptor:
        """
        自动识别并迁移任何类型的队列 stub
        
        Args:
            queue_stub: 任何类型的队列 stub 实例
            
        Returns:
            新的 QueueDescriptor 实例
        """
        class_name = queue_stub.__class__.__name__
        
        if 'SageQueue' in class_name:
            return QueueMigrationHelper.migrate_from_sage_queue_stub(queue_stub)
        elif 'LocalQueue' in class_name:
            return QueueMigrationHelper.migrate_from_local_queue_stub(queue_stub)
        elif 'SharedMemory' in class_name or 'ShmQueue' in class_name:
            return QueueMigrationHelper.migrate_from_shm_queue_stub(queue_stub)
        elif 'RayQueue' in class_name:
            return QueueMigrationHelper.migrate_from_ray_queue_stub(queue_stub)
        else:
            logger.warning(f"Unknown queue stub type: {class_name}, attempting generic migration")
            
            # 尝试通用迁移
            if hasattr(queue_stub, 'descriptor'):
                return queue_stub.descriptor
            
            # 创建一个通用的本地队列描述符
            return QueueDescriptor.create_local_queue(
                queue_id=f"migrated_unknown_{id(queue_stub)}"
            )


def migrate_queue_pool(old_queue_pool: Dict[str, Any]) -> Dict[str, QueueDescriptor]:
    """
    迁移整个队列池
    
    Args:
        old_queue_pool: 旧的队列池（包含各种 stub 实例）
        
    Returns:
        新的队列池（全部为 QueueDescriptor 实例）
    """
    new_pool = {}
    migration_helper = QueueMigrationHelper()
    
    for queue_id, queue_stub in old_queue_pool.items():
        try:
            new_descriptor = migration_helper.auto_migrate(queue_stub)
            # 保持原有的 queue_id
            new_descriptor.queue_id = queue_id
            new_pool[queue_id] = new_descriptor
            
            logger.info(f"Successfully migrated queue: {queue_id}")
        except Exception as e:
            logger.error(f"Failed to migrate queue {queue_id}: {e}")
            # 创建一个默认的本地队列作为回退
            new_pool[queue_id] = QueueDescriptor.create_local_queue(queue_id=queue_id)
    
    return new_pool


# 便利函数
def quick_migrate(queue_stub) -> QueueDescriptor:
    """快速迁移单个队列 stub"""
    return QueueMigrationHelper.auto_migrate(queue_stub)


# 向后兼容性包装器
class LegacyQueueStubWrapper:
    """
    旧队列 stub 的向后兼容包装器
    为使用旧 API 的代码提供平滑迁移路径
    """
    
    def __init__(self, queue_descriptor: QueueDescriptor):
        self.descriptor = queue_descriptor
        self._queue_descriptor = queue_descriptor
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        return self._queue_descriptor.put(item, block=block, timeout=timeout)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        return self._queue_descriptor.get(block=block, timeout=timeout)
    
    def put_nowait(self, item: Any) -> None:
        return self._queue_descriptor.put_nowait(item)
    
    def get_nowait(self) -> Any:
        return self._queue_descriptor.get_nowait()
    
    def empty(self) -> bool:
        return self._queue_descriptor.empty()
    
    def qsize(self) -> int:
        return self._queue_descriptor.qsize()
    
    def full(self) -> bool:
        return self._queue_descriptor.full()
    
    def to_descriptor(self) -> QueueDescriptor:
        return self._queue_descriptor
    
    @classmethod
    def from_descriptor(cls, descriptor: QueueDescriptor) -> 'LegacyQueueStubWrapper':
        return cls(descriptor)
    
    def close(self):
        """向后兼容的关闭方法"""
        if hasattr(self._queue_descriptor, 'close'):
            self._queue_descriptor.close()
    
    def destroy(self):
        """向后兼容的销毁方法"""
        if hasattr(self._queue_descriptor, 'destroy'):
            self._queue_descriptor.destroy()


def create_legacy_wrapper(queue_type: str, **kwargs) -> LegacyQueueStubWrapper:
    """
    创建旧风格的队列 stub 包装器
    
    Args:
        queue_type: 队列类型
        **kwargs: 队列参数
        
    Returns:
        向后兼容的包装器实例
    """
    if queue_type == "sage_queue":
        descriptor = QueueDescriptor.create_sage_queue(**kwargs)
    elif queue_type == "local":
        descriptor = QueueDescriptor.create_local_queue(**kwargs)
    elif queue_type == "shm":
        descriptor = QueueDescriptor.create_shm_queue(**kwargs)
    elif queue_type == "ray_queue":
        descriptor = QueueDescriptor.create_ray_queue(**kwargs)
    elif queue_type == "ray_actor":
        descriptor = QueueDescriptor.create_ray_actor_queue(**kwargs)
    else:
        raise ValueError(f"Unsupported queue type: {queue_type}")
    
    return LegacyQueueStubWrapper(descriptor)
