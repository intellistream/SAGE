"""
Local Queue Stub - 本地进程内队列的封装实现

提供标准 Python Queue 与 Queue Descriptor 之间的转换方法
"""

import logging
from typing import Any, Optional, Dict
from queue import Queue, Empty, Full
from ..queue_descriptor import QueueDescriptor, QueueLike

logger = logging.getLogger(__name__)


class LocalQueueStub:
    """
    本地 Queue 的封装类，实现 QueueLike 接口
    
    封装标准 Python queue.Queue，支持与 QueueDescriptor 的双向转换
    """
    
    def __init__(self, descriptor: QueueDescriptor):
        """
        从 QueueDescriptor 初始化本地队列
        
        Args:
            descriptor: 队列描述符
        """
        if descriptor.queue_type != "local":
            raise ValueError(f"Expected local, got {descriptor.queue_type}")
        
        self.descriptor = descriptor
        maxsize = descriptor.metadata.get('maxsize', 0)
        self._queue = Queue(maxsize=maxsize)
        
        logger.info(f"Successfully initialized local queue: {descriptor.queue_id}")
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        """向队列添加元素"""
        return self._queue.put(item, block=block, timeout=timeout)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """从队列获取元素"""
        return self._queue.get(block=block, timeout=timeout)
    
    def put_nowait(self, item: Any) -> None:
        """非阻塞添加元素"""
        return self._queue.put_nowait(item)
    
    def get_nowait(self) -> Any:
        """非阻塞获取元素"""
        return self._queue.get_nowait()
    
    def empty(self) -> bool:
        """检查队列是否为空"""
        return self._queue.empty()
    
    def qsize(self) -> int:
        """获取队列大小"""
        return self._queue.qsize()
    
    def full(self) -> bool:
        """检查队列是否已满"""
        return self._queue.full()
    
    def to_descriptor(self) -> QueueDescriptor:
        """
        将当前本地队列转换为 QueueDescriptor
        
        Returns:
            对应的队列描述符
        """
        return self.descriptor
    
    @classmethod
    def from_descriptor(cls, descriptor: QueueDescriptor) -> 'LocalQueueStub':
        """
        从 QueueDescriptor 创建 LocalQueueStub 实例
        
        Args:
            descriptor: 队列描述符
            
        Returns:
            LocalQueueStub 实例
        """
        return cls(descriptor)
    
    @classmethod
    def from_queue(cls, queue: Queue, queue_id: Optional[str] = None, **metadata) -> 'LocalQueueStub':
        """
        从现有的 Queue 对象创建 LocalQueueStub
        
        Args:
            queue: 现有的 Queue 对象
            queue_id: 队列ID
            **metadata: 额外的元数据
            
        Returns:
            LocalQueueStub 实例
        """
        from ..queue_descriptor import LocalQueueDescriptor
        
        if queue_id is None:
            queue_id = f"local_{id(queue)}"
        
        # 提取 Queue 的配置信息
        maxsize = getattr(queue, '_maxsize', 0)
        
        # 创建本地队列描述符（包含队列引用，不可序列化）
        descriptor = LocalQueueDescriptor(
            queue_id=queue_id,
            queue_obj=queue,
            maxsize=maxsize,
            **metadata
        )
        
        # 创建 stub 实例
        stub = cls.__new__(cls)  # 避免调用 __init__
        stub.descriptor = descriptor
        stub._queue = queue
        
        logger.info(f"Successfully created LocalQueueStub from existing queue: {queue_id}")
        return stub
    
    def to_serializable_descriptor(self):
        """
        获取可序列化的描述符版本
        
        Returns:
            可序列化的 QueueDescriptor（不包含队列对象引用）
        """
        if hasattr(self.descriptor, 'to_serializable_descriptor'):
            return self.descriptor.to_serializable_descriptor()
        else:
            # 如果不是 LocalQueueDescriptor，创建一个新的可序列化版本
            from ..queue_descriptor import QueueDescriptor
            
            serializable_metadata = {
                k: v for k, v in self.descriptor.metadata.items() 
                if k != 'queue_ref' and not callable(v)
            }
            
            return QueueDescriptor(
                queue_id=self.descriptor.queue_id,
                queue_type=self.descriptor.queue_type,
                metadata=serializable_metadata,
                can_serialize=True,
                created_timestamp=self.descriptor.created_timestamp
            )
    
    def __repr__(self) -> str:
        return f"LocalQueueStub(queue_id='{self.descriptor.queue_id}', maxsize={self._queue._maxsize})"


# 便利函数
def create_local_queue_descriptor(queue_id: Optional[str] = None, 
                                 maxsize: int = 0) -> QueueDescriptor:
    """
    创建本地队列描述符的便利函数
    
    Args:
        queue_id: 队列ID
        maxsize: 最大大小
        
    Returns:
        本地队列描述符
    """
    return QueueDescriptor.create_local_queue(queue_id=queue_id, maxsize=maxsize)


def local_queue_from_descriptor(descriptor: QueueDescriptor) -> LocalQueueStub:
    """
    从描述符创建本地队列的便利函数
    
    Args:
        descriptor: 队列描述符
        
    Returns:
        LocalQueueStub 实例
    """
    return LocalQueueStub.from_descriptor(descriptor)
