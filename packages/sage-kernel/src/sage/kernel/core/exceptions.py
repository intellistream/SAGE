"""
Kernel 共享异常类

定义了 sage-kernel 中使用的异常类层次结构。
"""


class KernelError(Exception):
    """
    Kernel 基础异常
    
    所有 sage-kernel 相关异常的基类。
    """
    pass


class SchedulingError(KernelError):
    """
    调度相关异常
    
    在任务调度、资源分配等过程中发生的异常。
    """
    pass


class FaultToleranceError(KernelError):
    """
    容错相关异常
    
    在故障检测、恢复等过程中发生的异常。
    """
    pass


class ResourceAllocationError(SchedulingError):
    """
    资源分配异常
    
    当无法分配所需资源时抛出。
    """
    pass


class RecoveryError(FaultToleranceError):
    """
    恢复失败异常
    
    当任务或作业恢复失败时抛出。
    """
    pass


class CheckpointError(FaultToleranceError):
    """
    Checkpoint 异常
    
    在保存或加载 checkpoint 时发生的异常。
    """
    pass


class PlacementError(SchedulingError):
    """
    放置策略异常
    
    在决定任务放置位置时发生的异常。
    """
    pass


__all__ = [
    "KernelError",
    "SchedulingError",
    "FaultToleranceError",
    "ResourceAllocationError",
    "RecoveryError",
    "CheckpointError",
    "PlacementError",
]
