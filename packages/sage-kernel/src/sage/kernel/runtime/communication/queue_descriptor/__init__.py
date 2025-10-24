"""
SAGE - Streaming-Augmented Generative Execution

Layer: L3 (Kernel)
Dependencies: sage.platform (L2)

Architecture Notes:
- L3 queue descriptors inherit from L2 base classes
- RPCQueueDescriptor is imported from sage-platform (L2) - proper downward dependency
"""

# 直接从本包的_version模块加载版本信息
try:
    from sage.kernel._version import __author__, __email__, __version__
except ImportError:
    # 备用硬编码版本
    __version__ = "0.1.4"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"

# RPCQueueDescriptor从L2导入 - 正确的向下依赖
from sage.platform.queue import RPCQueueDescriptor

# 导出队列描述符类 - L3实现
from .base_queue_descriptor import BaseQueueDescriptor
from .python_queue_descriptor import PythonQueueDescriptor
from .ray_queue_descriptor import RayQueueDescriptor


def resolve_descriptor(data):
    """
    从序列化数据解析出对应的队列描述符实例

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
    "resolve_descriptor",
    "__version__",
    "__author__",
    "__email__",
]
