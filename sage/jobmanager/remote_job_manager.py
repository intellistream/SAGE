import ray
import time
import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, TYPE_CHECKING
from jobmanager.job_manager import JobManager
from utils.custom_logger import CustomLogger
from ray.actor import ActorHandle
if TYPE_CHECKING:
    from core.environment.base_environment import BaseEnvironment


@ray.remote
class RemoteJobManager(JobManager):
    """
    基于Ray Actor的JobManager，继承本地JobManager的所有功能
    通过Ray装饰器自动支持远程调用
    """
    
    def __init__(self, *args, **kwargs):
        # 调用父类初始化
        super().__init__(*args, **kwargs)
        
        # Ray特有的Actor信息
        self.actor_id = ray.get_runtime_context().get_actor_id()
        self.node_id = ray.get_runtime_context().get_node_id()
        
        self.logger.info(f"RemoteJobManager Actor initialized: {self.actor_id}")
        self.logger.info(f"Running on Ray node: {self.node_id}")
        self._actor_handle: ActorHandle = None
    

    # === 继承的核心方法自动支持Ray远程调用 ===
    # submit_job, pause_job, get_job_status, list_jobs 等方法
    # 无需重写，直接继承父类实现即可
    
    # === Ray Actor专用方法 ===
    
    def keep_alive(self) -> Dict[str, Any]:
        """
        防止Actor被回收的心跳方法
        返回Actor的健康状态信息
        """
        return {
            "status": "alive",
            "actor_id": self.actor_id,
            "node_id": self.node_id,
            "session_id": self.session_id,
            "timestamp": time.time(),
            "active_jobs": len(self.jobs),
            "memory_info": self._get_memory_info()
        }
    
    def get_actor_info(self) -> Dict[str, Any]:
        """获取Actor基本信息"""
        return {
            "actor_id": self.actor_id,
            "node_id": self.node_id,
            "session_id": self.session_id,
            "log_base_dir": str(self.log_base_dir),
            "actor_type": "RemoteJobManager"
        }
    
    def get_log_directory(self) -> Dict[str, Any]:
        """获取日志目录信息"""
        return {
            "status": "success",
            "log_base_dir": str(self.log_base_dir),
            "session_id": self.session_id,
            "latest_link": "/tmp/sage-jm/session_latest"
        }
    
    def get_environment_info(self) -> Dict[str, Any]:
        """获取远程JobManager的环境信息"""
        try:
            env_info = {
                "python_version": sys.version,
                "python_executable": sys.executable,
                "platform": sys.platform,
                "python_path": sys.path[:5],  # 只返回前5个路径，避免过长
                "virtual_env": os.environ.get("VIRTUAL_ENV"),
                "conda_env": os.environ.get("CONDA_DEFAULT_ENV"),
                "working_directory": os.getcwd(),
                "ray_version": ray.__version__,
                "actor_id": self.actor_id,
                "node_id": self.node_id,
            }
            
            # 获取关键依赖版本
            try:
                import dill
                env_info["dill_version"] = dill.__version__
            except ImportError:
                env_info["dill_version"] = None
            
            # 获取一些关键的已安装包（避免全量查询影响性能）
            critical_packages = ["ray", "dill", "numpy", "torch", "transformers", "sage_core"]
            try:
                result = subprocess.run([sys.executable, "-m", "pip", "show"] + critical_packages,
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    # 解析pip show输出
                    package_info = {}
                    current_package = None
                    for line in result.stdout.split('\n'):
                        if line.startswith('Name: '):
                            current_package = line.split('Name: ')[1].strip()
                        elif line.startswith('Version: ') and current_package:
                            package_info[current_package] = line.split('Version: ')[1].strip()
                    
                    env_info["critical_packages"] = package_info
                else:
                    env_info["critical_packages"] = {}
            except Exception:
                env_info["critical_packages"] = {}
            
            return env_info
            
        except Exception as e:
            self.logger.warning(f"Failed to get environment info: {e}")
            return {
                "error": str(e),
                "python_version": sys.version,
                "python_executable": sys.executable,
                "platform": sys.platform
            }
    
    def _get_memory_info(self) -> Dict[str, Any]:
        """获取内存使用信息（简单版本）"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return {
                "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
                "available": True
            }
        except ImportError:
            return {
                "rss_mb": -1,
                "vms_mb": -1,
                "available": False,
                "error": "psutil not available"
            }
    
    def graceful_shutdown(self) -> Dict[str, Any]:
        """
        优雅关闭Actor
        停止所有Job并清理资源
        """
        self.logger.info("RemoteJobManager Actor shutting down...")
        
        shutdown_report = {
            "jobs_stopped": 0,
            "jobs_failed_to_stop": 0,
            "errors": []
        }
        
        # 停止所有活跃的Job
        for env_uuid, job_info in list(self.jobs.items()):
            try:
                if job_info.status in ["running", "submitted"]:
                    self.pause_job(env_uuid)
                    shutdown_report["jobs_stopped"] += 1
            except Exception as e:
                shutdown_report["jobs_failed_to_stop"] += 1
                shutdown_report["errors"].append(f"Failed to stop job {env_uuid}: {str(e)}")
                self.logger.error(f"Error stopping job {env_uuid} during shutdown: {e}")
        
        # 调用父类shutdown
        try:
            super().shutdown()
        except Exception as e:
            shutdown_report["errors"].append(f"Parent shutdown error: {str(e)}")
        
        shutdown_report["status"] = "shutdown_complete"
        shutdown_report["timestamp"] = time.time()
        
        self.logger.info(f"RemoteJobManager Actor shutdown complete: {shutdown_report}")
        return shutdown_report
    
    # === 增强的状态监控方法 ===
    
    def get_extended_server_info(self) -> Dict[str, Any]:
        """获取扩展的服务器信息，包含Ray Actor特有信息"""
        base_info = super().get_server_info()
        
        # 添加Ray Actor信息
        base_info.update({
            "actor_id": self.actor_id,
            "node_id": self.node_id,
            "actor_type": "RemoteJobManager",
            "memory_info": self._get_memory_info(),
            "uptime_seconds": time.time() - self.session_timestamp.timestamp()
        })
        
        return base_info
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查方法"""
        try:
            job_count = len(self.jobs)
            running_jobs = len([j for j in self.jobs.values() if j.status == "running"])
            
            return {
                "status": "healthy",
                "actor_id": self.actor_id,
                "total_jobs": job_count,
                "running_jobs": running_jobs,
                "timestamp": time.time(),
                "session_uptime": time.time() - self.session_timestamp.timestamp()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
    
    def __repr__(self) -> str:
        return f"RemoteJobManager(actor_id={self.actor_id[:8]}..., session={self.session_id}, jobs={len(self.jobs)})"

    def setup_logging_system(self):
        """
        重写日志系统设置，为RemoteJobManager使用专门的日志目录结构
        - 日志目录: /tmp/sage-jm/session_xxxx
        - 软链接: /tmp/sage-jm/session_latest -> session_xxxx
        """
        # 1. 生成时间戳标识
        self.session_timestamp = datetime.now()
        self.session_id = self.session_timestamp.strftime("%Y%m%d_%H%M%S")
        
        # 2. 设置RemoteJobManager专用的日志目录结构
        sage_jm_base = Path("/tmp/sage-jm")
        sage_jm_base.mkdir(parents=True, exist_ok=True)
        
        # 具体的session目录
        session_dir = sage_jm_base / f"session_{self.session_id}"
        session_dir.mkdir(parents=True, exist_ok=True)
        self.log_base_dir = session_dir
        
        # 3. 创建或更新 session_latest 软链接
        latest_link = sage_jm_base / "session_latest"
        try:
            # 如果软链接已存在，先删除
            if latest_link.is_symlink() or latest_link.exists():
                latest_link.unlink()
            
            # 创建新的软链接，指向当前session目录
            latest_link.symlink_to(f"session_{self.session_id}")
            
        except Exception as e:
            # 如果创建软链接失败，记录警告但不影响主要功能
            print(f"Warning: Failed to create session_latest symlink: {e}")
        
        # 4. 创建RemoteJobManager专用的日志配置
        self.logger = CustomLogger([
            ("console", "INFO"),  # 控制台显示重要信息
            (os.path.join(self.log_base_dir, "remote_jobmanager.log"), "DEBUG"),  # 详细日志
            (os.path.join(self.log_base_dir, "error.log"), "ERROR"),  # 错误日志
            (os.path.join(self.log_base_dir, "actor.log"), "INFO")    # Actor专用日志
        ], name="RemoteJobManager")
        
        # 5. 记录初始化信息
        self.logger.info(f"RemoteJobManager logging system initialized")
        self.logger.info(f"Session ID: {self.session_id}")
        self.logger.info(f"Log directory: {self.log_base_dir}")
        self.logger.info(f"Latest session link: {latest_link}")

    @property
    def handle(self) -> 'ActorHandle':
        if self._actor_handle is None:
            try:
                # 方法1: 通过Actor名称获取（如果有的话）
                try:
                    self._actor_handle = ray.get_actor("sage_global_jobmanager", namespace="sage_system")
                    self.logger.debug("Got actor handle by name")
                except ValueError:
                    # 方法2: 通过全局注册表获取（需要事先注册）
                    # 方法3: 返回一个代理对象
                    self._actor_handle = self._create_self_proxy()
                    self.logger.debug("Created self proxy actor handle")
                    
            except Exception as e:
                self.logger.error(f"Failed to get actor handle: {e}")
                raise RuntimeError(f"Cannot obtain actor handle: {e}")
        
        return self._actor_handle

    def _create_self_proxy(self) -> 'ActorHandle':
        """
        创建自身的代理ActorHandle
        这是一个临时解决方案，用于在无法通过名称获取ActorHandle时使用
        """
        try:
            # 获取当前Actor的handle（这需要Ray版本支持）
            import ray.actor
            return ray.actor.ActorHandle._get_handle_for_current_actor()
        except (AttributeError, NotImplementedError):
            # 如果不支持，返回self作为fallback
            self.logger.warning("Cannot create self proxy, using self as fallback")
            return self