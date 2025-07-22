from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from pathlib import Path
import os
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
        
        # 初始化时尝试创建日志软链接
        self._log_symlink_created = False
        self._setup_log_symlink()

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

    def _setup_log_symlink(self):
        """创建远程JobManager日志目录到本地codebase的软链接"""
        try:
            # 获取项目根目录（SAGE目录）
            current_file = Path(__file__)
            project_root = None
            
            # 向上查找包含setup.py或pyproject.toml的目录
            for parent in current_file.parents:
                if (parent / "setup.py").exists() or (parent / "pyproject.toml").exists():
                    project_root = parent
                    break
            
            if not project_root:
                # 如果找不到，使用当前文件向上三级目录（sage_core/api -> sage_core -> SAGE）
                project_root = current_file.parent.parent.parent
            
            # 在项目根目录下的logs目录中创建软链接
            local_logs_dir = project_root / "logs"
            local_logs_dir.mkdir(exist_ok=True)
            
            # 远程日志软链接目标
            remote_log_symlink = local_logs_dir / "remote_jobmanager_latest"
            
            # 检查是否能连接到远程JobManager
            try:
                log_info = self.client.get_log_directory()
                
                if log_info.get("status") == "success":
                    remote_latest_link = log_info.get("latest_link", "/tmp/sage-jm/session_latest")
                    
                    # 如果软链接已存在，先删除
                    if remote_log_symlink.is_symlink() or remote_log_symlink.exists():
                        remote_log_symlink.unlink()
                    
                    # 创建软链接
                    remote_log_symlink.symlink_to(remote_latest_link)
                    self._log_symlink_created = True
                    
                    self.logger.info(f"Created symlink: {remote_log_symlink} -> {remote_latest_link}")
                    
                else:
                    self.logger.warning(f"Failed to get remote log directory: {log_info.get('message')}")
                    
            except Exception as e:
                self.logger.warning(f"Could not connect to remote JobManager for log symlink: {e}")
                
        except Exception as e:
            self.logger.warning(f"Failed to setup log symlink: {e}")

    def _update_log_symlink(self):
        """更新日志软链接（在连接建立后调用）"""
        if not self._log_symlink_created:
            self._setup_log_symlink()
        
    def get_log_symlink_status(self) -> dict:
        """获取日志软链接状态"""
        try:
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent
            remote_log_symlink = project_root / "logs" / "remote_jobmanager_latest"
            
            if remote_log_symlink.exists():
                target = remote_log_symlink.resolve()
                return {
                    "status": "active",
                    "symlink_path": str(remote_log_symlink),
                    "target_path": str(target),
                    "exists": target.exists()
                }
            else:
                return {
                    "status": "not_created",
                    "symlink_path": str(remote_log_symlink),
                    "target_path": None,
                    "exists": False
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def submit(self):
        # 序列化环境
        from sage_utils.serialization.dill_serializer import trim_object_for_ray
        serialized_env = trim_object_for_ray(self)
        
        # 通过jobmanager属性提交job
        env_uuid = self.jobmanager.submit_job(serialized_env)
        
        if env_uuid:
            self.env_uuid = env_uuid
            self.logger.info(f"Environment submitted with UUID: {self.env_uuid}")
            
            # 提交成功后更新日志软链接
            self._update_log_symlink()
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
            
            # 清理日志软链接（可选，也可以保留用于查看历史日志）
            self._cleanup_log_symlink_if_needed()

    def _cleanup_log_symlink_if_needed(self):
        """根据需要清理日志软链接"""
        # 这里可以根据具体需求决定是否清理软链接
        # 通常建议保留软链接，便于查看历史日志
        pass

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
            
            # 添加日志软链接信息
            symlink_status = self.get_log_symlink_status()
            response["log_symlink"] = symlink_status
            
            return response
        except Exception as e:
            self.logger.error(f"Failed to get remote info: {e}")
            return {"status": "error", "message": str(e)}