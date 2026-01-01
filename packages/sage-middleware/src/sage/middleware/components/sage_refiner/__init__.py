"""
SAGE Refiner - 上下文压缩和精炼组件
===================================

#    llm_model="Qwen/Qwen2.5-7B-Instruct",
    llm_model="Qwen/Qwen2.5-7B-Instruct",SOTA压缩算法。
context service的基础组件。

:
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

import warnings

# SAGE framework dependencies (always required)
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

# Default exports (core components)
__all__ = [
    # 基础类
    "BaseRefiner",
    "RefineResult",
    "RefinerMetrics",
    # 服务
    "RefinerService",
    "ContextService",
    # 适配器
    "RefinerAdapter",
    # 算法
    "LongRefinerAlgorithm",
    "SimpleRefiner",
]

# Try to import from sageRefiner submodule
try:
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

    __all__.extend(
        [
            # 配置
            "RefinerConfig",
            "RefinerAlgorithm",
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
        ]
    )

    _SAGE_REFINER_AVAILABLE = True

except (ImportError, ModuleNotFoundError) as e:
    warnings.warn(
        f"sageRefiner submodule not available: {e}. "
        "Advanced compression algorithms will not be available. "
        "Run './manage.sh' or 'git submodule update --init' to initialize submodules.",
        UserWarning,
        stacklevel=2,
    )
    _SAGE_REFINER_AVAILABLE = False

    # Set placeholder values
    RefinerConfig = None
    RefinerAlgorithm = None

# LLMLingua2 算法 (基于 BERT token 分类的快速压缩)
try:
    if _SAGE_REFINER_AVAILABLE:
        from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.llmlingua2 import (
            LLMLingua2Compressor,
            LLMLingua2Operator,
        )

        __all__.extend(["LLMLingua2Compressor", "LLMLingua2Operator"])
    else:
        LLMLingua2Compressor = None
        LLMLingua2Operator = None
except ImportError:
    LLMLingua2Compressor = None
    LLMLingua2Operator = None

# LongLLMLingua 算法 (问题感知的长文档压缩)
try:
    if _SAGE_REFINER_AVAILABLE:
        from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.longllmlingua import (
            DEFAULT_LONG_LLMLINGUA_CONFIG,
            LongLLMLinguaCompressor,
            LongLLMLinguaOperator,
        )

        __all__.extend(
            [
                "LongLLMLinguaCompressor",
                "LongLLMLinguaOperator",
                "DEFAULT_LONG_LLMLINGUA_CONFIG",
            ]
        )
    else:
        LongLLMLinguaCompressor = None
        LongLLMLinguaOperator = None
        DEFAULT_LONG_LLMLINGUA_CONFIG = None
except ImportError:
    LongLLMLinguaCompressor = None
    LongLLMLinguaOperator = None
    DEFAULT_LONG_LLMLINGUA_CONFIG = None

# Optional: RECOMP Extractive Operator (requires SAGE framework)
try:
    if _SAGE_REFINER_AVAILABLE:
        from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.recomp_extr import (
            RECOMPExtractiveOperator,
        )

        __all__.append("RECOMPExtractiveOperator")
    else:
        RECOMPExtractiveOperator = None
except ImportError:
    RECOMPExtractiveOperator = None

# Optional: RECOMP Abstractive Operator (requires SAGE framework)
try:
    if _SAGE_REFINER_AVAILABLE:
        from sage.middleware.components.sage_refiner.sageRefiner.sage_refiner.algorithms.recomp_abst import (
            RECOMPAbstractiveOperator,
        )

        __all__.append("RECOMPAbstractiveOperator")
    else:
        RECOMPAbstractiveOperator = None
except ImportError:
    RECOMPAbstractiveOperator = None

__version__ = "0.1.0"
