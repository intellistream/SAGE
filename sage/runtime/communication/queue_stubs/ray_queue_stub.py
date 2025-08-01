"""
Ray Queue Stub - Ray 分布式队列的封装实现

提供 Ray Queue 与 Queue Descriptor 之间的转换方法
支持 Ray Actor Queue 和 Ray 原生分布式队列
"""

import logging
import time
from typing import Any, Optional, Dict, Union
from ..queue_descriptor import QueueDescriptor, QueueLike

logger = logging.getLogger(__name__)


class RayQueueStub:
    """
    Ray Queue 的封装类，实现 QueueLike 接口
    
    支持两种 Ray 队列类型：
    1. ray_queue: Ray 原生分布式队列
    2. ray_actor: Ray Actor 队列
    
    支持与 QueueDescriptor 的双向转换
    """
    
    def __init__(self, descriptor: QueueDescriptor):
        """
        从 QueueDescriptor 初始化 Ray Queue
        
        Args:
            descriptor: 队列描述符
        """
        if descriptor.queue_type not in ["ray_queue", "ray_actor"]:
            raise ValueError(f"Expected ray_queue or ray_actor, got {descriptor.queue_type}")
        
        self.descriptor = descriptor
        self._ray_queue = None
        self._ray_actor = None
        self._queue_type = descriptor.queue_type
        self._initialize_ray_queue()
    
    def _initialize_ray_queue(self):
        """初始化底层的 Ray Queue"""
        try:
            import ray
            
            if not ray.is_initialized():
                logger.warning("Ray is not initialized, attempting to initialize...")
                ray.init()
            
            if self._queue_type == "ray_queue":
                self._initialize_ray_native_queue()
            elif self._queue_type == "ray_actor":
                self._initialize_ray_actor_queue()
                
        except ImportError as e:
            logger.error(f"Failed to import Ray: {e}")
            raise RuntimeError(f"Ray not available: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize Ray Queue: {e}")
            raise
    
    def _initialize_ray_native_queue(self):
        """初始化 Ray 原生分布式队列"""
        import ray
        
        maxsize = self.descriptor.metadata.get('maxsize', 0)
        queue_id = self.descriptor.queue_id
        
        # Ray 的分布式队列
        self._ray_queue = ray.util.queue.Queue(maxsize=maxsize)
        logger.info(f"Successfully initialized Ray native queue: {queue_id}")
    
    def _initialize_ray_actor_queue(self):
        """初始化 Ray Actor 队列"""
        import ray
        
        actor_name = self.descriptor.metadata.get('actor_name')
        if not actor_name:
            raise ValueError("Ray Actor queue requires 'actor_name' in metadata")
        
        try:
            # 尝试获取现有的 Actor
            self._ray_actor = ray.get_actor(actor_name)
            logger.info(f"Connected to existing Ray Actor: {actor_name}")
        except ValueError:
            # Actor 不存在，创建新的
            maxsize = self.descriptor.metadata.get('maxsize', 0)
            actor_class = self.descriptor.metadata.get('actor_class', 'QueueActor')
            
            # 动态创建 QueueActor 类
            if actor_class == 'QueueActor':
                @ray.remote
                class QueueActor:
                    def __init__(self, maxsize=0):
                        from queue import Queue
                        self._queue = Queue(maxsize=maxsize)
                    
                    def put(self, item, block=True, timeout=None):
                        return self._queue.put(item, block=block, timeout=timeout)
                    
                    def get(self, block=True, timeout=None):
                        return self._queue.get(block=block, timeout=timeout)
                    
                    def empty(self):
                        return self._queue.empty()
                    
                    def qsize(self):
                        return self._queue.qsize()
                    
                    def full(self):
                        return self._queue.full()
                
                # 创建 Actor 实例
                self._ray_actor = QueueActor.options(name=actor_name).remote(maxsize=maxsize)
                logger.info(f"Created new Ray Actor: {actor_name}")
            else:
                raise ValueError(f"Unsupported actor_class: {actor_class}")
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        """向队列添加元素"""
        if self._queue_type == "ray_queue":
            return self._put_ray_queue(item, block, timeout)
        elif self._queue_type == "ray_actor":
            return self._put_ray_actor(item, block, timeout)
    
    def _put_ray_queue(self, item: Any, block: bool, timeout: Optional[float]):
        """向 Ray 原生队列添加元素"""
        import ray
        
        if self._ray_queue is None:
            raise RuntimeError("Ray queue not initialized")
        
        # Ray 原生队列的 put 方法
        if block:
            if timeout is not None:
                # Ray 队列不直接支持超时，需要手动实现
                start_time = time.time()
                while True:
                    try:
                        self._ray_queue.put(item, block=False)
                        return
                    except ray.util.queue.Full:
                        if time.time() - start_time > timeout:
                            from queue import Full
                            raise Full("Ray queue put timeout")
                        time.sleep(0.01)  # 短暂等待
            else:
                self._ray_queue.put(item, block=True)
        else:
            self._ray_queue.put(item, block=False)
    
    def _put_ray_actor(self, item: Any, block: bool, timeout: Optional[float]):
        """向 Ray Actor 队列添加元素"""
        import ray
        
        if self._ray_actor is None:
            raise RuntimeError("Ray actor not initialized")
        
        # 调用 Actor 的 put 方法
        future = self._ray_actor.put.remote(item, block=block, timeout=timeout)
        
        if block:
            if timeout is not None:
                try:
                    return ray.get(future, timeout=timeout)
                except ray.exceptions.GetTimeoutError:
                    from queue import Full
                    raise Full("Ray actor put timeout")
            else:
                return ray.get(future)
        else:
            # 非阻塞模式，立即返回，不等待结果
            return ray.get(future)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """从队列获取元素"""
        if self._queue_type == "ray_queue":
            return self._get_ray_queue(block, timeout)
        elif self._queue_type == "ray_actor":
            return self._get_ray_actor(block, timeout)
    
    def _get_ray_queue(self, block: bool, timeout: Optional[float]):
        """从 Ray 原生队列获取元素"""
        import ray
        
        if self._ray_queue is None:
            raise RuntimeError("Ray queue not initialized")
        
        if block:
            if timeout is not None:
                # Ray 队列不直接支持超时，需要手动实现
                start_time = time.time()
                while True:
                    try:
                        return self._ray_queue.get(block=False)
                    except ray.util.queue.Empty:
                        if time.time() - start_time > timeout:
                            from queue import Empty
                            raise Empty("Ray queue get timeout")
                        time.sleep(0.01)  # 短暂等待
            else:
                return self._ray_queue.get(block=True)
        else:
            return self._ray_queue.get(block=False)
    
    def _get_ray_actor(self, block: bool, timeout: Optional[float]):
        """从 Ray Actor 队列获取元素"""
        import ray
        
        if self._ray_actor is None:
            raise RuntimeError("Ray actor not initialized")
        
        # 调用 Actor 的 get 方法
        future = self._ray_actor.get.remote(block=block, timeout=timeout)
        
        if block:
            if timeout is not None:
                try:
                    return ray.get(future, timeout=timeout)
                except ray.exceptions.GetTimeoutError:
                    from queue import Empty
                    raise Empty("Ray actor get timeout")
            else:
                return ray.get(future)
        else:
            return ray.get(future)
    
    def put_nowait(self, item: Any) -> None:
        """非阻塞添加元素"""
        return self.put(item, block=False)
    
    def get_nowait(self) -> Any:
        """非阻塞获取元素"""
        return self.get(block=False)
    
    def empty(self) -> bool:
        """检查队列是否为空"""
        if self._queue_type == "ray_queue":
            if self._ray_queue is None:
                return True
            return self._ray_queue.empty()
        elif self._queue_type == "ray_actor":
            if self._ray_actor is None:
                return True
            import ray
            return ray.get(self._ray_actor.empty.remote())
    
    def qsize(self) -> int:
        """获取队列大小"""
        if self._queue_type == "ray_queue":
            if self._ray_queue is None:
                return 0
            return self._ray_queue.qsize()
        elif self._queue_type == "ray_actor":
            if self._ray_actor is None:
                return 0
            import ray
            return ray.get(self._ray_actor.qsize.remote())
    
    def full(self) -> bool:
        """检查队列是否已满"""
        if self._queue_type == "ray_queue":
            if self._ray_queue is None:
                return False
            return self._ray_queue.full()
        elif self._queue_type == "ray_actor":
            if self._ray_actor is None:
                return False
            import ray
            return ray.get(self._ray_actor.full.remote())
    
    def to_descriptor(self) -> QueueDescriptor:
        """
        将当前 Ray Queue 转换为 QueueDescriptor
        
        Returns:
            对应的队列描述符
        """
        return self.descriptor
    
    @classmethod
    def from_descriptor(cls, descriptor: QueueDescriptor) -> 'RayQueueStub':
        """
        从 QueueDescriptor 创建 RayQueueStub 实例
        
        Args:
            descriptor: 队列描述符
            
        Returns:
            RayQueueStub 实例
        """
        return cls(descriptor)
    
    @classmethod
    def from_ray_queue(cls, ray_queue, queue_type: str = "ray_queue", 
                      queue_id: Optional[str] = None, **metadata) -> 'RayQueueStub':
        """
        从现有的 Ray Queue 对象创建 RayQueueStub
        
        Args:
            ray_queue: 现有的 Ray Queue 对象或 Actor
            queue_type: 队列类型 ("ray_queue" 或 "ray_actor")
            queue_id: 队列ID
            **metadata: 额外的元数据
            
        Returns:
            RayQueueStub 实例
        """
        if queue_id is None:
            queue_id = f"{queue_type}_{id(ray_queue)}"
        
        # 根据队列类型设置默认元数据
        if queue_type == "ray_queue":
            default_metadata = {
                'maxsize': getattr(ray_queue, '_maxsize', 0)
            }
        elif queue_type == "ray_actor":
            default_metadata = {
                'actor_name': metadata.get('actor_name', f'actor_{id(ray_queue)}'),
                'maxsize': 0
            }
        else:
            raise ValueError(f"Unsupported queue_type: {queue_type}")
        
        # 合并用户提供的元数据
        default_metadata.update(metadata)
        
        # 创建描述符
        descriptor = QueueDescriptor(
            queue_id=queue_id,
            queue_type=queue_type,
            metadata=default_metadata
        )
        
        # 创建 stub 实例
        stub = cls(descriptor)
        
        # 直接使用传入的 ray_queue 对象，而不是重新创建
        if queue_type == "ray_queue":
            stub._ray_queue = ray_queue
        elif queue_type == "ray_actor":
            stub._ray_actor = ray_queue
        
        return stub
    
    def __repr__(self) -> str:
        return f"RayQueueStub(queue_id='{self.descriptor.queue_id}', type='{self.descriptor.queue_type}')"


