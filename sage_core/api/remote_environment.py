from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from sage_core.environment.base_environment import BaseEnvironment
from sage_core.jobmanager_client import JobManagerClient
from sage_utils.actor_wrapper import ActorWrapper
if TYPE_CHECKING:
    from sage_jobmanager.job_manager import JobManager

class RemoteEnvironment(BaseEnvironment):
    """远程环境，通过客户端连接远程JobManager"""

    def __init__(self, name: str, config: dict | None = None, host: str = "127.0.0.1", port: int = 19001):
        super().__init__(name, config, platform="remote")
        
        # 设置远程连接配置
        self.daemon_host = host
        self.daemon_port = port
        
        # 更新配置
        self.config.update({
            "engine_host": self.daemon_host,
            "engine_port": self.daemon_port
        })

    @property
    def client(self) -> JobManagerClient:
        """获取远程JobManager客户端"""
        if self._engine_client is None:
            self._engine_client = JobManagerClient(
                host=self.daemon_host, 
                port=self.daemon_port
            )
        return self._engine_client

    @property
    def jobmanager(self) -> 'JobManager': # 是actorwrapper无感包着的
        """通过客户端获取远程JobManager句柄"""
        if self._jobmanager is None:
            self._jobmanager = self.client.get_actor_handle()
        return self._jobmanager

    def submit(self):
        # 序列化环境
        from sage_utils.serialization.dill_serializer import trim_object_for_ray
        serialized_env = trim_object_for_ray(self)
        
        # 通过jobmanager属性提交job
        env_uuid = self.jobmanager.submit_job(serialized_env)
        
        if env_uuid:
            self.env_uuid = env_uuid
            self.logger.info(f"Environment submitted with UUID: {self.env_uuid}")
        else:
            raise RuntimeError("Failed to submit environment: no UUID returned")

    def stop(self):
        """停止远程环境"""
        if not self.env_uuid:
            self.logger.warning("Remote environment not submitted, nothing to stop")
            return
        
        self.logger.info("Stopping remote pipeline...")
        
        try:
            response = self.jobmanager.pause_job(self.env_uuid)
            
            if response.get("status") == "stopped":
                self.is_running = False
                self.logger.info("Remote pipeline stopped successfully")
            else:
                self.logger.warning(f"Failed to stop remote pipeline: {response.get('message')}")
                
        except Exception as e:
            self.logger.error(f"Error stopping remote pipeline: {e}")

    def close(self):
        """关闭远程环境"""
        if not self.env_uuid:
            self.logger.warning("Remote environment not submitted, nothing to close")
            return
        
        self.logger.info("Closing remote environment...")
        
        try:
            response = self.jobmanager.pause_job(self.env_uuid)
            
            if response.get("status") == "stopped":
                self.logger.info("Remote environment closed successfully")
            else:
                self.logger.warning(f"Failed to close remote environment: {response.get('message')}")
                
        except Exception as e:
            self.logger.error(f"Error closing remote environment: {e}")
        finally:
            # 清理本地资源
            self.is_running = False
            self.env_uuid = None
            
            # 清理管道
            self.pipeline.clear()

    def health_check(self):
        """检查远程JobManager健康状态"""
        try:
            response = self.client.health_check()
            return response
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {"status": "error", "message": str(e)}

    def get_remote_info(self):
        """获取远程JobManager信息"""
        try:
            response = self.client.get_actor_info()
            return response
        except Exception as e:
            self.logger.error(f"Failed to get remote info: {e}")
            return {"status": "error", "message": str(e)}