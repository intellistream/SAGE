"""
Queue Stubs Registration - 队列实现注册模块

自动注册所有队列实现类到 QUEUE_STUB_MAPPING 中，
提供统一的初始化和便利函数。
"""

import logging
from typing import Dict, Type, Optional, Any

from ..queue_descriptor import (
    QueueDescriptor, 
    QUEUE_STUB_MAPPING,
    register_queue_implementation
)

# 导入所有 stub 实现
from .sage_queue_stub import SageQueueStub
from .ray_queue_stub import RayQueueStub
from .local_queue_stub import LocalQueueStub
from .shared_memory_queue_stub import SharedMemoryQueueStub

logger = logging.getLogger(__name__)


def initialize_queue_stubs():
    """
    初始化并注册所有队列实现类
    
    这个函数会自动注册所有可用的队列类型到全局映射表中
    """
    # 注册所有队列实现
    implementations = {
        "sage_queue": SageQueueStub,
        "ray_queue": RayQueueStub,
        "ray_actor": RayQueueStub,  # Ray Actor 也使用同一个 stub
        "local": LocalQueueStub,
        "shm": SharedMemoryQueueStub,
    }
    
    registered_count = 0
    
    for queue_type, impl_class in implementations.items():
        try:
            register_queue_implementation(queue_type, impl_class)
            registered_count += 1
            logger.debug(f"Registered queue implementation: {queue_type} -> {impl_class.__name__}")
        except Exception as e:
            logger.warning(f"Failed to register queue implementation {queue_type}: {e}")
    
    logger.info(f"Successfully registered {registered_count}/{len(implementations)} queue implementations")
    
    return registered_count


def get_queue_stub_class(queue_type: str) -> Optional[Type]:
    """
    获取指定队列类型的实现类
    
    Args:
        queue_type: 队列类型
        
    Returns:
        对应的实现类，如果不存在则返回 None
    """
    return QUEUE_STUB_MAPPING.get(queue_type)


def is_queue_type_supported(queue_type: str) -> bool:
    """
    检查指定的队列类型是否被支持
    
    Args:
        queue_type: 队列类型
        
    Returns:
        是否支持该队列类型
    """
    return queue_type in QUEUE_STUB_MAPPING


def list_supported_queue_types() -> list:
    """
    列出所有支持的队列类型
    
    Returns:
        支持的队列类型列表
    """
    return list(QUEUE_STUB_MAPPING.keys())


# 便利函数 - 提供更简洁的队列创建方式
def create_sage_queue(queue_id: Optional[str] = None, 
                     maxsize: int = 1024 * 1024,
                     auto_cleanup: bool = True,
                     namespace: Optional[str] = None,
                     enable_multi_tenant: bool = True) -> Any:
    """
    创建 SAGE 高性能队列
    
    Args:
        queue_id: 队列ID
        maxsize: 最大大小
        auto_cleanup: 是否自动清理
        namespace: 命名空间
        enable_multi_tenant: 是否启用多租户
        
    Returns:
        SAGE Queue 实例
    """
    from ..queue_descriptor import resolve_descriptor
    
    descriptor = QueueDescriptor.create_sage_queue(
        queue_id=queue_id,
        maxsize=maxsize,
        auto_cleanup=auto_cleanup,
        namespace=namespace,
        enable_multi_tenant=enable_multi_tenant
    )
    
    return resolve_descriptor(descriptor)


def create_ray_queue(queue_id: Optional[str] = None, 
                    maxsize: int = 0) -> Any:
    """
    创建 Ray 分布式队列
    
    Args:
        queue_id: 队列ID
        maxsize: 最大大小
        
    Returns:
        Ray Queue 实例
    """
    from ..queue_descriptor import resolve_descriptor
    
    descriptor = QueueDescriptor.create_ray_queue(
        queue_id=queue_id,
        maxsize=maxsize
    )
    
    return resolve_descriptor(descriptor)


