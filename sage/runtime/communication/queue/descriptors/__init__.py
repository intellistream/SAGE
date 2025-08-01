"""
Queue Descriptors Package - 队列描述符包

统一管理各种队列描述符类型

注意：现在所有队列类型都通过主要的 QueueDescriptor 类统一处理，
     不再需要特定的描述符子类。
"""

# 导入主要的 QueueDescriptor 类
from ..queue_descriptor import QueueDescriptor

# 通用接口函数
def create_queue_descriptor(queue_type: str, queue_id: str = None, **kwargs):
    """
    通用队列描述符创建函数
    
    Args:
        queue_type: 队列类型
        queue_id: 队列ID
        **kwargs: 其他参数
        
    Returns:
        QueueDescriptor 实例
    """
    return QueueDescriptor(
        queue_id=queue_id or f"{queue_type}_default",
        queue_type=queue_type,
        metadata=kwargs
    )


def list_supported_queue_types():
    """
    列出所有支持的队列类型
    
    Returns:
        支持的队列类型列表
    """
    return ["local", "shm", "ray_actor", "ray_queue", "rpc", "sage_queue"]


def get_descriptor_info():
    """
    获取所有描述符的信息
    
    Returns:
        描述符信息字典
    """
    return {
        'supported_types': list_supported_queue_types(),
        'main_class': 'QueueDescriptor',
        'note': 'All queue types are now handled through the unified QueueDescriptor class'
    }


# 为了向后兼容，创建一些别名工厂函数
def create_local_queue_descriptor(queue_id: str = None, maxsize: int = 0, **kwargs):
    """创建本地队列描述符"""
    return QueueDescriptor.create_local_queue(queue_id, maxsize)


def create_shm_queue_descriptor(shm_name: str, queue_id: str = None, maxsize: int = 1000, **kwargs):
    """创建共享内存队列描述符"""
    return QueueDescriptor.create_shm_queue(shm_name, queue_id, maxsize)


def create_ray_queue_descriptor(queue_id: str = None, maxsize: int = 0, **kwargs):
    """创建Ray队列描述符"""
    return QueueDescriptor.create_ray_queue(queue_id, maxsize)


def create_ray_actor_queue_descriptor(actor_name: str, queue_id: str = None, maxsize: int = 0, **kwargs):
    """创建Ray Actor队列描述符"""
    return QueueDescriptor.create_ray_actor_queue(actor_name, queue_id, maxsize)


def create_rpc_queue_descriptor(server_address: str, port: int, queue_id: str = None, **kwargs):
    """创建RPC队列描述符"""
    return QueueDescriptor.create_rpc_queue(server_address, port, queue_id)


def create_sage_queue_descriptor(queue_id: str = None, maxsize: int = 1000, **kwargs):
    """创建SAGE队列描述符"""
    return QueueDescriptor.create_sage_queue(queue_id, maxsize, **kwargs)


# 导出主要的接口
__all__ = [
    # 主要的描述符类
    'QueueDescriptor',
    
    # 工厂函数
    'create_queue_descriptor',
    'create_local_queue_descriptor',
    'create_shm_queue_descriptor',
    'create_ray_queue_descriptor',
    'create_ray_actor_queue_descriptor',
    'create_rpc_queue_descriptor',
    'create_sage_queue_descriptor',
    
    # 通用接口
    'list_supported_queue_types',
    'get_descriptor_info'
]
