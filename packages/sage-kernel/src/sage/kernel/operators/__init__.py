"""
SAGE Kernel Operators - 基础算子

Layer: L3 (Kernel - Operators)
Dependencies: sage.kernel.api.function (L3 internal)

这个模块提供 SAGE 数据流中的基础算子类型。
这些算子是所有数据流转换的基础，不依赖具体业务逻辑。

基础算子类型：
- BaseOperator: 所有算子的基类
- MapOperator: 一对一映射算子
- FilterOperator: 过滤算子
- FlatMapOperator: 一对多映射算子
- AggregateOperator: 聚合算子

Architecture Note:
本模块是 api.function 的别名导出，用于保持向后兼容性。
新代码应优先使用 api.function 中的类。
"""

# 从 api.function 重新导出基础算子（保持向后兼容）
from sage.kernel.api.function.base_function import BaseFunction as BaseOperator
from sage.kernel.api.function.filter_function import FilterFunction as FilterOperator
from sage.kernel.api.function.flatmap_function import FlatMapFunction as FlatMapOperator
from sage.kernel.api.function.map_function import MapFunction as MapOperator

# 为了保持一致性，同时导出原始名称
from sage.kernel.api.function.base_function import BaseFunction
from sage.kernel.api.function.filter_function import FilterFunction
from sage.kernel.api.function.flatmap_function import FlatMapFunction
from sage.kernel.api.function.map_function import MapFunction

__all__ = [
    # 算子风格命名
    "BaseOperator",
    "MapOperator",
    "FilterOperator",
    "FlatMapOperator",
    # 原始函数风格命名（保持兼容）
    "BaseFunction",
    "MapFunction",
    "FilterFunction",
    "FlatMapFunction",
]
