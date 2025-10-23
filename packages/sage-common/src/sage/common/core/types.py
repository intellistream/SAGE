"""
Common Core Types

定义了 SAGE 框架中使用的核心数据类型和枚举。
这些类型可以被所有 SAGE 包使用（kernel, libs, middleware 等）。

Layer: L1 (Foundation)
"""

from enum import Enum
from typing import Any, Dict, List, TypeVar, Union


# 执行模式枚举
class ExecutionMode(Enum):
    """任务执行模式"""

    LOCAL = "local"  # 本地执行
    REMOTE = "remote"  # 远程执行（Ray）
    HYBRID = "hybrid"  # 混合模式


# 任务状态枚举
class TaskStatus(Enum):
    """任务运行状态"""

    PENDING = "pending"  # 等待中
    RUNNING = "running"  # 运行中
    STOPPED = "stopped"  # 已停止
    FAILED = "failed"  # 失败
    COMPLETED = "completed"  # 完成


# 作业状态枚举
class JobStatus(Enum):
    """作业状态"""

    PENDING = "pending"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    COMPLETED = "completed"
    DELETED = "deleted"


# 类型别名
TaskID = str  # 任务标识符
ServiceID = str  # 服务标识符
NodeID = str  # 节点标识符
QueueID = str  # 队列标识符
JobID = str  # 作业标识符

# 泛型类型变量
T = TypeVar("T")
TaskType = TypeVar("TaskType")
ServiceType = TypeVar("ServiceType")

__all__ = [
    "ExecutionMode",
    "TaskStatus",
    "JobStatus",
    "TaskID",
    "ServiceID",
    "NodeID",
    "QueueID",
    "JobID",
    "T",
    "TaskType",
    "ServiceType",
]
