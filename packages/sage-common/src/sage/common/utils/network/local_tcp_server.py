import socket
import threading
import pickle
import json
import time
from typing import Dict, Any, Callable, Optional, Union
import os
from abc import ABC, abstractmethod

class BaseTcpServer(ABC):
    """
    通用TCP服务器基类
    提供基础的TCP服务器功能，包括连接管理、消息收发等
    子类需要实现具体的消息处理逻辑
    """
    
    def __init__(self, 
                 host: str = None, 
                 port: int = None,
                 logger=None,
                 server_name: str = "TcpServer"):
        """
        初始化TCP服务器
        
        Args:
            host: 监听地址
            port: 监听端口
            logger: 日志记录器
            server_name: 服务器名称，用于日志和线程命名
        """
        self.server_name = server_name
        self.server_cwd = os.getcwd()
        
        # 日志记录器需要先初始化
        self.logger = logger or self._create_default_logger()
        
        self.host = host or self._get_host_ip()
        self.port = port or self._allocate_tcp_port()
        self.server_socket: Optional[socket.socket] = None
        self.server_thread: Optional[threading.Thread] = None
        self.running = False
        
        # 客户端连接管理
        self.client_connections: Dict[str, socket.socket] = {}  # client_id -> socket
        self.client_lock = threading.Lock()
    
    def _create_default_logger(self):
        """创建默认日志记录器"""
        import logging
        logger = logging.getLogger(f"{self.server_name}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def _get_host_ip(self):
        """自动获取本机可用于外部连接的 IP 地址"""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            self.logger.warning("Failed to get external IP, using localhost")
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip
    
    def _allocate_tcp_port(self) -> int:
        """为服务器分配可用的TCP端口"""
        # 尝试从预设范围分配端口
        for port in range(19200, 20000):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((self.host or "127.0.0.1", port))
                    self.logger.debug(f"Allocated port: {port}")
                    return port
            except OSError:
                continue
        
        # 如果预设范围都被占用，直接抛出异常
        self.logger.error("All predefined ports are occupied, no available port")
        raise OSError("No available port in the predefined range (19200-19999)")

    def start(self):
        """启动TCP服务器"""
        if self.running:
            self.logger.warning(f"{self.server_name} is already running")
            return
        
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.settimeout(5)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            
            self.running = True
            self.server_thread = threading.Thread(
                target=self._server_loop,
                name=f"{self.server_name}Thread"
            )
            self.server_thread.daemon = True
            self.server_thread.start()
            
            self.logger.info(f"{self.server_name} started on {self.host}:{self.port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start {self.server_name}: {e}")
            self.running = False
            raise
    
    def stop(self):
        """停止TCP服务器"""
        if not self.running:
            return
        
        self.logger.info(f"Stopping {self.server_name}...")
        self.running = False
        
        if self.server_socket:
            self.server_socket.close()
        
        if self.server_thread and self.server_thread.is_alive():
            for _ in range(5):
                self.server_thread.join(timeout=1.0)
                if not self.server_thread.is_alive():
                    break
            else:
                self.logger.warning(f"{self.server_name} thread did not stop gracefully")
        
        self.logger.info(f"{self.server_name} stopped")
    
    def _server_loop(self):
        """TCP服务器主循环"""
        try:
            self.logger.debug(f"{self.server_name} loop started")
        except:
            print(f"{self.server_name} loop started")
        
        while self.running:
            try:
                if not self.server_socket:
                    break
                
                # 检查socket是否仍然有效
                try:
                    result = self.server_socket.accept()
                    if result is None or len(result) != 2:
                        self.logger.warning("Socket accept returned invalid result")
                        break
                    client_socket, address = result
                except ValueError as ve:
                    self.logger.warning(f"Socket accept unpacking error: {ve}")
                    break
                    
                try:
                    self.logger.debug(f"New TCP client connected from {address}")
                except:
                    print(f"New TCP client connected from {address}")
                
                # 在新线程中处理客户端
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address),
                    name=f"{self.server_name}Client-{address[0]}:{address[1]}"
                )
                client_thread.daemon = True
                client_thread.start()
            except socket.timeout:
                continue
            except OSError as e:
                if self.running:
                    try:
                        self.logger.error(f"Error accepting TCP connection: {e}")
                    except:
                        print(f"Error accepting TCP connection: {e}")
                break
            except Exception as e:
                if self.running:
                    # 使用print而不是logger来避免I/O错误
                    print(f"Unexpected error in server loop: {e}")
                break
        
        try:
            self.logger.debug(f"{self.server_name} loop stopped")
        except:
            print(f"{self.server_name} loop stopped")
    
    def _handle_client(self, client_socket: socket.socket, address: tuple):
        """处理客户端连接和消息"""
        try:
            while self.running:
                # 读取消息长度
                size_data = client_socket.recv(4)
                if not size_data:
                    break
                
                message_size = int.from_bytes(size_data, byteorder='big')
                if message_size <= 0 or message_size > 10 * 1024 * 1024:  # 10MB limit
                    self.logger.warning(f"Invalid message size {message_size} from {address}")
                    break
                
                # 读取消息内容
                message_data = self._receive_full_message(client_socket, message_size)
                if not message_data:
                    break
                
                # 处理消息
                try:
                    response = self._handle_message_data(message_data, address)
                    
                    # 发送响应
                    if response:
                        self._send_response(client_socket, response)
                        
                except Exception as e:
                    # 安全地记录错误，避免I/O错误
                    try:
                        self.logger.error(f"Error processing message from {address}: {e}")
                    except:
                        print(f"Error processing message from {address}: {e}")
                    # 发送错误响应
                    error_response = self._create_error_response(
                        {"request_id": None}, "ERR_INTERNAL_ERROR", f"Internal server error: {str(e)}"
                    )
                    self._send_response(client_socket, error_response)
                
        except Exception as e:
            # 安全地记录错误，避免I/O错误
            try:
                self.logger.error(f"Error handling TCP client {address}: {e}")
            except:
                print(f"Error handling TCP client {address}: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
            try:
                self.logger.debug(f"TCP client {address} disconnected")
            except:
                pass
    
    def _receive_full_message(self, client_socket: socket.socket, message_size: int) -> Optional[bytes]:
        """接收完整的消息数据"""
        message_data = b''
        while len(message_data) < message_size:
            chunk_size = min(message_size - len(message_data), 8192)
            chunk = client_socket.recv(chunk_size)
            if not chunk:
                try:
                    self.logger.warning("Connection closed while receiving message")
                except:
                    print("Connection closed while receiving message")
                return None
            message_data += chunk
        
        return message_data
    
    @abstractmethod
    def _handle_message_data(self, message_data: bytes, client_address: tuple) -> Optional[Dict[str, Any]]:
        """
        处理接收到的消息数据（抽象方法）
        
        Args:
            message_data: 原始消息数据
            client_address: 客户端地址
            
        Returns:
            响应字典，如果返回None则不发送响应
        """
        pass
    
    def _send_response(self, client_socket: socket.socket, response: Union[Dict[str, Any], bytes]):
        """发送响应到客户端"""
        try:
            # 确定响应数据格式
            if isinstance(response, dict):
                response["cwd"] = self.server_cwd  # 添加服务器当前工作目录
                serialized = self._serialize_response(response)
            elif isinstance(response, bytes):
                serialized = response
            else:
                # 其他类型，尝试序列化
                serialized = self._serialize_response(response)
            
            message_size = len(serialized)
            
            # 发送消息长度
            client_socket.send(message_size.to_bytes(4, byteorder='big'))
            
            # 发送消息内容
            client_socket.send(serialized)
            
            self.logger.debug(f"Sent response (size: {message_size})")
            
        except Exception as e:
            self.logger.error(f"Error sending response: {e}")
    
    def _serialize_response(self, response: Any) -> bytes:
        """序列化响应（默认使用pickle，子类可以重写）"""
        return pickle.dumps(response)
    
    def _create_error_response(self, original_message: Dict[str, Any], error_code: str, error_message: str) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "type": f"{original_message.get('type', 'unknown')}_response",
            "request_id": original_message.get("request_id"),
            "timestamp": int(time.time()),
            "status": "error",
            "message": error_message,
            "payload": {
                "error_code": error_code,
                "details": {}
            }
        }

    def get_server_info(self) -> Dict[str, Any]:
        """获取服务器信息"""
        return {
            "server_name": self.server_name,
            "host": self.host,
            "port": self.port,
            "running": self.running,
            "address": f"{self.host}:{self.port}"
        }
    
    def __del__(self):
        """析构函数，确保资源清理"""
        try:
            self.stop()
        except:
            pass


