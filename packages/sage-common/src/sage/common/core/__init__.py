"""
Common Core Module - 共享类型、异常和常量

这个模块包含 SAGE 框架中各个包共享的核心定义。
"""

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
    # Exceptions
    "KernelError",
    "SchedulingError",
    "FaultToleranceError",
    "ResourceAllocationError",
    "RecoveryError",
]
