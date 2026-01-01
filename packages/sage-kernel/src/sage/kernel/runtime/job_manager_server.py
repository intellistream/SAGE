import json
import os
import sys
from typing import TYPE_CHECKING, Any

import ray

from sage.common.utils.network.local_tcp_server import BaseTcpServer
from sage.common.utils.serialization.dill import deserialize_object

if TYPE_CHECKING:
    from sage.kernel.runtime.job_manager import JobManager


class JobManagerServer(BaseTcpServer):
    """
    JobManager内置的TCP守护服务
    负责解析TCP消息并调用JobManager的服务方法
    """

    def __init__(
        self,
        jobmanager: "JobManager",
        host: str = "127.0.0.1",
        port: int = 19001,
        actor_name: str = "sage_global_jobmanager",
        namespace: str = "sage_system",
    ):
        """
        初始化守护服务

        Args:
            jobmanager: JobManager实例
            host: Socket服务监听地址
            port: Socket服务端口
            actor_name: JobManager Actor名称（如果作为Ray Actor运行）
            namespace: Ray命名空间
        """
        # 初始化基类
        super().__init__(host, port, jobmanager.logger, "JobManagerServer")

        self.jobmanager = jobmanager
        self.actor_name = actor_name
        self.namespace = namespace

        try:
            self.logger.info("Starting JobManager TCP Daemon...")

            # 启动Socket服务
            self.start()

            self.logger.info(f"JobManager Daemon started successfully on {self.host}:{self.port}")

        except Exception as e:
            self.logger.error(f"Failed to start daemon: {e}")
            self.shutdown()

    def _handle_message_data(
        self, message_data: bytes, client_address: tuple
    ) -> dict[str, Any] | None:
        """处理接收到的消息数据"""
        try:
            # JobManager使用JSON格式的消息
            request_data = message_data.decode("utf-8")
            request = json.loads(request_data)
            self.logger.debug(f"Received request from {client_address}: {request}")

            # 处理请求
            response = self._process_request(request)
            return response

        except Exception as e:
            self.logger.error(f"Error processing message from {client_address}: {e}")
            return {"status": "error", "message": str(e), "request_id": None}

    def _serialize_response(self, response: Any) -> bytes:
        """序列化响应（JobManager使用JSON格式）"""
        return json.dumps(response).encode("utf-8")

    def _process_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """处理客户端请求 - 解析消息并调用JobManager方法"""
        try:
            self.logger.debug(f"Processing request: {request}")
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
            elif action == "receive_node_stop_signal":
                return self._handle_receive_node_stop_signal(request)
            elif action == "health_check":
                return self._handle_health_check(request)
            elif action == "get_environment_info":
                return self._handle_get_environment_info(request)
            else:
                return {
                    "status": "error",
                    "message": f"Unknown action: {action}",
                    "request_id": request_id,
                }

        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            return {
                "status": "error",
                "message": str(e),
                "request_id": request.get("request_id"),
            }

    def _handle_submit_job(self, request: dict[str, Any]) -> dict[str, Any]:
        """处理提交作业请求"""
        try:
            # 获取 autostop 参数
            autostop = request.get("autostop", False)

            # 在反序列化之前添加额 Python 路径
            # 这样反序列化时可以正确导入自定义模块
            extra_python_paths = request.get("extra_python_paths", [])
            if extra_python_paths:
                self.logger.debug(f"Adding extra Python paths: {extra_python_paths}")
                for path in extra_python_paths:
                    if path not in sys.path:
                        sys.path.insert(0, path)
                        self.logger.debug(f"Added to sys.path: {path}")

            # 获取序列化的数据（新格式：base64编码的dill序列化数据）
            serialized_data_b64 = request.get("serialized_data")
            if serialized_data_b64:
                # 新格式：base64解码 + dill反序列化
                import base64

                serialized_data = base64.b64decode(serialized_data_b64)
                self.logger.debug("[SUBMIT-1] Starting deserialization")
                self.logger.debug("Deserializing environment from base64 + dill format")
                self.logger.debug("[SUBMIT-2] Deserialization completed")
                env = deserialize_object(serialized_data)
            else:
                # 兼容旧格式
                env_data = request.get("environment")
                if not env_data:
                    return {
                        "status": "error",
                        "message": "Missing serialized_data or environment data",
                        "request_id": request.get("request_id"),
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
                    "request_id": request.get("request_id"),
                }

            # 调试: 检查反序列化后的 jobmanager_host 值
            self.logger.debug(
                f"[SUBMIT-DEBUG] env.jobmanager_host={getattr(env, 'jobmanager_host', 'NOT_SET')}, "
                f"env.jobmanager_port={getattr(env, 'jobmanager_port', 'NOT_SET')}"
            )

            # 调用JobManager的submit_job方法，传递 autostop 参数
            self.logger.debug(
                f"Submitting deserialized environment: {getattr(env, 'name', 'Unknown')} (autostop={autostop})"
            )
            self.logger.debug(
                f"[SUBMIT-3] Calling jobmanager.submit_job, env={getattr(env, 'name', 'Unknown')}"
            )
            job_uuid = self.jobmanager.submit_job(env, autostop=autostop)
            self.logger.debug(f"[SUBMIT-4] submit_job returned UUID: {job_uuid}")

            return {
                "status": "success",
                "job_uuid": job_uuid,
                "message": f"Job submitted successfully with UUID: {job_uuid}",
                "request_id": request.get("request_id"),
            }

        except Exception as e:
            self.logger.error(f"Failed to submit job: {e}")
            return {
                "status": "error",
                "message": f"Failed to submit job: {str(e)}",
                "request_id": request.get("request_id"),
            }

    def _handle_get_job_status(self, request: dict[str, Any]) -> dict[str, Any]:
        """处理获取作业状态请求"""
        try:
            # 支持新旧两种参数名
            job_uuid = request.get("job_uuid") or request.get("env_uuid")
            if not job_uuid:
                return {
                    "status": "error",
                    "message": "Missing job_uuid parameter",
                    "request_id": request.get("request_id"),
                }

            job_status = self.jobmanager.get_job_status(job_uuid)

            return {
                "status": "success",
                "job_status": job_status,
                "request_id": request.get("request_id"),
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get job status: {str(e)}",
                "request_id": request.get("request_id"),
            }

    def _handle_pause_job(self, request: dict[str, Any]) -> dict[str, Any]:
        """处理暂停作业请求"""
        try:
            # 支持新旧两种参数名
            job_uuid = request.get("job_uuid") or request.get("env_uuid")
            if not job_uuid:
                return {
                    "status": "error",
                    "message": "Missing job_uuid parameter",
                    "request_id": request.get("request_id"),
                }

            result = self.jobmanager.pause_job(job_uuid)
            result["request_id"] = request.get("request_id")
            return result

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to pause job: {str(e)}",
                "request_id": request.get("request_id"),
            }

    def _handle_continue_job(self, request: dict[str, Any]) -> dict[str, Any]:
        """处理继续作业请求"""
        try:
            # 支持新旧两种参数名
            job_uuid = request.get("job_uuid") or request.get("env_uuid")
            if not job_uuid:
                return {
                    "status": "error",
                    "message": "Missing job_uuid parameter",
                    "request_id": request.get("request_id"),
                }

            result = self.jobmanager.continue_job(job_uuid)
            result["request_id"] = request.get("request_id")
            return result

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to continue job: {str(e)}",
                "request_id": request.get("request_id"),
            }

    def _handle_delete_job(self, request: dict[str, Any]) -> dict[str, Any]:
        """处理删除作业请求"""
        try:
            # 支持新旧两种参数名
            job_uuid = request.get("job_uuid") or request.get("env_uuid")
            force = request.get("force", False)

            if not job_uuid:
                return {
                    "status": "error",
                    "message": "Missing job_uuid parameter",
                    "request_id": request.get("request_id"),
                }

            result = self.jobmanager.delete_job(job_uuid, force=force)
            result["request_id"] = request.get("request_id")
            return result

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to delete job: {str(e)}",
                "request_id": request.get("request_id"),
            }

    def _handle_list_jobs(self, request: dict[str, Any]) -> dict[str, Any]:
        """处理列出作业请求"""
        try:
            jobs = self.jobmanager.list_jobs()

            return {
                "status": "success",
                "jobs": jobs,
                "request_id": request.get("request_id"),
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to list jobs: {str(e)}",
                "request_id": request.get("request_id"),
            }

    def _handle_get_server_info(self, request: dict[str, Any]) -> dict[str, Any]:
        """处理获取服务器信息请求"""
        try:
            server_info = self.jobmanager.get_server_info()

            return {
                "status": "success",
                "server_info": server_info,
                "request_id": request.get("request_id"),
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get server info: {str(e)}",
                "request_id": request.get("request_id"),
            }

    def _handle_cleanup_all_jobs(self, request: dict[str, Any]) -> dict[str, Any]:
        """处理清理所有作业请求"""
        try:
            result = self.jobmanager.cleanup_all_jobs()
            result["request_id"] = request.get("request_id")
            return result

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to cleanup jobs: {str(e)}",
                "request_id": request.get("request_id"),
            }

    def _handle_receive_node_stop_signal(self, request: dict[str, Any]) -> dict[str, Any]:
        """处理节点停止信号"""
        try:
            job_uuid = request.get("job_uuid")
            node_name = request.get("node_name")

            if not job_uuid or not node_name:
                return {
                    "status": "error",
                    "message": "Missing job_uuid or node_name",
                    "request_id": request.get("request_id"),
                }

            # 调用JobManager的方法
            self.jobmanager.receive_node_stop_signal(job_uuid, node_name)

            return {
                "status": "success",
                "message": f"Node stop signal received for {node_name}",
                "request_id": request.get("request_id"),
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to process node stop signal: {str(e)}",
                "request_id": request.get("request_id"),
            }

    def _handle_health_check(self, request: dict[str, Any]) -> dict[str, Any]:
        """处理健康检查请求"""
        daemon_status = {
            "daemon_running": True,
            "socket_service": f"{self.host}:{self.port}",
            "jobmanager_ready": True,
            "session_id": self.jobmanager.session_id,
            "jobs_count": len(self.jobmanager.jobs),
        }

        return {
            "status": "success",
            "message": "JobManager and Daemon are healthy",
            "daemon_status": daemon_status,
            "request_id": request.get("request_id"),
        }

    def _handle_get_environment_info(self, request: dict[str, Any]) -> dict[str, Any]:
        """处理获取环境信息请求"""
        try:
            import platform

            environment_info = {
                "python_version": sys.version,
                "python_executable": sys.executable,
                "platform": platform.platform(),
                "ray_version": (ray.__version__ if hasattr(ray, "__version__") else "unknown"),
                "session_id": self.jobmanager.session_id,
                "log_base_dir": str(self.jobmanager.log_base_dir),
                "working_directory": os.getcwd(),
            }

            return {
                "status": "success",
                "environment_info": environment_info,
                "request_id": request.get("request_id"),
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get environment info: {e}",
                "request_id": request.get("request_id"),
            }

    def shutdown(self):
        """关闭守护服务"""
        self.logger.info("Shutting down JobManager daemon...")

        # 调用基类的停止方法
        self.stop()

        self.logger.info("JobManager daemon shutdown complete")
