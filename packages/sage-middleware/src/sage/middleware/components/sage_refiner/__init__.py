"""
SAGE Refiner - 上下文压缩和精炼组件
===================================

提供统一的上下文压缩接口，支持多种SOTA压缩算法。
可作为全局context service的基础组件。

使用示例:
    >>> from sage.middleware.components.sage_refiner import RefinerService, RefinerConfig
    >>>
    >>> # 创建配置
    >>> config = RefinerConfig(
    ...     algorithm="long_refiner",
    ...     budget=2048,
    ...     enable_cache=True
    ... )
    >>>
    >>> # 创建服务
    >>> service = RefinerService(config)
    >>>
    >>> # 压缩上下文
    >>> result = service.refine(
    ...     query="用户问题",
    ...     documents=["文档1", "文档2", "文档3"]
    ... )
"""

from sage.middleware.components.sage_refiner.python.adapter import RefinerAdapter
from sage.middleware.components.sage_refiner.python.algorithms import (
    LongRefinerAlgorithm,
    SimpleRefiner,
)
from sage.middleware.components.sage_refiner.python.base import (
    BaseRefiner,
    RefineResult,
    RefinerMetrics,
)
from sage.middleware.components.sage_refiner.python.config import (
    RefinerAlgorithm,
    RefinerConfig,
)
from sage.middleware.components.sage_refiner.python.service import RefinerService

__all__ = [
    # 基础类
    "BaseRefiner",
    "RefineResult",
    "RefinerMetrics",
    # 配置
    "RefinerConfig",
    "RefinerAlgorithm",
    # 服务
    "RefinerService",
    # 适配器
    "RefinerAdapter",
    # 算法
    "LongRefinerAlgorithm",
    "SimpleRefiner",
]

__version__ = "0.1.0"
