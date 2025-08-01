"""
Queue Descriptor - 统一多态通信描述符

提供一个统一的多态队列描述符结构，支持：
1. 直接调用队列方法 (put, get, empty, qsize等)
2. 懒加载内部队列实例
3. 序列化支持（自动删除不可序列化的队列引用）
4. 跨进程传递队列描述符信息

统一管理各种类型的队列通信方式：本地队列、共享内存队列、Ray Actor队列、RPC队列等。
"""

import json
import uuid
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union, Protocol, runtime_checkable
import logging
import weakref

# 导入新的描述符架构
try:
    from .descriptors import (
        BaseQueueDescriptor,
        QueueLike,
        create_queue_descriptor,
        list_supported_queue_types,
        get_descriptor_info
    )
except ImportError:
    # 如果新的描述符架构不存在，则定义基本接口
    from typing import Protocol
    
    @runtime_checkable
    class QueueLike(Protocol):
        """队列接口协议"""
        def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None: ...
        def get(self, block: bool = True, timeout: Optional[float] = None) -> Any: ...
        def empty(self) -> bool: ...
        def qsize(self) -> int: ...
    
    class BaseQueueDescriptor(ABC):
        """基础描述符抽象类"""
        @abstractmethod
        def create_queue(self) -> QueueLike: ...

logger = logging.getLogger(__name__)


