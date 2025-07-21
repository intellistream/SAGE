
import socket, ray
import threading
import time
import json
import pickle
import signal
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, TYPE_CHECKING
from sage_utils.custom_logger import CustomLogger
from sage_jobmanager.remote_job_manager import RemoteJobManager
from ray.actor import ActorHandle
    



class RayJobManagerDaemon:
    """
    Ray JobManager守护服务
    负责启动detached JobManager Actor并通过socket暴露句柄
    """
    
    def __init__(self, 
                 host: str = "127.0.0.1", 
                 port: int = 19001,
                 actor_name: str = "sage_global_jobmanager",
                 namespace: str = "sage_system"):
        """
        初始化守护服务
        
        Args:
            host: Socket服务监听地址
            port: Socket服务端口  
            actor_name: JobManager Actor名称
            namespace: Ray命名空间
        """
        self.host = host
        self.port = port
        self.actor_name = actor_name
        self.namespace = namespace
        
        # Actor句柄
        self._actor_handle: Optional[ActorHandle] = None
        
        # Socket服务
        self._server_socket: Optional[socket.socket] = None
        self._server_thread: Optional[threading.Thread] = None
        self._running = False
        
        # 日志
        self._setup_logging()
        
        # 信号处理
        self._setup_signal_handlers()
        
    def _setup_logging(self):
        """设置日志"""
        # 获取项目根目录：当前文件在deployment目录下，需要回到项目根目录
        project_root = Path(__file__).parent.parent
        log_dir = project_root / "logs" / "daemon"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.logger = CustomLogger([
            ("console", "INFO"),
            (log_dir / f"jobmanager_daemon_{timestamp}.log", "DEBUG"),
            (log_dir / "daemon_error.log", "ERROR")
        ], name="JobManagerDaemon")
        
    def _setup_signal_handlers(self):
        """设置信号处理"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down daemon...")
            self.shutdown()
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def start_daemon(self):
        """启动守护服务"""
        try:
            self.logger.info("Starting Ray JobManager Daemon...")
            
            # 1. 确保进程内Ray客户端已初始化
            if not ray.is_initialized():
                ray.init(address="auto", _temp_dir="/var/lib/ray_shared")
                self.logger.info("Ray initialized")
            
            # 2. 启动JobManager Actor
            self._start_jobmanager_actor()
            
            # 3. 启动Socket服务
            self._start_socket_service()
            
            self.logger.info(f"Daemon started successfully on {self.host}:{self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start daemon: {e}")
            self.shutdown()
            return False
    
    def _start_jobmanager_actor(self):
        """启动JobManager Actor"""
        try:
            # 检查是否已存在Actor
            try:
                existing_actor = ray.get_actor(self.actor_name, namespace=self.namespace)
                # 测试Actor是否健康
                ray.get(existing_actor.health_check.remote(), timeout=5)
                self.logger.info(f"Found existing healthy JobManager Actor: {self.actor_name}")
                self._actor_handle = existing_actor
                return
            except (ValueError, ray.exceptions.RayActorError):
                self.logger.info("No existing healthy Actor found, creating new one")
            
            # 创建新的detached Actor
            self.logger.info(f"Creating detached JobManager Actor: {self.actor_name}")
            
            self._actor_handle = RemoteJobManager.options(
                name=self.actor_name,
                namespace=self.namespace,
                lifetime="detached",  # 关键：使用detached生命周期
                max_restarts=3,
                max_task_retries=2,
                resources={"jobmanager": 1.0}  # 资源标记防止回收
            ).remote()
            
            # 验证Actor创建成功 - 使用Ray内置的ready检查
            self.logger.info("Waiting for Actor to be ready...")
            ray.get(self._actor_handle.get_actor_info.remote(), timeout=30)
            
            # 获取Actor基本信息
            try:
                actor_id = self._actor_handle._actor_id.hex()
                self.logger.info(f"JobManager Actor created successfully: {actor_id}")
            except Exception as e:
                self.logger.info("JobManager Actor created (could not get ID)")
            
        except Exception as e:
            self.logger.error(f"Failed to start JobManager Actor: {e}")
            raise
    
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
        """处理客户端请求"""
        try:
            action = request.get("action", "")
            
            if action == "get_actor_handle":
                return self._handle_get_actor_handle(request)
            elif action == "get_actor_info":
                return self._handle_get_actor_info(request)
            elif action == "health_check":
                return self._handle_health_check(request)
            elif action == "restart_actor":
                return self._handle_restart_actor(request)
            else:
                return {
                    "status": "error",
                    "message": f"Unknown action: {action}",
                    "request_id": request.get("request_id")
                }
                
        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            return {
                "status": "error", 
                "message": str(e),
                "request_id": request.get("request_id")
            }
    
    def _handle_get_actor_handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理获取Actor句柄请求"""
        if self._actor_handle is None:
            return {
                "status": "error",
                "message": "No JobManager Actor available",
                "request_id": request.get("request_id")
            }
        
        try:
            # 序列化Actor句柄
            # 注意：Ray ActorHandle需要特殊处理
            actor_serialized = pickle.dumps(self._actor_handle)
            
            return {
                "status": "success",
                "actor_handle": actor_serialized.hex(),  # 转换为hex字符串传输
                "actor_name": self.actor_name,
                "namespace": self.namespace,
                "request_id": request.get("request_id")
            }
            
        except Exception as e:
            self.logger.error(f"Failed to serialize actor handle: {e}")
            return {
                "status": "error",
                "message": f"Failed to serialize actor handle: {e}",
                "request_id": request.get("request_id")
            }
    
    def _handle_get_actor_info(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理获取Actor信息请求"""
        if self._actor_handle is None:
            return {
                "status": "error",
                "message": "No JobManager Actor available",
                "request_id": request.get("request_id")
            }
        
        try:
            # 构建基本的Actor信息
            actor_info = {
                "actor_name": self.actor_name,
                "namespace": self.namespace,
            }
            
            # 尝试获取Actor ID
            try:
                actor_info["actor_id"] = self._actor_handle._actor_id.hex()
            except:
                actor_info["actor_id"] = "unknown"
            
            # 检查Actor是否ready
            try:
                ray.get(self._actor_handle.__ray_ready__.remote(), timeout=3)
                actor_info["status"] = "ready"
            except:
                actor_info["status"] = "not_ready"
            
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
    
    def _handle_health_check(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理健康检查请求"""
        daemon_status = {
            "daemon_running": True,
            "socket_service": f"{self.host}:{self.port}",
            "actor_name": self.actor_name,
            "namespace": self.namespace
        }
        
        if self._actor_handle is None:
            daemon_status["actor_available"] = False
            return {
                "status": "warning",
                "message": "Daemon running but no Actor available",
                "daemon_status": daemon_status,
                "request_id": request.get("request_id")
            }
        
        try:
            # 使用Ray内置的健康检查
            ray.get(self._actor_handle.__ray_ready__.remote(), timeout=5)
            daemon_status["actor_available"] = True
            daemon_status["actor_ready"] = True
            
            return {
                "status": "success",
                "message": "Daemon and Actor are healthy",
                "daemon_status": daemon_status,
                "request_id": request.get("request_id")
            }
        except Exception as e:
            daemon_status["actor_available"] = False
            daemon_status["actor_error"] = str(e)
            
            return {
                "status": "error",
                "message": f"Actor health check failed: {e}",
                "daemon_status": daemon_status,
                "request_id": request.get("request_id")
            }
    
    def _handle_restart_actor(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理重启Actor请求"""
        try:
            # 停止现有Actor
            if self._actor_handle:
                try:
                    ray.kill(self._actor_handle)
                    self.logger.info("Old Actor killed")
                except:
                    pass
            
            # 启动新Actor
            self._start_jobmanager_actor()
            
            return {
                "status": "success",
                "message": "Actor restarted successfully",
                "request_id": request.get("request_id")
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to restart Actor: {e}",
                "request_id": request.get("request_id")
            }
    
    def shutdown(self):
        """关闭守护服务"""
        self.logger.info("Shutting down daemon...")
        
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
        
        # 注意：不要杀死detached Actor，它应该继续运行
        # 只是释放句柄
        self._actor_handle = None
        
        self.logger.info("Daemon shutdown complete")
    
    def run_forever(self):
        """运行守护服务直到收到停止信号"""
        if not self.start_daemon():
            return False
        
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()
        
        return True



# ==================== 命令行工具 ====================

def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ray JobManager Daemon")
    parser.add_argument("--host", default="127.0.0.1", help="Daemon host")
    parser.add_argument("--port", type=int, default=19001, help="Daemon port")
    parser.add_argument("--actor-name", default="sage_global_jobmanager", help="Actor name")
    parser.add_argument("--namespace", default="sage_system", help="Ray namespace")
    
    args = parser.parse_args()
    
    daemon = RayJobManagerDaemon(
        host=args.host,
        port=args.port,
        actor_name=args.actor_name,
        namespace=args.namespace
    )
    
    print(f"Starting JobManager Daemon on {args.host}:{args.port}")
    print(f"Actor: {args.actor_name}@{args.namespace}")
    print("Press Ctrl+C to stop...")
    
    daemon.run_forever()


if __name__ == "__main__":
    main()