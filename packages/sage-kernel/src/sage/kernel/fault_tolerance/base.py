"""
容错处理器抽象基类

定义了容错处理的接口和抽象方法。
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseFaultHandler(ABC):
    """
    容错处理器基类

    定义了处理故障、恢复任务的接口。
    """

    def __init__(self):
        self.logger: Any = None  # Will be injected by dispatcher
        self.dispatcher: Any = None  # Will be injected by dispatcher

    @abstractmethod
    def handle_failure(self, task_id: str, error: Exception) -> bool:
        """
        处理任务失败

        Args:
            task_id: 失败的任务 ID
            error: 失败的异常信息

        Returns:
            True 如果处理成功
        """
        pass

    @abstractmethod
    def can_recover(self, task_id: str) -> bool:
        """
        检查任务是否可以恢复

        Args:
            task_id: 任务 ID

        Returns:
            True 如果任务可以恢复
        """
        pass

    @abstractmethod
    def recover(self, task_id: str) -> bool:
        """
        恢复任务

        Args:
            task_id: 要恢复的任务 ID

        Returns:
            True 如果恢复成功
        """
        pass

    def on_failure_detected(self, task_id: str, error: Exception):  # noqa: B027
        """
        故障检测回调

        当检测到故障时调用，默认实现为空。

        Args:
            task_id: 任务 ID
            error: 异常信息
        """
        pass

    def on_recovery_started(self, task_id: str):  # noqa: B027
        """
        恢复开始回调

        当开始恢复时调用，默认实现为空。

        Args:
            task_id: 任务 ID
        """
        pass

    def on_recovery_completed(self, task_id: str, success: bool):  # noqa: B027
        """
        恢复完成回调

        当恢复完成时调用，默认实现为空。

        Args:
            task_id: 任务 ID
            success: 恢复是否成功
        """
        pass


__all__ = ["BaseFaultHandler"]
