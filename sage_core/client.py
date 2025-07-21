import socket
import pickle
import time
import threading
from typing import Dict, Any, Optional
from sage_utils.custom_logger import CustomLogger


class EngineClient:
    """Engine 客户端，用于 Environment 与 Engine 通信"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 19000, timeout: int = 30):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket: Optional[socket.socket] = None
        self.connected = False
        
        # 响应处理
        self.pending_responses: Dict[str, Dict] = {}  # request_id -> response_info
        self.response_lock = threading.Lock()
        self.listener_thread: Optional[threading.Thread] = None
        self.running = False
        
        self.logger = CustomLogger()

    def connect(self) -> bool:
        """连接到 Engine"""
        try:
            if self.connected:
                return True
                
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            
            self.connected = True
            self.running = True
            
            # 启动响应监听线程
            self.listener_thread = threading.Thread(
                target=self._response_listener,
                name="EngineClientListener",
                daemon=True
            )
            self.listener_thread.start()
            
            self.logger.info(f"Connected to Engine at {self.host}:{self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Engine: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """断开连接"""
        self.running = False
        self.connected = False
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
            
        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.join(timeout=5)
            
        self.logger.info("Disconnected from Engine")
    
    def send_message(self, message_type: str, payload: Dict[str, Any], 
                    env_name: str = None, env_uuid: str = None,
                    wait_for_response: bool = True, timeout: int = None) -> Optional[Dict[str, Any]]:
        """
        发送消息给 Engine
        
        Args:
            message_type: 消息类型
            payload: 消息内容
            env_name: 环境名称
            env_uuid: 环境UUID
            wait_for_response: 是否等待响应
            timeout: 响应超时时间
            
        Returns:
            响应消息（如果 wait_for_response=True）
        """
        if not self.connected and not self.connect():
            raise ConnectionError("Failed to connect to Engine")
        
        # 生成请求ID
        request_id = f"{message_type}_{int(time.time() * 1000000)}"
        
        # 构建消息
        message = {
            "type": message_type,
            "request_id": request_id,
            "env_name": env_name,
            "env_uuid": env_uuid,
            "timestamp": int(time.time()),
            "payload": payload
        }
        
        try:
            # 如果需要等待响应，先注册
            if wait_for_response:
                with self.response_lock:
                    self.pending_responses[request_id] = {
                        "event": threading.Event(),
                        "response": None,
                        "timeout": timeout or self.timeout
                    }
            
            # 发送消息
            self._send_raw_message(message)
            
            if not wait_for_response:
                return None
            
            # 等待响应
            response_info = self.pending_responses[request_id]
            event = response_info["event"]
            
            if event.wait(timeout=response_info["timeout"]):
                response = response_info["response"]
                with self.response_lock:
                    del self.pending_responses[request_id]
                return response
            else:
                # 超时
                with self.response_lock:
                    del self.pending_responses[request_id]
                raise TimeoutError(f"Request {request_id} timed out")
                
        except Exception as e:
            # 清理
            with self.response_lock:
                self.pending_responses.pop(request_id, None)
            self.logger.error(f"Error sending message {message_type}: {e}")
            raise
    
    def _send_raw_message(self, message: Dict[str, Any]):
        """发送原始消息"""
        try:
            # 序列化消息
            serialized = pickle.dumps(message)
            message_size = len(serialized)
            
            # 发送消息长度
            self.socket.send(message_size.to_bytes(4, byteorder='big'))
            
            # 发送消息内容
            self.socket.send(serialized)
            
            self.logger.debug(f"Sent message type: {message.get('type')}")
            
        except Exception as e:
            self.logger.error(f"Error sending raw message: {e}")
            self.connected = False
            raise
    
    def _response_listener(self):
        """响应监听线程"""
        self.logger.debug("Response listener started")
        
        while self.running and self.connected:
            try:
                # 读取消息长度
                size_data = self.socket.recv(4)
                if not size_data:
                    break
                
                message_size = int.from_bytes(size_data, byteorder='big')
                if message_size <= 0 or message_size > 10 * 1024 * 1024:  # 10MB limit
                    self.logger.warning(f"Invalid message size: {message_size}")
                    break
                
                # 读取消息内容
                message_data = self._receive_full_message(message_size)
                if not message_data:
                    break
                
                # 反序列化并处理响应
                response = pickle.loads(message_data)
                self._handle_response(response)
                
            except socket.timeout:
                # 超时异常，继续监听
                if self.running:
                    self.logger.debug("Socket timeout, continuing to listen...")
                continue
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error in response listener: {e}")
                break
        
        self.connected = False
        self.logger.debug("Response listener stopped")
    
    def _receive_full_message(self, message_size: int) -> Optional[bytes]:
        """接收完整消息"""
        message_data = b''
        while len(message_data) < message_size:
            chunk_size = min(message_size - len(message_data), 8192)
            chunk = self.socket.recv(chunk_size)
            if not chunk:
                return None
            message_data += chunk
        return message_data
    
    def _handle_response(self, response: Dict[str, Any]):
        """处理响应消息"""
        request_id = response.get("request_id")
        if not request_id:
            self.logger.warning("Received response without request_id")
            return
        
        with self.response_lock:
            if request_id in self.pending_responses:
                response_info = self.pending_responses[request_id]
                response_info["response"] = response
                response_info["event"].set()
                print("Handled response for request:", response)
                self.logger.debug(f"Handled response for request: {request_id}")
            else:
                self.logger.warning(f"Received unexpected response for request: {request_id}")
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()