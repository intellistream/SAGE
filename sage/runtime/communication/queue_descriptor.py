"""
Queue Descriptor - 统一通信描述符

提供一个可序列化的通信描述符结构，用于在异构通信系统中统一描述和管理各种类型的队列通信方式，
包括本地队列、共享内存队列、Ray Actor队列、RPC队列等。

支持跨进程传递队列引用并以统一的方式管理通信逻辑。
"""

import json
import uuid
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Union, Protocol, runtime_checkable
from abc import ABC, abstractmethod
import logging

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


@dataclass
class QueueDescriptor:
    """
    统一的队列通信描述符
    
    用于描述各种类型的队列通信方式，支持序列化和跨进程传递。
    
    Attributes:
        queue_id: 队列的唯一标识符
        queue_type: 通信方式类型 ("local", "shm", "ray_actor", "rpc", "sage_queue", "ray_queue")
        metadata: 保存额外参数的字典，如shm名称、socket地址、ray actor name等
        created_timestamp: 创建时间戳
    """
    queue_id: str
    queue_type: str
    metadata: Dict[str, Any]
    created_timestamp: Optional[float] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.created_timestamp is None:
            import time
            self.created_timestamp = time.time()
        
        # 验证queue_type
        valid_types = {"local", "shm", "ray_actor", "rpc", "sage_queue", "ray_queue"}
        if self.queue_type not in valid_types:
            raise ValueError(f"Invalid queue_type '{self.queue_type}'. Valid types: {valid_types}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)
    
    def to_json(self) -> str:
        """序列化为JSON字符串"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueueDescriptor':
        """从字典创建实例"""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'QueueDescriptor':
        """从JSON字符串创建实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def create_local_queue(cls, queue_id: Optional[str] = None, maxsize: int = 0) -> 'QueueDescriptor':
        """创建本地队列描述符"""
        if queue_id is None:
            queue_id = f"local_{uuid.uuid4().hex[:8]}"
        
        return cls(
            queue_id=queue_id,
            queue_type="local",
            metadata={"maxsize": maxsize}
        )
    
    @classmethod
    def create_shm_queue(cls, shm_name: str, queue_id: Optional[str] = None, maxsize: int = 1000) -> 'QueueDescriptor':
        """创建共享内存队列描述符"""
        if queue_id is None:
            queue_id = f"shm_{uuid.uuid4().hex[:8]}"
        
        return cls(
            queue_id=queue_id,
            queue_type="shm",
            metadata={"shm_name": shm_name, "maxsize": maxsize}
        )
    
    @classmethod
    def create_ray_actor_queue(cls, actor_name: str, queue_id: Optional[str] = None, maxsize: int = 0) -> 'QueueDescriptor':
        """创建Ray Actor队列描述符"""
        if queue_id is None:
            queue_id = f"ray_actor_{uuid.uuid4().hex[:8]}"
        
        return cls(
            queue_id=queue_id,
            queue_type="ray_actor",
            metadata={"actor_name": actor_name, "maxsize": maxsize}
        )
    
    @classmethod
    def create_ray_queue(cls, queue_id: Optional[str] = None, maxsize: int = 0) -> 'QueueDescriptor':
        """创建Ray分布式队列描述符"""
        if queue_id is None:
            queue_id = f"ray_queue_{uuid.uuid4().hex[:8]}"
        
        return cls(
            queue_id=queue_id,
            queue_type="ray_queue",
            metadata={"maxsize": maxsize}
        )
    
    @classmethod
    def create_rpc_queue(cls, server_address: str, port: int, queue_id: Optional[str] = None) -> 'QueueDescriptor':
        """创建RPC队列描述符"""
        if queue_id is None:
            queue_id = f"rpc_{uuid.uuid4().hex[:8]}"
        
        return cls(
            queue_id=queue_id,
            queue_type="rpc",
            metadata={"server_address": server_address, "port": port}
        )
    
    @classmethod
    def create_sage_queue(cls, queue_id: Optional[str] = None, maxsize: int = 1000, 
                         auto_cleanup: bool = True, namespace: Optional[str] = None,
                         enable_multi_tenant: bool = True) -> 'QueueDescriptor':
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
            }
        )
    
    def __repr__(self) -> str:
        return f"QueueDescriptor(id='{self.queue_id}', type='{self.queue_type}', metadata={self.metadata})"