class LocalTcpServer(BaseTcpServer):
    """
    本地TCP服务器，用于接收Ray Actor发送的数据
    支持基于消息类型的多个处理器
    """
    
    def __init__(self, 
                 host: str = None, 
                 port: int = None,
                 default_handler: Optional[Callable[[Dict[str, Any], tuple], Dict[str, Any]]] = None,
                 logger=None):
        """
        初始化TCP服务器
        
        Args:
            host: 监听地址
            port: 监听端口
            default_handler: 默认消息处理回调函数，用于处理未知类型的消息
            logger: 日志记录器
        """
        super().__init__(host, port, logger, "LocalTcpServer")
        
        # 消息处理器字典：消息类型 -> 处理函数
        self.message_handlers: Dict[str, Callable[[Dict[str, Any], tuple], Dict[str, Any]]] = {}
        self.default_handler = default_handler
        
        # 添加锁保护处理器字典
        self._handlers_lock = threading.RLock()
    
    def _handle_message_data(self, message_data: bytes, client_address: tuple) -> Optional[Dict[str, Any]]:
        """处理接收到的消息数据"""
        try:
            # 反序列化消息
            message = pickle.loads(message_data)
            return self._process_message(message, client_address)
        except Exception as e:
            self.logger.error(f"Error deserializing message from {client_address}: {e}")
            return self._create_error_response(
                {"request_id": None}, "ERR_DESERIALIZATION_FAILED", f"Failed to deserialize message: {str(e)}"
            )
    
    def _process_message(self, message: Dict[str, Any], client_address: tuple) -> Optional[Dict[str, Any]]:
        """
        处理接收到的消息，根据消息类型分发给对应的处理器
        
        Args:
            message: 接收到的消息字典
            client_address: 客户端地址
            
        Returns:
            响应字典，如果处理器返回 None 则不发送响应
        """
        try:
            # 尝试获取消息类型
            message_type = self._extract_message_type(message)
            if message_type is None:
                # 无法提取消息类型，使用默认处理器
                self.logger.warning(f"Could not extract message type from message, using default handler")
                return self._use_default_handler(message, client_address, None)

            self.logger.debug(f"Processing message type '{message_type}' from {client_address}")
            
            # 查找对应的处理器
            with self._handlers_lock:
                handler = self.message_handlers.get(message_type, None)
            
            if handler is None:
                # 没有找到对应的处理器，使用默认处理器
                self.logger.warning(f"No handler found for message type '{message_type}', using default handler")
                return self._use_default_handler(message, client_address, message_type)
            

            try:
                response = handler(message, client_address)
                self.logger.debug(f"Message type '{message_type}' processed successfully")
                return response
            except Exception as e:
                self.logger.error(f"Error in handler for message type '{message_type}': {e}", exc_info=True)
                return self._create_error_response(message, "ERR_HANDLER_FAILED", str(e))

                
        except Exception as e:
            self.logger.error(f"Error in message processing: {e}", exc_info=True)
            return self._create_error_response(message, "ERR_PROCESSING_FAILED", str(e))
    
    def _extract_message_type(self, message: Dict[str, Any]) -> Optional[str]:
        """从消息中提取消息类型"""
        if not isinstance(message, dict):
            self.logger.warning(f"Message is not a dictionary: {type(message)}")
            return None
        
        # 尝试多种可能的类型字段名
        type_fields = ['type', 'message_type', 'msg_type', 'event_type', 'command']
        
        for field in type_fields:
            if field in message:
                msg_type = message[field]
                if isinstance(msg_type, str) and msg_type.strip():
                    return msg_type.strip()
        
        self.logger.debug(f"No valid type field found in message keys: {list(message.keys())}")
        return None
    
    def _use_default_handler(self, message: Dict[str, Any], client_address: tuple, message_type: Optional[str]) -> Optional[Dict[str, Any]]:
        """使用默认处理器处理消息"""
        if self.default_handler:
            try:
                response = self.default_handler(message, client_address)
                self.logger.debug("Message processed by default handler")
                return response
            except Exception as e:
                self.logger.error(f"Error in default handler: {e}", exc_info=True)
                return self._create_error_response(message, "ERR_DEFAULT_HANDLER_FAILED", str(e))
        else:
            self.logger.warning(f"No default handler set, ignoring message from {client_address}")
            if message_type:
                self.logger.info(f"Consider registering a handler for message type '{message_type}'")
            return self._create_error_response(message, "ERR_NO_HANDLER", "No handler available for this message type")
    
    def _create_error_response(self, original_message: Dict[str, Any], error_code: str, error_message: str) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "type": f"{original_message.get('type', 'unknown')}_response",
            "request_id": original_message.get("request_id"),
            "env_name": original_message.get("env_name"),
            "env_uuid": original_message.get("env_uuid"),
            "timestamp": int(time.time()),
            "status": "error",
            "message": error_message,
            "payload": {
                "error_code": error_code,
                "details": {}
            }
        }

    def _send_response(self, client_socket: socket.socket, response: Dict[str, Any]):
        """发送响应到客户端"""
        try:
            # 序列化响应
            if isinstance(response, dict):
                response["cwd"] = self.server_cwd  # 添加服务器当前工作目录
            serialized = pickle.dumps(response)
            message_size = len(serialized)
            
            # 发送消息长度
            client_socket.send(message_size.to_bytes(4, byteorder='big'))
            
            # 发送消息内容
            client_socket.send(serialized)
            
            self.logger.debug(f"Sent response: {response.get('type')}")
            
        except Exception as e:
            self.logger.error(f"Error sending response: {e}")

    def get_server_info(self) -> Dict[str, Any]:
        """获取服务器信息"""
        with self._handlers_lock:
            registered_types = list(self.message_handlers.keys())
        
        base_info = super().get_server_info()
        base_info.update({
            "registered_message_types": registered_types,
            "has_default_handler": self.default_handler is not None
        })
        return base_info

    ########################################################
    #                handler  registration                 #
    ########################################################

    def register_handler(self, message_type: str, handler: Callable[[Dict[str, Any], tuple], Dict[str, Any]]):
        """注册消息处理器"""
        with self._handlers_lock:
            self.message_handlers[message_type] = handler
            self.logger.info(f"Registered handler for message type: {message_type}")

    def set_default_handler(self, handler: Callable[[Dict[str, Any], tuple], Dict[str, Any]]):
        """设置默认消息处理器"""
        self.default_handler = handler
        self.logger.info("Default message handler set")

    def unregister_handler(self, message_type: str):
        """注销消息处理器"""
        with self._handlers_lock:
            if message_type in self.message_handlers:
                del self.message_handlers[message_type]
                self.logger.info(f"Unregistered handler for message type: {message_type}")
            else:
                self.logger.warning(f"No handler found for message type: {message_type}")

    def get_registered_types(self) -> list[str]:
        """获取已注册的消息类型列表"""
        with self._handlers_lock:
            return list(self.message_handlers.keys())



# 使用示例
if __name__ == "__main__":
    def handle_status_message(message: Dict[str, Any], client_address: tuple) -> Dict[str, Any]:
        print(f"Status message from {client_address}: {message}")
        return {"type": "status_response", "status": "success", "message": "Status received"}
    
    def handle_data_message(message: Dict[str, Any], client_address: tuple) -> Dict[str, Any]:
        print(f"Data message from {client_address}: {message}")
        return {"type": "data_response", "status": "success", "message": "Data processed"}
    
    def handle_unknown_message(message: Dict[str, Any], client_address: tuple) -> Dict[str, Any]:
        print(f"Unknown message from {client_address}: {message}")
        return {"type": "unknown_response", "status": "success", "message": "Unknown message received"}
    
    # 创建服务器
    server = LocalTcpServer(default_handler=handle_unknown_message)
    
    # 注册不同类型的处理器
    server.register_handler("status", handle_status_message)
    server.register_handler("data", handle_data_message)
    
    # 启动服务器
    server.start()
    
    print(f"Server info: {server.get_server_info()}")
    
    try:
        # 保持服务器运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping server...")
        server.stop()