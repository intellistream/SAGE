"""
Local Queue Descriptor - 本地队列描述符

用于管理本地内存中的队列，支持直接操作和对象引用
"""

import queue
import uuid
from typing import Any, Dict, Optional
from .base_descriptor import BaseQueueDescriptor, QueueLike, register_descriptor_class
import logging

logger = logging.getLogger(__name__)


class LocalQueueDescriptor(BaseQueueDescriptor):
    """
    本地队列描述符
    
    特点：
    - 包含对实际队列对象的直接引用
    - 不可序列化（因为包含对象引用）
    - 支持直接的队列操作
    - 适用于单进程内的队列管理
    """
    
    def __init__(self, queue_id: str, queue_obj: Any = None, maxsize: int = 0, 
                 **extra_metadata):
        """
        初始化本地队列描述符
        
        Args:
            queue_id: 队列ID
            queue_obj: 实际的队列对象，如果为None则自动创建
            maxsize: 队列最大大小
            **extra_metadata: 额外的元数据
        """
        metadata = {
            'maxsize': maxsize,
            **extra_metadata
        }
        
        # 如果提供了队列对象，则存储引用并设置为不可序列化
        if queue_obj is not None:
            metadata['queue_ref'] = queue_obj
            can_serialize = False
            self._queue = queue_obj
        else:
            can_serialize = True
            self._queue = None
        
        super().__init__(
            queue_id=queue_id,
            queue_type="local",
            metadata=metadata,
            can_serialize=can_serialize
        )
        
        self._initialized = queue_obj is not None
        
        logger.info(f"LocalQueueDescriptor '{queue_id}' created, "
                   f"has_queue_ref={queue_obj is not None}, "
                   f"can_serialize={can_serialize}")
    
    def create_queue(self) -> QueueLike:
        """创建本地队列对象"""
        if self._queue is not None:
            return self._queue
        
        maxsize = self.metadata.get('maxsize', 0)
        queue_obj = queue.Queue(maxsize=maxsize)
        
        logger.info(f"Created local queue '{self.queue_id}' with maxsize={maxsize}")
        return queue_obj
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        """直接向队列中放入项目"""
        if not self._initialized:
            self._queue = self.create_queue()
            self._initialized = True
        
        logger.debug(f"LocalQueue[{self.queue_id}]: put({item})")
        return self._queue.put(item, block=block, timeout=timeout)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """直接从队列中获取项目"""
        if not self._initialized:
            self._queue = self.create_queue()
            self._initialized = True
        
        item = self._queue.get(block=block, timeout=timeout)
        logger.debug(f"LocalQueue[{self.queue_id}]: get() -> {item}")
        return item
    
    def put_nowait(self, item: Any) -> None:
        """非阻塞放入项目"""
        return self.put(item, block=False)
    
    def get_nowait(self) -> Any:
        """非阻塞获取项目"""
        return self.get(block=False)
    
    def empty(self) -> bool:
        """检查队列是否为空"""
        if not self._initialized:
            return True
        return self._queue.empty()
    
    def qsize(self) -> int:
        """获取队列大小"""
        if not self._initialized:
            return 0
        return self._queue.qsize()
    
    def full(self) -> bool:
        """检查队列是否已满"""
        if not self._initialized:
            return False
        return self._queue.full()
    
    @property
    def queue(self) -> Any:
        """获取底层队列对象"""
        if not self._initialized:
            self._queue = self.create_queue()
            self._initialized = True
        return self._queue
    
    def to_serializable_descriptor(self) -> 'SerializableLocalQueueDescriptor':
        """
        转换为可序列化的本地队列描述符
        
        Returns:
            可序列化的本地队列描述符（不包含队列引用）
        """
        # 过滤掉不可序列化的元数据
        serializable_metadata = {
            k: v for k, v in self.metadata.items() 
            if k != 'queue_ref' and not callable(v)
        }
        
        return SerializableLocalQueueDescriptor(
            queue_id=self.queue_id,
            metadata=serializable_metadata,
            created_timestamp=self.created_timestamp
        )
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        if not self._initialized:
            return {
                'initialized': False,
                'size': 0,
                'empty': True,
                'full': False
            }
        
        return {
            'initialized': True,
            'size': self.qsize(),
            'empty': self.empty(),
            'full': self.full(),
            'maxsize': self.metadata.get('maxsize', 0)
        }
    
    def __repr__(self) -> str:
        queue_type = type(self._queue).__name__ if self._queue else "None"
        status = "initialized" if self._initialized else "uninitialized"
        return f"LocalQueueDescriptor(id='{self.queue_id}', queue={queue_type}, {status})"