def create_ray_actor_queue(actor_name: str,
                          queue_id: Optional[str] = None, 
                          maxsize: int = 0) -> Any:
    """
    创建 Ray Actor 队列
    
    Args:
        actor_name: Actor 名称
        queue_id: 队列ID
        maxsize: 最大大小
        
    Returns:
        Ray Actor Queue 实例
    """
    from ..queue_descriptor import resolve_descriptor
    
    descriptor = QueueDescriptor.create_ray_actor_queue(
        actor_name=actor_name,
        queue_id=queue_id,
        maxsize=maxsize
    )
    
    return resolve_descriptor(descriptor)


def create_local_queue(queue_id: Optional[str] = None, 
                      maxsize: int = 0) -> Any:
    """
    创建本地队列
    
    Args:
        queue_id: 队列ID
        maxsize: 最大大小
        
    Returns:
        本地队列实例
    """
    from ..queue_descriptor import resolve_descriptor
    
    descriptor = QueueDescriptor.create_local_queue(
        queue_id=queue_id,
        maxsize=maxsize
    )
    
    return resolve_descriptor(descriptor)


def create_shm_queue(shm_name: str,
                    queue_id: Optional[str] = None, 
                    maxsize: int = 1000) -> Any:
    """
    创建共享内存队列
    
    Args:
        shm_name: 共享内存名称
        queue_id: 队列ID
        maxsize: 最大大小
        
    Returns:
        共享内存队列实例
    """
    from ..queue_descriptor import resolve_descriptor
    
    descriptor = QueueDescriptor.create_shm_queue(
        shm_name=shm_name,
        queue_id=queue_id,
        maxsize=maxsize
    )
    
    return resolve_descriptor(descriptor)


def auto_select_queue_type(**kwargs) -> str:
    """
    根据当前环境自动选择最适合的队列类型
    
    Args:
        **kwargs: 额外参数，用于影响选择逻辑
        
    Returns:
        推荐的队列类型
    """
    # 检查 Ray 是否可用且已初始化
    try:
        import ray
        if ray.is_initialized():
            return "ray_queue"
    except ImportError:
        pass
    
    # 检查 SAGE Queue 是否可用
    try:
        from sage_ext.sage_queue.python.sage_queue import SageQueue
        return "sage_queue"
    except ImportError:
        pass
    
    # 检查是否在多进程环境中
    import multiprocessing
    if multiprocessing.current_process().name != 'MainProcess':
        return "shm"
    
    # 默认使用本地队列
    return "local"


def create_auto_queue(queue_id: Optional[str] = None, 
                     maxsize: int = 1000,
                     **kwargs) -> Any:
    """
    根据环境自动创建最适合的队列类型
    
    Args:
        queue_id: 队列ID
        maxsize: 最大大小
        **kwargs: 额外参数
        
    Returns:
        自动选择的队列实例
    """
    queue_type = auto_select_queue_type(**kwargs)
    
    logger.info(f"Auto-selected queue type: {queue_type}")
    
    # 根据队列类型创建相应的队列
    if queue_type == "sage_queue":
        return create_sage_queue(queue_id=queue_id, maxsize=maxsize)
    elif queue_type == "ray_queue":
        return create_ray_queue(queue_id=queue_id, maxsize=maxsize)
    elif queue_type == "shm":
        shm_name = kwargs.get('shm_name', f'auto_shm_{queue_id or "default"}')
        return create_shm_queue(shm_name=shm_name, queue_id=queue_id, maxsize=maxsize)
    else:  # local
        return create_local_queue(queue_id=queue_id, maxsize=maxsize)


# 在模块导入时自动初始化
try:
    initialize_queue_stubs()
except Exception as e:
    logger.warning(f"Failed to auto-initialize queue stubs: {e}")


__all__ = [
    'initialize_queue_stubs',
    'get_queue_stub_class', 
    'is_queue_type_supported',
    'list_supported_queue_types',
    'create_sage_queue',
    'create_ray_queue',
    'create_ray_actor_queue', 
    'create_local_queue',
    'create_shm_queue',
    'auto_select_queue_type',
    'create_auto_queue'
]
