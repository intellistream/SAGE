"""
Checkpoint-based Fault Tolerance Strategy

基于检查点的容错恢复策略，周期性保存任务状态，失败时从最近的检查点恢复。
"""

import time
from typing import TYPE_CHECKING, Any

from sage.common.core import TaskID
from sage.kernel.fault_tolerance.base import BaseFaultHandler
from sage.kernel.fault_tolerance.impl.checkpoint_impl import CheckpointManagerImpl

if TYPE_CHECKING:
    from sage.kernel.runtime.dispatcher import Dispatcher


class CheckpointBasedRecovery(BaseFaultHandler):
    """
    基于 Checkpoint 的容错恢复策略

    定期保存任务状态，失败时从最近的 checkpoint 恢复。
    适用于长时间运行的任务，能够减少重新计算的开销。
    """

    def __init__(
        self,
        checkpoint_manager: CheckpointManagerImpl | None = None,
        checkpoint_interval: float = 60.0,
        max_recovery_attempts: int = 3,
        checkpoint_dir: str = ".sage/checkpoints",
    ):
        """
        初始化 Checkpoint 容错策略

        Args:
            checkpoint_manager: Checkpoint 管理器
            checkpoint_interval: Checkpoint 保存间隔（秒）
            max_recovery_attempts: 最大恢复尝试次数
            checkpoint_dir: Checkpoint 存储目录
        """
        self.checkpoint_manager = checkpoint_manager or CheckpointManagerImpl(checkpoint_dir)
        self.checkpoint_interval = checkpoint_interval
        self.max_recovery_attempts = max_recovery_attempts

        # 记录失败信息
        self.failure_counts: dict[TaskID, int] = {}
        self.last_checkpoint_time: dict[TaskID, float] = {}

        self.logger = None  # 可以后续注入
        self.dispatcher: Dispatcher | None = None  # 可以后续注入

    def handle_failure(self, task_id: TaskID, error: Exception) -> bool:
        """
        处理任务失败

        Args:
            task_id: 失败的任务 ID
            error: 失败的异常信息

        Returns:
            True 如果处理成功
        """
        # 记录失败
        self.failure_counts[task_id] = self.failure_counts.get(task_id, 0) + 1

        if self.logger:
            self.logger.warning(
                f"Task {task_id} failed (attempt #{self.failure_counts[task_id]}): {error}"
            )

        # 调用回调
        self.on_failure_detected(task_id, error)

        # 检查是否可以恢复
        if self.can_recover(task_id):
            return self.recover(task_id)
        else:
            if self.logger:
                self.logger.error(f"Task {task_id} cannot be recovered (max attempts reached)")
            return False

    def can_recover(self, task_id: TaskID) -> bool:
        """
        检查任务是否可以恢复

        Args:
            task_id: 任务 ID

        Returns:
            True 如果任务可以恢复
        """
        failure_count = self.failure_counts.get(task_id, 0)
        has_checkpoint = len(self.checkpoint_manager.list_checkpoints(task_id)) > 0

        return failure_count < self.max_recovery_attempts and has_checkpoint

    def _is_remote_task(self, task_id: TaskID) -> bool:
        """判断是否为远程任务"""
        if not hasattr(self, "dispatcher") or not self.dispatcher:
            return False
        task = self.dispatcher.tasks.get(task_id)
        from sage.kernel.utils.ray.actor import ActorWrapper

        return isinstance(task, ActorWrapper)

    def recover(self, task_id: TaskID) -> bool:
        """
        从 Checkpoint 恢复任务（本地或远程）
        """
        self.on_recovery_started(task_id)
        try:
            state = self.checkpoint_manager.load_checkpoint(task_id)
            if state is None:
                if self.logger:
                    self.logger.error(f"No checkpoint found for task {task_id}")
                self.on_recovery_completed(task_id, False)
                return False

            if self.logger:
                self.logger.info(
                    f"Loaded checkpoint for task {task_id}, "
                    f"processed_count={state.get('processed_count', 0)}, "
                    f"checkpoint_counter={state.get('checkpoint_counter', 0)}"
                )

            if not hasattr(self, "dispatcher") or not self.dispatcher:
                if self.logger:
                    self.logger.error("No dispatcher available for recovery")
                self.on_recovery_completed(task_id, False)
                return False

            success = self.dispatcher.restart_task_with_state(task_id, state)

            if success and self.logger:
                self.logger.info(f"Task {task_id} restarted and state restored")
            elif not success and self.logger:
                self.logger.error(f"Failed to restart task {task_id}")

            self.on_recovery_completed(task_id, success)
            return success

        except Exception as e:
            if self.logger:
                self.logger.error(f"Recover task {task_id} failed: {e}", exc_info=True)
            self.on_recovery_completed(task_id, False)
            return False

    def on_recovery_started(self, task_id: TaskID):
        """恢复开始时的回调"""
        if self.logger:
            self.logger.info(f"🔄 Starting recovery for task {task_id}")

    def on_recovery_completed(self, task_id: TaskID, success: bool):
        """恢复完成时的回调"""
        if self.logger:
            if success:
                self.logger.info(f"✅ Recovery completed successfully for task {task_id}")
                # 可以在这里添加更多逻辑，如：
                # - 发送通知
                # - 记录指标
                # - 触发告警解除
            else:
                self.logger.error(f"❌ Recovery failed for task {task_id}")
                # 可以在这里添加失败处理逻辑，如：
                # - 发送告警
                # - 记录失败原因
                # - 触发备用方案

    def on_failure_detected(self, task_id: TaskID, error: Exception):
        """检测到失败时的回调"""
        if self.logger:
            self.logger.warning(f"⚠️ Failure detected for task {task_id}: {error}")
            # 可以在这里添加更多逻辑，如：
            # - 发送告警通知
            # - 记录失败模式
            # - 更新监控面板

    def save_checkpoint(self, task_id: TaskID, state: dict[str, Any], force: bool = False) -> bool:
        """
        保存任务 checkpoint

        Args:
            task_id: 任务 ID
            state: 任务状态
            force: 是否强制保存（忽略时间间隔）

        Returns:
            True 如果保存成功
        """
        current_time = time.time()
        last_time = self.last_checkpoint_time.get(task_id, 0)

        # 检查是否需要保存
        if not force and (current_time - last_time) < self.checkpoint_interval:
            return False

        try:
            self.checkpoint_manager.save_checkpoint(task_id, state)
            self.last_checkpoint_time[task_id] = current_time

            if self.logger:
                self.logger.debug(f"Saved checkpoint for task {task_id}")

            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to save checkpoint for {task_id}: {e}")
            return False

    def cleanup_checkpoints(self, task_id: TaskID):
        """
        清理任务的所有 checkpoint

        Args:
            task_id: 任务 ID
        """
        try:
            self.checkpoint_manager.delete_checkpoint(task_id)

            if task_id in self.failure_counts:
                del self.failure_counts[task_id]
            if task_id in self.last_checkpoint_time:
                del self.last_checkpoint_time[task_id]

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to cleanup checkpoints for {task_id}: {e}")


__all__ = ["CheckpointBasedRecovery"]
