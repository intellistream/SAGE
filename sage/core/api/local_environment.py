from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from sage.core.environment.base_environment import BaseEnvironment
from sage.utils.actor_wrapper import ActorWrapper
if TYPE_CHECKING:
    from sage.jobmanager.job_manager import JobManager

class LocalEnvironment(BaseEnvironment):
    """本地环境，直接使用本地JobManager实例"""

    def __init__(self, name: str = "localenvironment", config: dict | None = None):
        super().__init__(name, config, platform="local")
        
        # 本地环境不需要客户端
        self._engine_client = None

    def submit(self):
        # 如果需要阻塞，就在用户程序里自己写个循环阻塞。
        env_uuid = self.jobmanager.submit_job(self)

    @property
    def jobmanager(self) -> 'JobManager':
        """直接返回JobManager的单例实例"""
        if self._jobmanager is None:
            from sage.jobmanager.job_manager import JobManager
            # 获取JobManager单例实例
            jobmanager_instance = JobManager()
            # 本地环境直接返回JobManager实例，不使用ActorWrapper
            self._jobmanager = jobmanager_instance
            
        return self._jobmanager
