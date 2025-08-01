"""
RPC Queue Descriptor - RPC队列描述符

用于管理远程过程调用(RPC)环境中的队列
"""

import uuid
from typing import Any, Dict, Optional, List
from .base_descriptor import BaseQueueDescriptor, QueueLike, register_descriptor_class
import logging

logger = logging.getLogger(__name__)


class RpcQueueDescriptor(BaseQueueDescriptor):
    """
    RPC队列描述符
    
    特点：
    - 支持远程过程调用
    - 可序列化
    - 支持多种RPC协议 (gRPC, HTTP, TCP等)
    - 支持懒加载
    """
    
    def __init__(self, queue_id: str, endpoint: str, protocol: str = "grpc",
                 timeout: int = 30, **extra_metadata):
        """
        初始化RPC队列描述符
        
        Args:
            queue_id: 队列ID
            endpoint: RPC端点地址
            protocol: RPC协议类型 (grpc, http, tcp等)
            timeout: 请求超时时间(秒)
            **extra_metadata: 额外的元数据
        """
        metadata = {
            'endpoint': endpoint,
            'protocol': protocol,
            'timeout': timeout,
            **extra_metadata
        }
        
        super().__init__(
            queue_id=queue_id,
            queue_type="rpc",
            metadata=metadata,
            can_serialize=True
        )
        
        logger.info(f"RpcQueueDescriptor '{queue_id}' created for endpoint '{endpoint}' "
                   f"with protocol '{protocol}'")
    
    def _validate_descriptor(self):
        """验证RPC队列描述符"""
        super()._validate_descriptor()
        if not self.metadata.get('endpoint'):
            raise ValueError("endpoint is required for RPC queue")
        
        protocol = self.metadata.get('protocol', 'grpc')
        supported_protocols = ['grpc', 'http', 'tcp', 'websocket']
        if protocol not in supported_protocols:
            raise ValueError(f"Unsupported protocol '{protocol}'. "
                           f"Supported: {supported_protocols}")
    
    def create_queue(self) -> QueueLike:
        """创建RPC队列对象"""
        endpoint = self.metadata['endpoint']
        protocol = self.metadata.get('protocol', 'grpc')
        timeout = self.metadata.get('timeout', 30)
        
        # 这里应该实现真正的RPC队列
        # 目前使用存根实现
        from ..queue_stubs.rpc_queue_stub import RpcQueueStub
        
        # 创建一个临时的描述符用于存根
        temp_descriptor = type('TempDescriptor', (), {
            'queue_id': self.queue_id,
            'queue_type': self.queue_type,
            'metadata': self.metadata
        })()
        
        queue_obj = RpcQueueStub(temp_descriptor)
        
        logger.info(f"Created RPC queue '{self.queue_id}' "
                   f"with endpoint='{endpoint}', protocol='{protocol}', timeout={timeout}")
        return queue_obj
    
    def get_rpc_info(self) -> Dict[str, Any]:
        """获取RPC相关信息"""
        return {
            'endpoint': self.metadata['endpoint'],
            'protocol': self.metadata.get('protocol', 'grpc'),
            'timeout': self.metadata.get('timeout', 30),
            'queue_id': self.queue_id,
            'initialized': self._initialized
        }
    
    def update_endpoint(self, new_endpoint: str):
        """更新RPC端点"""
        old_endpoint = self.metadata['endpoint']
        self.metadata['endpoint'] = new_endpoint
        logger.info(f"Updated endpoint from '{old_endpoint}' to '{new_endpoint}' "
                   f"for queue '{self.queue_id}'")
    
    def __repr__(self) -> str:
        status = "initialized" if self._initialized else "lazy"
        endpoint = self.metadata.get('endpoint', 'unknown')
        protocol = self.metadata.get('protocol', 'grpc')
        return f"RpcQueueDescriptor(id='{self.queue_id}', endpoint='{endpoint}', protocol='{protocol}', {status})"


