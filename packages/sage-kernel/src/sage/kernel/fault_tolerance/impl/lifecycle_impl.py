"""
Actor 和 Task 生命周期管理实现

负责管理 Actor 和 Task 的创建、监控、清理和终止的具体实现。
"""

from typing import Any, Protocol

from sage.common.core import DEFAULT_CLEANUP_TIMEOUT, TaskID
from sage.kernel.utils.helpers import wait_for_all_stopped


class LoggerProtocol(Protocol):
    """Logger 协议，定义日志器的接口"""

    def debug(self, msg: str, *args, **kwargs) -> None:
        """Debug level logging"""
        ...

    def info(self, msg: str, *args, **kwargs) -> None:
        """Info level logging"""
        ...

    def warning(self, msg: str, *args, **kwargs) -> None:
        """Warning level logging"""
        ...

    def error(self, msg: str, *args, **kwargs) -> None:
        """Error level logging"""
        ...


class LifecycleManagerImpl:
    """
    Actor 生命周期管理器实现

    负责管理 Ray Actor 和本地 Task 的生命周期。
    """

    def __init__(self):
        """初始化生命周期管理器"""
        self.logger: LoggerProtocol | None = None  # 可以后续注入 logger

    def cleanup_actor(
        self,
        actor_wrapper,
        cleanup_timeout: float = DEFAULT_CLEANUP_TIMEOUT,
        no_restart: bool = True,
    ) -> tuple[bool, bool]:
        """
        清理并终止单个 Actor

        Args:
            actor_wrapper: ActorWrapper 实例
            cleanup_timeout: 清理超时时间（秒）
            no_restart: 是否禁止 Ray Actor 重启

        Returns:
            (cleanup_success, kill_success) 元组
        """
        cleanup_success = False
        kill_success = False

        try:
            # 1. 尝试正常清理
            if hasattr(actor_wrapper, "cleanup"):
                try:
                    if actor_wrapper.is_ray_actor():
                        # Ray Actor: 异步调用 cleanup
                        cleanup_ref = actor_wrapper.call_async("cleanup")

                        # 等待清理完成（带超时）
                        import ray

                        ray.get(cleanup_ref, timeout=cleanup_timeout)
                        cleanup_success = True
                    else:
                        # 本地对象: 直接调用 cleanup
                        actor_wrapper.cleanup()
                        cleanup_success = True

                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Cleanup failed: {e}")

            # 2. 终止 Actor
            if actor_wrapper.is_ray_actor():
                kill_success = actor_wrapper.kill_actor(no_restart=no_restart)
            else:
                # 本地对象，标记为成功
                kill_success = True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in cleanup_actor: {e}")

        return cleanup_success, kill_success

    def cleanup_all(
        self,
        tasks: dict[TaskID, Any],
        services: dict[str, Any] | None = None,
        cleanup_timeout: float = DEFAULT_CLEANUP_TIMEOUT,
        no_restart: bool = True,
    ) -> dict[str, tuple[bool, bool]]:
        """
        清理所有任务和服务

        Args:
            tasks: 任务字典 {task_id: task_wrapper}
            services: 服务字典 {service_id: service_wrapper}
            cleanup_timeout: 清理超时时间（秒）
            no_restart: 是否禁止 Ray Actor 重启（默认True）

        Returns:
            结果字典 {id: (cleanup_success, kill_success)}
        """
        results = {}

        # 清理任务
        for task_id, task in tasks.items():
            result = self.cleanup_actor(task, cleanup_timeout, no_restart=no_restart)
            results[task_id] = result

            if self.logger:
                cleanup_ok, kill_ok = result
                if kill_ok:
                    self.logger.debug(f"Successfully cleaned up task: {task_id}")
                else:
                    self.logger.warning(f"Failed to clean up task: {task_id}")

        # 清理服务
        if services:
            for service_id, service in services.items():
                result = self.cleanup_actor(service, cleanup_timeout, no_restart=no_restart)
                results[service_id] = result

                if self.logger:
                    cleanup_ok, kill_ok = result
                    if kill_ok:
                        self.logger.debug(f"Successfully cleaned up service: {service_id}")
                    else:
                        self.logger.warning(f"Failed to clean up service: {service_id}")

        return results

    def cleanup_batch(
        self,
        actors: list[tuple[str, Any]],
        cleanup_timeout: float = DEFAULT_CLEANUP_TIMEOUT,
    ) -> dict[str, tuple[bool, bool]]:
        """
        批量清理 Actor

        Args:
            actors: Actor 列表 [(id, actor_wrapper), ...]
            cleanup_timeout: 清理超时时间（秒）

        Returns:
            结果字典 {id: (cleanup_success, kill_success)}
        """
        results = {}

        for actor_id, actor_wrapper in actors:
            result = self.cleanup_actor(actor_wrapper, cleanup_timeout)
            results[actor_id] = result

        return results

    def get_cleanup_statistics(
        self, cleanup_results: dict[str, tuple[bool, bool]]
    ) -> dict[str, Any]:
        """
        获取清理统计信息

        Args:
            cleanup_results: 清理结果字典

        Returns:
            统计信息字典
        """
        total = len(cleanup_results)
        cleanup_success = sum(1 for _, (c, _) in cleanup_results.items() if c)
        kill_success = sum(1 for _, (_, k) in cleanup_results.items() if k)

        return {
            "total": total,
            "cleanup_success": cleanup_success,
            "kill_success": kill_success,
            "cleanup_rate": cleanup_success / total if total > 0 else 0,
            "kill_rate": kill_success / total if total > 0 else 0,
        }

    def wait_for_actors_stop(self, tasks: dict[TaskID, Any], timeout: float = 10.0) -> bool:
        """
        等待所有任务停止

        Args:
            tasks: 任务字典
            timeout: 超时时间（秒）

        Returns:
            True 如果所有任务都已停止
        """
        return wait_for_all_stopped(tasks, timeout=timeout, logger=self.logger)


__all__ = ["LifecycleManagerImpl"]
