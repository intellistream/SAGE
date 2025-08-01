"""
SAGE Queue Descriptor - SAGE高性能队列描述符

支持SAGE高性能队列的创建和管理
"""

from typing import Any, Dict, Optional
import logging
from .queue_descriptor import QueueDescriptor

logger = logging.getLogger(__name__)


class SageQueueDescriptor(QueueDescriptor):
    """
    SAGE高性能队列描述符
    
    支持SAGE队列的高级特性：
    - 高性能内存管理
    - 多租户支持
    - 自动清理
    - 命名空间隔离
    """
    
    def __init__(self, maxsize: int = 1024 * 1024, auto_cleanup: bool = True,
                 namespace: Optional[str] = None, enable_multi_tenant: bool = True,
                 queue_id: Optional[str] = None, queue_instance: Optional[Any] = None):
        """
        初始化SAGE队列描述符
        
        Args:
            maxsize: 队列最大大小（字节）
            auto_cleanup: 是否自动清理
            namespace: 命名空间
            enable_multi_tenant: 是否启用多租户
            queue_id: 队列唯一标识符
            queue_instance: 可选的队列实例
        """
        self.maxsize = maxsize
        self.auto_cleanup = auto_cleanup
        self.namespace = namespace
        self.enable_multi_tenant = enable_multi_tenant
        super().__init__(queue_id=queue_id, queue_instance=queue_instance)
    
    @property
    def queue_type(self) -> str:
        """队列类型标识符"""
        return "sage_queue"
    
    @property
    def can_serialize(self) -> bool:
        """SAGE队列可以序列化"""
        return self._queue_instance is None
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """元数据字典"""
        return {
            "maxsize": self.maxsize,
            "auto_cleanup": self.auto_cleanup,
            "namespace": self.namespace,
            "enable_multi_tenant": self.enable_multi_tenant
        }
    
    def _create_queue_instance(self) -> Any:
        """创建SAGE队列实例"""
        try:
            # 动态导入 SAGE Queue，避免循环依赖
            from sage_ext.sage_queue.python.sage_queue import SageQueue
            
            # 创建或连接到 SAGE Queue
            sage_queue = SageQueue(
                name=self.queue_id,
                maxsize=self.maxsize,
                auto_cleanup=self.auto_cleanup,
                namespace=self.namespace,
                enable_multi_tenant=self.enable_multi_tenant
            )
            
            logger.info(f"Successfully initialized SAGE Queue: {self.queue_id}")
            return sage_queue
            
        except ImportError as e:
            logger.error(f"Failed to import SageQueue: {e}")
            raise RuntimeError(f"SAGE Queue not available: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize SAGE Queue: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        if self._initialized and hasattr(self._queue_instance, 'get_stats'):
            return self._queue_instance.get_stats()
        return {}
    
    def close(self):
        """关闭队列"""
        if self._initialized and hasattr(self._queue_instance, 'close'):
            self._queue_instance.close()
            self._queue_instance = None
            self._initialized = False
    
    def destroy(self):
        """销毁队列"""
        if self._initialized and hasattr(self._queue_instance, 'destroy'):
            self._queue_instance.destroy()
            self._queue_instance = None
            self._initialized = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SageQueueDescriptor':
        """从字典创建实例"""
        metadata = data.get('metadata', {})
        instance = cls(
            maxsize=metadata.get('maxsize', 1024 * 1024),
            auto_cleanup=metadata.get('auto_cleanup', True),
            namespace=metadata.get('namespace'),
            enable_multi_tenant=metadata.get('enable_multi_tenant', True),
            queue_id=data['queue_id']
        )
        instance.created_timestamp = data.get('created_timestamp', instance.created_timestamp)
        return instance


# 便利函数
def create_sage_queue(queue_id: Optional[str] = None, maxsize: int = 1024 * 1024,
                     auto_cleanup: bool = True, namespace: Optional[str] = None,
                     enable_multi_tenant: bool = True) -> SageQueueDescriptor:
    """创建SAGE队列描述符"""
    return SageQueueDescriptor(
        maxsize=maxsize,
        auto_cleanup=auto_cleanup,
        namespace=namespace,
        enable_multi_tenant=enable_multi_tenant,
        queue_id=queue_id
    )
