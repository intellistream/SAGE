"""
Sage Runtime Communication Module

统一的通信系统，提供队列描述符和各种通信方式的抽象。
"""

from .queue_descriptor import (
    UnifiedQueueDescriptor,
    QueueDescriptor,  # 向后兼容别名
    LocalQueueDescriptor,  # 向后兼容别名
    RemoteQueueDescriptor,  # 向后兼容别名
    QueueLike,
    resolve_descriptor,
    register_queue_implementation,
    unregister_queue_implementation,
    get_registered_queue_types,
    create_descriptor_from_existing_queue,
    # 便利函数
    get_local_queue,
    attach_to_shm_queue,
    get_ray_actor_queue,
    get_ray_queue,
    get_rpc_queue,
    get_sage_queue,
)

__all__ = [
    # 核心类和协议
    'UnifiedQueueDescriptor',
    'QueueDescriptor',  # 向后兼容别名
    'LocalQueueDescriptor',  # 向后兼容别名
    'RemoteQueueDescriptor',  # 向后兼容别名
    'QueueLike',
    
    # 核心函数
    'resolve_descriptor',
    'register_queue_implementation',
    'unregister_queue_implementation',
    'get_registered_queue_types',
    'create_descriptor_from_existing_queue',
    
    # 便利函数
    'get_local_queue',
    'attach_to_shm_queue',
    'get_ray_actor_queue',
    'get_ray_queue',
    'get_rpc_queue',
    'get_sage_queue',
]

from .queue_descriptor import (
    QueueDescriptor,
    QueueLike,
    resolve_descriptor,
    create_descriptor_from_existing_queue,
    get_local_queue,
    attach_to_shm_queue,
    get_ray_actor_queue,
    get_ray_queue,
    get_rpc_queue,
    get_sage_queue,
    QUEUE_STUB_MAPPING,
)

__all__ = [
    'QueueDescriptor',
    'QueueLike',
    'resolve_descriptor',
    'create_descriptor_from_existing_queue',
    'get_local_queue',
    'attach_to_shm_queue', 
    'get_ray_actor_queue',
    'get_ray_queue',
    'get_rpc_queue',
    'get_sage_queue',
    'QUEUE_STUB_MAPPING',
]
