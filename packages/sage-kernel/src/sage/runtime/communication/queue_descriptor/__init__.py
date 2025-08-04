"""
Sage Runtime Communication Module

统一的通信系统，提供队列描述符和各种通信方式的抽象。
"""

# 基础抽象类
from .base_queue_descriptor import BaseQueueDescriptor, QueueDescriptor

# 专用队列描述符
from .python_queue_descriptor import PythonQueueDescriptor
from .ray_queue_descriptor import RayQueueDescriptor
from .sage_queue_descriptor import SageQueueDescriptor
from .rpc_queue_descriptor import RPCQueueDescriptor

# 类型解析
def resolve_descriptor(data):
    """从序列化数据解析队列描述符"""
    if isinstance(data, dict) and 'queue_type' in data:
        queue_type = data['queue_type']
        metadata = data.get('metadata', {})
        queue_id = data.get('queue_id')
        
        if queue_type == 'python':
            return PythonQueueDescriptor(
                queue_id=queue_id,
                maxsize=metadata.get('maxsize', 0),
                use_multiprocessing=metadata.get('use_multiprocessing', False)
            )
        elif queue_type == 'ray_queue':
            return RayQueueDescriptor(
                queue_id=queue_id,
                maxsize=metadata.get('maxsize', 0)
            )
        elif queue_type == 'sage_queue':
            return SageQueueDescriptor(
                queue_id=queue_id,
                maxsize=metadata.get('maxsize', 1024*1024),
                auto_cleanup=metadata.get('auto_cleanup', True),
                namespace=metadata.get('namespace'),
                enable_multi_tenant=metadata.get('enable_multi_tenant', True)
            )
        elif queue_type == 'rpc_queue':
            return RPCQueueDescriptor(
                queue_id=queue_id,
                host=metadata.get('host', 'localhost'),
                port=metadata.get('port', 8000),
                connection_timeout=metadata.get('connection_timeout', 30.0),
                retry_count=metadata.get('retry_count', 3),
                enable_pooling=metadata.get('enable_pooling', True)
            )
        else:
            raise ValueError(f"Unknown queue type: {queue_type}")
    else:
        raise ValueError("Invalid queue descriptor data")

__all__ = [
    # 抽象基类
    'BaseQueueDescriptor',
    'QueueDescriptor',  # 别名
    
    # 专用描述符类
    'PythonQueueDescriptor',
    'RayQueueDescriptor', 
    'SageQueueDescriptor',
    'RPCQueueDescriptor',
    
    # 工具函数
    'resolve_descriptor',
]
