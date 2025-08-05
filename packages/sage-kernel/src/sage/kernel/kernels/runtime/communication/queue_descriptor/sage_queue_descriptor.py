"""
SAGE Queue Descriptor - SAGE高性能队列描述符

支持SAGE高性能队列的创建和管理
"""

from typing import Any, Dict, Optional
import logging
from .base_queue_descriptor import BaseQueueDescriptor


class SageQueueDescriptor(BaseQueueDescriptor):
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
                 queue_id: Optional[str] = None):
        """
        初始化SAGE队列描述符
        
        Args:
            maxsize: 队列最大大小（字节）
            auto_cleanup: 是否自动清理
            namespace: 命名空间
            enable_multi_tenant: 是否启用多租户
            queue_id: 队列唯一标识符
        """
        self.maxsize = maxsize
        self.auto_cleanup = auto_cleanup
        self.namespace = namespace
        self.enable_multi_tenant = enable_multi_tenant
        super().__init__(queue_id=queue_id)
    
    @property
    def queue_type(self) -> str:
        """队列类型标识符"""
        return "sage_queue"
    
    @property
    def can_serialize(self) -> bool:
        """SAGE队列可以序列化"""
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
            "maxsize": self.maxsize,
            "auto_cleanup": self.auto_cleanup,
            "namespace": self.namespace,
            "enable_multi_tenant": self.enable_multi_tenant
        }
    
    @property
    def logger(self):
        """获取日志记录器"""
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(f"SageQueueDescriptor.{self.queue_id}")
            self._logger.setLevel(logging.INFO)
        return self._logger

    def _create_queue_instance(self) -> Any:
        """创建SAGE队列实例"""
        try:
            # 动态导入 SAGE Queue，避免循环依赖
            from sage.extensions.sage_queue.python.sage_queue import SageQueue
            import threading
            
            # 检查是否在主线程中
            is_main_thread = threading.current_thread() is threading.main_thread()
            
            # 创建或连接到 SAGE Queue
            sage_queue = SageQueue(
                name=self.queue_id,
                maxsize=self.maxsize,
                auto_cleanup=self.auto_cleanup,
                namespace=self.namespace,
                enable_multi_tenant=self.enable_multi_tenant
            )
            
            self.logger.info(f"Successfully initialized SAGE Queue: {self.queue_id} (main_thread: {is_main_thread})")
            return sage_queue
            
        except ImportError as e:
            self.logger.error(f"Failed to import SageQueue: {e}")
            raise RuntimeError(f"SAGE Queue not available: {e}")

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