class GrpcQueueDescriptor(RpcQueueDescriptor):
    """
    gRPC队列描述符
    
    专门用于gRPC协议的队列，提供gRPC特定的配置选项
    """
    
    def __init__(self, queue_id: str, endpoint: str, 
                 service_name: str, method_name: str = "QueueService",
                 credentials: Optional[Dict[str, Any]] = None, 
                 timeout: int = 30, **extra_metadata):
        """
        初始化gRPC队列描述符
        
        Args:
            queue_id: 队列ID
            endpoint: gRPC端点地址
            service_name: gRPC服务名称
            method_name: gRPC方法名称
            credentials: gRPC认证信息
            timeout: 请求超时时间(秒)
            **extra_metadata: 额外的元数据
        """
        extra_metadata.update({
            'service_name': service_name,
            'method_name': method_name,
            'credentials': credentials or {}
        })
        
        super().__init__(
            queue_id=queue_id,
            endpoint=endpoint,
            protocol="grpc",
            timeout=timeout,
            **extra_metadata
        )
    
    def get_service_info(self) -> Dict[str, Any]:
        """获取gRPC服务信息"""
        return {
            'service_name': self.metadata['service_name'],
            'method_name': self.metadata.get('method_name', 'QueueService'),
            'has_credentials': bool(self.metadata.get('credentials'))
        }
    
    def __repr__(self) -> str:
        status = "initialized" if self._initialized else "lazy"
        endpoint = self.metadata.get('endpoint', 'unknown')
        service = self.metadata.get('service_name', 'unknown')
        return f"GrpcQueueDescriptor(id='{self.queue_id}', endpoint='{endpoint}', service='{service}', {status})"


class HttpQueueDescriptor(RpcQueueDescriptor):
    """
    HTTP队列描述符
    
    专门用于HTTP协议的队列，支持RESTful API风格的队列操作
    """
    
    def __init__(self, queue_id: str, base_url: str,
                 headers: Optional[Dict[str, str]] = None,
                 auth_token: Optional[str] = None,
                 timeout: int = 30, **extra_metadata):
        """
        初始化HTTP队列描述符
        
        Args:
            queue_id: 队列ID
            base_url: HTTP基础URL
            headers: HTTP请求头
            auth_token: 认证令牌
            timeout: 请求超时时间(秒)
            **extra_metadata: 额外的元数据
        """
        if headers is None:
            headers = {'Content-Type': 'application/json'}
        
        extra_metadata.update({
            'headers': headers,
            'auth_token': auth_token,
            'base_url': base_url
        })
        
        super().__init__(
            queue_id=queue_id,
            endpoint=base_url,
            protocol="http",
            timeout=timeout,
            **extra_metadata
        )
    
    def get_http_info(self) -> Dict[str, Any]:
        """获取HTTP相关信息"""
        return {
            'base_url': self.metadata['base_url'],
            'headers': self.metadata.get('headers', {}),
            'has_auth_token': bool(self.metadata.get('auth_token')),
            'timeout': self.metadata.get('timeout', 30)
        }
    
    def update_auth_token(self, token: str):
        """更新认证令牌"""
        self.metadata['auth_token'] = token
        logger.info(f"Updated auth token for HTTP queue '{self.queue_id}'")
    
    def __repr__(self) -> str:
        status = "initialized" if self._initialized else "lazy"
        base_url = self.metadata.get('base_url', 'unknown')
        has_auth = "with auth" if self.metadata.get('auth_token') else "no auth"
        return f"HttpQueueDescriptor(id='{self.queue_id}', url='{base_url}', {has_auth}, {status})"


class WebSocketQueueDescriptor(RpcQueueDescriptor):
    """
    WebSocket队列描述符
    
    专门用于WebSocket协议的队列，支持实时双向通信
    """
    
    def __init__(self, queue_id: str, ws_url: str,
                 subprotocols: Optional[List[str]] = None,
                 ping_interval: int = 30, ping_timeout: int = 10,
                 **extra_metadata):
        """
        初始化WebSocket队列描述符
        
        Args:
            queue_id: 队列ID
            ws_url: WebSocket URL
            subprotocols: WebSocket子协议列表
            ping_interval: ping间隔时间(秒)
            ping_timeout: ping超时时间(秒)
            **extra_metadata: 额外的元数据
        """
        extra_metadata.update({
            'subprotocols': subprotocols or [],
            'ping_interval': ping_interval,
            'ping_timeout': ping_timeout
        })
        
        super().__init__(
            queue_id=queue_id,
            endpoint=ws_url,
            protocol="websocket",
            timeout=ping_timeout,
            **extra_metadata
        )
    
    def get_websocket_info(self) -> Dict[str, Any]:
        """获取WebSocket相关信息"""
        return {
            'ws_url': self.metadata['endpoint'],
            'subprotocols': self.metadata.get('subprotocols', []),
            'ping_interval': self.metadata.get('ping_interval', 30),
            'ping_timeout': self.metadata.get('ping_timeout', 10)
        }
    
    def __repr__(self) -> str:
        status = "initialized" if self._initialized else "lazy"
        ws_url = self.metadata.get('endpoint', 'unknown')
        protocols = len(self.metadata.get('subprotocols', []))
        return f"WebSocketQueueDescriptor(id='{self.queue_id}', url='{ws_url}', protocols={protocols}, {status})"


