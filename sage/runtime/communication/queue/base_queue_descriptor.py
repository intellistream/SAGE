"""
Base Queue Descriptor - 统一多态通信描述符基类

提供一个统一的多态队列描述符结构，支持：
1. 直接调用队列方法 (put, get, empty, qsize等)
2. 懒加载内部队列实例
3. 序列化支持（自动处理不可序列化对象）
4. 跨进程传递队列描述符信息

通过继承支持各种队列类型：本地队列、共享内存队列、Ray队列、SAGE队列等。
"""

import json
import uuid
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
import logging

logger = logging.getLogger(__name__)


class BaseQueueDescriptor(ABC):
    """
    统一的多态队列描述符基类
    
    这个抽象基类定义了队列描述符的标准接口，支持：
    1. 直接调用队列方法（多态）
    2. 懒加载内部队列实例
    3. 序列化支持（子类定义序列化能力）
    4. 跨进程传递
    
    队列接口方法：
    - put(item, block=True, timeout=None): 向队列中放入项目
    - get(block=True, timeout=None): 从队列中获取项目
    - empty(): 检查队列是否为空
    - qsize(): 获取队列大小
    
    Attributes:
        queue_id: 队列的唯一标识符
        queue_type: 通信方式类型（由子类定义）
        metadata: 保存额外参数的字典（由子类生成）
        created_timestamp: 创建时间戳（自动生成）
    """
    
    def __init__(self, queue_id: Optional[str] = None):
        """
        初始化队列描述符基类
        
        Args:
            queue_id: 队列唯一标识符，如果为None则自动生成
        """
        self.queue_id = queue_id or self._generate_queue_id()
        self.created_timestamp = time.time()
        
        # 队列实例管理
        self._queue_instance = None
        self._initialized = False
        
        # 子类应该实现metadata属性
        # self.metadata = {}  # 删除这行，让子类自己实现
        
        self._validate()
    
    def _generate_queue_id(self) -> str:
        """生成队列ID"""
        return f"{self.queue_type}_{uuid.uuid4().hex[:8]}"
    
    @property
    @abstractmethod
    def queue_type(self) -> str:
        """队列类型标识符"""
        pass
    
    @property
    @abstractmethod
    def can_serialize(self) -> bool:
        """是否可以序列化"""
        pass
    
    
    def _validate(self):
        """验证描述符参数"""
        if not self.queue_id or not isinstance(self.queue_id, str):
            raise ValueError("queue_id must be a non-empty string")
        if not self.queue_type or not isinstance(self.queue_type, str):
            raise ValueError("queue_type must be a non-empty string")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dictionary")
    
    # ============ 队列接口实现 ============
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        return self.queue_instance.put(item, block=block, timeout=timeout)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """从队列中获取项目"""
        return self.queue_instance.get(block=block, timeout=timeout)
    
    def empty(self) -> bool:
        """检查队列是否为空"""
        return self.queue_instance.empty()
    
    def qsize(self) -> int:
        """获取队列大小"""
        return self.queue_instance.qsize()
    
    # 额外的队列方法（如果底层队列支持）
    def put_nowait(self, item: Any) -> None:
        """非阻塞放入项目"""
        return self.queue_instance.put_nowait(item)
    
    def get_nowait(self) -> Any:
        """非阻塞获取项目"""
        return self.queue_instance.get_nowait()

    def full(self) -> bool:
        """检查队列是否已满"""
        return self.queue_instance.full()
    
    # ============ 描述符管理方法 ============

    @property
    @abstractmethod
    def queue_instance(self) -> Optional[Any]:
        pass
    
    def get_queue(self) -> Any:
        return self.queue_instance

    
    def clear_cache(self):
        """清除队列缓存，下次访问时重新初始化"""
        if hasattr(self, '_queue_instance'):
            self._queue_instance = None
        if hasattr(self, '_initialized'):
            self._initialized = False
    
    def is_initialized(self) -> bool:
        """检查队列是否已初始化"""
        return self._initialized
    
    def clone(self, new_queue_id: Optional[str] = None) -> 'BaseQueueDescriptor':
        """克隆描述符（不包含队列实例）"""
        # 创建同类型的新实例
        new_instance = type(self)(queue_id=new_queue_id or f"{self.queue_id}_clone")
        return new_instance
    
    def trim(self):
        """清除队列实例引用，释放内存但保留描述符信息"""
        if hasattr(self, '_queue_instance'):
            self._queue_instance = None
        if hasattr(self, '_initialized'):
            self._initialized = False
    
    # ============ 序列化支持 ============
    
    def to_dict(self, include_non_serializable: bool = False) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Args:
            include_non_serializable: 是否包含不可序列化的字段
        """
        result = {
            'queue_id': self.queue_id,
            'queue_type': self.queue_type,
            'class_name': self.__class__.__name__,
            'metadata': {},
            'can_serialize': self.can_serialize,
            'created_timestamp': self.created_timestamp
        }
        
        # 过滤元数据中的不可序列化对象
        for key, value in self.metadata.items():
            if key.startswith('_') and not include_non_serializable:
                continue  # 跳过私有字段
            
            try:
                json.dumps(value)  # 测试是否可序列化
                result['metadata'][key] = value
            except (TypeError, ValueError):
                if include_non_serializable:
                    result['metadata'][key] = f"<non-serializable: {type(value).__name__}>"
        
        return result
    
    def to_json(self) -> str:
        """序列化为JSON字符串"""
        if not self.can_serialize:
            raise ValueError(f"Queue descriptor '{self.queue_id}' contains non-serializable objects")
        return json.dumps(self.to_dict())
    
    def to_serializable_descriptor(self) -> 'BaseQueueDescriptor':
        """
        转换为可序列化的描述符（移除队列实例引用）
        
        Returns:
            新的可序列化描述符实例
        """
        if self.can_serialize:
            return self
        
        # 创建同类型的新实例（不包含队列实例）
        return type(self)(queue_id=self.queue_id)

    
    
    # ============ 魔法方法 ============
    
    def __repr__(self) -> str:
        status_parts = []
        if self._initialized:
            status_parts.append("initialized")
        else:
            status_parts.append("lazy")
        
        if self.can_serialize:
            status_parts.append("serializable")
        else:
            status_parts.append("non-serializable")
        
        status = ", ".join(status_parts)
        return f"{self.__class__.__name__}(id='{self.queue_id}', type='{self.queue_type}', {status})"
    
    def __str__(self) -> str:
        return f"Queue[{self.queue_type}]({self.queue_id})"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, BaseQueueDescriptor):
            return False
        return (self.queue_id == other.queue_id and 
                self.queue_type == other.queue_type and
                self.metadata == other.metadata)
    
    def __hash__(self) -> int:
        return hash((self.queue_id, self.queue_type))


# 为了向后兼容性，提供 QueueDescriptor 别名
QueueDescriptor = BaseQueueDescriptor
