"""
Sage Runtime Communication Module

统一的通信系统，提供队列描述符和各种通信方式的抽象。
"""

# 基础抽象类
from .queue_descriptor import QueueDescriptor

# 专用队列描述符
from .python_queue_descriptor import PythonQueueDescriptor, create_python_queue
from .ray_queue_descriptor import RayQueueDescriptor, create_ray_queue
from .sage_queue_descriptor import SageQueueDescriptor, create_sage_queue
from .rpc_queue_descriptor import RPCQueueDescriptor, create_rpc_queue

# 工厂函数和便利函数
def get_local_queue(queue_id=None, maxsize=0, use_multiprocessing=False):
    """获取本地Python队列"""
    return create_python_queue(
        queue_id=queue_id,
        maxsize=maxsize,
        use_multiprocessing=use_multiprocessing
    )

def get_ray_queue(queue_id=None, maxsize=0, actor_name=None):
    """获取Ray队列"""
    return create_ray_queue(
        queue_id=queue_id,
        maxsize=maxsize,
        actor_name=actor_name
    )

def get_sage_queue(queue_id=None, maxsize=1024*1024, auto_cleanup=True, namespace=None):
    """获取SAGE队列"""
    return create_sage_queue(
        queue_id=queue_id,
        maxsize=maxsize,
        auto_cleanup=auto_cleanup,
        namespace=namespace
    )

def get_rpc_queue(queue_id=None, host="localhost", port=8000):
    """获取RPC队列"""
    return create_rpc_queue(
        queue_id=queue_id,
        host=host,
        port=port
    )

# 类型解析
def resolve_descriptor(data):
    """从序列化数据解析队列描述符"""
    if isinstance(data, dict) and 'queue_type' in data:
        queue_type = data['queue_type']
        if queue_type == 'python_queue':
            return PythonQueueDescriptor.from_dict(data)
        elif queue_type == 'ray_queue':
            return RayQueueDescriptor.from_dict(data)
        elif queue_type == 'sage_queue':
            return SageQueueDescriptor.from_dict(data)
        elif queue_type == 'rpc_queue':
            return RPCQueueDescriptor.from_dict(data)
        else:
            raise ValueError(f"Unknown queue type: {queue_type}")
    else:
        raise ValueError("Invalid queue descriptor data")

def create_descriptor_from_existing_queue(queue_instance, queue_type=None, queue_id=None):
    """从现有队列实例创建描述符"""
    if queue_type == 'python' or str(type(queue_instance).__module__).startswith('queue'):
        return PythonQueueDescriptor(queue_id=queue_id, queue_instance=queue_instance)
    elif queue_type == 'ray' or 'ray' in str(type(queue_instance)):
        return RayQueueDescriptor(queue_id=queue_id, queue_instance=queue_instance)
    elif queue_type == 'sage' or 'sage' in str(type(queue_instance).__module__).lower():
        return SageQueueDescriptor(queue_id=queue_id, queue_instance=queue_instance)
    elif queue_type == 'rpc':
        return RPCQueueDescriptor(queue_id=queue_id, queue_instance=queue_instance)
    else:
        # 默认尝试Python描述符
        return PythonQueueDescriptor(queue_id=queue_id, queue_instance=queue_instance)

__all__ = [
    # 抽象基类
    'QueueDescriptor',
    
    # 专用描述符类
    'PythonQueueDescriptor',
    'RayQueueDescriptor', 
    'SageQueueDescriptor',
    'RPCQueueDescriptor',
    
    # 创建函数
    'create_python_queue',
    'create_ray_queue',
    'create_sage_queue', 
    'create_rpc_queue',
    
    # 便利函数
    'get_local_queue',
    'get_ray_queue',
    'get_sage_queue',
    'get_rpc_queue',
    
    # 工具函数
    'resolve_descriptor',
    'create_descriptor_from_existing_queue',
]