# 队列类型映射表 - 默认为空，由具体实现模块填充
QUEUE_STUB_MAPPING = {}


def resolve_descriptor(desc: QueueDescriptor) -> QueueLike:
    """
    根据队列描述符创建或附着对应类型的队列
    
    Args:
        desc: 队列描述符
        
    Returns:
        实现了QueueLike协议的队列对象
        
    Raises:
        ValueError: 如果队列类型不支持
        RuntimeError: 如果队列类型未注册实现
    """
    logger.info(f"Resolving queue descriptor: {desc}")
    
    if desc.queue_type not in QUEUE_STUB_MAPPING:
        raise ValueError(f"Unsupported queue type: {desc.queue_type}. "
                        f"Available types: {list(QUEUE_STUB_MAPPING.keys())}")
    
    stub_class = QUEUE_STUB_MAPPING[desc.queue_type]
    if stub_class is None:
        raise RuntimeError(f"Queue type '{desc.queue_type}' is registered but implementation is None")
    
    queue_instance = stub_class(desc)
    
    logger.info(f"Successfully resolved queue descriptor to {queue_instance.__class__.__name__}")
    return queue_instance


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


def create_descriptor_from_existing_queue(queue: QueueLike, queue_type: str, queue_id: Optional[str] = None, **metadata) -> QueueDescriptor:
    """
    从现有队列创建描述符
    
    Args:
        queue: 现有的队列对象
        queue_type: 队列类型
        queue_id: 队列ID，如果为None则自动生成
        **metadata: 额外的元数据
        
    Returns:
        队列描述符
    """
    if queue_id is None:
        queue_id = f"{queue_type}_{uuid.uuid4().hex[:8]}"
    
    return QueueDescriptor(
        queue_id=queue_id,
        queue_type=queue_type,
        metadata=metadata
    )


# 便利函数 - 需要先注册相应的实现类才能使用
def get_local_queue(queue_id: Optional[str] = None, maxsize: int = 0) -> QueueLike:
    """获取本地队列"""
    desc = QueueDescriptor.create_local_queue(queue_id, maxsize)
    return resolve_descriptor(desc)


def attach_to_shm_queue(shm_name: str, queue_id: Optional[str] = None, maxsize: int = 1000) -> QueueLike:
    """附着到共享内存队列"""
    desc = QueueDescriptor.create_shm_queue(shm_name, queue_id, maxsize)
    return resolve_descriptor(desc)


def get_ray_actor_queue(actor_name: str, queue_id: Optional[str] = None, maxsize: int = 0) -> QueueLike:
    """获取Ray Actor队列"""
    desc = QueueDescriptor.create_ray_actor_queue(actor_name, queue_id, maxsize)
    return resolve_descriptor(desc)


def get_ray_queue(queue_id: Optional[str] = None, maxsize: int = 0) -> QueueLike:
    """获取Ray分布式队列"""
    desc = QueueDescriptor.create_ray_queue(queue_id, maxsize)
    return resolve_descriptor(desc)


def get_rpc_queue(server_address: str, port: int, queue_id: Optional[str] = None) -> QueueLike:
    """获取RPC队列"""
    desc = QueueDescriptor.create_rpc_queue(server_address, port, queue_id)
    return resolve_descriptor(desc)


def get_sage_queue(queue_id: Optional[str] = None, maxsize: int = 1000) -> QueueLike:
    """获取SAGE高性能队列"""
    desc = QueueDescriptor.create_sage_queue(queue_id, maxsize)
    return resolve_descriptor(desc)
