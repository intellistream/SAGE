from datetime import datetime
import os
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Any, List, Optional
import time, uuid
import socket
import json
import pickle
import signal
import sys
from uuid import UUID
from sage.kernel.jobmanager.job_info import JobInfo
from sage.kernel.jobmanager.job_manager_server import JobManagerServer
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.runtime.dispatcher import Dispatcher
import threading
from sage.common.utils.serialization.dill import deserialize_object
if TYPE_CHECKING:
    from sage.kernel.jobmanager.compiler import ExecutionGraph
    from sage.core.api.base_environment import BaseEnvironment

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

    def __init__(self, 
                 enable_daemon: bool = True,
                 daemon_host: str = "127.0.0.1",
                 daemon_port: int = 19001):
        """
        初始化JobManager
        
        Args:
            enable_daemon: 是否启用内置TCP daemon
            daemon_host: Daemon监听地址
            daemon_port: Daemon监听端口
        """
        with JobManager.instance_lock:
            if self._initialized:
                return
            self._initialized = True
            JobManager.instance = self
            
            # 作业管理
            self.jobs: Dict[str, JobInfo] = {}  # uuid -> jobinfo
            self.deleted_jobs: Dict[str, Dict[str, Any]] = {}
            
            # 设置日志系统
            self.setup_logging_system()
            
            # 初始化内置daemon（如果启用）
            self.server = None
            if enable_daemon:
                self.server = JobManagerServer(
                    jobmanager=self,
                    host=daemon_host,
                    port=daemon_port
                )
                self.server.logger = self.logger
                # 设置信号处理
                self._setup_signal_handlers()


    def _setup_signal_handlers(self):
        """设置信号处理"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down JobManager...")
            self.shutdown()
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def run_forever(self):
        """运行JobManager直到收到停止信号"""
        
        self.logger.info("JobManager started successfully")
        self.logger.info(f"TCP service listening on {self.server.host}:{self.server.port}")
        self.logger.info("Press Ctrl+C to stop...")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()
        
        return True


    def submit_job(self, env: 'BaseEnvironment') -> str:
        """提交作业"""
        # 生成 UUID
        job_uuid = self._generate_job_uuid()
        env.uuid = job_uuid
        env.env_uuid = job_uuid
        
        # 设置环境的日志系统
        self.setup_env_logging(env)
        
        # 向环境注入JobManager的网络地址信息
        if self.server:
            env.jobmanager_host = self.server.host
            env.jobmanager_port = self.server.port
        else:
            # 如果没有daemon，使用默认地址
            env.jobmanager_host = "127.0.0.1"
            env.jobmanager_port = 19001
            
        # 创建执行图
        graph = self._create_execution_graph(env)
        
        # 创建 JobInfo 对象
        job_info = self._create_job_info(env, graph, job_uuid)
        
        # 提交到调度器
        success = self._submit_to_dispatcher(job_info)
        
        if success:
            self.logger.info(f"Environment '{env.name}' submitted with UUID {job_uuid}")
        else:
            raise Exception("Failed to submit job to dispatcher")

        return job_uuid

    def _generate_job_uuid(self) -> str:
        """生成作业UUID"""
        return str(uuid.uuid4())

    def _create_execution_graph(self, env: 'BaseEnvironment') -> 'ExecutionGraph':
        """创建执行图"""
        from sage.kernel.jobmanager.compiler import ExecutionGraph
        return ExecutionGraph(env)

    def _create_job_info(self, env: 'BaseEnvironment', graph: 'ExecutionGraph', job_uuid: str) -> JobInfo:
        """创建JobInfo对象"""
        dispatcher = Dispatcher(graph, env)
        job_info = JobInfo(env, graph, dispatcher, job_uuid)
        self.jobs[job_uuid] = job_info
        return job_info

    def _submit_to_dispatcher(self, job_info: JobInfo) -> bool:
        """提交到调度器"""
        try:
            job_info.dispatcher.submit()
            job_info.update_status("running")
            return True
        except Exception as e:
            job_info.update_status("failed", error=str(e))
            self.logger.error(f"Failed to submit job {job_info.uuid}: {e}")
            return False

    def _get_job_info(self, job_uuid: str) -> Optional[JobInfo]:
        """获取JobInfo对象"""
        return self.jobs.get(job_uuid)

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

    def receive_node_stop_signal(self, env_uuid: str, node_name: str):
        """接收来自单个节点的停止信号"""
        job_info = self.jobs.get(env_uuid)
        if not job_info:
            self.logger.error(f"Job with UUID {env_uuid} not found")
            return
        
        try:
            self.logger.info(f"Node {node_name} in job {env_uuid} requests to stop")
            
            # 通过dispatcher处理单个节点的停止
            all_nodes_stopped = job_info.dispatcher.receive_node_stop_signal(node_name)
            
            # 如果所有节点都已停止，则删除整个job
            if all_nodes_stopped:
                self.delete_job(env_uuid, force=True)
                self.logger.info(f"Job {env_uuid} deleted after all nodes stopped")
            else:
                self.logger.info(f"Node {node_name} stopped, job {env_uuid} continues with remaining nodes")
            
        except Exception as e:
            job_info.update_status("failed", error=str(e))
            self.logger.error(f"Failed to handle node stop signal from {node_name} in job {env_uuid}: {e}")


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
            return {
                "uuid": env_uuid,
                "status": "failed",
                "message": f"Failed to stop job: {str(e)}"
            }

    def get_job_status(self, env_uuid: str) -> Dict[str, Any]:
        """获取作业状态"""
        job_info = self._get_job_info(env_uuid)
        
        if not job_info:
            self.logger.warning(f"Job with UUID {env_uuid} not found")
            return {
                "success": False,
                "uuid": env_uuid,
                "status": "not_found",
                "message": f"Job with UUID {env_uuid} not found"
            }
        
        status_info = job_info.get_status()
        status_info["success"] = True
        return status_info

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "jobs_count": len(self.jobs)
        }

    def resume_job(self, env_uuid: str) -> Dict[str, Any]:
        """恢复作业（继续作业的别名）"""
        return self.continue_job(env_uuid)

    def _pause_job_execution(self, job_info: JobInfo) -> bool:
        """暂停作业执行"""
        try:
            job_info.dispatcher.stop()
            job_info.update_status("stopped")
            return True
        except Exception as e:
            job_info.update_status("failed", error=str(e))
            self.logger.error(f"Failed to pause job execution: {e}")
            return False

    def _resume_job_execution(self, job_info: JobInfo) -> bool:
        """恢复作业执行"""
        try:
            job_info.dispatcher.start()
            job_info.update_status("running")
            return True
        except Exception as e:
            job_info.update_status("failed", error=str(e))
            self.logger.error(f"Failed to resume job execution: {e}")
            return False

    def stop_daemon(self) -> bool:
        """停止守护进程"""
        if self.server:
            try:
                self.server.shutdown()
                return True
            except Exception as e:
                self.logger.error(f"Failed to stop daemon: {e}")
                return False
        return True

    def list_jobs(self) -> List[Dict[str, Any]]:
        return [job_info.get_summary() for job_info in self.jobs.values()]

    def get_server_info(self) -> Dict[str, Any]:
        job_summaries = [job_info.get_summary() for job_info in self.jobs.values()]
            
        return {
            "session_id": self.session_id,
            "log_base_dir": str(self.log_base_dir),
            "environments_count": len(self.jobs),
            "jobs": job_summaries,
            "daemon_enabled": self.server is not None,
            "daemon_address": f"{self.server.host}:{self.server.port}" if self.server else None
        }
    

    def shutdown(self):
        """关闭JobManager和所有资源"""
        self.logger.info("Shutting down JobManager and releasing resources")

        # 关闭daemon
        if self.server:
            self.server.shutdown()

        # 清理所有作业
        self.cleanup_all_jobs()

        # 重置单例
        JobManager.instance = None
        self.logger.info("JobManager shutdown complete")

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
        # 方案：项目的.sage/logs/jobmanager 作为实际存储位置
        # 优先使用环境变量指定的项目根目录，fallback到用户主目录
        project_root = os.environ.get('SAGE_PROJECT_ROOT')
        if project_root and Path(project_root).exists():
            self.log_base_dir = Path(project_root) / ".sage" / "logs" / "jobmanager" / f"session_{self.session_id}"
        else:
            # Fallback到用户主目录，但使用更清晰的结构
            self.log_base_dir = Path.home() / ".sage" / "logs" / "jobmanager" / f"session_{self.session_id}"
        
        print(f"JobManager logs: {self.log_base_dir}")
        Path(self.log_base_dir).mkdir(parents=True, exist_ok=True)

        
        # 3. 创建JobManager主日志
        self.logger = CustomLogger([
            ("console", "INFO"),  # 控制台显示重要信息
            (os.path.join(self.log_base_dir, "jobmanager.log"), "DEBUG"),      # 详细日志
            (os.path.join(self.log_base_dir, "error.log"), "ERROR") # 错误日志
        ], name="JobManager")

    def setup_env_logging(self, env: 'BaseEnvironment'):
        """为Environment设置日志系统"""
        from sage.kernel.jobmanager.utils.name_server import get_name
        
        # 确保环境名称唯一，不与其他注册过的环境冲突
        env.name = get_name(env.name)
        
        # 生成时间戳标识
        env.session_timestamp = datetime.now()
        env.session_id = env.session_timestamp.strftime("%Y%m%d_%H%M%S")
        
        # 设置环境基础目录
        env.env_base_dir = os.path.join(self.log_base_dir, f"env_{env.name}_{env.session_id}")
        Path(env.env_base_dir).mkdir(parents=True, exist_ok=True)

        # 创建Environment专用的日志器
        env._logger = CustomLogger([
                ("console", env.console_log_level),  # 使用用户设置的控制台日志等级
                (os.path.join(env.env_base_dir, "Environment.log"), "DEBUG"),  # 详细日志
                (os.path.join(env.env_base_dir, "Error.log"), "ERROR")  # 错误日志
            ],
            name=f"Environment_{env.name}",
        )

    @property
    def handle(self) -> 'JobManager':
        return self

# python -m sage.kernels.jobmanager.job_manager --host 127.0.0.1 --port 19001
# ==================== 命令行工具 ====================

def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SAGE JobManager with integrated TCP daemon")
    parser.add_argument("--host", default="127.0.0.1", help="Daemon host")
    parser.add_argument("--port", type=int, default=19001, help="Daemon port")
    parser.add_argument("--no-daemon", action="store_true", help="Disable TCP daemon")
    
    args = parser.parse_args()
    
    # 创建JobManager实例
    jobmanager = JobManager(
        enable_daemon=not args.no_daemon,
        daemon_host=args.host,
        daemon_port=args.port
    )
    
    if not args.no_daemon:
        print(f"Starting SAGE JobManager with TCP daemon on {args.host}:{args.port}")
        print("Press Ctrl+C to stop...")
        jobmanager.run_forever()
    else:
        print("SAGE JobManager started without TCP daemon")
        print("Use the JobManager instance directly in your code")


if __name__ == "__main__":
    main()