class SerializableLocalQueueDescriptor(BaseQueueDescriptor):
    """
    可序列化的本地队列描述符
    
    特点：
    - 不包含队列对象引用，可以序列化
    - 支持懒加载：首次访问时创建队列
    - 适用于跨进程传递队列配置
    """
    
    def __init__(self, queue_id: str, metadata: Optional[Dict[str, Any]] = None, 
                 created_timestamp: Optional[float] = None):
        """
        初始化可序列化的本地队列描述符
        
        Args:
            queue_id: 队列ID
            metadata: 元数据
            created_timestamp: 创建时间戳
        """
        super().__init__(
            queue_id=queue_id,
            queue_type="local",
            metadata=metadata or {},
            can_serialize=True,
            created_timestamp=created_timestamp
        )
        
        self._queue_cache = None
        self._initialized = False
    
    def create_queue(self) -> QueueLike:
        """创建本地队列对象"""
        maxsize = self.metadata.get('maxsize', 0)
        queue_obj = queue.Queue(maxsize=maxsize)
        
        logger.info(f"Created serializable local queue '{self.queue_id}' with maxsize={maxsize}")
        return queue_obj
    
    def _ensure_queue_initialized(self):
        """确保队列已初始化（懒加载）"""
        if not self._initialized and self._queue_cache is None:
            self._queue_cache = self.create_queue()
            self._initialized = True
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        """懒加载队列并放入项目"""
        self._ensure_queue_initialized()
        logger.debug(f"SerializableLocalQueue[{self.queue_id}]: put({item})")
        return self._queue_cache.put(item, block=block, timeout=timeout)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """懒加载队列并获取项目"""
        self._ensure_queue_initialized()
        item = self._queue_cache.get(block=block, timeout=timeout)
        logger.debug(f"SerializableLocalQueue[{self.queue_id}]: get() -> {item}")
        return item
    
    def empty(self) -> bool:
        """懒加载队列并检查是否为空"""
        self._ensure_queue_initialized()
        return self._queue_cache.empty()
    
    def qsize(self) -> int:
        """懒加载队列并获取大小"""
        self._ensure_queue_initialized()
        return self._queue_cache.qsize()
    
    @property
    def queue(self) -> Any:
        """获取底层队列对象（懒加载）"""
        self._ensure_queue_initialized()
        return self._queue_cache
    
    def clear_cache(self):
        """清除队列缓存，下次访问时重新初始化"""
        self._queue_cache = None
        self._initialized = False
    
    def to_local_descriptor_with_ref(self, queue_obj: Any) -> LocalQueueDescriptor:
        """
        转换为包含队列引用的本地描述符
        
        Args:
            queue_obj: 队列对象
            
        Returns:
            包含队列引用的本地描述符
        """
        return LocalQueueDescriptor(
            queue_id=self.queue_id,
            queue_obj=queue_obj,
            maxsize=self.metadata.get('maxsize', 0),
            **{k: v for k, v in self.metadata.items() if k != 'maxsize'}
        )
    
    def __repr__(self) -> str:
        status = "initialized" if self._initialized else "lazy"
        return f"SerializableLocalQueueDescriptor(id='{self.queue_id}', {status})"


# 工厂函数
def create_local_queue_descriptor(queue_id: Optional[str] = None, 
                                 maxsize: int = 0, 
                                 **extra_metadata) -> SerializableLocalQueueDescriptor:
    """
    创建可序列化的本地队列描述符
    
    Args:
        queue_id: 队列ID，如果为None则自动生成
        maxsize: 队列最大大小
        **extra_metadata: 额外的元数据
        
    Returns:
        可序列化的本地队列描述符
    """
    if queue_id is None:
        queue_id = f"local_{uuid.uuid4().hex[:8]}"
    
    metadata = {'maxsize': maxsize, **extra_metadata}
    
    return SerializableLocalQueueDescriptor(
        queue_id=queue_id,
        metadata=metadata
    )


def create_local_queue_descriptor_with_ref(queue_obj: Any, 
                                          queue_id: Optional[str] = None,
                                          maxsize: int = 0,
                                          **extra_metadata) -> LocalQueueDescriptor:
    """
    从现有队列对象创建本地队列描述符（包含对象引用，不可序列化）
    
    Args:
        queue_obj: 实际的队列对象
        queue_id: 队列ID，如果为None则自动生成
        maxsize: 队列最大大小
        **extra_metadata: 额外的元数据
        
    Returns:
        LocalQueueDescriptor 实例
    """
    if queue_id is None:
        queue_id = f"local_ref_{uuid.uuid4().hex[:8]}"
    
    return LocalQueueDescriptor(
        queue_id=queue_id,
        queue_obj=queue_obj,
        maxsize=maxsize,
        **extra_metadata
    )


# 注册描述符类
register_descriptor_class("local", LocalQueueDescriptor)
