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
from typing import Any, Dict, Optional, Union
import logging
import weakref

logger = logging.getLogger(__name__)


class QueueDescriptor:
    """
    统一的多态队列描述符
    
    这个类既是描述符又实现了队列接口，支持：
    1. 直接调用队列方法（多态）
    2. 懒加载内部队列实例
    3. 序列化支持（自动处理不可序列化对象）
    4. 跨进程传递
    
    队列接口方法：
    - put(item, block=True, timeout=None): 向队列中放入项目
    - get(block=True, timeout=None): 从队列中获取项目
    - empty(): 检查队列是否为空
    - qsize(): 获取队列大小
    
    Attributes:
        queue_id: 队列的唯一标识符
        queue_type: 通信方式类型 ("local", "shm", "ray_actor", "rpc", "sage_queue", etc.)
        metadata: 保存额外参数的字典
        can_serialize: 是否可以序列化
        created_timestamp: 创建时间戳
    """
    
    def __init__(self, queue_id: str, queue_type: str, metadata: Dict[str, Any], 
                 can_serialize: bool = True, created_timestamp: Optional[float] = None,
                 queue_instance: Optional[Any] = None):
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
    
    def _ensure_queue_initialized(self) -> Any:
        """确保队列实例已初始化（懒加载）"""
        if not self._initialized:
            if self._queue_instance is None:
                self._queue_instance = self._create_queue_instance()
            self._initialized = True
        return self._queue_instance
    
    def _create_queue_instance(self) -> Any:
        """创建队列实例"""
        if self.queue_type == "local":
            import queue
            maxsize = self.metadata.get('maxsize', 0)
            return queue.Queue(maxsize=maxsize)
        elif self.queue_type == "shm":
            # 共享内存队列创建逻辑
            try:
                import multiprocessing as mp
                maxsize = self.metadata.get('maxsize', 0)
                return mp.Queue(maxsize=maxsize)
            except Exception:
                # 回退到本地队列
                import queue
                return queue.Queue(maxsize=self.metadata.get('maxsize', 0))
        elif self.queue_type == "sage_queue":
            return self._create_sage_queue()
        elif self.queue_type in ["ray_queue", "ray_actor"]:
            return self._create_ray_queue()
        else:
            raise ValueError(f"Unsupported queue type: {self.queue_type}. "
                           f"Available types: ['local', 'shm', 'sage_queue', 'ray_queue', 'ray_actor']")
    
    def _create_sage_queue(self) -> Any:
        """创建 SAGE 队列实例"""
        try:
            # 动态导入 SAGE Queue，避免循环依赖
            from sage_ext.sage_queue.python.sage_queue import SageQueue
            
            # 从描述符元数据中获取参数
            queue_id = self.queue_id
            maxsize = self.metadata.get('maxsize', 1024 * 1024)
            auto_cleanup = self.metadata.get('auto_cleanup', True)
            namespace = self.metadata.get('namespace')
            enable_multi_tenant = self.metadata.get('enable_multi_tenant', True)
            
            # 创建或连接到 SAGE Queue
            sage_queue = SageQueue(
                name=queue_id,
                maxsize=maxsize,
                auto_cleanup=auto_cleanup,
                namespace=namespace,
                enable_multi_tenant=enable_multi_tenant
            )
            
            logger.info(f"Successfully initialized SAGE Queue: {queue_id}")
            return sage_queue
            
        except ImportError as e:
            logger.error(f"Failed to import SageQueue: {e}")
            raise RuntimeError(f"SAGE Queue not available: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize SAGE Queue: {e}")
            raise
    
    def _create_ray_queue(self) -> Any:
        """创建 Ray 队列实例"""
        try:
            import ray
            
            if not ray.is_initialized():
                logger.warning("Ray is not initialized, attempting to initialize...")
                ray.init()
            
            if self.queue_type == "ray_queue":
                # Ray 原生分布式队列
                maxsize = self.metadata.get('maxsize', 0)
                queue_instance = ray.util.Queue(maxsize=maxsize if maxsize > 0 else None)
                logger.info(f"Successfully initialized Ray Queue: {self.queue_id}")
                return queue_instance
            
            elif self.queue_type == "ray_actor":
                # Ray Actor 队列
                actor_name = self.metadata.get('actor_name')
                if not actor_name:
                    raise ValueError("Ray Actor queue requires 'actor_name' in metadata")
                
                # 获取或创建 Ray Actor
                try:
                    actor_handle = ray.get_actor(actor_name)
                    logger.info(f"Connected to existing Ray Actor: {actor_name}")
                except ValueError:
                    # Actor 不存在，需要创建
                    logger.warning(f"Ray Actor {actor_name} not found, please create it first")
                    raise RuntimeError(f"Ray Actor '{actor_name}' not found")
                
                return actor_handle
            
        except ImportError as e:
            logger.error(f"Failed to import Ray: {e}")
            raise RuntimeError(f"Ray not available: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize Ray queue: {e}")
            raise
    
    # ============ 队列接口实现 ============
    
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
    def queue_instance(self) -> Optional[Any]:
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
    
    def clone(self, new_queue_id: Optional[str] = None) -> 'QueueDescriptor':
        """克隆描述符（不包含队列实例）"""
        return QueueDescriptor(
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
    
    def to_serializable_descriptor(self) -> 'QueueDescriptor':
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
        
        return QueueDescriptor(
            queue_id=self.queue_id,
            queue_type=self.queue_type,
            metadata=serializable_metadata,
            can_serialize=True,
            created_timestamp=self.created_timestamp
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueueDescriptor':
        """从字典创建实例"""
        return cls(
            queue_id=data['queue_id'],
            queue_type=data['queue_type'],
            metadata=data.get('metadata', {}),
            can_serialize=data.get('can_serialize', True),
            created_timestamp=data.get('created_timestamp')
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'QueueDescriptor':
        """从JSON字符串创建实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    # ============ 工厂方法 ============
    
    @classmethod
    def create_local_queue(cls, queue_id: Optional[str] = None, maxsize: int = 0, 
                          queue_instance: Optional[Any] = None) -> 'QueueDescriptor':
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
                        maxsize: int = 1000) -> 'QueueDescriptor':
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
                              maxsize: int = 0) -> 'QueueDescriptor':
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
    def create_ray_queue(cls, queue_id: Optional[str] = None, maxsize: int = 0) -> 'QueueDescriptor':
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
                        queue_id: Optional[str] = None) -> 'QueueDescriptor':
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
            },
            can_serialize=True
        )
    
    @classmethod
    def from_existing_queue(cls, queue_instance: Any, queue_type: str, 
                           queue_id: Optional[str] = None, **metadata) -> 'QueueDescriptor':
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
        return f"QueueDescriptor(id='{self.queue_id}', type='{self.queue_type}', {status})"
    
    def __str__(self) -> str:
        return f"Queue[{self.queue_type}]({self.queue_id})"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, QueueDescriptor):
            return False
        return (self.queue_id == other.queue_id and 
                self.queue_type == other.queue_type and
                self.metadata == other.metadata)
    
    def __hash__(self) -> int:
        return hash((self.queue_id, self.queue_type))


# ============ 便利函数 ============

def resolve_descriptor(desc: QueueDescriptor) -> Any:
    """
    解析队列描述符，返回队列实例
    
    Args:
        desc: 队列描述符
        
    Returns:
        队列实例
    """
    return desc._ensure_queue_initialized()


def create_descriptor_from_existing_queue(queue: Any, queue_type: str, 
                                        queue_id: Optional[str] = None, 
                                        **metadata) -> QueueDescriptor:
    """从现有队列创建描述符"""
    return QueueDescriptor.from_existing_queue(
        queue_instance=queue,
        queue_type=queue_type,
        queue_id=queue_id,
        **metadata
    )


# ============ 工厂便利函数 ============

def get_local_queue(queue_id: Optional[str] = None, maxsize: int = 0) -> QueueDescriptor:
    """获取本地队列描述符"""
    return QueueDescriptor.create_local_queue(queue_id, maxsize)


def attach_to_shm_queue(shm_name: str, queue_id: Optional[str] = None, 
                       maxsize: int = 1000) -> QueueDescriptor:
    """附着到共享内存队列"""
    return QueueDescriptor.create_shm_queue(shm_name, queue_id, maxsize)


def get_ray_actor_queue(actor_name: str, queue_id: Optional[str] = None, 
                       maxsize: int = 0) -> QueueDescriptor:
    """获取Ray Actor队列"""
    return QueueDescriptor.create_ray_actor_queue(actor_name, queue_id, maxsize)


def get_ray_queue(queue_id: Optional[str] = None, maxsize: int = 0) -> QueueDescriptor:
    """获取Ray分布式队列"""
    return QueueDescriptor.create_ray_queue(queue_id, maxsize)


def get_rpc_queue(server_address: str, port: int, 
                 queue_id: Optional[str] = None) -> QueueDescriptor:
    """获取RPC队列"""
    return QueueDescriptor.create_rpc_queue(server_address, port, queue_id)


def get_sage_queue(queue_id: Optional[str] = None, maxsize: int = 1000) -> QueueDescriptor:
    """获取SAGE高性能队列"""
    return QueueDescriptor.create_sage_queue(queue_id, maxsize)


# ============ 批量操作工具 ============

def create_queue_pool(queue_configs: list, pool_id: Optional[str] = None) -> Dict[str, QueueDescriptor]:
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
        
        descriptor = QueueDescriptor(
            queue_id=queue_id,
            queue_type=queue_type,
            metadata=config
        )
        pool[queue_id] = descriptor
    
    return pool


def serialize_queue_pool(pool: Dict[str, QueueDescriptor]) -> str:
    """序列化队列池"""
    serializable_pool = {}
    for queue_id, descriptor in pool.items():
        if descriptor.can_serialize:
            serializable_pool[queue_id] = descriptor.to_dict()
        else:
            serializable_pool[queue_id] = descriptor.to_serializable_descriptor().to_dict()
    
    return json.dumps(serializable_pool)


def deserialize_queue_pool(json_str: str) -> Dict[str, QueueDescriptor]:
    """反序列化队列池"""
    data = json.loads(json_str)
    pool = {}
    for queue_id, descriptor_data in data.items():
        pool[queue_id] = QueueDescriptor.from_dict(descriptor_data)
    return pool