# 工厂函数
def create_rpc_queue_descriptor(endpoint: str, protocol: str = "grpc",
                               queue_id: Optional[str] = None,
                               timeout: int = 30,
                               **extra_metadata) -> RpcQueueDescriptor:
    """
    创建RPC队列描述符
    
    Args:
        endpoint: RPC端点地址
        protocol: RPC协议类型
        queue_id: 队列ID，如果为None则自动生成
        timeout: 请求超时时间(秒)
        **extra_metadata: 额外的元数据
        
    Returns:
        RPC队列描述符
    """
    if queue_id is None:
        queue_id = f"rpc_{uuid.uuid4().hex[:8]}"
    
    return RpcQueueDescriptor(
        queue_id=queue_id,
        endpoint=endpoint,
        protocol=protocol,
        timeout=timeout,
        **extra_metadata
    )


def create_grpc_queue_descriptor(endpoint: str, service_name: str,
                                queue_id: Optional[str] = None,
                                method_name: str = "QueueService",
                                credentials: Optional[Dict[str, Any]] = None,
                                timeout: int = 30,
                                **extra_metadata) -> GrpcQueueDescriptor:
    """
    创建gRPC队列描述符
    
    Args:
        endpoint: gRPC端点地址
        service_name: gRPC服务名称
        queue_id: 队列ID，如果为None则自动生成
        method_name: gRPC方法名称
        credentials: gRPC认证信息
        timeout: 请求超时时间(秒)
        **extra_metadata: 额外的元数据
        
    Returns:
        gRPC队列描述符
    """
    if queue_id is None:
        queue_id = f"grpc_{uuid.uuid4().hex[:8]}"
    
    return GrpcQueueDescriptor(
        queue_id=queue_id,
        endpoint=endpoint,
        service_name=service_name,
        method_name=method_name,
        credentials=credentials,
        timeout=timeout,
        **extra_metadata
    )


def create_http_queue_descriptor(base_url: str,
                                queue_id: Optional[str] = None,
                                headers: Optional[Dict[str, str]] = None,
                                auth_token: Optional[str] = None,
                                timeout: int = 30,
                                **extra_metadata) -> HttpQueueDescriptor:
    """
    创建HTTP队列描述符
    
    Args:
        base_url: HTTP基础URL
        queue_id: 队列ID，如果为None则自动生成
        headers: HTTP请求头
        auth_token: 认证令牌
        timeout: 请求超时时间(秒)
        **extra_metadata: 额外的元数据
        
    Returns:
        HTTP队列描述符
    """
    if queue_id is None:
        queue_id = f"http_{uuid.uuid4().hex[:8]}"
    
    return HttpQueueDescriptor(
        queue_id=queue_id,
        base_url=base_url,
        headers=headers,
        auth_token=auth_token,
        timeout=timeout,
        **extra_metadata
    )


def create_websocket_queue_descriptor(ws_url: str,
                                     queue_id: Optional[str] = None,
                                     subprotocols: Optional[List[str]] = None,
                                     ping_interval: int = 30,
                                     ping_timeout: int = 10,
                                     **extra_metadata) -> WebSocketQueueDescriptor:
    """
    创建WebSocket队列描述符
    
    Args:
        ws_url: WebSocket URL
        queue_id: 队列ID，如果为None则自动生成
        subprotocols: WebSocket子协议列表
        ping_interval: ping间隔时间(秒)
        ping_timeout: ping超时时间(秒)
        **extra_metadata: 额外的元数据
        
    Returns:
        WebSocket队列描述符
    """
    if queue_id is None:
        queue_id = f"ws_{uuid.uuid4().hex[:8]}"
    
    return WebSocketQueueDescriptor(
        queue_id=queue_id,
        ws_url=ws_url,
        subprotocols=subprotocols,
        ping_interval=ping_interval,
        ping_timeout=ping_timeout,
        **extra_metadata
    )


# 注册描述符类
register_descriptor_class("rpc", RpcQueueDescriptor)
register_descriptor_class("grpc", GrpcQueueDescriptor)
register_descriptor_class("http", HttpQueueDescriptor)
register_descriptor_class("websocket", WebSocketQueueDescriptor)
