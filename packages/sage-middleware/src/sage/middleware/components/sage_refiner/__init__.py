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

# SAGE framework dependencies
from sage.libs.foundation.context.compression.algorithms import (
    LongRefinerAlgorithm,
    SimpleRefiner,
)
from sage.libs.foundation.context.compression.refiner import (
    BaseRefiner,
    RefineResult,
    RefinerMetrics,
)

# SAGE adapter layer (depends on SAGE core)
from sage.middleware.components.sage_refiner.python.adapter import RefinerAdapter
from sage.middleware.components.sage_refiner.python.context_service import (
    ContextService,
)
from sage.middleware.components.sage_refiner.python.service import RefinerService

# sageRefiner submodule (standalone library)
from sage.middleware.components.sage_refiner.sageRefiner import (
    LongRefiner,
    RefinerAlgorithm,
    RefinerConfig,
    ReformCompressor,
)
from sage.middleware.components.sage_refiner.sageRefiner.algorithms.LongRefiner import (
    LongRefiner as LongRefinerCompressor,
    LongRefinerOperator,
)
from sage.middleware.components.sage_refiner.sageRefiner.algorithms.reform import (
    AttentionHookExtractor,
    ReformCompressor as REFORMCompressor,
    REformRefinerOperator as REFORMRefinerOperator,
)

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
    "ContextService",
    # 适配器
    "RefinerAdapter",
    # 算法
    "LongRefinerAlgorithm",
    "SimpleRefiner",
    # REFORM算法
    "REFORMCompressor",
    "REFORMRefinerOperator",
    "AttentionHookExtractor",
    # LongRefiner算法
    "LongRefinerCompressor",
    "LongRefinerOperator",
]

__version__ = "0.1.0"
