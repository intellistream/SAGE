"""
恢复管理器

负责处理任务和作业的故障恢复。
"""

import time
from typing import TYPE_CHECKING, Dict, Any, Optional

from sage.kernel.fault_tolerance.base import BaseFaultHandler
from sage.kernel.fault_tolerance.restart import RestartStrategy, ExponentialBackoffStrategy
from sage.kernel.fault_tolerance.checkpoint import CheckpointManager
from sage.kernel.core.types import TaskID, JobID
from sage.kernel.core.exceptions import RecoveryError

if TYPE_CHECKING:
    from sage.kernel.runtime.dispatcher import Dispatcher


class RecoveryManager(BaseFaultHandler):
    """
    恢复管理器
    
    处理任务和作业的故障恢复，整合重启策略和 checkpoint。
    """
    
    def __init__(
        self,
        restart_strategy: Optional[RestartStrategy] = None,
        checkpoint_manager: Optional[CheckpointManager] = None,
        enable_checkpoint: bool = False
    ):
        """
        初始化恢复管理器
        
        Args:
            restart_strategy: 重启策略（默认使用指数退避）
            checkpoint_manager: Checkpoint 管理器
            enable_checkpoint: 是否启用 checkpoint
        """
        self.restart_strategy = restart_strategy or ExponentialBackoffStrategy()
        self.checkpoint_manager = checkpoint_manager
        self.enable_checkpoint = enable_checkpoint
        
        # 记录失败信息
        self.failure_counts: Dict[TaskID, int] = {}
        self.failure_history: Dict[TaskID, list] = {}
        
        self.logger = None  # 可以后续注入
    
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
        
        if task_id not in self.failure_history:
            self.failure_history[task_id] = []
        
        self.failure_history[task_id].append({
            "timestamp": time.time(),
            "error": str(error),
            "failure_count": self.failure_counts[task_id],
        })
        
        if self.logger:
            self.logger.warning(
                f"Task {task_id} failed (attempt #{self.failure_counts[task_id]}): {error}"
            )
        
        # 调用回调
        self.on_failure_detected(task_id, error)
        
        # 检查是否可以重启
        if self.can_recover(task_id):
            return self.recover(task_id)
        else:
            if self.logger:
                self.logger.error(
                    f"Task {task_id} cannot be recovered (max attempts reached)"
                )
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
        return self.restart_strategy.should_restart(failure_count)
    
    def recover(self, task_id: TaskID) -> bool:
        """
        恢复任务
        
        Args:
            task_id: 要恢复的任务 ID
            
        Returns:
            True 如果恢复成功
        """
        failure_count = self.failure_counts.get(task_id, 0)
        
        # 调用回调
        self.on_recovery_started(task_id)
        
        # 获取重启延迟
        delay = self.restart_strategy.get_restart_delay(failure_count)
        
        if self.logger:
            self.logger.info(
                f"Attempting to recover task {task_id} after {delay}s delay "
                f"(attempt #{failure_count + 1})"
            )
        
        # 等待重启延迟
        time.sleep(delay)
        
        # 如果启用了 checkpoint，尝试从 checkpoint 恢复
        if self.enable_checkpoint and self.checkpoint_manager:
            try:
                state = self.checkpoint_manager.load_checkpoint(task_id)
                if state:
                    if self.logger:
                        self.logger.info(f"Loaded checkpoint for task {task_id}")
                    # TODO: 实际恢复状态的逻辑
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Failed to load checkpoint for {task_id}: {e}")
        
        # TODO: 实际重启任务的逻辑
        # 这里应该调用任务的重启方法
        
        success = True  # 暂时假设成功
        
        # 调用回调
        self.on_recovery_completed(task_id, success)
        
        return success
    
    def recover_job(
        self, 
        job_id: str,
        dispatcher: "Dispatcher",
        restart_count: int = 0
    ) -> Dict[str, Any]:
        """
        恢复整个作业
        
        Args:
            job_id: 作业 UUID
            dispatcher: 作业的 Dispatcher 实例
            restart_count: 当前重启次数
            
        Returns:
            恢复结果字典，包含 'success' 键和可选的 'error' 键
        """
        try:
            if self.logger:
                self.logger.info(f"Attempting to recover job {job_id}")
            
            # 重新启动 dispatcher
            dispatcher.start()
            
            if self.logger:
                self.logger.info(
                    f"Job {job_id} recovered successfully (restart #{restart_count + 1})"
                )
            
            return {
                "success": True,
                "job_id": job_id,
                "restart_count": restart_count + 1,
            }
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to recover job {job_id}: {e}")
            
            return {
                "success": False,
                "job_id": job_id,
                "error": str(e),
            }
    
    def get_failure_statistics(self, task_id: Optional[TaskID] = None) -> Dict[str, Any]:
        """
        获取失败统计信息
        
        Args:
            task_id: 任务 ID（如果为 None，返回所有任务的统计）
            
        Returns:
            统计信息字典
        """
        if task_id:
            return {
                "task_id": task_id,
                "failure_count": self.failure_counts.get(task_id, 0),
                "failure_history": self.failure_history.get(task_id, []),
            }
        else:
            return {
                "total_failed_tasks": len(self.failure_counts),
                "total_failures": sum(self.failure_counts.values()),
                "failure_counts": dict(self.failure_counts),
            }
    
    def reset_failure_count(self, task_id: TaskID):
        """
        重置任务的失败计数
        
        Args:
            task_id: 任务 ID
        """
        if task_id in self.failure_counts:
            del self.failure_counts[task_id]
        if task_id in self.failure_history:
            del self.failure_history[task_id]


__all__ = ["RecoveryManager"]
