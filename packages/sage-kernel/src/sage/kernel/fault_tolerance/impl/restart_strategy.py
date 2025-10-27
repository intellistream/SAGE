"""
重启策略实现

定义任务失败后的重启策略具体实现。
"""

from abc import ABC, abstractmethod

from sage.common.core import DEFAULT_MAX_RESTART_ATTEMPTS


class RestartStrategy(ABC):
    """
    重启策略基类

    定义任务重启的策略接口。
    """

    @abstractmethod
    def should_restart(self, failure_count: int) -> bool:
        """
        判断是否应该重启

        Args:
            failure_count: 当前失败次数

        Returns:
            True 如果应该重启
        """
        pass

    @abstractmethod
    def get_restart_delay(self, failure_count: int) -> float:
        """
        获取重启延迟时间

        Args:
            failure_count: 当前失败次数

        Returns:
            延迟时间（秒）
        """
        pass

    def on_restart_attempt(self, failure_count: int):  # noqa: B027
        """
        重启尝试回调

        Args:
            failure_count: 当前失败次数
        """
        pass


class FixedDelayStrategy(RestartStrategy):
    """
    固定延迟重启策略

    每次重启使用固定的延迟时间。
    """

    def __init__(self, delay: float = 5.0, max_attempts: int = DEFAULT_MAX_RESTART_ATTEMPTS):
        """
        初始化固定延迟策略

        Args:
            delay: 固定延迟时间（秒）
            max_attempts: 最大重启尝试次数
        """
        self.delay = delay
        self.max_attempts = max_attempts

    def should_restart(self, failure_count: int) -> bool:
        """
        检查是否应该重启

        Args:
            failure_count: 当前失败次数

        Returns:
            True 如果失败次数未超过最大尝试次数
        """
        return failure_count < self.max_attempts

    def get_restart_delay(self, failure_count: int) -> float:
        """
        获取固定延迟时间

        Args:
            failure_count: 当前失败次数（未使用）

        Returns:
            固定延迟时间
        """
        return self.delay


class ExponentialBackoffStrategy(RestartStrategy):
    """
    指数退避重启策略

    延迟时间随失败次数指数增长。
    """

    def __init__(
        self,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
        max_attempts: int = 5,
    ):
        """
        初始化指数退避策略

        Args:
            initial_delay: 初始延迟时间（秒）
            max_delay: 最大延迟时间（秒）
            multiplier: 延迟倍数
            max_attempts: 最大重启尝试次数
        """
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.max_attempts = max_attempts

    def should_restart(self, failure_count: int) -> bool:
        """
        检查是否应该重启

        Args:
            failure_count: 当前失败次数

        Returns:
            True 如果失败次数未超过最大尝试次数
        """
        return failure_count < self.max_attempts

    def get_restart_delay(self, failure_count: int) -> float:
        """
        计算指数退避延迟时间

        delay = min(initial_delay * multiplier^failure_count, max_delay)

        Args:
            failure_count: 当前失败次数

        Returns:
            计算后的延迟时间
        """
        delay = self.initial_delay * (self.multiplier**failure_count)
        return min(delay, self.max_delay)


class FailureRateStrategy(RestartStrategy):
    """
    基于失败率的重启策略

    根据一段时间内的失败率决定是否重启。
    """

    def __init__(
        self,
        max_failures_per_interval: int = 5,
        interval_seconds: float = 60.0,
        delay: float = 5.0,
    ):
        """
        初始化失败率策略

        Args:
            max_failures_per_interval: 时间窗口内最大失败次数
            interval_seconds: 时间窗口大小（秒）
            delay: 重启延迟时间（秒）
        """
        self.max_failures_per_interval = max_failures_per_interval
        self.interval_seconds = interval_seconds
        self.delay = delay
        self.failure_timestamps: list[float] = []

    def should_restart(self, failure_count: int) -> bool:
        """
        根据失败率判断是否应该重启

        Args:
            failure_count: 总失败次数（未使用，使用时间戳判断）

        Returns:
            True 如果时间窗口内失败次数未超过阈值
        """
        import time

        current_time = time.time()

        # 记录当前失败
        self.failure_timestamps.append(current_time)

        # 清理过期的失败记录
        cutoff_time = current_time - self.interval_seconds
        self.failure_timestamps = [ts for ts in self.failure_timestamps if ts > cutoff_time]

        # 检查失败率
        return len(self.failure_timestamps) <= self.max_failures_per_interval

    def get_restart_delay(self, failure_count: int) -> float:
        """
        获取重启延迟时间

        Args:
            failure_count: 当前失败次数（未使用）

        Returns:
            固定延迟时间
        """
        return self.delay


__all__ = [
    "RestartStrategy",
    "FixedDelayStrategy",
    "ExponentialBackoffStrategy",
    "FailureRateStrategy",
]
