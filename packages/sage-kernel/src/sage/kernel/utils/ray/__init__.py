"""
Ray 分布式工具

包含 Ray Actor 封装和 Ray 初始化相关的工具函数。
"""

from sage.kernel.utils.ray.actor import ActorWrapper
from sage.kernel.utils.ray.ray_utils import ensure_ray_initialized

__all__ = [
    "ActorWrapper",
    "ensure_ray_initialized",
]
