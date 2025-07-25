from datetime import datetime
import os
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Any, List, Optional
import time, uuid
from uuid import UUID
from sage.jobmanager.job_info import JobInfo
from sage_utils.custom_logger import CustomLogger
from sage_runtime.dispatcher import Dispatcher
import threading
from sage_utils.serialization.dill_serializer import deserialize_object
if TYPE_CHECKING:
    from sage.jobmanager.execution_graph import ExecutionGraph
    from sage.core.environment.base_environment import BaseEnvironment

import ray
class JobManager: #Job Manager
    instance = None
    instance_lock = threading.RLock()
    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            with cls.instance_lock:
                if cls.instance is None:
                    cls.instance = super(JobManager, cls).__new__(cls)
                    cls.instance._initialized = False
        return cls.instance

    def __init__(self):
        with JobManager.instance_lock:
            if self._initialized:
                return
            self._initialized = True
            JobManager.instance = self
            # 新增：UUID 到环境信息的映射
            self.jobs: Dict[str, JobInfo] = {}  # uuid -> jobinfo
            self.deleted_jobs: Dict[str, Dict[str, Any]] = {}
            self.setup_logging_system()


    def submit_job(self, env: 'BaseEnvironment') -> str:


        env.setup_logging_system(self.log_base_dir)
        # 生成 UUID
        env.uuid = str(uuid.uuid4())
        # 编译环境
        from sage.jobmanager.execution_graph import ExecutionGraph
        graph = ExecutionGraph(env, self.handle) 



        # TODO: 如果Job里面有申明'env.set_memory(config=None)'，则说明该job需要一个global memory manager.
        # 则在构建executiongraph的时候要单独是实例化一个特殊的operator，即 memory manager，并使得所有调用了memory相关操作的
        # 算子，双向连到该memory manager算子上。
        dispatcher = Dispatcher(graph, env)

            # 创建 JobInfo 对象
        job_info = JobInfo(env, graph, dispatcher, env.uuid)

        self.jobs[env.uuid] = job_info
        
        try:
            # 提交 DAG
            dispatcher.submit()
            job_info.update_status("running")
            
            self.logger.info(f"Environment '{env.name}' submitted with UUID {env.uuid}")
            
        except Exception as e:
            job_info.update_status("failed", error=str(e))
            self.logger.error(f"Failed to submit environment {env.uuid}: {e}")
            raise

        return env.uuid

    def continue_job(self, env_uuid: str) -> Dict[str, Any]:
        """重启作业"""
        job_info = self.jobs.get(env_uuid)
        
        if not job_info:
            self.logger.error(f"Job with UUID {env_uuid} not found")
            return {
                "uuid": env_uuid,
                "status": "not_found",
                "message": f"Job with UUID {env_uuid} not found"
            }
        
        try:
            current_status = job_info.status
            
            # 如果作业正在运行，先停止它
            if current_status == "running":
                self.logger.info(f"Stopping running job {env_uuid} before restart")
                stop_result = self.pause_job(env_uuid)
                if stop_result.get("status") not in ["stopped", "error"]:
                    return {
                        "uuid": env_uuid,
                        "status": "failed",
                        "message": f"Failed to stop job before restart: {stop_result.get('message')}"
                    }
                
                # 等待停止完成
                time.sleep(1.0)
        
            job_info.dispatcher.start()
            job_info.restart_count += 1
            
            # 重新提交作业
            job_info.update_status("running")
            
            self.logger.info(f"Job {env_uuid} restarted successfully (restart #{job_info.restart_count})")
            
            return {
                "uuid": env_uuid,
                "status": "running",
                "message": f"Job restarted successfully (restart #{job_info.restart_count})"
            }
            
        except Exception as e:
            job_info.update_status("failed", error=str(e))
            self.logger.error(f"Failed to restart job {env_uuid}: {e}")
            return {
                "uuid": env_uuid,
                "status": "failed",
                "message": f"Failed to restart job: {str(e)}"
            }

    def delete_job(self, env_uuid: str, force: bool = False) -> Dict[str, Any]:
        """删除作业"""
        job_info = self.jobs.get(env_uuid)
        
        if not job_info:
            self.logger.error(f"Job with UUID {env_uuid} not found")
            return {
                "uuid": env_uuid,
                "status": "not_found",
                "message": f"Job with UUID {env_uuid} not found"
            }
        
        try:
            current_status = job_info.status
            
            # 如果作业正在运行且未强制删除，先停止它
            if current_status == "running" and not force:
                self.logger.info(f"Stopping running job {env_uuid} before deletion")
                stop_result = self.pause_job(env_uuid)
                if stop_result.get("status") not in ["stopped", "error"]:
                    return {
                        "uuid": env_uuid,
                        "status": "failed",
                        "message": f"Failed to stop job before deletion: {stop_result.get('message')}"
                    }
                
                # 等待停止完成
                time.sleep(0.5)
            elif current_status == "running" and force:
                # 强制删除：直接停止
                self.logger.warning(f"Force deleting running job {env_uuid}")
                job_info.dispatcher.stop()
            
            # 清理资源
            job_info.dispatcher.cleanup()
            
            # 保存删除历史（可选）
            deletion_info = {
                "deleted_at": datetime.now().isoformat(),
                "final_status": job_info.status,
                "name": job_info.environment.name,
                "runtime": job_info.get_runtime(),
                "restart_count": job_info.restart_count
            }
            self.deleted_jobs[env_uuid] = deletion_info
            
            # 从活动作业列表中移除
            del self.jobs[env_uuid]
            
            self.logger.info(f"Job {env_uuid} deleted successfully")
            
            return {
                "uuid": env_uuid,
                "status": "deleted",
                "message": "Job deleted successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to delete job {env_uuid}: {e}")
            return {
                "uuid": env_uuid,
                "status": "failed",
                "message": f"Failed to delete job: {str(e)}"
            }

    def receive_stop_signal(self, env_uuid: str):
        """接收停止信号"""
        job_info = self.jobs.get(env_uuid)
        try:
            # 停止 dispatcher
            if (job_info.dispatcher.receive_stop_signal()) is True:
                self.delete_job(env_uuid, force=True)
                self.logger.info(f"Batch job: {env_uuid} completed ")
            
        except Exception as e:
            job_info.update_status("failed", error=str(e))
            self.logger.error(f"Failed to stop job {env_uuid}: {e}")


    def pause_job(self, env_uuid: str) -> Dict[str, Any]:
        """停止Job"""
        job_info = self.jobs.get(env_uuid, None)
        
        if not job_info:
            self.logger.error(f"Job with UUID {env_uuid} not found")
            return {
                "uuid": env_uuid,
                "status": "not_found",
                "message": f"Job with UUID {env_uuid} not found"
            }
        
        try:
            # 停止 dispatcher
            job_info.dispatcher.stop()
            job_info.update_status("stopped")
            
            self.logger.info(f"Job {env_uuid} stopped successfully")
            
            return {
                "uuid": env_uuid,
                "status": "stopped",
                "message": "Job stopped successfully"
            }
            
        except Exception as e:
            job_info.update_status("failed", error=str(e))
            self.logger.error(f"Failed to stop job {env_uuid}: {e}")

    def get_job_status(self, env_uuid: str) -> Dict[str, Any]:
        job_info = self.jobs.get(env_uuid)
        
        if not job_info:
            self.logger.warning(f"Job with UUID {env_uuid} not found")
        
        return job_info.get_status()

    def list_jobs(self) -> List[Dict[str, Any]]:
        return [job_info.get_summary() for job_info in self.jobs.values()]

    def get_server_info(self) -> Dict[str, Any]:
        job_summaries = [job_info.get_summary() for job_info in self.jobs.values()]
            
        return {
            "session_id": self.session_id,
            "log_base_dir": self.log_base_dir,
            "environments_count": len(self.jobs),
            "jobs": job_summaries
        }
    

    def shutdown(self):
        """
        完整释放 Engine 持有的所有资源：
        - 停掉 RuntimeManager（线程、Ray actor 等）
        - 停掉可能的 TCP/HTTP server
        - 清空 DAG 映射与缓存
        - 重置 Engine 单例
        """
        self.logger.info("Shutting down Engine and releasing resources")

        JobManager._instance = None
        self.logger.info("Engine shutdown complete")

    def cleanup_all_jobs(self) -> Dict[str, Any]:
        """清理所有作业"""
        try:
            cleanup_results = {}
            
            for env_uuid in list(self.jobs.keys()):
                result = self.delete_job(env_uuid, force=True)
                cleanup_results[env_uuid] = result
            
            self.logger.info(f"Cleaned up {len(cleanup_results)} jobs")
            
            return {
                "status": "success",
                "message": f"Cleaned up {len(cleanup_results)} jobs",
                "results": cleanup_results
            }
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup all jobs: {e}")
            return {
                "status": "failed",
                "message": f"Failed to cleanup jobs: {str(e)}"
            }

    ########################################################
    #                internal  methods                     #
    ########################################################

    def setup_logging_system(self):
        """设置分层日志系统"""
        # 1. 生成时间戳标识
        self.session_timestamp = datetime.now()
        self.session_id = self.session_timestamp.strftime("%Y%m%d_%H%M%S")
        
        # 2. 确定日志基础目录
        # 方案：/tmp/sage/logs 作为实际存储位置
        project_root = Path(__file__).parent.parent
        self.log_base_dir = project_root / "logs" / f"jobmanager_{self.session_id}"
        Path(self.log_base_dir).mkdir(parents=True, exist_ok=True)

        
        # 3. 创建JobManager主日志
        self.logger = CustomLogger([
            ("console", "INFO"),  # 控制台显示重要信息
            (os.path.join(self.log_base_dir, "jobmanager.log"), "DEBUG"),      # 详细日志
            (os.path.join(self.log_base_dir, "error.log"), "ERROR") # 错误日志
        ], name="JobManager")

    @property
    def handle(self) -> 'JobManager':
        return self