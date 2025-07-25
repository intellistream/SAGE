from __future__ import annotations

import logging
from typing import Optional, Dict, Any
from sage.core.api.base_environment import BaseEnvironment
from sage.jobmanager.jobmanager_client import JobManagerClient
from sage.utils.serialization.dill_serializer import trim_object_for_ray

logger = logging.getLogger(__name__)

class RemoteEnvironment(BaseEnvironment):
    """
    简化的远程环境实现
    专注于序列化环境并发送给远程JobManager
    """
    
    # 序列化时排除的属性
    __state_exclude__ = [
        'logger', '_logger', 
        '_engine_client', '_jobmanager'
        # 注意：不直接排除'client', 'jobmanager'，因为它们是@property
        # 而是通过排除底层的私有属性来实现
    ]

    def __init__(self, name: str, config: dict | None = None, host: str = "127.0.0.1", port: int = 19001):
        """
        初始化远程环境
        
        Args:
            name: 环境名称
            config: 环境配置
            host: JobManager服务主机
            port: JobManager服务端口
        """
        super().__init__(name, config, platform="remote")
        
        # 远程连接配置
        self.daemon_host = host
        self.daemon_port = port
        
        # 客户端连接（延迟初始化）
        self._engine_client: Optional[JobManagerClient] = None
        self._jobmanager = None
        
        # 更新配置
        self.config.update({
            "engine_host": self.daemon_host,
            "engine_port": self.daemon_port
        })
        
        logger.info(f"RemoteEnvironment '{name}' initialized for {host}:{port}")

    @property
    def client(self) -> JobManagerClient:
        """获取JobManager客户端（延迟创建）"""
        if self._engine_client is None:
            logger.debug(f"Creating JobManager client for {self.daemon_host}:{self.daemon_port}")
            self._engine_client = JobManagerClient(
                host=self.daemon_host, 
                port=self.daemon_port
            )
        return self._engine_client

    @property
    def jobmanager(self):
        """获取远程JobManager句柄（延迟创建）"""
        if self._jobmanager is None:
            logger.debug("Getting JobManager actor handle")
            self._jobmanager = self.client.get_actor_handle()
        return self._jobmanager

    def submit(self) -> str:
        """
        提交环境到远程JobManager
        
        Returns:
            环境UUID
        """
        try:
            logger.info(f"Submitting environment '{self.name}' to remote JobManager")
            
            # 序列化环境，排除不可序列化的内容
            logger.debug("Serializing environment for remote submission")
            serialized_env = trim_object_for_ray(self)
            
            # 通过JobManager提交作业
            logger.debug("Calling jobmanager.submit_job()")
            env_uuid = self.jobmanager.submit_job(serialized_env)
            
            if env_uuid:
                self.env_uuid = env_uuid
                logger.info(f"Environment submitted successfully with UUID: {self.env_uuid}")
                return env_uuid
            else:
                raise RuntimeError("Failed to submit environment: no UUID returned")
                
        except Exception as e:
            logger.error(f"Failed to submit environment: {e}")
            raise

    def stop(self) -> Dict[str, Any]:
        """
        停止远程环境
        
        Returns:
            停止操作的结果
        """
        if not self.env_uuid:
            logger.warning("Remote environment not submitted, nothing to stop")
            return {"status": "warning", "message": "Environment not submitted"}
        
        try:
            logger.info(f"Stopping remote environment {self.env_uuid}")
            response = self.jobmanager.pause_job(self.env_uuid)
            
            if response.get("status") == "stopped":
                logger.info(f"Environment {self.env_uuid} stopped successfully")
            else:
                logger.warning(f"Stop operation returned: {response}")
                
            return response
            
        except Exception as e:
            logger.error(f"Error stopping remote environment: {e}")
            return {"status": "error", "message": str(e)}

    def close(self) -> Dict[str, Any]:
        """
        关闭远程环境
        
        Returns:
            关闭操作的结果
        """
        if not self.env_uuid:
            logger.warning("Remote environment not submitted, nothing to close")
            return {"status": "warning", "message": "Environment not submitted"}
        
        try:
            logger.info(f"Closing remote environment {self.env_uuid}")
            response = self.jobmanager.pause_job(self.env_uuid)
            
            # 清理本地资源
            self.is_running = False
            self.env_uuid = None
            self.pipeline.clear()
            
            logger.info("Remote environment closed and local resources cleaned")
            return response
            
        except Exception as e:
            logger.error(f"Error closing remote environment: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            # 确保本地状态被清理
            self.is_running = False
            self.env_uuid = None

    def health_check(self) -> Dict[str, Any]:
        """
        检查远程JobManager健康状态
        
        Returns:
            健康检查结果
        """
        try:
            logger.debug("Performing health check")
            response = self.client.health_check()
            logger.debug(f"Health check result: {response}")
            return response
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "message": str(e)}

    def get_remote_info(self) -> Dict[str, Any]:
        """
        获取远程JobManager信息
        
        Returns:
            远程JobManager信息
        """
        try:
            logger.debug("Getting remote JobManager info")
            response = self.client.get_actor_info()
            return response
        except Exception as e:
            logger.error(f"Failed to get remote info: {e}")
            return {"status": "error", "message": str(e)}

    def get_job_status(self) -> Dict[str, Any]:
        """
        获取当前环境作业状态
        
        Returns:
            作业状态信息
        """
        if not self.env_uuid:
            return {"status": "not_submitted", "message": "Environment not submitted"}
        
        try:
            logger.debug(f"Getting job status for {self.env_uuid}")
            response = self.jobmanager.get_job_status(self.env_uuid)
            return response
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            return {"status": "error", "message": str(e)}

    def __repr__(self) -> str:
        return f"RemoteEnvironment(name='{self.name}', host='{self.daemon_host}', port={self.daemon_port})"
