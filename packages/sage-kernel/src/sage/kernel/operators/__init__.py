"""
SAGE Kernel Operators - 基础算子 (向后兼容层)

⚠️ Deprecated: 算子基类已迁移到 sage.common.core.functions
请使用: from sage.common.core.functions import MapFunction, ...
"""

from sage.common.core.functions import (
    BaseFunction,  # 保持原名称
    BaseFunction as BaseOperator,
    FilterFunction,
    FilterFunction as FilterOperator,
    FlatMapFunction,
    FlatMapFunction as FlatMapOperator,
    MapFunction,
    MapFunction as MapOperator,
)

__all__ = [
    "BaseOperator",
    "MapOperator",
    "FilterOperator",
    "FlatMapOperator",
    "BaseFunction",
    "MapFunction",
    "FilterFunction",
    "FlatMapFunction",
]
