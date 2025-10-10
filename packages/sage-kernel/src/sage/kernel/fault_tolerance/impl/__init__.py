"""
Fault Tolerance Implementation Module

包含各种容错策略的具体实现。
"""

from sage.kernel.fault_tolerance.impl.checkpoint_impl import CheckpointManagerImpl
from sage.kernel.fault_tolerance.impl.checkpoint_recovery import CheckpointBasedRecovery
from sage.kernel.fault_tolerance.impl.lifecycle_impl import LifecycleManagerImpl
from sage.kernel.fault_tolerance.impl.restart_recovery import RestartBasedRecovery
from sage.kernel.fault_tolerance.impl.restart_strategy import (
    ExponentialBackoffStrategy,
    FailureRateStrategy,
    FixedDelayStrategy,
    RestartStrategy,
)

__all__ = [
    # Recovery implementations
    "CheckpointBasedRecovery",
    "RestartBasedRecovery",
    # Manager implementations
    "LifecycleManagerImpl",
    "CheckpointManagerImpl",
    # Restart strategies
    "RestartStrategy",
    "FixedDelayStrategy",
    "ExponentialBackoffStrategy",
    "FailureRateStrategy",
]
