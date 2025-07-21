"""
JobManager持久化Actor实现示例
展示如何在SAGE系统中创建持久化的JobManager Actor
"""
import ray
import time
import threading
from typing import Dict, Any, Optional
from sage_jobmanager.job_manager import JobManager
from draft.persistent_actor_manager import create_persistent_actor
from sage_utils.custom_logger import CustomLogger


@ray.remote
class PersistentJobManagerActor(JobManager):
    """持久化JobManager Actor - 绕过_ray_weak_ref限制"""
    
    def __init__(self, *args, **kwargs):
        # 禁用TCP服务器，使用Ray通信
        kwargs['enable_tcp_server'] = False
        super().__init__(*args, **kwargs)
        
        # Ray Actor特有的设置
        self.actor_id = ray.get_runtime_context().get_actor_id()
        self.start_time = time.time()
        self.heartbeat_count = 0
        
        self.logger.info(f"PersistentJobManagerActor initialized: {self.actor_id}")

    def keep_alive(self) -> Dict[str, Any]:
        """心跳保活方法 - 防止Actor被回收"""
        self.heartbeat_count += 1
        current_time = time.time()
        uptime = current_time - self.start_time
        
        return {
            "status": "alive",
            "actor_id": self.actor_id,
            "timestamp": current_time,
            "uptime_seconds": uptime,
            "heartbeat_count": self.heartbeat_count
        }

    def get_actor_info(self) -> Dict[str, Any]:
        """获取Actor信息"""
        return {
            "actor_id": self.actor_id,
            "start_time": self.start_time,
            "uptime": time.time() - self.start_time,
            "heartbeat_count": self.heartbeat_count,
            "weak_ref_info": "Using persistent actor strategies to bypass _ray_weak_ref"
        }

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 执行一些基本的健康检查
            status = {
                "status": "healthy",
                "actor_id": self.actor_id,
                "uptime": time.time() - self.start_time,
                "active_environments": len(getattr(self, 'environments', {})),
                "memory_usage": "N/A"  # 可以添加内存使用情况
            }
            return status
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "actor_id": self.actor_id
            }

    def graceful_shutdown(self) -> Dict[str, Any]:
        """优雅关闭Actor"""
        self.logger.info(f"PersistentJobManagerActor {self.actor_id} shutting down...")
        try:
            # 清理资源
            if hasattr(self, 'environments'):
                for env_uuid in list(self.jobs.keys()):
                    try:
                        self.stop_job(env_uuid)
                    except Exception as e:
                        self.logger.error(f"Error stopping environment {env_uuid}: {e}")
            
            return {
                "status": "shutdown_complete",
                "actor_id": self.actor_id,
                "final_heartbeat_count": self.heartbeat_count
            }
        except Exception as e:
            return {
                "status": "shutdown_error",
                "error": str(e),
                "actor_id": self.actor_id
            }


