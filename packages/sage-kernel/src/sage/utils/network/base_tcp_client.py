import socket
import json
import uuid
import time
from typing import Optional, Dict, Any, Union
from abc import ABC, abstractmethod


class BaseTcpClient(ABC):
    """
    通用TCP客户端基类
    提供基础的TCP客户端功能，包括连接管理、消息收发等
    子类需要实现具体的消息构建和响应处理逻辑
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 19001, 
                 timeout: float = 30.0, client_name: str = "TcpClient"):
        """
        初始化TCP客户端
        
        Args:
            host: 服务器地址
            port: 服务器端口
            timeout: 连接超时时间
            client_name: 客户端名称，用于日志记录
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.client_name = client_name
        
        # 连接状态
        self.connected = False
        self._socket: Optional[socket.socket] = None
        
        # 日志记录器（子类可以设置自己的logger）
        self.logger = self._create_default_logger()
    
    def _create_default_logger(self):
        """创建默认日志记录器"""
        import logging
        logger = logging.getLogger(f"{self.client_name}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def connect(self) -> bool:
        """
        连接到服务器
        
        Returns:
            bool: 连接成功返回True，否则返回False
        """
        if self.connected:
            return True
        
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.timeout)
            self._socket.connect((self.host, self.port))
            self.connected = True
            self.logger.debug(f"{self.client_name} connected to {self.host}:{self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to {self.host}:{self.port}: {e}")
            self.connected = False
            if self._socket:
                try:
                    self._socket.close()
                except:
                    pass
                self._socket = None
            return False
    
    def disconnect(self):
        """断开与服务器的连接"""
        if self._socket:
            try:
                self._socket.close()
            except:
                pass
            self._socket = None
        
        self.connected = False
        self.logger.debug(f"{self.client_name} disconnected")
    
    def send_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送请求到服务器并返回响应
        
        Args:
            request_data: 请求数据字典
            
        Returns:
            Dict[str, Any]: 服务器响应
        """
        # 确保连接
        if not self.connected:
            if not self.connect():
                return self._create_error_response("ERR_CONNECTION_FAILED", "Failed to connect to server")
        
        try:
            # 序列化请求数据
            serialized_request = self._serialize_request(request_data)
            
            # 发送请求
            self._send_data(serialized_request)
            
            # 接收响应
            response_data = self._receive_response()
            
            if response_data is None:
                return self._create_error_response("ERR_NO_RESPONSE", "No response received from server")
            
            # 反序列化响应
            response = self._deserialize_response(response_data)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error sending request: {e}")
            # 连接可能已断开，重置连接状态
            self.connected = False
            return self._create_error_response("ERR_COMMUNICATION_FAILED", f"Communication error: {e}")
    
    def _send_data(self, data: bytes):
        """发送数据到服务器"""
        if not self._socket:
            raise RuntimeError("Socket not connected")
        
        # 发送数据长度
        data_length = len(data).to_bytes(4, byteorder='big')
        self._socket.sendall(data_length)
        
        # 发送数据内容
        self._socket.sendall(data)
        
        self.logger.debug(f"Sent data (size: {len(data)})")
    
    def _receive_response(self) -> Optional[bytes]:
        """接收服务器响应"""
        if not self._socket:
            raise RuntimeError("Socket not connected")
        
        try:
            # 接收响应长度
            response_length_data = self._receive_full_data(4)
            if not response_length_data:
                return None
            
            response_length = int.from_bytes(response_length_data, byteorder='big')
            
            if response_length <= 0 or response_length > 100 * 1024 * 1024:  # 100MB limit
                self.logger.warning(f"Invalid response length: {response_length}")
                return None
            
            # 接收响应数据
            response_data = self._receive_full_data(response_length)
            
            self.logger.debug(f"Received response (size: {len(response_data) if response_data else 0})")
            
            return response_data
            
        except Exception as e:
            self.logger.error(f"Error receiving response: {e}")
            return None
    
    def _receive_full_data(self, size: int) -> Optional[bytes]:
        """接收指定大小的完整数据"""
        if not self._socket:
            return None
        
        data = b''
        while len(data) < size:
            try:
                chunk_size = min(size - len(data), 8192)
                chunk = self._socket.recv(chunk_size)
                if not chunk:
                    self.logger.warning("Connection closed while receiving data")
                    return None
                data += chunk
            except socket.timeout:
                self.logger.error("Timeout while receiving data")
                return None
            except Exception as e:
                self.logger.error(f"Error receiving data: {e}")
                return None
        
        return data
    
    def _serialize_request(self, request_data: Dict[str, Any]) -> bytes:
        """
        序列化请求数据（默认使用JSON，子类可以重写）
        
        Args:
            request_data: 请求数据
            
        Returns:
            bytes: 序列化后的数据
        """
        # 添加通用字段
        if "request_id" not in request_data:
            request_data["request_id"] = str(uuid.uuid4())
        
        if "timestamp" not in request_data:
            request_data["timestamp"] = int(time.time())
        
        return json.dumps(request_data).encode('utf-8')
    
    def _deserialize_response(self, response_data: bytes) -> Dict[str, Any]:
        """
        反序列化响应数据（默认使用JSON，子类可以重写）
        
        Args:
            response_data: 响应数据
            
        Returns:
            Dict[str, Any]: 反序列化后的响应
        """
        try:
            return json.loads(response_data.decode('utf-8'))
        except Exception as e:
            self.logger.error(f"Error deserializing response: {e}")
            return self._create_error_response("ERR_DESERIALIZATION_FAILED", f"Failed to deserialize response: {e}")
    
    def _create_error_response(self, error_code: str, error_message: str) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "status": "error",
            "error_code": error_code,
            "message": error_message,
            "timestamp": int(time.time())
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        通用健康检查方法
        
        Returns:
            Dict[str, Any]: 健康检查响应
        """
        request = self._build_health_check_request()
        return self.send_request(request)
    
    @abstractmethod
    def _build_health_check_request(self) -> Dict[str, Any]:
        """
        构建健康检查请求（抽象方法）
        子类需要实现此方法来定义具体的健康检查请求格式
        
        Returns:
            Dict[str, Any]: 健康检查请求数据
        """
        pass
    
    def get_server_info(self) -> Dict[str, Any]:
        """
        获取服务器信息的通用方法
        
        Returns:
            Dict[str, Any]: 服务器信息响应
        """
        request = self._build_server_info_request()
        return self.send_request(request)
    
    @abstractmethod
    def _build_server_info_request(self) -> Dict[str, Any]:
        """
        构建服务器信息请求（抽象方法）
        子类需要实现此方法来定义具体的服务器信息请求格式
        
        Returns:
            Dict[str, Any]: 服务器信息请求数据
        """
        pass
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()
    
    def __del__(self):
        """析构函数，确保连接清理"""
        try:
            self.disconnect()
        except:
            pass
