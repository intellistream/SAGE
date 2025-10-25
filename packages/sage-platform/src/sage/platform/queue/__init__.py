"""SAGE Platform - Queue Abstractions

Layer: L2 (Platform Services - Queue Module)

Unified queue descriptor interface supporting multiple backends.

This module provides queue descriptors that abstract different queue implementations:
- PythonQueueDescriptor: Standard Python queue.Queue
- RayQueueDescriptor: Ray distributed queue
- RPCQueueDescriptor: Remote procedure call queue (requires L3 registration)

Architecture:
✅ Clean L2 design - no direct imports from L3
✅ RPCQueueDescriptor uses factory pattern - L3 registers implementation
"""

# 导出队列描述符类
from .base_queue_descriptor import BaseQueueDescriptor
from .python_queue_descriptor import PythonQueueDescriptor
from .ray_queue_descriptor import RayQueueDescriptor
from .rpc_queue_descriptor import RPCQueueDescriptor, register_rpc_queue_factory


def resolve_descriptor(data):
    """从序列化数据解析出对应的队列描述符实例

    Args:
        data: 包含队列描述符信息的字典

    Returns:
        对应类型的队列描述符实例
    """
    if isinstance(data, dict):
        queue_type = data.get("queue_type")
        if queue_type == "python":
            return PythonQueueDescriptor.from_dict(data)
        elif queue_type == "ray_queue":
            return RayQueueDescriptor.from_dict(data)
        elif queue_type == "rpc_queue":
            return RPCQueueDescriptor.from_dict(data)
        else:
            raise ValueError(f"Unknown queue type: {queue_type}")
    else:
        raise TypeError(f"Expected dict, got {type(data)}")


__all__ = [
    "BaseQueueDescriptor",
    "PythonQueueDescriptor",
    "RayQueueDescriptor",
    "RPCQueueDescriptor",
    "register_rpc_queue_factory",
    "resolve_descriptor",
]
