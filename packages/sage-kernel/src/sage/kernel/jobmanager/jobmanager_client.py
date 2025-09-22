import base64
import uuid
from typing import Dict, Any
from sage.common.utils.network.base_tcp_client import BaseTcpClient

# ==================== 客户端工具类 ====================

class JobManagerClient(BaseTcpClient):
    """JobManager客户端，专门用于发送序列化数据"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 19001, timeout: float = 30.0):
        # 验证端口范围
        if not (1 <= port <= 65535):
            raise ValueError(f"Port must be between 1 and 65535, got {port}")
        
        # 验证超时时间
        if timeout <= 0:
            raise ValueError(f"Timeout must be positive, got {timeout}")
        
        super().__init__(host, port, timeout, "JobManagerClient")
    
    def _build_health_check_request(self) -> Dict[str, Any]:
        """构建健康检查请求"""
        return {
            "action": "health_check",
            "request_id": str(uuid.uuid4())
        }
    
    def _build_server_info_request(self) -> Dict[str, Any]:
        """构建服务器信息请求"""
        return {
            "action": "get_server_info",
            "request_id": str(uuid.uuid4())
        }
    
    def submit_job(self, serialized_data: bytes) -> Dict[str, Any]:
        """提交序列化的作业数据"""
        # 验证输入参数
        if serialized_data is None:
            raise ValueError("Serialized data cannot be None")
        if isinstance(serialized_data, bytes) and len(serialized_data) == 0:
            raise ValueError("Serialized data cannot be empty")
        
        request = {
            "action": "submit_job",
            "request_id": str(uuid.uuid4()),
            "serialized_data": base64.b64encode(serialized_data).decode('utf-8')
        }
        
        return self.send_request(request)
    
    def pause_job(self, job_uuid: str) -> Dict[str, Any]:
        """暂停/停止作业"""
        # 验证输入参数
        if job_uuid is None:
            raise ValueError("Job UUID cannot be None")
        if job_uuid == "":
            raise ValueError("Job UUID cannot be empty")
        
        request = {
            "action": "pause_job",
            "request_id": str(uuid.uuid4()),
            "job_uuid": job_uuid
        }
        
        return self.send_request(request)
    
    def get_job_status(self, job_uuid: str) -> Dict[str, Any]:
        """获取作业状态"""
        request = {
            "action": "get_job_status", 
            "request_id": str(uuid.uuid4()),
            "job_uuid": job_uuid
        }
        
        return self.send_request(request)
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        request = self._build_health_check_request()
        return self.send_request(request)
    
    def get_server_info(self) -> Dict[str, Any]:
        """获取服务器信息"""
        request = self._build_server_info_request()
        return self.send_request(request)
    
    def list_jobs(self) -> Dict[str, Any]:
        """获取作业列表"""
        request = {
            "action": "list_jobs",
            "request_id": str(uuid.uuid4())
        }
        
        return self.send_request(request)
    
    def continue_job(self, job_uuid: str) -> Dict[str, Any]:
        """继续作业"""
        request = {
            "action": "continue_job",
            "request_id": str(uuid.uuid4()),
            "job_uuid": job_uuid
        }
        
        return self.send_request(request)
    
    def delete_job(self, job_uuid: str, force: bool = False) -> Dict[str, Any]:
        """删除作业"""
        request = {
            "action": "delete_job",
            "request_id": str(uuid.uuid4()),
            "job_uuid": job_uuid,
            "force": force
        }
        
        return self.send_request(request)
    
    def receive_node_stop_signal(self, job_uuid: str, node_name: str) -> Dict[str, Any]:
        """发送节点停止信号"""
        request = {
            "action": "receive_node_stop_signal",
            "request_id": str(uuid.uuid4()),
            "job_uuid": job_uuid,
            "node_name": node_name
        }
        
        return self.send_request(request)
    
    def cleanup_all_jobs(self) -> Dict[str, Any]:
        """清理所有作业"""
        request = {
            "action": "cleanup_all_jobs",
            "request_id": str(uuid.uuid4())
        }
        
        return self.send_request(request)

    def _retry_request(self, request: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        """重试请求机制"""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return self.send_request(request)
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    # 等待一段时间后重试
                    import time
                    time.sleep(0.5 * (attempt + 1))
                    continue
                else:
                    # 最后一次尝试失败，抛出异常
                    raise last_exception
        
        # 理论上不会到达这里
        raise last_exception if last_exception else Exception("Retry failed")
