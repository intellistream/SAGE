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

# sage_refiner submodule (standalone library)
from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner import (
    LongRefiner,
    LongRefinerCompressor,
    ProvenceCompressor,
    RefinerAlgorithm,
    RefinerConfig,
    REFORMCompressor,
    ReformCompressor,
)
from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.LongRefiner import (
    LongRefinerOperator,
)
from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.provence import (
    ProvenceRefinerOperator,
)
from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.reform import (
    AttentionHookExtractor,
    REFORMRefinerOperator,
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
    # Provence算法
    "ProvenceCompressor",
    "ProvenceRefinerOperator",
]

# Adaptive算法 (新增)
try:
    from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.adaptive import (
        AdaptiveCompressor,
        AdaptiveRefinerOperator,
    )

    __all__.extend(
        [
            "AdaptiveCompressor",
            "AdaptiveRefinerOperator",
        ]
    )
except ImportError:
    # Adaptive算法依赖未满足时的后备
    AdaptiveCompressor = None
    AdaptiveRefinerOperator = None

# LLMLingua算法 (可选依赖: llmlingua)
try:
    from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.llmlingua import (
        LLMLinguaCompressor,
        LLMLinguaRefinerOperator,
    )

    __all__.extend(
        [
            "LLMLinguaCompressor",
            "LLMLinguaRefinerOperator",
        ]
    )
except ImportError:
    # LLMLingua未安装时的后备
    LLMLinguaCompressor = None
    LLMLinguaRefinerOperator = None

__version__ = "0.1.0"
