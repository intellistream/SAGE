"""
Fault Tolerance Module - 分布式容错

这个模块负责故障检测、恢复、Checkpoint 和生命周期管理。

主要组件:
- BaseFaultHandler: 容错处理器基类
- RecoveryManager: 恢复管理器
- ActorLifecycleManager: Actor 生命周期管理
- CheckpointManager: Checkpoint 管理
- RestartStrategy: 重启策略
"""

from sage.kernel.fault_tolerance.base import BaseFaultHandler
from sage.kernel.fault_tolerance.checkpoint import CheckpointManager
from sage.kernel.fault_tolerance.lifecycle import ActorLifecycleManager
from sage.kernel.fault_tolerance.recovery import RecoveryManager
from sage.kernel.fault_tolerance.restart import (
    ExponentialBackoffStrategy,
    FixedDelayStrategy,
    RestartStrategy,
)

__all__ = [
    "BaseFaultHandler",
    "RecoveryManager",
    "ActorLifecycleManager",
    "CheckpointManager",
    "RestartStrategy",
    "FixedDelayStrategy",
    "ExponentialBackoffStrategy",
]
