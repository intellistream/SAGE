from __future__ import annotations

from typing import TYPE_CHECKING

from sage.kernel.api.base_environment import BaseEnvironment

if TYPE_CHECKING:
    from sage.kernel.runtime.job_manager import JobManager


class LocalEnvironment(BaseEnvironment):
    """本地环境，直接使用本地JobManager实例"""

    def __init__(
        self,
        name: str = "localenvironment",
        config: dict | None = None,
        scheduler=None,
        enable_monitoring: bool = False,
    ):
        super().__init__(
            name,
            config,
            platform="local",
            scheduler=scheduler,
            enable_monitoring=enable_monitoring,
        )

        # 本地环境不需要客户端
        self._engine_client = None

    def submit(self, autostop: bool = False):
        """
        提交作业到JobManager执行

        Args:
            autostop (bool): 如果为True，方法将阻塞直到所有批处理任务完成后自动停止
                           如果为False，方法立即返回，需要手动管理任务生命周期

        Returns:
            str: 任务的UUID
        """
        # 提交作业（传递 autostop 参数）
        env_uuid = self.jobmanager.submit_job(self, autostop=autostop)

        if autostop:
            self._wait_for_completion()

        return env_uuid

    def _wait_for_completion(self):
        """
        等待批处理任务完成
        在本地环境中直接监控JobManager实例的状态

        改进的等待策略：
        1. 不监控源节点停止（源节点停止 ≠ 数据处理完）
        2. 监控 Sink 节点接收到停止信号（所有数据已处理完）
        3. 或监控所有任务都停止（dispatcher 清理完成）
        """
        import time

        if not self.env_uuid:
            self.logger.warning("No environment UUID found, cannot wait for completion")
            return

        self.logger.info("Waiting for batch processing to complete...")
        self.logger.info(
            "⏳ Strategy: Wait for all data to be processed (not just source completion)"
        )

        # 设置最大等待时间，避免无限等待
        max_wait_time = 12000.0  # 增加到 10 分钟，适应长时间处理
        start_time = time.time()
        check_interval = 1.0  # 增加检查间隔，减少 CPU 占用

        try:
            while time.time() - start_time < max_wait_time:
                # 直接检查本地JobManager实例中的作业状态
                job_info = self.jobmanager.jobs.get(self.env_uuid)

                if job_info is None:
                    # 作业已被删除，说明完成了
                    self.logger.info("✅ Batch processing completed successfully (job deleted)")
                    break

                # 检查作业状态（优先检查这个，因为它更可靠）
                if job_info.status in ["stopped", "failed"]:
                    self.logger.info(
                        f"✅ Batch processing completed with status: {job_info.status}"
                    )
                    break

                # 改进的停止检测：检查所有 Task 是否都已停止
                # 这确保队列中的数据都被处理完
                dispatcher = job_info.dispatcher
                if hasattr(dispatcher, "tasks") and len(dispatcher.tasks) > 0:
                    all_tasks_stopped = all(
                        not task.is_running for task in dispatcher.tasks.values()
                    )
                    if all_tasks_stopped:
                        self.logger.info("✅ All tasks stopped, processing complete")
                        break

                # 检查dispatcher状态
                # 注意：dispatcher.is_running 可能在stop()方法执行期间仍然为True
                # 所以我们也检查dispatcher是否已经开始停止过程
                dispatcher_stopped = not job_info.dispatcher.is_running
                if dispatcher_stopped:
                    # Dispatcher已停止，但还需要等待服务清理完成
                    # 检查是否所有服务都已清理
                    if (
                        len(job_info.dispatcher.services) == 0
                        and len(job_info.dispatcher.tasks) == 0
                    ):
                        self.logger.info(
                            "Dispatcher stopped and all resources cleaned up, batch processing completed"
                        )
                        break
                    else:
                        # 服务还在清理中，继续等待
                        self.logger.debug(
                            f"Waiting for resources to be cleaned up: {len(job_info.dispatcher.tasks)} tasks, {len(job_info.dispatcher.services)} services"
                        )

                # 如果dispatcher正在停止过程中，等待更短的时间
                # 这样可以避免在dispatcher停止过程中的race condition
                time.sleep(check_interval)

            else:
                # 超时了，强制停止作业
                self.logger.warning(
                    f"Timeout waiting for batch processing to complete after {max_wait_time}s"
                )
                try:
                    self.stop()
                except Exception as stop_error:
                    self.logger.error(f"Error stopping timed out job: {stop_error}")

        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal, stopping batch processing...")
            self.stop()
        except Exception as e:
            self.logger.error(f"Error waiting for completion: {e}")
            # 在出错时尝试停止作业
            try:
                self.stop()
            except Exception as stop_error:
                self.logger.error(f"Error stopping job after wait error: {stop_error}")

        finally:
            # 确保清理资源
            self.is_running = False

    @property
    def jobmanager(self) -> JobManager:
        """直接返回JobManager的单例实例"""
        if self._jobmanager is None:
            from sage.kernel.runtime.job_manager import JobManager

            # 获取JobManager单例实例
            jobmanager_instance = JobManager()
            # 本地环境直接返回JobManager实例，不使用ActorWrapper
            self._jobmanager = jobmanager_instance

        return self._jobmanager

    def stop(self):
        """停止管道运行"""
        if not self.env_uuid:
            self.logger.warning("Environment not submitted, nothing to stop")
            return

        self.logger.info("Stopping pipeline...")

        try:
            response = self.jobmanager.pause_job(self.env_uuid)

            if response.get("status") == "success":
                self.is_running = False
                self.logger.info("Pipeline stopped successfully")
            else:
                self.logger.warning(f"Failed to stop pipeline: {response.get('message')}")
        except Exception as e:
            self.logger.error(f"Error stopping pipeline: {e}")

    def close(self):
        """关闭管道运行"""
        if not self.env_uuid:
            self.logger.warning("Environment not submitted, nothing to close")
            return

        self.logger.info("Closing environment...")

        try:
            response = self.jobmanager.pause_job(self.env_uuid)

            if response.get("status") == "success":
                self.logger.info("Environment closed successfully")
            else:
                self.logger.warning(f"Failed to close environment: {response.get('message')}")

        except Exception as e:
            self.logger.error(f"Error closing environment: {e}")
        finally:
            # 清理本地资源
            self.is_running = False
            self.env_uuid = None

            # 清理管道
            self.pipeline.clear()
