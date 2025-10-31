"""
Fault Tolerance Factory

从配置创建容错策略实例的工厂模块。
这是内部使用的模块，应用用户不会直接使用。
"""

from typing import Any

from sage.kernel.fault_tolerance.base import BaseFaultHandler
from sage.kernel.fault_tolerance.impl.checkpoint_recovery import CheckpointBasedRecovery
from sage.kernel.fault_tolerance.impl.lifecycle_impl import LifecycleManagerImpl
from sage.kernel.fault_tolerance.impl.restart_recovery import RestartBasedRecovery
from sage.kernel.fault_tolerance.impl.restart_strategy import (
    ExponentialBackoffStrategy,
    FailureRateStrategy,
    FixedDelayStrategy,
)


def create_fault_handler_from_config(
    config: dict[str, Any] | None = None,
) -> BaseFaultHandler:
    """
    从配置字典创建容错处理器

    这是内部使用的工厂函数，由 Dispatcher/JobManager 调用。
    应用用户不会直接调用此函数。

    Args:
        config: 容错配置字典，示例：
            {
                "strategy": "checkpoint",  # 或 "restart"
                "checkpoint_interval": 60.0,
                "max_recovery_attempts": 3,
                ...
            }

    Returns:
        BaseFaultHandler 实例

    Raises:
        ValueError: 如果配置无效

    Examples:
        # 从 Environment 配置创建
        config = env.config.get("fault_tolerance", {})
        handler = create_fault_handler_from_config(config)
    """
    if not config:
        # 默认使用重启策略
        return RestartBasedRecovery(restart_strategy=ExponentialBackoffStrategy())

    strategy = config.get("strategy", "restart")

    if strategy == "checkpoint":
        return _create_checkpoint_handler(config)
    elif strategy == "restart":
        return _create_restart_handler(config)
    else:
        raise ValueError(
            f"Unknown fault tolerance strategy: {strategy}. "
            f"Supported strategies: 'checkpoint', 'restart'"
        )


def _create_checkpoint_handler(config: dict[str, Any]) -> CheckpointBasedRecovery:
    """创建基于 Checkpoint 的容错处理器"""
    checkpoint_dir = config.get("checkpoint_dir", ".sage/checkpoints")
    checkpoint_interval = config.get("checkpoint_interval", 60.0)
    max_recovery_attempts = config.get("max_recovery_attempts", 3)

    return CheckpointBasedRecovery(
        checkpoint_dir=checkpoint_dir,
        checkpoint_interval=checkpoint_interval,
        max_recovery_attempts=max_recovery_attempts,
    )


def _create_restart_handler(config: dict[str, Any]) -> RestartBasedRecovery:
    """创建基于重启的容错处理器"""

    restart_strategy_type = config.get("restart_strategy", "exponential")

    # 创建重启策略
    restart_strategy: FixedDelayStrategy | ExponentialBackoffStrategy | FailureRateStrategy
    if restart_strategy_type == "fixed":
        delay = config.get("delay", 5.0)
        max_attempts = config.get("max_attempts", 3)
        restart_strategy = FixedDelayStrategy(delay=delay, max_attempts=max_attempts)

    elif restart_strategy_type == "exponential":
        initial_delay = config.get("initial_delay", 1.0)
        max_delay = config.get("max_delay", 60.0)
        multiplier = config.get("multiplier", 2.0)
        max_attempts = config.get("max_attempts", 5)
        restart_strategy = ExponentialBackoffStrategy(
            initial_delay=initial_delay,
            max_delay=max_delay,
            multiplier=multiplier,
            max_attempts=max_attempts,
        )

    elif restart_strategy_type == "failure_rate":
        max_failures = config.get("max_failures_per_interval", 5)
        interval = config.get("interval_seconds", 60.0)
        delay = config.get("delay", 5.0)
        restart_strategy = FailureRateStrategy(
            max_failures_per_interval=max_failures,
            interval_seconds=interval,
            delay=delay,
        )
    else:
        # 默认使用指数退避
        restart_strategy = ExponentialBackoffStrategy()

    return RestartBasedRecovery(restart_strategy=restart_strategy)


def create_lifecycle_manager() -> LifecycleManagerImpl:
    """
    创建生命周期管理器

    Returns:
        LifecycleManagerImpl 实例
    """
    return LifecycleManagerImpl()


__all__ = [
    "create_fault_handler_from_config",
    "create_lifecycle_manager",
]
