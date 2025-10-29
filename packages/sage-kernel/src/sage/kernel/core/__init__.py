"""
Kernel Core Module - 共享类型、异常和常量

这个模块包含 sage-kernel 中各个子模块共享的核心定义。

注意：core 已迁移到 sage-common，此文件保留用于向后兼容。
请更新导入为: from sage.common.core import ...
"""

import warnings

# 兼容性导入 - 从 sage-common 重新导出
from sage.common.core.exceptions import (
    FaultToleranceError,
    KernelError,
    RecoveryError,
    ResourceAllocationError,
    SchedulingError,
)
from sage.common.core.types import ExecutionMode, NodeID, ServiceID, TaskID, TaskStatus

# 发出弃用警告
warnings.warn(
    "sage.kernel.core has been moved to sage.common.core. "
    "Please update your imports to: from sage.common.core import ...",
    DeprecationWarning,
    stacklevel=2,
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
