"""
Queue Stubs Package

包含各种队列类型的具体实现类，用于与 QueueDescriptor 配合使用。
"""

from .sage_queue_stub import SageQueueStub
from .ray_queue_stub import RayQueueStub
from .local_queue_stub import LocalQueueStub
from .shared_memory_queue_stub import SharedMemoryQueueStub

# 导入注册和便利函数
from .registry import (
    initialize_queue_stubs,
    get_queue_stub_class,
    is_queue_type_supported,
    list_supported_queue_types,
    create_sage_queue,
    create_ray_queue,
    create_ray_actor_queue,
    create_local_queue,
    create_shm_queue,
    auto_select_queue_type,
    create_auto_queue
)

__all__ = [
    # Stub 类
    'SageQueueStub',
    'RayQueueStub',
    'LocalQueueStub', 
    'SharedMemoryQueueStub',
    
    # 注册功能
    'initialize_queue_stubs',
    'get_queue_stub_class',
    'is_queue_type_supported', 
    'list_supported_queue_types',
    
    # 便利创建函数
    'create_sage_queue',
    'create_ray_queue',
    'create_ray_actor_queue',
    'create_local_queue', 
    'create_shm_queue',
    'auto_select_queue_type',
    'create_auto_queue'
]
