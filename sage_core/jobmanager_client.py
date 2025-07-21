import ray
import socket
import json
import pickle
from ray.actor import ActorHandle
from pathlib import Path
from typing import Optional, Dict, Any
from sage_jobmanager.remote_job_manager import RemoteJobManager
from sage_utils.custom_logger import CustomLogger
from sage_utils.actor_wrapper import ActorWrapper

# ==================== 客户端工具类 ====================

class JobManagerClient:
    """JobManager客户端，用于连接守护服务获取Actor句柄"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 19001):
        self.host = host
        self.port = port
    
    def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """发送请求到守护服务"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(10)
                sock.connect((self.host, self.port))
                
                # 发送请求
                request_data = json.dumps(request).encode('utf-8')
                length_data = len(request_data).to_bytes(4, byteorder='big')
                sock.sendall(length_data + request_data)
                
                # 接收响应
                response_length_data = sock.recv(4)
                response_length = int.from_bytes(response_length_data, byteorder='big')
                
                response_data = b''
                while len(response_data) < response_length:
                    chunk = sock.recv(min(response_length - len(response_data), 8192))
                    response_data += chunk
                
                return json.loads(response_data.decode('utf-8'))
                
        except Exception as e:
            return {"status": "error", "message": f"Connection error: {e}"}
    
    def get_actor_handle(self) -> 'RemoteJobManager':
        """获取JobManager Actor句柄"""
        import uuid
        request = {
            "action": "get_actor_handle",
            "request_id": str(uuid.uuid4())
        }
        if not ray.is_initialized():
            ray.init(address="auto", _temp_dir="/var/lib/ray_shared")

        response = self._send_request(request)
        
        if response.get("status") != "success":
            raise Exception(f"Failed to get actor handle: {response.get('message')}")
        
        # 反序列化Actor句柄
        actor_handle_hex = response.get("actor_handle")
        actor_handle_bytes = bytes.fromhex(actor_handle_hex)
        actor_handle = pickle.loads(actor_handle_bytes)
        jobmanager = ActorWrapper(actor_handle)
        return jobmanager
    
    def get_actor_info(self) -> Dict[str, Any]:
        """获取Actor信息"""
        import uuid
        request = {
            "action": "get_actor_info",
            "request_id": str(uuid.uuid4())
        }
        
        response = self._send_request(request)
        
        if response.get("status") != "success":
            raise Exception(f"Failed to get actor info: {response.get('message')}")
        
        return response.get("actor_info", {})
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        import uuid
        request = {
            "action": "health_check",
            "request_id": str(uuid.uuid4())
        }
        
        return self._send_request(request)
    
    def restart_actor(self) -> Dict[str, Any]:
        """重启Actor"""
        import uuid
        request = {
            "action": "restart_actor", 
            "request_id": str(uuid.uuid4())
        }
        
        return self._send_request(request)