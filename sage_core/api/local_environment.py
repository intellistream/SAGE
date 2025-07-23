from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from sage_core.environment.base_environment import BaseEnvironment
from sage_utils.actor_wrapper import ActorWrapper
if TYPE_CHECKING:
    from sage_jobmanager.job_manager import JobManager

class LocalEnvironment(BaseEnvironment):
    """本地环境，直接使用本地JobManager实例"""

    def __init__(self, name: str = "localenvironment", config: dict | None = None):
        super().__init__(name, config, platform="local")
        
        # 本地环境不需要客户端
        self._engine_client = None

    def submit(self):
        import time
        # 序列化环境
        env_uuid = self.jobmanager.submit_job(self)
        
        if env_uuid:
            self.env_uuid = env_uuid
            self.logger.info(f"Environment submitted with UUID: {self.env_uuid}")
            try:
                # 阻塞主线程，直到 job 结束或被 Ctrl+C 打断
                while True:
                    status = self.jobmanager.get_job_status(self.env_uuid)
                    if status.get("status") not in ("running", "submitted"):
                        break
                    time.sleep(0.5)
            except KeyboardInterrupt:
                self.logger.info("KeyboardInterrupt received, stopping job...")
                self.jobmanager.pause_job(self.env_uuid)
        else:
            raise RuntimeError("Failed to submit environment: no UUID returned")

    @property
    def jobmanager(self) -> 'JobManager':
        """直接返回JobManager的单例实例"""
        if self._jobmanager is None:
            from sage_jobmanager.job_manager import JobManager
            # 获取JobManager单例实例
            jobmanager_instance = JobManager()
            # 本地环境直接返回JobManager实例，不使用ActorWrapper
            self._jobmanager = jobmanager_instance
            
        return self._jobmanager