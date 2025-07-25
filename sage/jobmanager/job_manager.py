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
from sage.jobmanager.job_info import JobInfo
from sage.utils.custom_logger import CustomLogger
from sage.runtime.dispatcher import Dispatcher
import threading
from sage.utils.serialization.dill_serializer import deserialize_object
if TYPE_CHECKING:
    from sage.jobmanager.execution_graph import ExecutionGraph
    from sage.core.api.base_environment import BaseEnvironment

import ray


class JobManagerDaemon:
    """
    JobManager内置的TCP守护服务
    负责解析TCP消息并调用JobManager的服务方法
    """
    
    def __init__(self, jobmanager: 'JobManager',
                 host: str = "127.0.0.1", 
                 port: int = 19001,
                 actor_name: str = "sage_global_jobmanager",
                 namespace: str = "sage_system"):
        """
        初始化守护服务
        
        Args:
            jobmanager: JobManager实例
            host: Socket服务监听地址
            port: Socket服务端口  
            actor_name: JobManager Actor名称（如果作为Ray Actor运行）
            namespace: Ray命名空间
        """
        self.jobmanager = jobmanager
        self.host = host
        self.port = port
        self.actor_name = actor_name
        self.namespace = namespace
        
        # Socket服务
        self._server_socket: Optional[socket.socket] = None
        self._server_thread: Optional[threading.Thread] = None
        self._running = False
        
        # 日志使用JobManager的logger
        self.logger = jobmanager.logger
        
    def start_daemon(self):
        """启动守护服务"""
        try:
            self.logger.info("Starting JobManager TCP Daemon...")
            
            # 启动Socket服务
            self._start_socket_service()
            
            self.logger.info(f"JobManager Daemon started successfully on {self.host}:{self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start daemon: {e}")
            self.shutdown()
            return False
    
    def _start_socket_service(self):
        """启动Socket服务"""
        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind((self.host, self.port))
            self._server_socket.listen(10)
            
            self._running = True
            self._server_thread = threading.Thread(
                target=self._socket_server_loop,
                name="SocketServer",
                daemon=True
            )
            self._server_thread.start()
            
            self.logger.info(f"Socket service started on {self.host}:{self.port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start socket service: {e}")
            raise
    
    def _socket_server_loop(self):
        """Socket服务主循环"""
        self.logger.debug("Socket server loop started")
        
        while self._running:
            try:
                if not self._server_socket:
                    break
                    
                self._server_socket.settimeout(1.0)  # 1秒超时，允许检查_running状态
                
                try:
                    client_socket, address = self._server_socket.accept()
                    self.logger.debug(f"New client connected: {address}")
                    
                    # 在新线程中处理客户端
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, address),
                        name=f"Client-{address[0]}:{address[1]}",
                        daemon=True
                    )
                    client_thread.start()
                    
                except socket.timeout:
                    continue
                    
            except Exception as e:
                if self._running:
                    self.logger.error(f"Error in socket server loop: {e}")
                break
        
        self.logger.debug("Socket server loop stopped")
    
    def _handle_client(self, client_socket: socket.socket, address: tuple):
        """处理客户端请求"""
        try:
            with client_socket:
                # 接收请求
                request_data = self._receive_message(client_socket)
                if not request_data:
                    return
                
                request = json.loads(request_data.decode('utf-8'))
                self.logger.debug(f"Received request from {address}: {request}")
                
                # 处理请求
                response = self._process_request(request)
                
                # 发送响应
                self._send_message(client_socket, json.dumps(response).encode('utf-8'))
                
        except Exception as e:
            self.logger.error(f"Error handling client {address}: {e}")
    
    def _receive_message(self, client_socket: socket.socket) -> Optional[bytes]:
        """接收消息"""
        try:
            # 接收消息长度
            length_data = client_socket.recv(4)
            if len(length_data) != 4:
                return None
            
            message_length = int.from_bytes(length_data, byteorder='big')
            if message_length <= 0 or message_length > 10 * 1024 * 1024:  # 10MB限制
                return None
            
            # 接收消息内容
            message_data = b''
            while len(message_data) < message_length:
                chunk = client_socket.recv(min(message_length - len(message_data), 8192))
                if not chunk:
                    return None
                message_data += chunk
            
            return message_data
            
        except Exception as e:
            self.logger.debug(f"Error receiving message: {e}")
            return None
    
    def _send_message(self, client_socket: socket.socket, message: bytes):
        """发送消息"""
        try:
            # 发送消息长度
            length_data = len(message).to_bytes(4, byteorder='big')
            client_socket.sendall(length_data)
            
            # 发送消息内容
            client_socket.sendall(message)
            
        except Exception as e:
            self.logger.debug(f"Error sending message: {e}")
    
    def _process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理客户端请求 - 解析消息并调用JobManager方法"""
        try:
            action = request.get("action", "")
            request_id = request.get("request_id")
            
            # 根据action调用相应的JobManager方法
            if action == "submit_job":
                return self._handle_submit_job(request)
            elif action == "get_job_status":
                return self._handle_get_job_status(request)
            elif action == "pause_job":
                return self._handle_pause_job(request)
            elif action == "continue_job":
                return self._handle_continue_job(request)
            elif action == "delete_job":
                return self._handle_delete_job(request)
            elif action == "list_jobs":
                return self._handle_list_jobs(request)
            elif action == "get_server_info":
                return self._handle_get_server_info(request)
            elif action == "cleanup_all_jobs":
                return self._handle_cleanup_all_jobs(request)
            elif action == "health_check":
                return self._handle_health_check(request)
            elif action == "get_actor_handle":
                return self._handle_get_actor_handle(request)
            elif action == "get_actor_info":
                return self._handle_get_actor_info(request)
            elif action == "restart_actor":
                return self._handle_restart_actor(request)
            elif action == "get_environment_info":
                return self._handle_get_environment_info(request)
            else:
                return {
                    "status": "error",
                    "message": f"Unknown action: {action}",
                    "request_id": request_id
                }
                
        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            return {
                "status": "error", 
                "message": str(e),
                "request_id": request.get("request_id")
            }
    
    def _handle_submit_job(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理提交作业请求"""
        try:
            # 从请求中解析环境数据
            env_data = request.get("environment")
            if not env_data:
                return {
                    "status": "error",
                    "message": "Missing environment data",
                    "request_id": request.get("request_id")
                }
            
            # 反序列化环境对象
            if isinstance(env_data, str):
                # 如果是hex字符串，先转换为bytes
                env_bytes = bytes.fromhex(env_data)
                env = pickle.loads(env_bytes)
            else:
                env = deserialize_object(env_data)
            
            # 调用JobManager的submit_job方法
            job_uuid = self.jobmanager.submit_job(env)
            
            return {
                "status": "success",
                "job_uuid": job_uuid,
                "message": f"Job submitted successfully with UUID: {job_uuid}",
                "request_id": request.get("request_id")
            }
            
        except Exception as e:
            self.logger.error(f"Failed to submit job: {e}")
            return {
                "status": "error",
                "message": f"Failed to submit job: {str(e)}",
                "request_id": request.get("request_id")
            }
    
    def _handle_get_job_status(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理获取作业状态请求"""
        try:
            env_uuid = request.get("env_uuid")
            if not env_uuid:
                return {
                    "status": "error",
                    "message": "Missing env_uuid parameter",
                    "request_id": request.get("request_id")
                }
            
            job_status = self.jobmanager.get_job_status(env_uuid)
            
            return {
                "status": "success",
                "job_status": job_status,
                "request_id": request.get("request_id")
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get job status: {str(e)}",
                "request_id": request.get("request_id")
            }
    
    def _handle_pause_job(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理暂停作业请求"""
        try:
            env_uuid = request.get("env_uuid")
            if not env_uuid:
                return {
                    "status": "error",
                    "message": "Missing env_uuid parameter",
                    "request_id": request.get("request_id")
                }
            
            result = self.jobmanager.pause_job(env_uuid)
            result["request_id"] = request.get("request_id")
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to pause job: {str(e)}",
                "request_id": request.get("request_id")
            }
    
    def _handle_continue_job(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理继续作业请求"""
        try:
            env_uuid = request.get("env_uuid")
            if not env_uuid:
                return {
                    "status": "error",
                    "message": "Missing env_uuid parameter",
                    "request_id": request.get("request_id")
                }
            
            result = self.jobmanager.continue_job(env_uuid)
            result["request_id"] = request.get("request_id")
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to continue job: {str(e)}",
                "request_id": request.get("request_id")
            }
    
    def _handle_delete_job(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理删除作业请求"""
        try:
            env_uuid = request.get("env_uuid")
            force = request.get("force", False)
            
            if not env_uuid:
                return {
                    "status": "error",
                    "message": "Missing env_uuid parameter",
                    "request_id": request.get("request_id")
                }
            
            result = self.jobmanager.delete_job(env_uuid, force=force)
            result["request_id"] = request.get("request_id")
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to delete job: {str(e)}",
                "request_id": request.get("request_id")
            }
    
    def _handle_list_jobs(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理列出作业请求"""
        try:
            jobs = self.jobmanager.list_jobs()
            
            return {
                "status": "success",
                "jobs": jobs,
                "request_id": request.get("request_id")
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to list jobs: {str(e)}",
                "request_id": request.get("request_id")
            }
    
    def _handle_get_server_info(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理获取服务器信息请求"""
        try:
            server_info = self.jobmanager.get_server_info()
            
            return {
                "status": "success",
                "server_info": server_info,
                "request_id": request.get("request_id")
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get server info: {str(e)}",
                "request_id": request.get("request_id")
            }
    
    def _handle_cleanup_all_jobs(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理清理所有作业请求"""
        try:
            result = self.jobmanager.cleanup_all_jobs()
            result["request_id"] = request.get("request_id")
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to cleanup jobs: {str(e)}",
                "request_id": request.get("request_id")
            }
    
    def _handle_health_check(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理健康检查请求"""
        daemon_status = {
            "daemon_running": True,
            "socket_service": f"{self.host}:{self.port}",
            "jobmanager_ready": True,
            "session_id": self.jobmanager.session_id,
            "jobs_count": len(self.jobmanager.jobs)
        }
        
        return {
            "status": "success",
            "message": "JobManager and Daemon are healthy",
            "daemon_status": daemon_status,
            "request_id": request.get("request_id")
        }
    
    def _handle_get_actor_handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理获取Actor句柄请求（如果JobManager作为Ray Actor运行）"""
        try:
            # 如果JobManager作为Ray Actor运行，返回当前Actor的句柄
            # 注意：这里需要根据实际情况调整
            return {
                "status": "success",
                "actor_name": self.actor_name,
                "namespace": self.namespace,
                "message": "JobManager is running as embedded daemon",
                "request_id": request.get("request_id")
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get actor handle: {e}",
                "request_id": request.get("request_id")
            }
    
    def _handle_get_actor_info(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理获取Actor信息请求"""
        try:
            actor_info = {
                "actor_name": self.actor_name,
                "namespace": self.namespace,
                "session_id": self.jobmanager.session_id,
                "status": "ready",
                "jobs_count": len(self.jobmanager.jobs)
            }
            
            return {
                "status": "success",
                "actor_info": actor_info,
                "request_id": request.get("request_id")
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get actor info: {e}",
                "request_id": request.get("request_id")
            }
    
    def _handle_restart_actor(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理重启Actor请求"""
        try:
            # 清理所有作业
            self.jobmanager.cleanup_all_jobs()
            
            # 重新初始化日志系统
            self.jobmanager.setup_logging_system()
            
            return {
                "status": "success",
                "message": "JobManager restarted successfully",
                "request_id": request.get("request_id")
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to restart JobManager: {e}",
                "request_id": request.get("request_id")
            }
    
    def _handle_get_environment_info(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理获取环境信息请求"""
        try:
            import platform
            
            environment_info = {
                "python_version": sys.version,
                "python_executable": sys.executable,
                "platform": platform.platform(),
                "ray_version": ray.__version__ if hasattr(ray, '__version__') else "unknown",
                "session_id": self.jobmanager.session_id,
                "log_base_dir": str(self.jobmanager.log_base_dir),
                "working_directory": os.getcwd()
            }
            
            return {
                "status": "success",
                "environment_info": environment_info,
                "request_id": request.get("request_id")
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get environment info: {e}",
                "request_id": request.get("request_id")
            }
    
    def shutdown(self):
        """关闭守护服务"""
        self.logger.info("Shutting down JobManager daemon...")
        
        # 停止socket服务
        self._running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except:
                pass
        
        # 等待服务线程结束
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=5)
        
        self.logger.info("JobManager daemon shutdown complete")


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
            self.daemon = None
            if enable_daemon:
                self.daemon = JobManagerDaemon(
                    jobmanager=self,
                    host=daemon_host,
                    port=daemon_port
                )
                
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
    
    def start_daemon(self):
        """启动内置daemon服务"""
        if self.daemon:
            return self.daemon.start_daemon()
        else:
            self.logger.warning("Daemon not enabled")
            return False
    
    def run_forever(self):
        """运行JobManager直到收到停止信号"""
        if not self.start_daemon():
            self.logger.error("Failed to start daemon")
            return False
        
        self.logger.info("JobManager started successfully")
        self.logger.info(f"TCP service listening on {self.daemon.host}:{self.daemon.port}")
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
            return {
                "uuid": env_uuid,
                "status": "failed",
                "message": f"Failed to stop job: {str(e)}"
            }

    def get_job_status(self, env_uuid: str) -> Dict[str, Any]:
        job_info = self.jobs.get(env_uuid)
        
        if not job_info:
            self.logger.warning(f"Job with UUID {env_uuid} not found")
            return {
                "uuid": env_uuid,
                "status": "not_found",
                "message": f"Job with UUID {env_uuid} not found"
            }
        
        return job_info.get_status()

    def list_jobs(self) -> List[Dict[str, Any]]:
        return [job_info.get_summary() for job_info in self.jobs.values()]

    def get_server_info(self) -> Dict[str, Any]:
        job_summaries = [job_info.get_summary() for job_info in self.jobs.values()]
            
        return {
            "session_id": self.session_id,
            "log_base_dir": str(self.log_base_dir),
            "environments_count": len(self.jobs),
            "jobs": job_summaries,
            "daemon_enabled": self.daemon is not None,
            "daemon_address": f"{self.daemon.host}:{self.daemon.port}" if self.daemon else None
        }
    

    def shutdown(self):
        """关闭JobManager和所有资源"""
        self.logger.info("Shutting down JobManager and releasing resources")

        # 关闭daemon
        if self.daemon:
            self.daemon.shutdown()

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

# python -m sage.jobmanager.job_manager --host 127.0.0.1 --port 19001
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