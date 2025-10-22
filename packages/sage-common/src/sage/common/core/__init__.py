"""
Common Core Module - 共享类型、异常和常量

这个模块包含 SAGE 框架中各个包共享的核心定义。
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
]
