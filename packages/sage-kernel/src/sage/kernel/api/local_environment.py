from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from sage.kernel.api.base_environment import BaseEnvironment
from sage.kernel.kernels.runtime.communication.queue_descriptor.python_queue_descriptor import PythonQueueDescriptor
if TYPE_CHECKING:
    from sage.kernel.kernels.jobmanager.job_manager import JobManager

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
            from sage.kernel.kernels.jobmanager.job_manager import JobManager
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

    def get_qd(self, name, maxsize = 10000):
        return PythonQueueDescriptor(queue_id=name, maxsize=maxsize)