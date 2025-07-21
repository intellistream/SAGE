import ray
import time
from typing import Dict, Any, List, TYPE_CHECKING
from sage_jobmanager.job_manager import JobManager

if TYPE_CHECKING:
    from sage_core.environment.base_environment import BaseEnvironment


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
    
    # === 继承的核心方法自动支持Ray远程调用 ===
    # submit_job, stop_job, get_job_status, list_jobs 等方法
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
            "log_base_dir": self.log_base_dir,
            "actor_type": "RemoteJobManager"
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
                    self.stop_job(env_uuid)
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