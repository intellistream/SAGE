"""
Common Core Exception Classes

定义了 SAGE 框架中使用的异常类层次结构。
这些异常可以被所有 SAGE 包使用，主要用于 kernel 的任务调度和容错。

Layer: L1 (Foundation)
"""


class KernelError(Exception):
    """
    Base Kernel Exception

    The base class for all sage-kernel related exceptions.
    """

    pass


class SchedulingError(KernelError):
    """
    Scheduling Related Exception

    Exception occurring during task scheduling, resource allocation, etc.
    """

    pass


class FaultToleranceError(KernelError):
    """
    Fault Tolerance Related Exception

    Exception occurring during fault detection, recovery, etc.
    """

    pass


class ResourceAllocationError(SchedulingError):
    """
    Resource Allocation Exception

    Raised when required resources cannot be allocated.
    """

    pass


class RecoveryError(FaultToleranceError):
    """
    Recovery Failure Exception

    Raised when task or job recovery fails.
    """

    pass


class CheckpointError(FaultToleranceError):
    """
    Checkpoint Exception

    Exception occurring when saving or loading a checkpoint.
    """

    pass


class PlacementError(SchedulingError):
    """
    Placement Strategy Exception

    Exception occurring when deciding task placement.
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