class JobManagerActorService:
    """JobManager Actor服务管理器"""
    
    def __init__(self, actor_name: str = "sage_jobmanager", namespace: str = "sage"):
        self.actor_name = actor_name
        self.namespace = namespace
        self.logger = CustomLogger()
        self._actor_handle: Optional[ray.actor.ActorHandle] = None
        self._persistence_method = "detached"  # 默认使用detached方法

    def start_persistent_jobmanager(
        self,
        method: str = "detached",
        **actor_options
    ) -> ray.actor.ActorHandle:
        """
        启动持久化JobManager Actor
        
        Args:
            method: 持久化方法 ("detached", "named", "resource_locked")
            **actor_options: 其他Actor选项
        
        Returns:
            Ray ActorHandle
        """
        try:
            self.logger.info(f"Starting persistent JobManager using method: {method}")
            
            # 根据不同方法设置不同的选项
            if method == "detached":
                # 方案1：使用detached生命周期（最推荐）
                actor_handle = create_persistent_actor(
                    PersistentJobManagerActor,
                    name=self.actor_name,
                    method="detached",
                    namespace=self.namespace,
                    max_restarts=3,
                    resources={"jobmanager": 1.0},  # 资源占用防止回收
                    **actor_options
                )
                
            elif method == "named":
                # 方案2：命名Actor + 心跳保活
                actor_handle = create_persistent_actor(
                    PersistentJobManagerActor,
                    name=self.actor_name,
                    method="named",
                    namespace=self.namespace,
                    keepalive_interval=30,  # 30秒心跳
                    **actor_options
                )
                
            elif method == "resource_locked":
                # 方案3：资源锁定
                actor_handle = create_persistent_actor(
                    PersistentJobManagerActor,
                    name=self.actor_name,
                    method="resource_locked",
                    namespace=self.namespace,
                    resource_name="jobmanager_lock",
                    resource_amount=1.0,
                    **actor_options
                )
            else:
                raise ValueError(f"Unknown persistence method: {method}")

            self._actor_handle = actor_handle
            self._persistence_method = method
            
            # 验证Actor是否正常启动
            actor_info = ray.get(actor_handle.get_actor_info.remote(), timeout=10)
            self.logger.info(f"JobManager Actor started successfully: {actor_info}")
            
            return actor_handle
            
        except Exception as e:
            self.logger.error(f"Failed to start persistent JobManager: {e}")
            raise

    def get_or_create_jobmanager(self, **options) -> ray.actor.ActorHandle:
        """获取现有JobManager或创建新的"""
        try:
            # 尝试获取现有Actor
            existing_actor = ray.get_actor(self.actor_name, namespace=self.namespace)
            
            # 检查Actor是否健康
            health_status = ray.get(existing_actor.health_check.remote(), timeout=5)
            if health_status.get("status") == "healthy":
                self.logger.info("Found existing healthy JobManager Actor")
                self._actor_handle = existing_actor
                return existing_actor
            else:
                self.logger.warning(f"Existing Actor unhealthy: {health_status}")
                
        except (ValueError, Exception) as e:
            self.logger.info(f"No existing JobManager Actor found: {e}")
        
        # 创建新的持久化Actor
        return self.start_persistent_jobmanager(**options)

    def stop_jobmanager(self, graceful: bool = True) -> bool:
        """停止JobManager Actor"""
        if not self._actor_handle:
            self.logger.warning("No JobManager Actor to stop")
            return True
            
        try:
            if graceful:
                # 优雅关闭
                shutdown_info = ray.get(
                    self._actor_handle.graceful_shutdown.remote(), 
                    timeout=30
                )
                self.logger.info(f"JobManager graceful shutdown: {shutdown_info}")
            
            # 杀死Actor
            ray.kill(self._actor_handle)
            self._actor_handle = None
            
            self.logger.info("JobManager Actor stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping JobManager Actor: {e}")
            return False

    def get_actor_handle(self) -> Optional[ray.actor.ActorHandle]:
        """获取当前Actor句柄"""
        return self._actor_handle

    def monitor_actor_health(self, interval: int = 60) -> threading.Thread:
        """启动Actor健康监控线程"""
        def monitor_worker():
            while self._actor_handle:
                try:
                    health_status = ray.get(
                        self._actor_handle.health_check.remote(), 
                        timeout=10
                    )
                    
                    if health_status.get("status") != "healthy":
                        self.logger.warning(f"JobManager Actor unhealthy: {health_status}")
                        # 可以在这里实现重启逻辑
                    else:
                        self.logger.debug(f"JobManager Actor healthy: {health_status}")
                    
                    time.sleep(interval)
                    
                except Exception as e:
                    self.logger.error(f"Health check failed: {e}")
                    time.sleep(interval)
        
        thread = threading.Thread(
            target=monitor_worker,
            name="JobManagerHealthMonitor",
            daemon=True
        )
        thread.start()
        self.logger.info("Started JobManager health monitoring")
        return thread


# 使用示例
def example_usage():
    """展示如何使用持久化JobManager Actor"""
    
    # 确保Ray已初始化
    if not ray.is_initialized():
        ray.init(address="auto", ignore_reinit_error=True)
    
    # 创建JobManager服务
    jm_service = JobManagerActorService()
    
    # 方法1：使用detached生命周期（推荐）
    print("=== 方法1：Detached生命周期 ===")
    jobmanager_actor = jm_service.start_persistent_jobmanager(method="detached")
    
    # 测试Actor功能
    actor_info = ray.get(jobmanager_actor.get_actor_info.remote())
    print(f"Actor Info: {actor_info}")
    
    # 心跳测试
    heartbeat = ray.get(jobmanager_actor.keep_alive.remote())
    print(f"Heartbeat: {heartbeat}")
    
    # 健康检查
    health = ray.get(jobmanager_actor.health_check.remote())
    print(f"Health: {health}")
    
    # 启动健康监控
    monitor_thread = jm_service.monitor_actor_health(interval=30)
    
    print("JobManager Actor is now persistent and resistant to _ray_weak_ref issues")
    print("The actor will survive even if the original handle goes out of scope")
    
    return jobmanager_actor


if __name__ == "__main__":
    example_usage()
