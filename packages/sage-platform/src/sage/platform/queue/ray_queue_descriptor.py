"""
Ray Queue Descriptor - Ray分布式队列描述符

支持Ray分布式队列和Ray Actor队列
"""

import logging
import queue
import threading
from typing import TYPE_CHECKING, Any, Optional

import ray

from .base_queue_descriptor import BaseQueueDescriptor

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SimpleTestQueue:
    """测试模式下的简单队列实现，避开Ray队列的async actor限制"""

    def __init__(self, maxsize=0):
        self._queue = queue.Queue(maxsize=maxsize)
        self._lock = threading.Lock()

    def put(self, item, timeout=None):
        """添加项目到队列"""
        return self._queue.put(item, timeout=timeout)

    def get(self, timeout=None):
        """从队列获取项目"""
        return self._queue.get(timeout=timeout)

    def size(self):
        """获取队列大小"""
        return self._queue.qsize()

    def qsize(self):
        """获取队列大小（兼容性方法）"""
        return self._queue.qsize()

    def empty(self):
        """检查队列是否为空"""
        return self._queue.empty()

    def full(self):
        """检查队列是否已满"""
        return self._queue.full()


def _is_ray_local_mode():
    """检查Ray是否在local mode下运行"""
    try:
        if not ray.is_initialized():
            return False
        ctx = ray.get_runtime_context()
        return ctx.worker.mode == ray.LOCAL_MODE
    except Exception:
        return False


class RayQueueProxy:
    """Ray队列代理，提供类似队列的接口但通过manager访问实际队列"""

    def __init__(self, manager, queue_id: str):
        self.manager = manager
        self.queue_id = queue_id

    def put(self, item, timeout=None):
        """向队列添加项目"""
        return ray.get(self.manager.put.remote(self.queue_id, item))

    def put_nowait(self, item):
        """非阻塞添加项目到队列（实际上Ray队列始终是阻塞的）"""
        return ray.get(self.manager.put.remote(self.queue_id, item))

    def get(self, block=True, timeout=None):
        """从队列获取项目

        Args:
            block: 是否阻塞等待（为了API兼容性，但Ray队列始终是阻塞的）
            timeout: 超时时间（秒）
        """
        # Ray队列不支持非阻塞模式，block参数仅用于API兼容性
        return ray.get(self.manager.get.remote(self.queue_id, timeout))

    def size(self):
        """获取队列大小"""
        return ray.get(self.manager.size.remote(self.queue_id))

    def qsize(self):
        """获取队列大小（兼容性方法）"""
        return self.size()

    def empty(self):
        """检查队列是否为空"""
        return self.size() == 0

    def full(self):
        """检查队列是否已满（简化实现）"""
        # 对于Ray队列，这个很难确定，返回False
        return False


# 全局队列管理器，用于在不同Actor之间共享队列实例
@ray.remote
class RayQueueManager:
    """Ray队列管理器，管理全局队列实例"""

    def __init__(self):
        self.queues = {}

    def get_or_create_queue(self, queue_id: str, maxsize: int):
        """获取或创建队列，返回队列ID而不是队列对象"""
        if queue_id not in self.queues:
            # 在local mode下使用简单队列实现
            if _is_ray_local_mode():
                self.queues[queue_id] = SimpleTestQueue(maxsize=maxsize if maxsize > 0 else 0)
                logger.debug(f"Created new SimpleTestQueue {queue_id} (local mode)")
            else:
                # 在分布式模式下使用Ray原生队列
                try:
                    from ray.util.queue import Queue

                    # Ray Queue expects int for maxsize, where 0 means unlimited
                    self.queues[queue_id] = Queue(maxsize=maxsize if maxsize > 0 else 0)
                    logger.debug(f"Created new Ray queue {queue_id} (distributed mode)")
                except Exception as e:
                    # 如果Ray队列创建失败，回退到简单队列
                    logger.warning(
                        f"Failed to create Ray queue, falling back to SimpleTestQueue: {e}"
                    )
                    self.queues[queue_id] = SimpleTestQueue(maxsize=maxsize if maxsize > 0 else 0)
        else:
            logger.debug(f"Retrieved existing queue {queue_id}")
        return queue_id  # 返回队列ID而不是队列对象

    def put(self, queue_id: str, item):
        """向指定队列添加项目"""
        if queue_id in self.queues:
            return self.queues[queue_id].put(item)
        else:
            raise ValueError(f"Queue {queue_id} does not exist")

    def get(self, queue_id: str, timeout=None):
        """从指定队列获取项目"""
        if queue_id in self.queues:
            return self.queues[queue_id].get(timeout=timeout)
        else:
            raise ValueError(f"Queue {queue_id} does not exist")

    def size(self, queue_id: str):
        """获取队列大小"""
        if queue_id in self.queues:
            if hasattr(self.queues[queue_id], "size"):
                return self.queues[queue_id].size()
            else:
                # 对于标准Queue，没有size方法，使用qsize
                return self.queues[queue_id].qsize()
        else:
            raise ValueError(f"Queue {queue_id} does not exist")

    def queue_exists(self, queue_id: str):
        """检查队列是否存在"""
        return queue_id in self.queues

    def delete_queue(self, queue_id: str):
        """删除队列"""
        if queue_id in self.queues:
            del self.queues[queue_id]
            return True
        return False


