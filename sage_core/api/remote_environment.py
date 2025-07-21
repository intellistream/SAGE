from __future__ import annotations
import ray
import socket
import json
import time
from sage_core.environment.batch_environment import BatchEnvironment
from sage_core.environment.stream_environment import StreamEnvironment
from sage_utils.actor_wrapper import ActorWrapper


class RemoteStreamEnvironment(StreamEnvironment):
    """
    分布式执行环境（Ray），用于生产或大规模部署。
    """

    def __init__(self, name: str = "remote_environment", config: dict | None = None):
        super().__init__(name, config, platform="remote")
        if not ray.is_initialized():
            ray.init(address="auto", _temp_dir="/var/lib/ray_shared")
            # 确保Ray初始化时不启动Dashboard，避免端口冲突

    def _get_jobmanager_handle(self) -> ActorWrapper:
        """获取全局JobManager Actor句柄"""
        return self._get_global_jobmanager_actor()

    def _get_global_jobmanager_actor(self) -> ActorWrapper:
        """通过daemon端口获取全局JobManager Actor句柄"""
        daemon_host = self.config.get("jobmanager_daemon_host", "127.0.0.1")
        daemon_port = self.config.get("jobmanager_daemon_port", 19000)
        
        try:
            # 首先尝试直接从Ray获取已注册的Actor
            try:
                jobmanager_actor = ray.get_actor("sage_jobmanager", namespace="sage")
                self.logger.info("Found existing JobManager Actor")
                return ActorWrapper(jobmanager_actor)
            except ValueError:
                self.logger.info("No existing JobManager Actor found, requesting from daemon")
            
            # 通过daemon端口请求JobManager Actor句柄
            jobmanager_actor = self._request_jobmanager_from_daemon(daemon_host, daemon_port)
            
            if jobmanager_actor is None:
                raise RuntimeError("Failed to obtain JobManager Actor from daemon")
            
            return ActorWrapper(jobmanager_actor)
            
        except Exception as e:
            self.logger.error(f"Failed to get global JobManager Actor: {e}")
            raise RuntimeError(f"Cannot connect to global JobManager: {e}")

    def _request_jobmanager_from_daemon(self, host: str, port: int) -> ray.actor.ActorHandle:
        """通过TCP连接向daemon请求JobManager Actor句柄"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(10)
                    sock.connect((host, port))
                    
                    # 发送请求
                    request = {
                        "type": "get_jobmanager_actor",
                        "timestamp": time.time(),
                        "client_info": {
                            "env_name": self.name,
                            "platform": self.platform
                        }
                    }
                    
                    message_str = json.dumps(request)
                    message_bytes = message_str.encode('utf-8')
                    length_header = len(message_bytes).to_bytes(4, byteorder='big')
                    
                    sock.sendall(length_header + message_bytes)
                    
                    # 接收响应
                    response_length_bytes = sock.recv(4)
                    if len(response_length_bytes) != 4:
                        raise RuntimeError("Invalid response from daemon")
                    
                    response_length = int.from_bytes(response_length_bytes, byteorder='big')
                    response_data = sock.recv(response_length)
                    response = json.loads(response_data.decode('utf-8'))
                    
                    if response.get("status") == "success":
                        # daemon返回的应该是actor的注册信息，我们可以通过ray.get_actor获取
                        actor_name = response.get("actor_name", "sage_jobmanager")
                        actor_namespace = response.get("actor_namespace", "sage")
                        
                        try:
                            jobmanager_actor = ray.get_actor(actor_name, namespace=actor_namespace)
                            self.logger.info(f"Retrieved JobManager Actor: {actor_name}")
                            return jobmanager_actor
                        except ValueError as e:
                            raise RuntimeError(f"Actor not found: {actor_name} in namespace {actor_namespace}")
                    
                    else:
                        error_msg = response.get("message", "Unknown error")
                        raise RuntimeError(f"Daemon request failed: {error_msg}")
                        
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise e

    def submit(self, name="example_pipeline"):
        """提交Job到 dispatcher"""
        self._submit_job()


class RemoteBatchEnvironment(BatchEnvironment):
    """
    分布式执行环境（Ray），用于生产或大规模部署。
    """

    def __init__(self, name: str = "remote_environment", config: dict | None = None):
        super().__init__(name, config, platform="remote")

    def _get_jobmanager_handle(self) -> ActorWrapper:
        """获取全局JobManager Actor句柄"""
        return self._get_global_jobmanager_actor()

    def _get_global_jobmanager_actor(self) -> ActorWrapper:
        """通过daemon端口获取全局JobManager Actor句柄"""
        daemon_host = self.config.get("jobmanager_daemon_host", "127.0.0.1")
        daemon_port = self.config.get("jobmanager_daemon_port", 19000)
        
        try:
            # 首先尝试直接从Ray获取已注册的Actor
            try:
                jobmanager_actor = ray.get_actor("sage_jobmanager", namespace="sage")
                self.logger.info("Found existing JobManager Actor")
                return ActorWrapper(jobmanager_actor)
            except ValueError:
                self.logger.info("No existing JobManager Actor found, requesting from daemon")
            
            # 通过daemon端口请求JobManager Actor句柄
            jobmanager_actor = self._request_jobmanager_from_daemon(daemon_host, daemon_port)
            
            if jobmanager_actor is None:
                raise RuntimeError("Failed to obtain JobManager Actor from daemon")
            
            return ActorWrapper(jobmanager_actor)
            
        except Exception as e:
            self.logger.error(f"Failed to get global JobManager Actor: {e}")
            raise RuntimeError(f"Cannot connect to global JobManager: {e}")

    def _request_jobmanager_from_daemon(self, host: str, port: int) -> ray.actor.ActorHandle:
        """通过TCP连接向daemon请求JobManager Actor句柄"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(10)
                    sock.connect((host, port))
                    
                    # 发送请求
                    request = {
                        "type": "get_jobmanager_actor",
                        "timestamp": time.time(),
                        "client_info": {
                            "env_name": self.name,
                            "platform": self.platform
                        }
                    }
                    
                    message_str = json.dumps(request)
                    message_bytes = message_str.encode('utf-8')
                    length_header = len(message_bytes).to_bytes(4, byteorder='big')
                    
                    sock.sendall(length_header + message_bytes)
                    
                    # 接收响应
                    response_length_bytes = sock.recv(4)
                    if len(response_length_bytes) != 4:
                        raise RuntimeError("Invalid response from daemon")
                    
                    response_length = int.from_bytes(response_length_bytes, byteorder='big')
                    response_data = sock.recv(response_length)
                    response = json.loads(response_data.decode('utf-8'))
                    
                    if response.get("status") == "success":
                        # daemon返回的应该是actor的注册信息，我们可以通过ray.get_actor获取
                        actor_name = response.get("actor_name", "sage_jobmanager")
                        actor_namespace = response.get("actor_namespace", "sage")
                        
                        try:
                            jobmanager_actor = ray.get_actor(actor_name, namespace=actor_namespace)
                            self.logger.info(f"Retrieved JobManager Actor: {actor_name}")
                            return jobmanager_actor
                        except ValueError as e:
                            raise RuntimeError(f"Actor not found: {actor_name} in namespace {actor_namespace}")
                    
                    else:
                        error_msg = response.get("message", "Unknown error")
                        raise RuntimeError(f"Daemon request failed: {error_msg}")
                        
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise e

    def submit(self, name="example_pipeline"):
        """提交Job到 dispatcher"""
        self._submit_job()