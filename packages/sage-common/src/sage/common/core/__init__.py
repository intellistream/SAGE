"""
Common Core Module - 共享类型、异常、常量和函数接口

这个模块包含 SAGE 框架中各个包共享的核心定义。

包含:
- data_types: 基础数据类型和查询结果
- exceptions: 核心异常类型
- types: 执行模式、状态等枚举
- functions: 用户自定义函数的基础接口 (NEW)
"""

from sage.common.core.data_types import (
    BaseDocument,
    BaseQueryResult,
    ExtendedQueryResult,
    QueryResultInput,
    QueryResultOutput,
    create_query_result,
    ensure_query_result,
    extract_query,
    extract_results,
)
from sage.common.core.exceptions import (
    FaultToleranceError,
    KernelError,
    RecoveryError,
    ResourceAllocationError,
    SchedulingError,
)

# Import function interfaces
from sage.common.core.functions import (
    BaseCoMapFunction,
    BaseFunction,
    BaseJoinFunction,
    BatchFunction,
    Collector,
    FilterFunction,
    FlatMapFunction,
    FutureFunction,
    KeyByFunction,
    LambdaMapFunction,
    MapFunction,
    SinkFunction,
    SourceFunction,
    wrap_lambda,
)
from sage.common.core.types import ExecutionMode, NodeID, ServiceID, TaskID, TaskStatus

__all__ = [
    # Types
    "ExecutionMode",
    "TaskStatus",
    "TaskID",
    "ServiceID",
    "NodeID",
    # Data Types
    "BaseDocument",
    "BaseQueryResult",
    "ExtendedQueryResult",
    "QueryResultInput",
    "QueryResultOutput",
    # Data Type Helpers
    "ensure_query_result",
    "extract_query",
    "extract_results",
    "create_query_result",
    # Exceptions
    "KernelError",
    "SchedulingError",
    "FaultToleranceError",
    "ResourceAllocationError",
    "RecoveryError",
    # Function Interfaces
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
