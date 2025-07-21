#!/usr/bin/env python3

"""
Ray JobManager守护进程脚本
管理全局的Ray JobManager Actor，并提供句柄获取服务
"""

import os
import sys
import socket
import time
import signal
import json
import threading
import argparse
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import ray
from ray.actor import ActorHandle

# 添加项目根目录到Python路径
SAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SAGE_ROOT))

from sage_jobmanager.ray_job_manager import RayJobManager
from sage_examples.persistent_jobmanager_example import JobManagerActorService

class RayJobManagerDaemon:
    """Ray JobManager守护进程"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 19000,
                 actor_name: str = "sage_jobmanager",
                 actor_namespace: str = "sage"):
        self.host = host
        self.port = port
        self.actor_name = actor_name
        self.actor_namespace = actor_namespace
        self.logger = self._setup_logger()
        
        # JobManager Actor服务管理器
        self.jm_service: Optional[JobManagerActorService] = None
        self.actor_handle: Optional[ActorHandle] = None
        
        # TCP服务器相关
        self.tcp_server: Optional[socket.socket] = None
        self.server_thread: Optional[threading.Thread] = None
        self.running = False
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('RayJobManagerDaemon')
        logger.setLevel(logging.INFO)
        
        # 清除现有的处理器
        logger.handlers.clear()
        
        # 文件处理器
        logfile = Path("/tmp/ray_jobmanager_daemon.log")
        file_handler = logging.FileHandler(logfile)
        file_handler.setLevel(logging.DEBUG)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def init_ray(self) -> bool:
        """初始化Ray"""
        try:
            if not ray.is_initialized():
                # 尝试连接到现有Ray集群，如果失败则本地启动
                try:
                    ray.init(address="auto", ignore_reinit_error=True)
                    self.logger.info("Connected to existing Ray cluster")
                except:
                    ray.init(ignore_reinit_error=True)
                    self.logger.info("Started local Ray cluster")
            else:
                self.logger.info("Ray already initialized")
                
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize Ray: {e}")
            return False
    
    def start_ray_jobmanager_actor(self) -> bool:
        """启动Ray JobManager Actor"""
        try:
            if not self.init_ray():
                return False
            
            self.jm_service = JobManagerActorService(
                actor_name=self.actor_name,
                namespace=self.actor_namespace
            )
            
            # 获取或创建持久化JobManager
            self.actor_handle = self.jm_service.get_or_create_jobmanager(
                method="detached",
                resources={"jobmanager": 1.0}
            )
            
            # 验证Actor健康状态
            health = ray.get(self.actor_handle.health_check.remote(), timeout=10)
            if health.get("status") != "healthy":
                raise RuntimeError(f"JobManager Actor unhealthy: {health}")
            
            self.logger.info(f"Ray JobManager Actor started: {self.actor_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start Ray JobManager Actor: {e}")
            return False
    
    def start_tcp_server(self) -> bool:
        """启动TCP服务器以处理客户端请求"""
        try:
            self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_server.bind((self.host, self.port))
            self.tcp_server.listen(10)
            
            self.running = True
            self.server_thread = threading.Thread(
                target=self._server_loop,
                name="TCPServerThread",
                daemon=True
            )
            self.server_thread.start()
            
            self.logger.info(f"TCP server started on {self.host}:{self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start TCP server: {e}")
            return False
    
    def _server_loop(self):
        """TCP服务器主循环"""
        while self.running:
            try:
                client_socket, client_address = self.tcp_server.accept()
                self.logger.debug(f"Client connected: {client_address}")
                
                # 在新线程中处理客户端请求
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error in server loop: {e}")
    
    def _handle_client(self, client_socket: socket.socket, client_address: tuple):
        """处理客户端请求"""
        try:
            with client_socket:
                # 读取请求长度
                length_bytes = client_socket.recv(4)
                if len(length_bytes) != 4:
                    return
                
                request_length = int.from_bytes(length_bytes, byteorder='big')
                
                # 读取请求数据
                request_data = client_socket.recv(request_length)
                request = json.loads(request_data.decode('utf-8'))
                
                self.logger.debug(f"Received request: {request['type']}")
                
                # 处理不同类型的请求
                response = self._process_request(request)
                
                # 发送响应
                response_str = json.dumps(response)
                response_bytes = response_str.encode('utf-8')
                response_length = len(response_bytes).to_bytes(4, byteorder='big')
                
                client_socket.sendall(response_length + response_bytes)
                
        except Exception as e:
            self.logger.error(f"Error handling client {client_address}: {e}")
    
    def _process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理客户端请求"""
        request_type = request.get("type")
        
        if request_type == "get_jobmanager_actor":
            return self._handle_get_jobmanager_actor(request)
        elif request_type == "ping":
            return {"status": "success", "message": "pong", "timestamp": time.time()}
        elif request_type == "health_check":
            return self._handle_health_check(request)
        else:
            return {"status": "error", "message": f"Unknown request type: {request_type}"}
    
    def _handle_get_jobmanager_actor(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理获取JobManager Actor句柄的请求"""
        try:
            if not self.actor_handle:
                return {
                    "status": "error",
                    "message": "JobManager Actor not available"
                }
            
            # 验证Actor是否仍然健康
            try:
                health = ray.get(self.actor_handle.health_check.remote(), timeout=5)
                if health.get("status") != "healthy":
                    raise RuntimeError("Actor unhealthy")
            except Exception as e:
                self.logger.warning(f"Actor health check failed: {e}")
                # 尝试重新获取Actor
                if not self._recover_actor():
                    return {
                        "status": "error", 
                        "message": "JobManager Actor unavailable and recovery failed"
                    }
            
            return {
                "status": "success",
                "message": "JobManager Actor available",
                "actor_name": self.actor_name,
                "actor_namespace": self.actor_namespace,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"Error handling get_jobmanager_actor request: {e}")
            return {"status": "error", "message": str(e)}
    
    def _handle_health_check(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理健康检查请求"""
        try:
            status = {
                "daemon_status": "healthy",
                "ray_initialized": ray.is_initialized(),
                "actor_available": self.actor_handle is not None,
                "tcp_server_running": self.running
            }
            
            if self.actor_handle:
                try:
                    actor_health = ray.get(self.actor_handle.health_check.remote(), timeout=5)
                    status["actor_health"] = actor_health
                except Exception as e:
                    status["actor_health"] = {"status": "unhealthy", "error": str(e)}
            
            return {
                "status": "success",
                "health": status,
                "timestamp": time.time()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": time.time()
            }
    
    def _recover_actor(self) -> bool:
        """尝试恢复JobManager Actor"""
        try:
            self.logger.info("Attempting to recover JobManager Actor...")
            
            if self.jm_service:
                self.actor_handle = self.jm_service.get_or_create_jobmanager(
                    method="detached",
                    resources={"jobmanager": 1.0}
                )
                
                # 验证恢复的Actor
                health = ray.get(self.actor_handle.health_check.remote(), timeout=10)
                if health.get("status") == "healthy":
                    self.logger.info("JobManager Actor recovered successfully")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to recover JobManager Actor: {e}")
            return False
    
    def start(self) -> bool:
        """启动守护进程"""
        self.logger.info("Starting Ray JobManager Daemon...")
        
        # 启动Ray JobManager Actor
        if not self.start_ray_jobmanager_actor():
            return False
        
        # 启动TCP服务器
        if not self.start_tcp_server():
            return False
        
        self.logger.info(f"Ray JobManager Daemon started successfully on {self.host}:{self.port}")
        return True
    
    def stop(self) -> bool:
        """停止守护进程"""
        self.logger.info("Stopping Ray JobManager Daemon...")
        
        # 停止TCP服务器
        self.running = False
        if self.tcp_server:
            try:
                self.tcp_server.close()
            except:
                pass
        
        # 停止JobManager Actor
        if self.jm_service:
            try:
                self.jm_service.stop_jobmanager(graceful=True)
            except Exception as e:
                self.logger.warning(f"Error stopping JobManager Actor: {e}")
        
        # 关闭Ray（可选）
        # ray.shutdown()
        
        self.logger.info("Ray JobManager Daemon stopped")
        return True
    
    def run_forever(self):
        """持续运行守护进程"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down...")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        self.logger.info("Daemon running. Press Ctrl+C to stop.")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        finally:
            self.stop()


def main():
    parser = argparse.ArgumentParser(description="Ray JobManager守护进程管理器")
    parser.add_argument("command", choices=["start", "stop", "status"],
                       help="要执行的命令")
    parser.add_argument("--host", default="127.0.0.1", help="服务主机地址")
    parser.add_argument("--port", type=int, default=19000, help="服务端口")
    parser.add_argument("--actor-name", default="sage_jobmanager", help="Actor名称")
    parser.add_argument("--actor-namespace", default="sage", help="Actor命名空间")
    
    args = parser.parse_args()
    
    daemon = RayJobManagerDaemon(
        host=args.host,
        port=args.port,
        actor_name=args.actor_name,
        actor_namespace=args.actor_namespace
    )
    
    if args.command == "start":
        if daemon.start():
            daemon.run_forever()
        else:
            print("❌ Failed to start Ray JobManager Daemon")
            sys.exit(1)
            
    elif args.command == "stop":
        # 这里可以实现通过TCP发送停止命令
        print("Stop command not implemented yet. Use Ctrl+C to stop running daemon.")
        
    elif args.command == "status":
        # 这里可以实现通过TCP查询状态
        print("Status command not implemented yet.")


if __name__ == "__main__":
    main()
