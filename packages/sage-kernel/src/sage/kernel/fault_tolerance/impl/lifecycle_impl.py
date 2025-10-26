"""
Actor 和 Task 生命周期管理实现

负责管理 Actor 和 Task 的创建、监控、清理和终止的具体实现。
"""

import time
from typing import Any

from sage.common.core.constants import DEFAULT_CLEANUP_TIMEOUT
from sage.common.core.types import TaskID


class LifecycleManagerImpl:
    """
    <<<<<<< HEAD:packages/sage-kernel/src/sage/kernel/fault_tolerance/lifecycle.py
        Actor 生命周期管理器

    =======
        Actor 生命周期管理器实现

    >>>>>>> refactor/fault_tolreance:packages/sage-kernel/src/sage/kernel/fault_tolerance/impl/lifecycle_impl.py
        负责管理 Ray Actor 和本地 Task 的生命周期。
    """

    def __init__(self):
        """初始化生命周期管理器"""
        self.logger = None  # 可以后续注入 logger

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
    ) -> dict[str, tuple[bool, bool]]:
        """
        清理所有任务和服务

        Args:
            tasks: 任务字典 {task_id: task_wrapper}
            services: 服务字典 {service_id: service_wrapper}
            cleanup_timeout: 清理超时时间（秒）

        Returns:
            结果字典 {id: (cleanup_success, kill_success)}
        """
        results = {}

        # 清理任务
        for task_id, task in tasks.items():
            result = self.cleanup_actor(task, cleanup_timeout)
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
                result = self.cleanup_actor(service, cleanup_timeout)
                results[service_id] = result

                if self.logger:
                    cleanup_ok, kill_ok = result
                    if kill_ok:
                        self.logger.debug(
                            f"Successfully cleaned up service: {service_id}"
                        )
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

    def wait_for_actors_stop(
        self, tasks: dict[TaskID, Any], timeout: float = 10.0
    ) -> bool:
        """
        等待所有任务停止

        Args:
            tasks: 任务字典
            timeout: 超时时间（秒）

        Returns:
            True 如果所有任务都已停止
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            all_stopped = True

            for _task_id, task in tasks.items():
                if hasattr(task, "is_running") and task.is_running:
                    all_stopped = False
                    break

            if all_stopped:
                if self.logger:
                    self.logger.debug("All tasks stopped")
                return True

            time.sleep(0.1)

        if self.logger:
            self.logger.warning(f"Timeout waiting for tasks to stop after {timeout}s")

        return False


__all__ = ["LifecycleManagerImpl"]
