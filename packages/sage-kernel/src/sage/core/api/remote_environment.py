from __future__ import annotations

import logging
from typing import Optional, Dict, Any
from sage.core.api.base_environment import BaseEnvironment
from sage.kernel import JobManagerClient
from sage.common.utils.serialization.dill import trim_object_for_ray, serialize_object

logger = logging.getLogger(__name__)

class RemoteEnvironment(BaseEnvironment):
    """
    简化的远程环境实现
    专注于序列化环境并发送给远程JobManager
    """
    
    # 序列化时排除的属性
    __state_exclude__ = [
        'logger', '_logger', 
        '_engine_client',
        '_jobmanager'
        # 移除了'_jobmanager'，因为我们不再使用它
    ]

    def __init__(self, name: str = "remote_environment", config: dict | None = None, host: str = "127.0.0.1", port: int = 19001):
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

    def submit(self) -> str:
        """
        提交环境到远程JobManager
        
        Returns:
            环境UUID
        """
        try:
            logger.info(f"Submitting environment '{self.name}' to remote JobManager")
            
            # 第一步：使用 trim_object_for_ray 清理环境，排除不可序列化的内容
            logger.debug("Trimming environment for serialization")
            trimmed_env = trim_object_for_ray(self)
            
            # 第二步：使用 dill_serializer 打包
            logger.debug("Serializing environment with dill")
            serialized_data = serialize_object(trimmed_env)
            
            # 第三步：通过JobManager Client发送到JobManager端口
            logger.debug("Submitting serialized environment to JobManager")
            response = self.client.submit_job(serialized_data)
            
            if response.get("status") == "success":
                env_uuid = response.get("job_uuid")
                if env_uuid:
                    self.env_uuid = env_uuid
                    logger.info(f"Environment submitted successfully with UUID: {self.env_uuid}")
                    return env_uuid
                else:
                    raise RuntimeError("JobManager returned success but no job UUID")
            else:
                error_msg = response.get("message", "Unknown error")
                raise RuntimeError(f"Failed to submit environment: {error_msg}")
                
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
            response = self.client.pause_job(self.env_uuid)
            
            if response.get("status") == "success":
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
            response = self.client.pause_job(self.env_uuid)
            
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
            response = self.client.get_job_status(self.env_uuid)
            return response
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            return {"status": "error", "message": str(e)}

    def __repr__(self) -> str:
        return f"RemoteEnvironment(name='{self.name}', host='{self.daemon_host}', port={self.daemon_port})"