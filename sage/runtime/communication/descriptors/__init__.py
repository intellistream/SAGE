"""
Queue Descriptors Package - 队列描述符包

统一管理各种队列描述符类型
"""

# 基础描述符
from .base_descriptor import (
    BaseQueueDescriptor,
    QueueLike,
    get_registered_descriptors,
    create_descriptor_from_type,
    register_descriptor_class
)

# 本地队列描述符
from .local_descriptor import (
    LocalQueueDescriptor,
    SerializableLocalQueueDescriptor,
    create_local_queue_descriptor,
    create_serializable_local_queue_descriptor
)

# 共享内存队列描述符
from .shm_descriptor import (
    ShmQueueDescriptor,
    MultiProcessShmQueueDescriptor,
    create_shm_queue_descriptor,
    create_multiprocess_shm_queue_descriptor
)

# Ray队列描述符
from .ray_descriptor import (
    RayQueueDescriptor,
    RayActorQueueDescriptor,
    RayClusterQueueDescriptor,
    create_ray_queue_descriptor,
    create_ray_actor_queue_descriptor,
    create_ray_cluster_queue_descriptor
)

# RPC队列描述符
from .rpc_descriptor import (
    RpcQueueDescriptor,
    GrpcQueueDescriptor,
    HttpQueueDescriptor,
    WebSocketQueueDescriptor,
    create_rpc_queue_descriptor,
    create_grpc_queue_descriptor,
    create_http_queue_descriptor,
    create_websocket_queue_descriptor
)

# 所有描述符类
ALL_DESCRIPTOR_CLASSES = [
    # 基础类
    BaseQueueDescriptor,
    
    # 本地队列
    LocalQueueDescriptor,
    SerializableLocalQueueDescriptor,
    
    # 共享内存
    ShmQueueDescriptor,
    MultiProcessShmQueueDescriptor,
    
    # Ray
    RayQueueDescriptor,
    RayActorQueueDescriptor,
    RayClusterQueueDescriptor,
    
    # RPC
    RpcQueueDescriptor,
    GrpcQueueDescriptor,
    HttpQueueDescriptor,
    WebSocketQueueDescriptor
]

# 所有工厂函数
FACTORY_FUNCTIONS = {
    # 本地队列
    'local': create_local_queue_descriptor,
    'serializable_local': create_serializable_local_queue_descriptor,
    
    # 共享内存
    'shm': create_shm_queue_descriptor,
    'multiprocess_shm': create_multiprocess_shm_queue_descriptor,
    
    # Ray
    'ray': create_ray_queue_descriptor,
    'ray_actor': create_ray_actor_queue_descriptor,
    'ray_cluster': create_ray_cluster_queue_descriptor,
    
    # RPC
    'rpc': create_rpc_queue_descriptor,
    'grpc': create_grpc_queue_descriptor,
    'http': create_http_queue_descriptor,
    'websocket': create_websocket_queue_descriptor
}


def create_queue_descriptor(queue_type: str, **kwargs):
    """
    通用队列描述符创建函数
    
    Args:
        queue_type: 队列类型
        **kwargs: 传递给具体工厂函数的参数
        
    Returns:
        对应类型的队列描述符
        
    Raises:
        ValueError: 如果队列类型不支持
    """
    if queue_type not in FACTORY_FUNCTIONS:
        supported_types = list(FACTORY_FUNCTIONS.keys())
        raise ValueError(f"Unsupported queue type '{queue_type}'. "
                        f"Supported types: {supported_types}")
    
    factory_func = FACTORY_FUNCTIONS[queue_type]
    return factory_func(**kwargs)


def list_supported_queue_types():
    """
    列出所有支持的队列类型
    
    Returns:
        支持的队列类型列表
    """
    return list(FACTORY_FUNCTIONS.keys())


def get_descriptor_info():
    """
    获取所有描述符的信息
    
    Returns:
        描述符信息字典
    """
    return {
        'registered_classes': get_registered_descriptors(),
        'supported_types': list_supported_queue_types(),
        'total_classes': len(ALL_DESCRIPTOR_CLASSES),
        'factory_functions': len(FACTORY_FUNCTIONS)
    }


# 导出主要的接口
__all__ = [
    # 基础类
    'BaseQueueDescriptor',
    'QueueLike',
    
    # 具体描述符类
    'LocalQueueDescriptor',
    'SerializableLocalQueueDescriptor',
    'ShmQueueDescriptor',
    'MultiProcessShmQueueDescriptor',
    'RayQueueDescriptor',
    'RayActorQueueDescriptor',
    'RayClusterQueueDescriptor',
    'RpcQueueDescriptor',
    'GrpcQueueDescriptor',
    'HttpQueueDescriptor',
    'WebSocketQueueDescriptor',
    
    # 工厂函数
    'create_local_queue_descriptor',
    'create_serializable_local_queue_descriptor',
    'create_shm_queue_descriptor',
    'create_multiprocess_shm_queue_descriptor',
    'create_ray_queue_descriptor',
    'create_ray_actor_queue_descriptor',
    'create_ray_cluster_queue_descriptor',
    'create_rpc_queue_descriptor',
    'create_grpc_queue_descriptor',
    'create_http_queue_descriptor',
    'create_websocket_queue_descriptor',
    
    # 通用接口
    'create_queue_descriptor',
    'list_supported_queue_types',
    'get_descriptor_info',
    'create_descriptor_from_type',
    'register_descriptor_class',
    'get_registered_descriptors',
    
    # 集合
    'ALL_DESCRIPTOR_CLASSES',
    'FACTORY_FUNCTIONS'
]
