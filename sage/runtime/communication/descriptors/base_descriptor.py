"""
Base Queue Descriptor - 队列描述符基类

定义所有队列描述符的通用接口和基础功能
"""

import json
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union, Protocol, runtime_checkable, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@runtime_checkable
class QueueLike(Protocol):
    """队列接口协议，定义所有队列类型必须实现的方法"""
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        """向队列中放入一个项目"""
        ...
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """从队列中获取一个项目"""
        ...
    
    def empty(self) -> bool:
        """检查队列是否为空"""
        ...
    
    def qsize(self) -> int:
        """获取队列的大小"""
        ...


class BaseQueueDescriptor(ABC):
    """
    队列描述符基类
    
    定义所有队列描述符的通用字段和方法，并支持直接队列操作
    
    Attributes:
        queue_id: 队列的唯一标识符
        queue_type: 通信方式类型
        metadata: 保存额外参数的字典
        can_serialize: 是否可以序列化
        created_timestamp: 创建时间戳
    """
    
    def __init__(self, queue_id: str, queue_type: str, metadata: Dict[str, Any], 
                 can_serialize: bool = True, created_timestamp: Optional[float] = None):
        """初始化队列描述符"""
        self.queue_id = queue_id
        self.queue_type = queue_type
        self.metadata = metadata
        self.can_serialize = can_serialize
        self.created_timestamp = created_timestamp if created_timestamp is not None else time.time()
        
        # 队列缓存和状态管理
        self._queue_cache = None
        self._initialized = False
        
        # 子类可以重写此方法进行特定的验证
        self._validate_descriptor()
    
    def _validate_descriptor(self):
        """验证描述符，子类可以重写"""
        if not self.queue_id:
            raise ValueError("queue_id cannot be empty")
        if not self.queue_type:
            raise ValueError("queue_type cannot be empty")
    
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'queue_id': self.queue_id,
            'queue_type': self.queue_type,
            'metadata': self.metadata,
            'can_serialize': self.can_serialize,
            'created_timestamp': self.created_timestamp
        }
    
    def to_json(self) -> str:
        """序列化为JSON字符串"""
        if not self.can_serialize:
            raise ValueError(f"Queue descriptor '{self.queue_id}' contains non-serializable objects and cannot be converted to JSON")
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseQueueDescriptor':
        """从字典创建实例"""
        return cls(
            queue_id=data['queue_id'],
            queue_type=data['queue_type'],
            metadata=data['metadata'],
            can_serialize=data.get('can_serialize', True),
            created_timestamp=data.get('created_timestamp')
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BaseQueueDescriptor':
        """从JSON字符串创建实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @abstractmethod
    def create_queue(self) -> QueueLike:
        """
        创建实际的队列对象
        
        每个子类必须实现此方法来创建对应类型的队列
        
        Returns:
            实现了QueueLike协议的队列对象
        """
        pass
    
    def get_queue_info(self) -> Dict[str, Any]:
        """获取队列信息"""
        return {
            'queue_id': self.queue_id,
            'queue_type': self.queue_type,
            'can_serialize': self.can_serialize,
            'created_timestamp': self.created_timestamp,
            'metadata_keys': list(self.metadata.keys()) if self.metadata else []
        }
    
    def copy(self, **overrides) -> 'BaseQueueDescriptor':
        """创建描述符的副本，可以覆盖某些字段"""
        data = self.to_dict()
        data.update(overrides)
        return self.__class__(**data)
    
    def _ensure_queue_initialized(self):
        """确保队列已初始化（懒加载）"""
        if not self._initialized and self._queue_cache is None:
            self._queue_cache = self.create_queue()
            self._initialized = True
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        """向队列中放入项目"""
        self._ensure_queue_initialized()
        return self._queue_cache.put(item, block=block, timeout=timeout)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """从队列中获取项目"""
        self._ensure_queue_initialized()
        return self._queue_cache.get(block=block, timeout=timeout)
    
    def empty(self) -> bool:
        """检查队列是否为空"""
        self._ensure_queue_initialized()
        return self._queue_cache.empty()
    
    def qsize(self) -> int:
        """获取队列大小"""
        self._ensure_queue_initialized()
        return self._queue_cache.qsize()
    
    @property
    def queue(self) -> QueueLike:
        """获取底层队列对象（懒加载）"""
        self._ensure_queue_initialized()
        return self._queue_cache
    
    def clear_cache(self):
        """清除队列缓存，下次访问时重新初始化"""
        self._queue_cache = None
        self._initialized = False
    
    def __repr__(self) -> str:
        status = "initialized" if self._initialized else "lazy"
        serializable_str = "serializable" if self.can_serialize else "non-serializable"
        return f"{self.__class__.__name__}(id='{self.queue_id}', type='{self.queue_type}', {status}, {serializable_str})"


# 全局描述符注册表
DESCRIPTOR_REGISTRY: Dict[str, type] = {}


def register_descriptor_class(queue_type: str, descriptor_class: type):
    """
    注册队列描述符类
    
    Args:
        queue_type: 队列类型名称
        descriptor_class: 描述符类
    """
    DESCRIPTOR_REGISTRY[queue_type] = descriptor_class
    logger.info(f"Registered descriptor class: {queue_type} -> {descriptor_class.__name__}")


def get_descriptor_class(queue_type: str) -> Optional[type]:
    """
    获取队列类型对应的描述符类
    
    Args:
        queue_type: 队列类型名称
        
    Returns:
        描述符类，如果未找到则返回None
    """
    return DESCRIPTOR_REGISTRY.get(queue_type)


def create_descriptor(queue_type: str, queue_id: str, metadata: Dict[str, Any], 
                     **kwargs) -> BaseQueueDescriptor:
    """
    工厂函数：根据队列类型创建对应的描述符
    
    Args:
        queue_type: 队列类型
        queue_id: 队列ID
        metadata: 元数据
        **kwargs: 其他参数
        
    Returns:
        对应类型的队列描述符
        
    Raises:
        ValueError: 如果队列类型未注册
    """
    descriptor_class = get_descriptor_class(queue_type)
    if descriptor_class is None:
        raise ValueError(f"Unknown queue type: {queue_type}. Available types: {list(DESCRIPTOR_REGISTRY.keys())}")
    
    return descriptor_class(
        queue_id=queue_id,
        queue_type=queue_type,
        metadata=metadata,
        **kwargs
    )


def get_registered_descriptor_types() -> list:
    """获取已注册的描述符类型列表"""
    return list(DESCRIPTOR_REGISTRY.keys())
