from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from sage.core.api.base_environment import BaseEnvironment
if TYPE_CHECKING:
    from sage.kernel import JobManager

class LocalEnvironment(BaseEnvironment):
    """本地环境，直接使用本地JobManager实例"""

    def __init__(self, name: str = "localenvironment", config: dict | None = None):
        super().__init__(name, config, platform="local")
        
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
        # 提交作业
        env_uuid = self.jobmanager.submit_job(self)
        
        if autostop:
            self._wait_for_completion()
            
        return env_uuid
    
    def _wait_for_completion(self):
        """
        等待批处理任务完成
        在本地环境中直接监控JobManager实例的状态
        """
        import time
        
        if not self.env_uuid:
            self.logger.warning("No environment UUID found, cannot wait for completion")
            return
            
        self.logger.info("Waiting for batch processing to complete...")
        
        try:
            while True:
                # 直接检查本地JobManager实例中的作业状态
                job_info = self.jobmanager.jobs.get(self.env_uuid)
                
                if job_info is None:
                    # 作业已被删除，说明完成了
                    self.logger.info("Batch processing completed successfully")
                    break
                    
                # 检查dispatcher状态
                if not job_info.dispatcher.is_running:
                    self.logger.info("Dispatcher stopped, batch processing completed")
                    break
                    
                # 检查作业状态
                if job_info.status in ["stopped", "failed"]:
                    self.logger.info(f"Batch processing completed with status: {job_info.status}")
                    break
                    
                # 短暂等待后再次检查
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal, stopping batch processing...")
            self.stop()
        except Exception as e:
            self.logger.error(f"Error waiting for completion: {e}")
            
        finally:
            # 确保清理资源
            self.is_running = False

    @property
    def jobmanager(self) -> 'JobManager':
        """直接返回JobManager的单例实例"""
        if self._jobmanager is None:
            from sage.kernel import JobManager
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