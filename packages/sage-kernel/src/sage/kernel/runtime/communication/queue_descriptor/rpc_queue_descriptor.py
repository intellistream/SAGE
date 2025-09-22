"""
RPC Queue Descriptor - RPC队列描述符

支持基于RPC的远程队列创建和管理
"""

from typing import Any, Dict, Optional
import logging
from .base_queue_descriptor import BaseQueueDescriptor

logger = logging.getLogger(__name__)


class RPCQueueDescriptor(BaseQueueDescriptor):
    """
    RPC队列描述符
    
    支持基于RPC的远程队列：
    - TCP连接
    - 远程队列访问
    - 连接池管理
    - 自动重连
    """
    
    def __init__(self, host: str = "localhost", port: int = 8000,
                 connection_timeout: float = 30.0, retry_count: int = 3,
                 enable_pooling: bool = True, queue_id: Optional[str] = None):
        """
        初始化RPC队列描述符
        
        Args:
            host: RPC服务器主机
            port: RPC服务器端口
            connection_timeout: 连接超时时间（秒）
            retry_count: 重试次数
            enable_pooling: 是否启用连接池
            queue_id: 队列唯一标识符
        """
        self.host = host
        self.port = port
        self.connection_timeout = connection_timeout
        self.retry_count = retry_count
        self.enable_pooling = enable_pooling
        super().__init__(queue_id=queue_id)
    
    @property
    def queue_type(self) -> str:
        """队列类型标识符"""
        return "rpc_queue"
    
    @property
    def can_serialize(self) -> bool:
        """RPC队列可以序列化"""
        return self._queue_instance is None
    
    @property
    def queue_instance(self) -> Optional[Any]:
        """获取队列实例（实现抽象方法）"""
        if not self._initialized:
            self._queue_instance = self._create_queue_instance()
            self._initialized = True
        return self._queue_instance
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """元数据字典"""
        return {
            "host": self.host,
            "port": self.port,
            "connection_timeout": self.connection_timeout,
            "retry_count": self.retry_count,
            "enable_pooling": self.enable_pooling
        }
    
    def _create_queue_instance(self) -> Any:
        """创建RPC队列实例"""
        try:
            # 动态导入 RPC Queue，避免循环依赖
            from sage.kernel.runtime.communication.rpc.rpc_queue import RPCQueue
            
            # 创建RPC Queue客户端
            rpc_queue = RPCQueue(
                queue_id=self.queue_id,
                host=self.host,
                port=self.port,
                connection_timeout=self.connection_timeout,
                retry_count=self.retry_count,
                enable_pooling=self.enable_pooling
            )
            
            logger.info(f"Successfully initialized RPC Queue: {self.queue_id} at {self.host}:{self.port}")
            return rpc_queue
            
        except ImportError as e:
            logger.error(f"Failed to import RPCQueue: {e}")
            raise RuntimeError(f"RPC Queue not available: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize RPC Queue: {e}")
            raise
    
    def get_connection_status(self) -> Dict[str, Any]:
        """获取连接状态"""
        if self._initialized and hasattr(self._queue_instance, 'get_connection_status'):
            return self._queue_instance.get_connection_status()
        return {"connected": False}
    
    def reconnect(self):
        """重新连接"""
        if self._initialized and hasattr(self._queue_instance, 'reconnect'):
            self._queue_instance.reconnect()
    
    def close(self):
        """关闭连接"""
        if self._initialized and hasattr(self._queue_instance, 'close'):
            self._queue_instance.close()
            self._queue_instance = None
            self._initialized = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RPCQueueDescriptor':
        """从字典创建实例"""
        metadata = data.get('metadata', {})
        instance = cls(
            host=metadata.get('host', 'localhost'),
            port=metadata.get('port', 8000),
            connection_timeout=metadata.get('connection_timeout', 30.0),
            retry_count=metadata.get('retry_count', 3),
            enable_pooling=metadata.get('enable_pooling', True),
            queue_id=data['queue_id']
        )
        instance.created_timestamp = data.get('created_timestamp', instance.created_timestamp)
        return instance
