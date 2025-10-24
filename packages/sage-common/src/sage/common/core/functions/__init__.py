"""
SAGE Common Functions - 基础函数接口定义

Layer: L1 (Common - Core Abstractions)
Dependencies: 无

提供用户自定义函数的基础接口：
- BaseFunction: 所有函数的基类
- MapFunction: 一对一映射函数
- FilterFunction: 过滤函数
- SinkFunction: 输出函数
- SourceFunction: 数据源函数
- BatchFunction: 批处理函数
等等...

这些接口是纯抽象定义，不依赖任何执行引擎。

示例:
    from sage.common.core.functions import MapFunction

    class MyMapper(MapFunction):
        def map(self, value):
            return value * 2
"""

from .base_function import BaseFunction
from .batch_function import BatchFunction
from .comap_function import BaseCoMapFunction
from .filter_function import FilterFunction
from .flatmap_function import FlatMapFunction
from .future_function import FutureFunction
from .join_function import BaseJoinFunction
from .keyby_function import KeyByFunction
from .lambda_function import LambdaMapFunction, wrap_lambda
from .map_function import MapFunction
from .sink_function import SinkFunction
from .source_function import SourceFunction

# Note: flatmap_collector exports Collector, not FlatMapCollector
try:
    from .flatmap_collector import Collector
except ImportError:
    Collector = None  # type: ignore

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
    "Collector",
    "LambdaMapFunction",
    "wrap_lambda",
    "FutureFunction",
]
