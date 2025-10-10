"""
Kernel Core Module - 共享类型、异常和常量

这个模块包含 sage-kernel 中各个子模块共享的核心定义。
"""

from sage.kernel.core.types import ExecutionMode, TaskStatus, TaskID, ServiceID, NodeID
from sage.kernel.core.exceptions import (
    KernelError,
    SchedulingError,
    FaultToleranceError,
    ResourceAllocationError,
    RecoveryError,
)

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
