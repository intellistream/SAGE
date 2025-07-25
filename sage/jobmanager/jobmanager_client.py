import socket
import json
import uuid
from typing import Optional, Dict, Any

# ==================== 客户端工具类 ====================

class JobManagerClient:
    """简化的JobManager客户端，专门用于发送序列化数据"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 19001):
        self.host = host
        self.port = port
    
    def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """发送请求到守护服务"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(30)
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
    
    def submit_job(self, serialized_data: bytes) -> Dict[str, Any]:
        """提交序列化的作业数据"""
        import base64
        request = {
            "action": "submit_job",
            "request_id": str(uuid.uuid4()),
            "serialized_data": base64.b64encode(serialized_data).decode('utf-8')
        }
        
        return self._send_request(request)
    
    def pause_job(self, job_uuid: str) -> Dict[str, Any]:
        """暂停/停止作业"""
        request = {
            "action": "pause_job",
            "request_id": str(uuid.uuid4()),
            "job_uuid": job_uuid
        }
        
        return self._send_request(request)
    
    def get_job_status(self, job_uuid: str) -> Dict[str, Any]:
        """获取作业状态"""
        request = {
            "action": "get_job_status", 
            "request_id": str(uuid.uuid4()),
            "job_uuid": job_uuid
        }
        
        return self._send_request(request)
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        request = {
            "action": "health_check",
            "request_id": str(uuid.uuid4())
        }
        
        return self._send_request(request)
    
    def list_jobs(self) -> Dict[str, Any]:
        """获取作业列表"""
        request = {
            "action": "list_jobs",
            "request_id": str(uuid.uuid4())
        }
        
        return self._send_request(request)
    
    def continue_job(self, job_uuid: str) -> Dict[str, Any]:
        """继续作业"""
        request = {
            "action": "continue_job",
            "request_id": str(uuid.uuid4()),
            "job_uuid": job_uuid
        }
        
        return self._send_request(request)
    
    def delete_job(self, job_uuid: str, force: bool = False) -> Dict[str, Any]:
        """删除作业"""
        request = {
            "action": "delete_job",
            "request_id": str(uuid.uuid4()),
            "job_uuid": job_uuid,
            "force": force
        }
        
        return self._send_request(request)
    
    def get_server_info(self) -> Dict[str, Any]:
        """获取服务器信息"""
        request = {
            "action": "get_server_info",
            "request_id": str(uuid.uuid4())
        }
        
        return self._send_request(request)
    
    def cleanup_all_jobs(self) -> Dict[str, Any]:
        """清理所有作业"""
        request = {
            "action": "cleanup_all_jobs",
            "request_id": str(uuid.uuid4())
        }
        
        return self._send_request(request)
