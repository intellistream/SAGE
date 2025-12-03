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
from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.recomp_abst import (
    RECOMPAbstractiveCompressor,
)
from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.recomp_extr import (
    RECOMPExtractiveCompressor,
)
from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.reform import (
    AttentionHookExtractor,
    REFORMRefinerOperator,
)

# LLMLingua2 算法 (基于 BERT token 分类的快速压缩)
try:
    from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.llmlingua2 import (
        LLMLingua2Compressor,
        LLMLingua2Operator,
    )
except ImportError:
    LLMLingua2Compressor = None
    LLMLingua2Operator = None

# LongLLMLingua 算法 (问题感知的长文档压缩)
try:
    from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.longllmlingua import (
        DEFAULT_LONG_LLMLINGUA_CONFIG,
        LongLLMLinguaCompressor,
        LongLLMLinguaOperator,
    )
except ImportError:
    LongLLMLinguaCompressor = None
    LongLLMLinguaOperator = None
    DEFAULT_LONG_LLMLINGUA_CONFIG = None

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
    # RECOMP Extractive算法
    "RECOMPExtractiveCompressor",
    # RECOMP Abstractive算法
    "RECOMPAbstractiveCompressor",
    # LongRefiner算法
    "LongRefinerCompressor",
    "LongRefinerOperator",
    # Provence算法
    "ProvenceCompressor",
    "ProvenceRefinerOperator",
    # LLMLingua2算法 (BERT-based fast compression)
    "LLMLingua2Compressor",
    "LLMLingua2Operator",
    # LongLLMLingua算法 (Question-aware long context compression)
    "LongLLMLinguaCompressor",
    "LongLLMLinguaOperator",
    "DEFAULT_LONG_LLMLINGUA_CONFIG",
]

# Optional: RECOMP Extractive Operator (requires SAGE framework)
try:
    from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.recomp_extr import (
        RECOMPExtractiveOperator,
    )

    __all__.append("RECOMPExtractiveOperator")
except ImportError:
    RECOMPExtractiveOperator = None

# Optional: RECOMP Abstractive Operator (requires SAGE framework)
try:
    from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.recomp_abst import (
        RECOMPAbstractiveOperator,
    )

    __all__.append("RECOMPAbstractiveOperator")
except ImportError:
    RECOMPAbstractiveOperator = None

__version__ = "0.1.0"