class UnifiedQueueDescriptor(QueueLike):
    """
    统一的多态队列描述符
    
    这个类既是描述符又实现了队列接口，支持：
    1. 直接调用队列方法（多态）
    2. 懒加载内部队列实例
    3. 序列化支持（自动处理不可序列化对象）
    4. 跨进程传递
    
    Attributes:
        queue_id: 队列的唯一标识符
        queue_type: 通信方式类型 ("local", "shm", "ray_actor", "rpc", "sage_queue", etc.)
        metadata: 保存额外参数的字典
        can_serialize: 是否可以序列化
        created_timestamp: 创建时间戳
    """
    
    def __init__(self, queue_id: str, queue_type: str, metadata: Dict[str, Any], 
                 can_serialize: bool = True, created_timestamp: Optional[float] = None,
                 queue_instance: Optional[QueueLike] = None):
        """
        初始化统一队列描述符
        
        Args:
            queue_id: 队列唯一标识符
            queue_type: 队列类型
            metadata: 元数据字典
            can_serialize: 是否可序列化
            created_timestamp: 创建时间戳
            queue_instance: 可选的队列实例（直接传入时不可序列化）
        """
        self.queue_id = queue_id
        self.queue_type = queue_type
        self.metadata = metadata.copy()  # 避免外部修改
        self.can_serialize = can_serialize and (queue_instance is None)
        self.created_timestamp = created_timestamp if created_timestamp is not None else time.time()
        
        # 队列实例管理
        self._queue_instance = queue_instance
        self._initialized = queue_instance is not None
        self._lazy_loading = queue_instance is None
        
        # 如果直接传入了队列实例，标记为不可序列化
        if queue_instance is not None:
            self.can_serialize = False
            self.metadata['_has_direct_instance'] = True
        
        self._validate()
    
    def _validate(self):
        """验证描述符参数"""
        if not self.queue_id or not isinstance(self.queue_id, str):
            raise ValueError("queue_id must be a non-empty string")
        if not self.queue_type or not isinstance(self.queue_type, str):
            raise ValueError("queue_type must be a non-empty string")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dictionary")
    
    def _ensure_queue_initialized(self) -> QueueLike:
        """确保队列实例已初始化（懒加载）"""
        if not self._initialized:
            if self._queue_instance is None:
                self._queue_instance = self._create_queue_instance()
            self._initialized = True
        return self._queue_instance
    
    def _create_queue_instance(self) -> QueueLike:
        """创建队列实例"""
        try:
            # 首先尝试使用新的描述符架构
            factory_kwargs = {'queue_id': self.queue_id, **self.metadata}
            new_descriptor = create_queue_descriptor(self.queue_type, **factory_kwargs)
            return new_descriptor.create_queue()
        except (ImportError, ValueError, NameError):
            # 回退到传统实现
            return self._create_queue_legacy()
    
    def _create_queue_legacy(self) -> QueueLike:
        """传统队列创建方式（回退机制）"""
        if self.queue_type not in QUEUE_STUB_MAPPING:
            raise ValueError(f"Unsupported queue type: {self.queue_type}. "
                           f"Available types: {list(QUEUE_STUB_MAPPING.keys())}")
        
        stub_class = QUEUE_STUB_MAPPING[self.queue_type]
        if stub_class is None:
            raise RuntimeError(f"Queue type '{self.queue_type}' is registered but implementation is None")
        
        return stub_class(self)
    
    # ============ 队列接口实现 (QueueLike Protocol) ============
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        """向队列中放入项目"""
        queue = self._ensure_queue_initialized()
        return queue.put(item, block=block, timeout=timeout)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """从队列中获取项目"""
        queue = self._ensure_queue_initialized()
        return queue.get(block=block, timeout=timeout)
    
    def empty(self) -> bool:
        """检查队列是否为空"""
        queue = self._ensure_queue_initialized()
        return queue.empty()
    
    def qsize(self) -> int:
        """获取队列大小"""
        queue = self._ensure_queue_initialized()
        return queue.qsize()
    
    # 额外的队列方法（如果底层队列支持）
    def put_nowait(self, item: Any) -> None:
        """非阻塞放入项目"""
        queue = self._ensure_queue_initialized()
        if hasattr(queue, 'put_nowait'):
            return queue.put_nowait(item)
        else:
            return queue.put(item, block=False)
    
    def get_nowait(self) -> Any:
        """非阻塞获取项目"""
        queue = self._ensure_queue_initialized()
        if hasattr(queue, 'get_nowait'):
            return queue.get_nowait()
        else:
            return queue.get(block=False)
    
    def full(self) -> bool:
        """检查队列是否已满"""
        queue = self._ensure_queue_initialized()
        if hasattr(queue, 'full'):
            return queue.full()
        else:
            # 默认实现：尝试估算
            try:
                maxsize = self.metadata.get('maxsize', 0)
                if maxsize <= 0:
                    return False  # 无限大小队列
                return queue.qsize() >= maxsize
            except:
                return False
    
    # ============ 描述符管理方法 ============
    
    @property
    def queue_instance(self) -> Optional[QueueLike]:
        """获取底层队列实例（如果已初始化）"""
        return self._queue_instance if self._initialized else None
    
    def clear_cache(self):
        """清除队列缓存，下次访问时重新初始化"""
        if self._lazy_loading:  # 只有懒加载的才能清除缓存
            self._queue_instance = None
            self._initialized = False
    
    def is_initialized(self) -> bool:
        """检查队列是否已初始化"""
        return self._initialized
    
    def clone(self, new_queue_id: Optional[str] = None) -> 'UnifiedQueueDescriptor':
        """克隆描述符（不包含队列实例）"""
        return UnifiedQueueDescriptor(
            queue_id=new_queue_id or f"{self.queue_id}_clone",
            queue_type=self.queue_type,
            metadata={k: v for k, v in self.metadata.items() if not k.startswith('_')},
            can_serialize=True,  # 克隆的总是可序列化的
            created_timestamp=time.time()
        )
    
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
    
    def to_serializable_descriptor(self) -> 'UnifiedQueueDescriptor':
        """
        转换为可序列化的描述符（移除队列实例引用）
        
        Returns:
            新的可序列化描述符实例
        """
        if self.can_serialize:
            return self
        
        # 创建新的可序列化实例
        serializable_metadata = {k: v for k, v in self.metadata.items() 
                                if not k.startswith('_')}
        
        return UnifiedQueueDescriptor(
            queue_id=self.queue_id,
            queue_type=self.queue_type,
            metadata=serializable_metadata,
            can_serialize=True,
            created_timestamp=self.created_timestamp
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedQueueDescriptor':
        """从字典创建实例"""
        return cls(
            queue_id=data['queue_id'],
            queue_type=data['queue_type'],
            metadata=data.get('metadata', {}),
            can_serialize=data.get('can_serialize', True),
            created_timestamp=data.get('created_timestamp')
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'UnifiedQueueDescriptor':
        """从JSON字符串创建实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    # ============ 工厂方法 ============
    
    @classmethod
    def create_local_queue(cls, queue_id: Optional[str] = None, maxsize: int = 0, 
                          queue_instance: Optional[QueueLike] = None) -> 'UnifiedQueueDescriptor':
        """创建本地队列描述符"""
        if queue_id is None:
            queue_id = f"local_{uuid.uuid4().hex[:8]}"
        
        return cls(
            queue_id=queue_id,
            queue_type="local",
            metadata={"maxsize": maxsize},
            can_serialize=queue_instance is None,
            queue_instance=queue_instance
        )
    
    @classmethod
    def create_shm_queue(cls, shm_name: str, queue_id: Optional[str] = None, 
                        maxsize: int = 1000) -> 'UnifiedQueueDescriptor':
        """创建共享内存队列描述符"""
        if queue_id is None:
            queue_id = f"shm_{uuid.uuid4().hex[:8]}"
        
        return cls(
            queue_id=queue_id,
            queue_type="shm",
            metadata={"shm_name": shm_name, "maxsize": maxsize},
            can_serialize=True
        )
    
    @classmethod
    def create_ray_actor_queue(cls, actor_name: str, queue_id: Optional[str] = None, 
                              maxsize: int = 0) -> 'UnifiedQueueDescriptor':
        """创建Ray Actor队列描述符"""
        if queue_id is None:
            queue_id = f"ray_actor_{uuid.uuid4().hex[:8]}"
        
        return cls(
            queue_id=queue_id,
            queue_type="ray_actor",
            metadata={"actor_name": actor_name, "maxsize": maxsize},
            can_serialize=True
        )
    
    @classmethod
    def create_ray_queue(cls, queue_id: Optional[str] = None, maxsize: int = 0) -> 'UnifiedQueueDescriptor':
        """创建Ray分布式队列描述符"""
        if queue_id is None:
            queue_id = f"ray_queue_{uuid.uuid4().hex[:8]}"
        
        return cls(
            queue_id=queue_id,
            queue_type="ray_queue",
            metadata={"maxsize": maxsize},
            can_serialize=True
        )
    
    @classmethod
    def create_rpc_queue(cls, server_address: str, port: int, 
                        queue_id: Optional[str] = None) -> 'UnifiedQueueDescriptor':
        """创建RPC队列描述符"""
        if queue_id is None:
            queue_id = f"rpc_{uuid.uuid4().hex[:8]}"
        
        return cls(
            queue_id=queue_id,
            queue_type="rpc",
            metadata={"server_address": server_address, "port": port},
            can_serialize=True
        )
    
    @classmethod
    def create_sage_queue(cls, queue_id: Optional[str] = None, maxsize: int = 1000, 
                         auto_cleanup: bool = True, namespace: Optional[str] = None,
                         enable_multi_tenant: bool = True) -> 'UnifiedQueueDescriptor':
        """创建SAGE高性能队列描述符"""
        if queue_id is None:
            queue_id = f"sage_{uuid.uuid4().hex[:8]}"
        
        return cls(
            queue_id=queue_id,
            queue_type="sage_queue",
            metadata={
                "maxsize": maxsize,
                "auto_cleanup": auto_cleanup,
                "namespace": namespace,
                "enable_multi_tenant": enable_multi_tenant
            },
            can_serialize=True
        )
    
    @classmethod
    def from_existing_queue(cls, queue_instance: QueueLike, queue_type: str, 
                           queue_id: Optional[str] = None, **metadata) -> 'UnifiedQueueDescriptor':
        """从现有队列实例创建描述符（不可序列化）"""
        if queue_id is None:
            queue_id = f"{queue_type}_ref_{uuid.uuid4().hex[:8]}"
        
        return cls(
            queue_id=queue_id,
            queue_type=queue_type,
            metadata=metadata,
            can_serialize=False,
            queue_instance=queue_instance
        )
    
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
        return f"UnifiedQueueDescriptor(id='{self.queue_id}', type='{self.queue_type}', {status})"
    
    def __str__(self) -> str:
        return f"Queue[{self.queue_type}]({self.queue_id})"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, UnifiedQueueDescriptor):
            return False
        return (self.queue_id == other.queue_id and 
                self.queue_type == other.queue_type and
                self.metadata == other.metadata)
    
    def __hash__(self) -> int:
        return hash((self.queue_id, self.queue_type))


# ============ 向后兼容的别名 ============

# 为了向后兼容，保留原来的类名
QueueDescriptor = UnifiedQueueDescriptor
LocalQueueDescriptor = UnifiedQueueDescriptor  # 向后兼容
RemoteQueueDescriptor = UnifiedQueueDescriptor  # 向后兼容


# ============ 队列类型注册系统 ============

# 队列类型映射表 - 用于回退机制
QUEUE_STUB_MAPPING = {}


def register_queue_implementation(queue_type: str, implementation_class):
    """
    注册队列类型的实现类
    
    Args:
        queue_type: 队列类型名称
        implementation_class: 实现类
    """
    QUEUE_STUB_MAPPING[queue_type] = implementation_class
    logger.info(f"Registered queue implementation: {queue_type} -> {implementation_class.__name__}")


def unregister_queue_implementation(queue_type: str):
    """
    注销队列类型的实现类
    
    Args:
        queue_type: 队列类型名称
    """
    if queue_type in QUEUE_STUB_MAPPING:
        del QUEUE_STUB_MAPPING[queue_type]
        logger.info(f"Unregistered queue implementation: {queue_type}")


def get_registered_queue_types():
    """获取已注册的队列类型列表"""
    return list(QUEUE_STUB_MAPPING.keys())


# ============ 便利函数 ============

def resolve_descriptor(desc: UnifiedQueueDescriptor) -> QueueLike:
    """
    解析队列描述符，返回队列实例
    
    Args:
        desc: 队列描述符
        
    Returns:
        队列实例
    """
    return desc._ensure_queue_initialized()


def create_descriptor_from_existing_queue(queue: QueueLike, queue_type: str, 
                                        queue_id: Optional[str] = None, 
                                        **metadata) -> UnifiedQueueDescriptor:
    """从现有队列创建描述符"""
    return UnifiedQueueDescriptor.from_existing_queue(
        queue_instance=queue,
        queue_type=queue_type,
        queue_id=queue_id,
        **metadata
    )


# ============ 工厂便利函数 ============

def get_local_queue(queue_id: Optional[str] = None, maxsize: int = 0) -> UnifiedQueueDescriptor:
    """获取本地队列描述符"""
    return UnifiedQueueDescriptor.create_local_queue(queue_id, maxsize)


def attach_to_shm_queue(shm_name: str, queue_id: Optional[str] = None, 
                       maxsize: int = 1000) -> UnifiedQueueDescriptor:
    """附着到共享内存队列"""
    return UnifiedQueueDescriptor.create_shm_queue(shm_name, queue_id, maxsize)


def get_ray_actor_queue(actor_name: str, queue_id: Optional[str] = None, 
                       maxsize: int = 0) -> UnifiedQueueDescriptor:
    """获取Ray Actor队列"""
    return UnifiedQueueDescriptor.create_ray_actor_queue(actor_name, queue_id, maxsize)


def get_ray_queue(queue_id: Optional[str] = None, maxsize: int = 0) -> UnifiedQueueDescriptor:
    """获取Ray分布式队列"""
    return UnifiedQueueDescriptor.create_ray_queue(queue_id, maxsize)


def get_rpc_queue(server_address: str, port: int, 
                 queue_id: Optional[str] = None) -> UnifiedQueueDescriptor:
    """获取RPC队列"""
    return UnifiedQueueDescriptor.create_rpc_queue(server_address, port, queue_id)


def get_sage_queue(queue_id: Optional[str] = None, maxsize: int = 1000) -> UnifiedQueueDescriptor:
    """获取SAGE高性能队列"""
    return UnifiedQueueDescriptor.create_sage_queue(queue_id, maxsize)


# ============ 批量操作工具 ============

def create_queue_pool(queue_configs: list, pool_id: Optional[str] = None) -> Dict[str, UnifiedQueueDescriptor]:
    """
    批量创建队列描述符池
    
    Args:
        queue_configs: 队列配置列表，每个配置包含 type 和其他参数
        pool_id: 池ID前缀
        
    Returns:
        队列描述符字典
    """
    if pool_id is None:
        pool_id = f"pool_{uuid.uuid4().hex[:8]}"
    
    pool = {}
    for i, config in enumerate(queue_configs):
        config = config.copy()
        queue_type = config.pop('type')
        queue_id = config.pop('queue_id', f"{pool_id}_{queue_type}_{i}")
        
        descriptor = UnifiedQueueDescriptor(
            queue_id=queue_id,
            queue_type=queue_type,
            metadata=config
        )
        pool[queue_id] = descriptor
    
    return pool


def serialize_queue_pool(pool: Dict[str, UnifiedQueueDescriptor]) -> str:
    """序列化队列池"""
    serializable_pool = {}
    for queue_id, descriptor in pool.items():
        if descriptor.can_serialize:
            serializable_pool[queue_id] = descriptor.to_dict()
        else:
            serializable_pool[queue_id] = descriptor.to_serializable_descriptor().to_dict()
    
    return json.dumps(serializable_pool)


def deserialize_queue_pool(json_str: str) -> Dict[str, UnifiedQueueDescriptor]:
    """反序列化队列池"""
    data = json.loads(json_str)
    pool = {}
    for queue_id, descriptor_data in data.items():
        pool[queue_id] = UnifiedQueueDescriptor.from_dict(descriptor_data)
    return pool
