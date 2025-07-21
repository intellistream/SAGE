from datetime import datetime
import os
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Any, List, Optional
import time, uuid
from uuid import UUID
from sage_jobmanager.job_info import JobInfo
from sage_utils.custom_logger import CustomLogger
from sage_runtime.dispatcher import Dispatcher
import threading
from sage_utils.serialization.dill_serializer import deserialize_object
if TYPE_CHECKING:
    from sage_jobmanager.execution_graph import ExecutionGraph
    from sage_core.environment.base_environment import BaseEnvironment

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
            self.setup_logging_system()

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


    ########################################################
    #                internal  methods                     #
    ########################################################

    def submit_job(self, env: 'BaseEnvironment') -> str:


        env.setup_logging_system(self.log_base_dir)
        # 生成 UUID
        env.uuid = str(uuid.uuid4())
        # 编译环境
        from sage_jobmanager.execution_graph import ExecutionGraph
        graph = ExecutionGraph(env) 



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

        return env.uuid

    def stop_job(self, env_uuid: str) -> Dict[str, Any]:
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