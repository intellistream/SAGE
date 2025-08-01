"""
Shared Memory Queue Stub - 共享内存队列的封装实现

提供 multiprocessing.Queue 与 Queue Descriptor 之间的转换方法
"""

import logging
import multiprocessing
from typing import Any, Optional, Dict
from ..queue_descriptor import QueueDescriptor, QueueLike

logger = logging.getLogger(__name__)


class SharedMemoryQueueStub:
    """
    共享内存 Queue 的封装类，实现 QueueLike 接口
    
    封装 multiprocessing.Queue，支持与 QueueDescriptor 的双向转换
    """
    
    def __init__(self, descriptor: QueueDescriptor):
        """
        从 QueueDescriptor 初始化共享内存队列
        
        Args:
            descriptor: 队列描述符
        """
        if descriptor.queue_type != "shm":
            raise ValueError(f"Expected shm, got {descriptor.queue_type}")
        
        self.descriptor = descriptor
        self._mp_queue = None
        self._initialize_shm_queue()
    
    def _initialize_shm_queue(self):
        """初始化共享内存队列"""
        try:
            maxsize = self.descriptor.metadata.get('maxsize', 1000)
            shm_name = self.descriptor.metadata.get('shm_name')
            
            # 创建 multiprocessing.Queue
            # 注意：multiprocessing.Queue 不支持命名，这里的 shm_name 主要用于标识
            self._mp_queue = multiprocessing.Queue(maxsize=maxsize)
            
            logger.info(f"Successfully initialized shared memory queue: {shm_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize shared memory queue: {e}")
            raise
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        """向队列添加元素"""
        if self._mp_queue is None:
            raise RuntimeError("Shared memory queue not initialized")
        
        return self._mp_queue.put(item, block=block, timeout=timeout)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """从队列获取元素"""
        if self._mp_queue is None:
            raise RuntimeError("Shared memory queue not initialized")
        
        return self._mp_queue.get(block=block, timeout=timeout)
    
    def put_nowait(self, item: Any) -> None:
        """非阻塞添加元素"""
        return self.put(item, block=False)
    
    def get_nowait(self) -> Any:
        """非阻塞获取元素"""
        return self.get(block=False)
    
    def empty(self) -> bool:
        """检查队列是否为空"""
        if self._mp_queue is None:
            return True
        return self._mp_queue.empty()
    
    def qsize(self) -> int:
        """获取队列大小"""
        if self._mp_queue is None:
            return 0
        return self._mp_queue.qsize()
    
    def full(self) -> bool:
        """检查队列是否已满"""
        if self._mp_queue is None:
            return False
        return self._mp_queue.full()
    
    def close(self):
        """关闭队列"""
        if self._mp_queue is not None:
            try:
                self._mp_queue.close()
            except Exception as e:
                logger.warning(f"Error closing shared memory queue: {e}")
            self._mp_queue = None
    
    def join_thread(self):
        """等待队列的内部线程结束"""
        if self._mp_queue is not None:
            try:
                self._mp_queue.join_thread()
            except Exception as e:
                logger.warning(f"Error joining queue thread: {e}")
    
    def to_descriptor(self) -> QueueDescriptor:
        """
        将当前共享内存队列转换为 QueueDescriptor
        
        Returns:
            对应的队列描述符
        """
        return self.descriptor
    
    @classmethod
    def from_descriptor(cls, descriptor: QueueDescriptor) -> 'SharedMemoryQueueStub':
        """
        从 QueueDescriptor 创建 SharedMemoryQueueStub 实例
        
        Args:
            descriptor: 队列描述符
            
        Returns:
            SharedMemoryQueueStub 实例
        """
        return cls(descriptor)
    
    @classmethod
    def from_mp_queue(cls, mp_queue: multiprocessing.Queue, 
                     shm_name: str, queue_id: Optional[str] = None, 
                     **metadata) -> 'SharedMemoryQueueStub':
        """
        从现有的 multiprocessing.Queue 对象创建 SharedMemoryQueueStub
        
        Args:
            mp_queue: 现有的 multiprocessing.Queue 对象
            shm_name: 共享内存名称
            queue_id: 队列ID
            **metadata: 额外的元数据
            
        Returns:
            SharedMemoryQueueStub 实例
        """
        if queue_id is None:
            queue_id = f"shm_{id(mp_queue)}"
        
        # 提取 multiprocessing.Queue 的配置信息
        default_metadata = {
            'shm_name': shm_name,
            'maxsize': getattr(mp_queue, '_maxsize', 1000)
        }
        
        # 合并用户提供的元数据
        default_metadata.update(metadata)
        
        # 创建描述符
        descriptor = QueueDescriptor(
            queue_id=queue_id,
            queue_type="shm",
            metadata=default_metadata
        )
        
        # 创建 stub 实例
        stub = cls(descriptor)
        
        # 直接使用传入的 mp_queue 对象，而不是重新创建
        stub._mp_queue = mp_queue
        
        return stub
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def __repr__(self) -> str:
        shm_name = self.descriptor.metadata.get('shm_name', 'unknown')
        return f"SharedMemoryQueueStub(queue_id='{self.descriptor.queue_id}', shm_name='{shm_name}')"


# 便利函数
def create_shm_queue_descriptor(shm_name: str, queue_id: Optional[str] = None, 
                               maxsize: int = 1000) -> QueueDescriptor:
    """
    创建共享内存队列描述符的便利函数
    
    Args:
        shm_name: 共享内存名称
        queue_id: 队列ID
        maxsize: 最大大小
        
    Returns:
        共享内存队列描述符
    """
    return QueueDescriptor.create_shm_queue(
        shm_name=shm_name, 
        queue_id=queue_id, 
        maxsize=maxsize
    )


def shm_queue_from_descriptor(descriptor: QueueDescriptor) -> SharedMemoryQueueStub:
    """
    从描述符创建共享内存队列的便利函数
    
    Args:
        descriptor: 队列描述符
        
    Returns:
        SharedMemoryQueueStub 实例
    """
    return SharedMemoryQueueStub.from_descriptor(descriptor)
