"""
SAGE Queue Stub - SAGE 高性能队列的封装实现

提供 SAGE Queue 与 Queue Descriptor 之间的转换方法
"""

import logging
from typing import Any, Optional, Dict
from ..queue_descriptor import QueueDescriptor

logger = logging.getLogger(__name__)


class SageQueueStub:
    """
    SAGE Queue 的封装类，实现队列接口
    
    支持与 QueueDescriptor 的双向转换：
    - from_descriptor: 从描述符创建 SAGE Queue 连接
    - to_descriptor: 将现有 SAGE Queue 转换为描述符
    """
    
    def __init__(self, descriptor: QueueDescriptor):
        """
        从 QueueDescriptor 初始化 SAGE Queue
        
        Args:
            descriptor: 队列描述符
        """
        if descriptor.queue_type != "sage_queue":
            raise ValueError(f"Expected sage_queue, got {descriptor.queue_type}")
        
        self.descriptor = descriptor
        self._sage_queue = None
        self._initialize_sage_queue()
    
    def _initialize_sage_queue(self):
        """初始化底层的 SAGE Queue"""
        try:
            # 动态导入 SAGE Queue，避免循环依赖
            from sage_ext.sage_queue.python.sage_queue import SageQueue
            
            # 从描述符元数据中获取参数
            queue_id = self.descriptor.queue_id
            maxsize = self.descriptor.metadata.get('maxsize', 1024 * 1024)
            auto_cleanup = self.descriptor.metadata.get('auto_cleanup', True)
            namespace = self.descriptor.metadata.get('namespace')
            enable_multi_tenant = self.descriptor.metadata.get('enable_multi_tenant', True)
            
            # 创建或连接到 SAGE Queue
            self._sage_queue = SageQueue(
                name=queue_id,
                maxsize=maxsize,
                auto_cleanup=auto_cleanup,
                namespace=namespace,
                enable_multi_tenant=enable_multi_tenant
            )
            
            logger.info(f"Successfully initialized SAGE Queue: {queue_id}")
            
        except ImportError as e:
            logger.error(f"Failed to import SageQueue: {e}")
            raise RuntimeError(f"SAGE Queue not available: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize SAGE Queue: {e}")
            raise
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        """向队列添加元素"""
        if self._sage_queue is None:
            raise RuntimeError("SAGE Queue not initialized")
        
        return self._sage_queue.put(item, block=block, timeout=timeout)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """从队列获取元素"""
        if self._sage_queue is None:
            raise RuntimeError("SAGE Queue not initialized")
        
        return self._sage_queue.get(block=block, timeout=timeout)
    
    def put_nowait(self, item: Any) -> None:
        """非阻塞添加元素"""
        return self.put(item, block=False)
    
    def get_nowait(self) -> Any:
        """非阻塞获取元素"""
        return self.get(block=False)
    
    def empty(self) -> bool:
        """检查队列是否为空"""
        if self._sage_queue is None:
            return True
        return self._sage_queue.empty()
    
    def qsize(self) -> int:
        """获取队列大小"""
        if self._sage_queue is None:
            return 0
        return self._sage_queue.qsize()
    
    def full(self) -> bool:
        """检查队列是否已满"""
        if self._sage_queue is None:
            return False
        return self._sage_queue.full()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        if self._sage_queue is None:
            return {}
        return self._sage_queue.get_stats()
    
    def close(self):
        """关闭队列"""
        if self._sage_queue is not None:
            self._sage_queue.close()
            self._sage_queue = None
    
    def destroy(self):
        """销毁队列"""
        if self._sage_queue is not None:
            self._sage_queue.destroy()
            self._sage_queue = None
    
    def to_descriptor(self) -> QueueDescriptor:
        """
        将当前 SAGE Queue 转换为 QueueDescriptor
        
        Returns:
            对应的队列描述符
        """
        return self.descriptor
    
    @classmethod
    def from_descriptor(cls, descriptor: QueueDescriptor) -> 'SageQueueStub':
        """
        从 QueueDescriptor 创建 SageQueueStub 实例
        
        Args:
            descriptor: 队列描述符
            
        Returns:
            SageQueueStub 实例
        """
        return cls(descriptor)
    
    @classmethod
    def from_sage_queue(cls, sage_queue, queue_id: Optional[str] = None, **metadata) -> 'SageQueueStub':
        """
        从现有的 SAGE Queue 对象创建 SageQueueStub
        
        Args:
            sage_queue: 现有的 SAGE Queue 对象
            queue_id: 队列ID，如果为None则使用 sage_queue 的名称
            **metadata: 额外的元数据
            
        Returns:
            SageQueueStub 实例
        """
        if queue_id is None:
            queue_id = getattr(sage_queue, 'name', f"sage_{id(sage_queue)}")
        
        # 提取 SAGE Queue 的配置信息
        default_metadata = {
            'maxsize': getattr(sage_queue, 'maxsize', 1024 * 1024),
            'auto_cleanup': getattr(sage_queue, 'auto_cleanup', True),
            'namespace': getattr(sage_queue, 'namespace', None),
            'enable_multi_tenant': getattr(sage_queue, 'enable_multi_tenant', True)
        }
        
        # 合并用户提供的元数据
        default_metadata.update(metadata)
        
        # 创建描述符
        descriptor = QueueDescriptor(
            queue_id=queue_id,
            queue_type="sage_queue",
            metadata=default_metadata
        )
        
        # 创建 stub 实例
        stub = cls(descriptor)
        
        # 直接使用传入的 sage_queue 对象，而不是重新创建
        stub._sage_queue = sage_queue
        
        return stub
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def __repr__(self) -> str:
        return f"SageQueueStub(queue_id='{self.descriptor.queue_id}', type='{self.descriptor.queue_type}')"


# 便利函数
def create_sage_queue_descriptor(queue_id: Optional[str] = None, 
                                maxsize: int = 1024 * 1024,
                                auto_cleanup: bool = True,
                                namespace: Optional[str] = None,
                                enable_multi_tenant: bool = True) -> QueueDescriptor:
    """
    创建 SAGE Queue 描述符的便利函数
    
    Args:
        queue_id: 队列ID
        maxsize: 最大大小
        auto_cleanup: 是否自动清理
        namespace: 命名空间
        enable_multi_tenant: 是否启用多租户
        
    Returns:
        SAGE Queue 描述符
    """
    return QueueDescriptor.create_sage_queue(
        queue_id=queue_id,
        maxsize=maxsize,
        auto_cleanup=auto_cleanup,
        namespace=namespace,
        enable_multi_tenant=enable_multi_tenant
    )


def sage_queue_from_descriptor(descriptor: QueueDescriptor) -> SageQueueStub:
    """
    从描述符创建 SAGE Queue 的便利函数
    
    Args:
        descriptor: 队列描述符
        
    Returns:
        SageQueueStub 实例
    """
    return SageQueueStub.from_descriptor(descriptor)
