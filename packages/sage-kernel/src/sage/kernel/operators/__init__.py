"""
SAGE Kernel Operators - 基础算子 (向后兼容层)

⚠️ Deprecated: 算子基类已迁移到 sage.common.core.functions
请使用: from sage.common.core.functions import MapFunction, ...
"""

from sage.common.core.functions import BaseFunction  # 保持原名称
from sage.common.core.functions import BaseFunction as BaseOperator
from sage.common.core.functions import FilterFunction
from sage.common.core.functions import FilterFunction as FilterOperator
from sage.common.core.functions import FlatMapFunction
from sage.common.core.functions import FlatMapFunction as FlatMapOperator
from sage.common.core.functions import MapFunction
from sage.common.core.functions import MapFunction as MapOperator

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