# 便利函数
def create_ray_queue_descriptor(queue_id: Optional[str] = None, 
                               maxsize: int = 0) -> QueueDescriptor:
    """
    创建 Ray 原生队列描述符的便利函数
    
    Args:
        queue_id: 队列ID
        maxsize: 最大大小
        
    Returns:
        Ray Queue 描述符
    """
    return QueueDescriptor.create_ray_queue(queue_id=queue_id, maxsize=maxsize)


def create_ray_actor_queue_descriptor(actor_name: str,
                                     queue_id: Optional[str] = None, 
                                     maxsize: int = 0) -> QueueDescriptor:
    """
    创建 Ray Actor 队列描述符的便利函数
    
    Args:
        actor_name: Actor 名称
        queue_id: 队列ID
        maxsize: 最大大小
        
    Returns:
        Ray Actor Queue 描述符
    """
    return QueueDescriptor.create_ray_actor_queue(
        actor_name=actor_name, 
        queue_id=queue_id, 
        maxsize=maxsize
    )


def ray_queue_from_descriptor(descriptor: QueueDescriptor) -> RayQueueStub:
    """
    从描述符创建 Ray Queue 的便利函数
    
    Args:
        descriptor: 队列描述符
        
    Returns:
        RayQueueStub 实例
    """
    return RayQueueStub.from_descriptor(descriptor)
