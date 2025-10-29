"""
SAGE Kernel API Functions - 向后兼容层

⚠️ Deprecated: 这些类已迁移到 sage.common.core.functions
请使用: from sage.common.core.functions import MapFunction, SinkFunction, ...

为了向后兼容，本模块仍然提供这些导入。
"""

import warnings

warnings.warn(
    "Importing from sage.kernel.api.function is deprecated. "
    "Please use: from sage.common.core.functions import MapFunction, ...",
    DeprecationWarning,
    stacklevel=2,
)

# 从 common 重新导出
from sage.common.core.functions import (
    BaseCoMapFunction,  # noqa: E402
    BaseFunction,
    BaseJoinFunction,
    BatchFunction,
    FilterFunction,
    FlatMapFunction,
    FutureFunction,
    KeyByFunction,
    LambdaMapFunction,
    MapFunction,
    SinkFunction,
    SourceFunction,
)

__all__ = [
    "BaseFunction",
    "MapFunction",
    "FilterFunction",
    "FlatMapFunction",
    "SinkFunction",
    "SourceFunction",
    "BatchFunction",
    "KeyByFunction",
    "BaseJoinFunction",
    "BaseCoMapFunction",
    "LambdaMapFunction",
    "FutureFunction",
]