# 全局队列管理器实例
_global_queue_manager: Any = None


def get_global_queue_manager() -> Any:
    """获取全局队列管理器

    Returns:
        ActorHandle: RayQueueManager的ActorHandle，具有RayQueueManager的所有方法
    """
    import random
    import time

    # 先尝试获取现有的命名Actor
    try:
        return ray.get_actor("global_ray_queue_manager")
    except ValueError:
        pass

    # 多次尝试创建命名Actor，处理并发冲突
    for attempt in range(3):
        try:
            # 如果不存在，创建新的命名Actor
            global _global_queue_manager
            _global_queue_manager = RayQueueManager.options(
                name="global_ray_queue_manager"
            ).remote()
            return _global_queue_manager
        except ValueError as e:
            # 如果Actor已存在，再次尝试获取
            if "already exists" in str(e):
                try:
                    return ray.get_actor("global_ray_queue_manager")
                except ValueError:
                    # 短暂等待后重试
                    time.sleep(random.uniform(0.1, 0.5))
                    continue
            else:
                raise
        except Exception:
            # 其他错误，短暂等待后重试
            time.sleep(random.uniform(0.1, 0.5))
            if attempt == 2:  # 最后一次尝试
                raise

    # 如果仍然失败，尝试最后一次获取
    return ray.get_actor("global_ray_queue_manager")


class RayQueueDescriptor(BaseQueueDescriptor):
    """
    Ray分布式队列描述符

    支持：
    - ray.util.Queue (Ray原生分布式队列)
    """

    def __init__(self, maxsize: int = 1024 * 1024, queue_id: Optional[str] = None):
        """
        初始化Ray队列描述符

        Args:
            maxsize: 队列最大大小，0表示无限制
            queue_id: 队列唯一标识符
        """
        self.maxsize = maxsize
        self._queue = None  # 延迟初始化
        super().__init__(queue_id=queue_id)

    @property
    def queue_type(self) -> str:
        """队列类型标识符"""
        return "ray_queue"

    @property
    def can_serialize(self) -> bool:
        """Ray队列可以序列化"""
        return True

    @property
    def metadata(self) -> dict[str, Any]:
        """元数据字典"""
        return {"maxsize": self.maxsize}

    @property
    def queue_instance(self) -> Any:
        """获取队列实例 - 返回一个代理对象而不是真实的队列"""
        if self._queue is None:
            manager = get_global_queue_manager()
            # 确保队列被创建，但不获取队列对象本身
            ray.get(manager.get_or_create_queue.remote(self.queue_id, self.maxsize))
            # 返回一个队列代理对象
            self._queue = RayQueueProxy(manager, self.queue_id)
        return self._queue

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典，包含队列元信息"""
        return {
            "queue_type": self.queue_type,
            "queue_id": self.queue_id,
            "metadata": self.metadata,
            "created_timestamp": self.created_timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RayQueueDescriptor":
        """从字典反序列化"""
        # 确保maxsize是整数
        maxsize = data["metadata"].get("maxsize", 1024 * 1024)
        if isinstance(maxsize, str):
            try:
                maxsize = int(maxsize)
            except ValueError:
                maxsize = 1024 * 1024  # 默认值

        instance = cls(
            maxsize=maxsize,
            queue_id=data["queue_id"],
        )
        instance.created_timestamp = data.get("created_timestamp", instance.created_timestamp)
        return instance
