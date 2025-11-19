"""RPC Queue Descriptor - RPC队列描述符

Layer: L2 (Platform Services - Queue Descriptors)

支持基于RPC的远程队列创建和管理。

Architecture:
- L2层仅定义描述符和参数
- 实际的RPCQueue实现由L3层提供
- 使用工厂注册模式避免直接依赖
"""

import logging
from typing import Any, Callable, Optional

from .base_queue_descriptor import BaseQueueDescriptor

logger = logging.getLogger(__name__)

# 工厂函数类型定义
QueueFactory = Callable[..., Any]

# 全局工厂注册表 - 由L3层注册实现
_rpc_queue_factory: Optional[QueueFactory] = None


def register_rpc_queue_factory(factory: QueueFactory) -> None:
    """注册RPC队列工厂函数

    This function should be called by sage-kernel (L3) to register
    the concrete RPCQueue implementation.

    Args:
        factory: Factory function that creates RPCQueue instances
            Signature: factory(queue_id, host, port, ...) -> RPCQueue
    """
    global _rpc_queue_factory
    _rpc_queue_factory = factory
    logger.info("RPC queue factory registered successfully")


class RPCQueueDescriptor(BaseQueueDescriptor):
    """RPC队列描述符

    支持基于RPC的远程队列：
    - TCP连接
    - 远程队列访问
    - 连接池管理
    - 自动重连

    Architecture Note:
    This descriptor (L2) does not import RPCQueue (L3) directly.
    Instead, it uses a factory pattern where L3 registers the implementation.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        connection_timeout: float = 30.0,
        retry_count: int = 3,
        enable_pooling: bool = True,
        queue_id: Optional[str] = None,
    ):
        """初始化RPC队列描述符

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
    def metadata(self) -> dict[str, Any]:
        """元数据字典"""
        return {
            "host": self.host,
            "port": self.port,
            "connection_timeout": self.connection_timeout,
            "retry_count": self.retry_count,
            "enable_pooling": self.enable_pooling,
        }

    def _create_queue_instance(self) -> Any:
        """创建RPC队列实例

        使用工厂模式创建实例，避免直接依赖sage-kernel。
        """
        if _rpc_queue_factory is None:
            raise RuntimeError(
                "RPC queue factory not registered. "
                "Please ensure sage-kernel is imported and initialized. "
                "The factory should be registered via: "
                "from sage.kernel.runtime.communication.rpc import register_with_platform"
            )

        try:
            # 使用注册的工厂函数创建队列实例
            rpc_queue = _rpc_queue_factory(
                queue_id=self.queue_id,
                host=self.host,
                port=self.port,
                connection_timeout=self.connection_timeout,
                retry_count=self.retry_count,
                enable_pooling=self.enable_pooling,
            )

            logger.info(
                f"Successfully initialized RPC Queue: {self.queue_id} at {self.host}:{self.port}"
            )
            return rpc_queue

        except Exception as e:
            logger.error(f"Failed to initialize RPC Queue: {e}")
            raise RuntimeError(f"RPC Queue initialization failed: {e}") from e

    def get_connection_status(self) -> dict[str, Any]:
        """获取连接状态"""
        if (
            self._initialized
            and self._queue_instance is not None
            and hasattr(self._queue_instance, "get_connection_status")
        ):
            return self._queue_instance.get_connection_status()
        return {"connected": False}

    def reconnect(self) -> None:
        """重新连接"""
        if (
            self._initialized
            and self._queue_instance is not None
            and hasattr(self._queue_instance, "reconnect")
        ):
            self._queue_instance.reconnect()

    def close(self) -> None:
        """关闭连接"""
        if (
            self._initialized
            and self._queue_instance is not None
            and hasattr(self._queue_instance, "close")
        ):
            self._queue_instance.close()
            self._queue_instance = None
            self._initialized = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RPCQueueDescriptor":
        """从字典创建实例"""
        metadata = data.get("metadata", {})
        instance = cls(
            host=metadata.get("host", "localhost"),
            port=metadata.get("port", 8000),
            connection_timeout=metadata.get("connection_timeout", 30.0),
            retry_count=metadata.get("retry_count", 3),
            enable_pooling=metadata.get("enable_pooling", True),
            queue_id=data["queue_id"],
        )
        instance.created_timestamp = data.get("created_timestamp", instance.created_timestamp)
        return instance

    def clone(self, new_queue_id: Optional[str] = None) -> "RPCQueueDescriptor":
        """克隆描述符（共享队列实例以避免竞态条件）

        重要：如果原描述符已初始化队列实例，克隆体将共享同一个队列实例。
        这对于服务通信至关重要 - 服务端和客户端必须使用相同的队列实例，
        否则会导致间歇性超时（竞态条件）。

        Args:
            new_queue_id: 新的队列ID，如果为None则自动生成

        Returns:
            新的描述符实例，如果原实例已初始化则共享队列实例
        """
        # 创建同类型的新实例
        cloned = RPCQueueDescriptor(
            host=self.host,
            port=self.port,
            connection_timeout=self.connection_timeout,
            retry_count=self.retry_count,
            enable_pooling=self.enable_pooling,
            queue_id=new_queue_id,
        )

        # 【关键修复】共享队列实例，避免竞态条件
        # 如果原描述符已经初始化了队列实例，克隆体应该共享同一个实例
        # 这确保服务端和客户端使用相同的队列，防止响应丢失
        if self._initialized:
            cloned._queue_instance = self._queue_instance
            cloned._initialized = True

        return cloned
