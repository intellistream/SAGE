from datetime import datetime
import os
import ray
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
    from sage.jobmanager.job_manager import JobManager



class JobManagerServer:
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
            # 获取序列化的数据（新格式：base64编码的dill序列化数据）
            serialized_data_b64 = request.get("serialized_data")
            if serialized_data_b64:
                # 新格式：base64解码 + dill反序列化
                import base64
                serialized_data = base64.b64decode(serialized_data_b64)
                self.logger.debug("Deserializing environment from base64 + dill format")
                env = deserialize_object(serialized_data)
            else:
                # 兼容旧格式
                env_data = request.get("environment")
                if not env_data:
                    return {
                        "status": "error",
                        "message": "Missing serialized_data or environment data",
                        "request_id": request.get("request_id")
                    }
                
                # 反序列化环境对象（旧格式）
                if isinstance(env_data, str):
                    # 如果是hex字符串，先转换为bytes
                    env_bytes = bytes.fromhex(env_data)
                    import pickle
                    env = pickle.loads(env_bytes)
                else:
                    env = deserialize_object(env_data)
            
            if env is None:
                return {
                    "status": "error", 
                    "message": "Failed to deserialize environment object",
                    "request_id": request.get("request_id")
                }
            
            # 调用JobManager的submit_job方法
            self.logger.debug(f"Submitting deserialized environment: {getattr(env, 'name', 'Unknown')}")
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
            # 支持新旧两种参数名
            job_uuid = request.get("job_uuid") or request.get("env_uuid")
            if not job_uuid:
                return {
                    "status": "error",
                    "message": "Missing job_uuid parameter",
                    "request_id": request.get("request_id")
                }
            
            job_status = self.jobmanager.get_job_status(job_uuid)
            
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
            # 支持新旧两种参数名
            job_uuid = request.get("job_uuid") or request.get("env_uuid")
            if not job_uuid:
                return {
                    "status": "error",
                    "message": "Missing job_uuid parameter",
                    "request_id": request.get("request_id")
                }
            
            result = self.jobmanager.pause_job(job_uuid)
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
            # 支持新旧两种参数名
            job_uuid = request.get("job_uuid") or request.get("env_uuid")
            if not job_uuid:
                return {
                    "status": "error",
                    "message": "Missing job_uuid parameter",
                    "request_id": request.get("request_id")
                }
            
            result = self.jobmanager.continue_job(job_uuid)
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
            # 支持新旧两种参数名
            job_uuid = request.get("job_uuid") or request.get("env_uuid")
            force = request.get("force", False)
            
            if not job_uuid:
                return {
                    "status": "error",
                    "message": "Missing job_uuid parameter",
                    "request_id": request.get("request_id")
                }
            
            result = self.jobmanager.delete_job(job_uuid, force=force)
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