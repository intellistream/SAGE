"""
Ray Queue Descriptor - Ray分布式队列描述符

支持Ray分布式队列和Ray Actor队列
"""

import logging
import queue
import threading
from typing import Any, Optional

import ray
import ray.actor

from .base_queue_descriptor import BaseQueueDescriptor

logger = logging.getLogger(__name__)


class SimpleTestQueue:
    """测试模式下的简单队列实现，避开Ray队列的async actor限制"""

    def __init__(self, maxsize: int = 0) -> None:
        self._queue: queue.Queue[Any] = queue.Queue(maxsize=maxsize)
        self._lock = threading.Lock()

    def put(self, item: Any, timeout: Optional[float] = None) -> None:
        """添加项目到队列"""
        return self._queue.put(item, timeout=timeout)

    def get(self, timeout: Optional[float] = None) -> Any:
        """从队列获取项目"""
        return self._queue.get(timeout=timeout)

    def size(self) -> int:
        """获取队列大小"""
        return self._queue.qsize()

    def qsize(self) -> int:
        """获取队列大小（兼容性方法）"""
        return self._queue.qsize()

    def empty(self) -> bool:
        """检查队列是否为空"""
        return self._queue.empty()

    def full(self) -> bool:
        """检查队列是否已满"""
        return self._queue.full()


def _is_ray_local_mode() -> bool:
    """检查Ray是否在local mode下运行"""
    try:
        return ray._private.worker.global_worker.mode == ray._private.worker.LOCAL_MODE  # type: ignore[attr-defined]
    except Exception:
        return False


class RayQueueProxy:
    """
    Ray队列代理 - 优化版本，支持批量异步操作

    性能优化：
    1. 批量put操作，减少网络往返
    2. 异步提交，避免同步等待
    3. 智能缓冲区管理
    """

    def __init__(
        self,
        manager: "ray.actor.ActorHandle[Any]",
        queue_id: str,
        batch_size: int = 100,
        auto_flush: bool = True,
    ) -> None:
        """
        初始化队列代理

        Args:
            manager: RayQueueManager实例
            queue_id: 队列ID
            batch_size: 批量操作大小，默认100（建议范围：50-500）
            auto_flush: 是否自动刷新缓冲区
        """
        self.manager: ray.actor.ActorHandle[Any] = manager
        self.queue_id = queue_id
        self.batch_size = batch_size
        self.auto_flush = auto_flush

        # Put缓冲区
        self._put_buffer: list[Any] = []
        self._put_lock = threading.Lock()
        self._pending_put_futures: list[ray.ObjectRef[Any]] = []

        # 性能统计
        self._total_puts = 0
        self._total_gets = 0
        self._batch_puts = 0

    def put(self, item: Any, timeout: Optional[float] = None) -> None:
        """
        向队列添加项目（优化版 - 批量异步）

        性能优化：使用缓冲区批量发送，减少网络往返次数
        """
        with self._put_lock:
            self._put_buffer.append(item)
            self._total_puts += 1

            # 达到批量大小时自动刷新
            if self.auto_flush and len(self._put_buffer) >= self.batch_size:
                self._flush_internal()

        return None  # 异步操作，立即返回

    def put_nowait(self, item: Any) -> None:
        """非阻塞添加项目到队列"""
        return self.put(item, timeout=None)

    def flush(self) -> None:
        """手动刷新缓冲区，将所有待发送的数据批量提交"""
        with self._put_lock:
            self._flush_internal()

    def _flush_internal(self) -> None:
        """内部刷新方法（需要持有锁）"""
        if not self._put_buffer:
            return

        # 批量远程调用
        items_to_send = self._put_buffer.copy()
        self._put_buffer.clear()

        try:
            # 异步批量发送
            future = self.manager.put_batch.remote(self.queue_id, items_to_send)
            self._pending_put_futures.append(future)
            self._batch_puts += 1

            # 定期清理已完成的futures，避免内存累积
            if len(self._pending_put_futures) > 10:
                self._pending_put_futures = [
                    f for f in self._pending_put_futures if not self._is_future_ready(f)
                ]

            logger.debug(
                f"Batch put {len(items_to_send)} items to queue {self.queue_id} "
                f"(total batches: {self._batch_puts})"
            )
        except Exception as e:
            # 批量发送失败，回退到单个发送
            logger.warning(f"Batch put failed, falling back to individual puts: {e}")
            for item in items_to_send:
                try:
                    ray.get(self.manager.put.remote(self.queue_id, item))
                except Exception as e2:
                    logger.error(f"Individual put also failed: {e2}")
                    raise

    def _is_future_ready(self, future: Any) -> bool:
        """检查future是否已完成"""
        try:
            ray.get(future, timeout=0)
            return True
        except Exception:
            return False

    def wait_for_pending_puts(self, timeout: float = 10.0) -> None:
        """
        等待所有待处理的put操作完成

        Args:
            timeout: 超时时间（秒）
        """
        if self._pending_put_futures:
            try:
                ray.get(self._pending_put_futures, timeout=timeout)
                self._pending_put_futures.clear()
                logger.debug(f"All pending puts completed for queue {self.queue_id}")
            except Exception as e:
                logger.warning(f"Some pending puts may have failed: {e}")

    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """
        从队列获取项目

        Note: get操作保持同步（因为需要立即返回数据）
        """
        self._total_gets += 1
        return ray.get(self.manager.get.remote(self.queue_id, timeout))

    def get_batch(self, count: int = 100, timeout: Optional[float] = None) -> list[Any]:
        """
        批量获取多个项目（优化版）

        Args:
            count: 要获取的项目数量
            timeout: 超时时间

        Returns:
            list: 获取到的项目列表
        """
        self._total_gets += count
        return ray.get(self.manager.get_batch.remote(self.queue_id, count, timeout))

    def size(self) -> int:
        """获取队列大小（包含待刷新的缓冲区）"""
        remote_size = ray.get(self.manager.size.remote(self.queue_id))
        with self._put_lock:
            buffer_size: int = len(self._put_buffer)
        return int(remote_size) + buffer_size

    def qsize(self) -> int:
        """获取队列大小（兼容性方法）"""
        return self.size()

    def empty(self) -> bool:
        """检查队列是否为空"""
        return self.size() == 0

    def full(self) -> bool:
        """检查队列是否已满（简化实现）"""
        # 对于Ray队列，这个很难确定，返回False
        return False

    def get_stats(self) -> dict[str, Any]:
        """
        获取性能统计信息

        Returns:
            dict: 包含total_puts, total_gets, batch_puts等统计信息
        """
        return {
            "total_puts": self._total_puts,
            "total_gets": self._total_gets,
            "batch_puts": self._batch_puts,
            "avg_batch_size": self._total_puts / max(1, self._batch_puts),
            "pending_batches": len(self._pending_put_futures),
            "buffer_size": len(self._put_buffer),
        }

    def __del__(self):
        """析构时自动刷新缓冲区"""
        try:
            if hasattr(self, "_put_buffer") and self._put_buffer:
                logger.debug(f"Flushing {len(self._put_buffer)} items on destruction")
                self.flush()
                self.wait_for_pending_puts(timeout=5.0)
        except Exception as e:
            logger.warning(f"Error during queue proxy cleanup: {e}")


# 全局队列管理器，用于在不同Actor之间共享队列实例
@ray.remote
class RayQueueManager:
    """
    Ray队列管理器 - 优化版本，支持批量操作

    管理全局队列实例，提供批量put/get操作以提升分布式性能
    """

    def __init__(self) -> None:
        self.queues: dict[str, Any] = {}
        # 性能统计
        self._stats: dict[str, int] = {
            "total_puts": 0,
            "total_gets": 0,
            "batch_puts": 0,
            "batch_gets": 0,
        }

    def get_or_create_queue(self, queue_id: str, maxsize: int) -> str:
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

                    queue_maxsize = maxsize if maxsize > 0 else 0
                    self.queues[queue_id] = Queue(maxsize=queue_maxsize)
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

    def put(self, queue_id: str, item: Any) -> Any:
        """向指定队列添加项目（单个）"""
        if queue_id in self.queues:
            self._stats["total_puts"] += 1
            return self.queues[queue_id].put(item)
        else:
            raise ValueError(f"Queue {queue_id} does not exist")

    def put_batch(self, queue_id: str, items: list[Any]) -> int:
        """
        批量添加项目（性能优化）

        Args:
            queue_id: 队列ID
            items: 要添加的项目列表

        Returns:
            int: 成功添加的项目数量
        """
        if queue_id not in self.queues:
            raise ValueError(f"Queue {queue_id} does not exist")

        q = self.queues[queue_id]
        count = 0

        for item in items:
            try:
                q.put(item)
                count += 1
            except queue.Full:
                logger.warning(f"Queue {queue_id} is full, dropped {len(items) - count} items")
                break

        self._stats["total_puts"] += count
        self._stats["batch_puts"] += 1

        logger.debug(f"Batch put {count} items to queue {queue_id}")
        return count

    def get(self, queue_id: str, timeout: Optional[float] = None) -> Any:
        """从指定队列获取项目（单个）"""
        if queue_id in self.queues:
            self._stats["total_gets"] += 1
            return self.queues[queue_id].get(timeout=timeout)
        else:
            raise ValueError(f"Queue {queue_id} does not exist")

    def get_batch(self, queue_id: str, count: int, timeout: Optional[float] = None) -> list[Any]:
        """
        批量获取项目（性能优化）

        Args:
            queue_id: 队列ID
            count: 要获取的项目数量
            timeout: 超时时间（秒），应用于每个get操作

        Returns:
            list: 获取到的项目列表（可能少于count）
        """
        if queue_id not in self.queues:
            raise ValueError(f"Queue {queue_id} does not exist")

        q = self.queues[queue_id]
        results: list[Any] = []

        def _get_item_timeout(i: int, timeout: Optional[float]) -> float:
            """
            Helper to determine timeout for each item in batch get.
            First item uses provided timeout, subsequent items use min(0.1, timeout) if timeout is set, else 0.1.
            """
            if i == 0:
                return timeout
            if timeout:
                return min(0.1, timeout)
            return 0.1

        for i in range(count):
            try:
                # 第一个item使用提供的timeout，后续使用更短的timeout避免整体阻塞
                item_timeout = _get_item_timeout(i, timeout)
                item = q.get(timeout=item_timeout)
                results.append(item)
            except queue.Empty:
                # 队列为空，返回已获取的项目
                break

        self._stats["total_gets"] += len(results)
        if results:
            self._stats["batch_gets"] += 1

        logger.debug(f"Batch get {len(results)} items from queue {queue_id}")
        return results

    def size(self, queue_id: str) -> int:
        """获取队列大小"""
        if queue_id in self.queues:
            if hasattr(self.queues[queue_id], "size"):
                return self.queues[queue_id].size()
            else:
                # 对于标准Queue，没有size方法，使用qsize
                return self.queues[queue_id].qsize()
        else:
            raise ValueError(f"Queue {queue_id} does not exist")

    def queue_exists(self, queue_id: str) -> bool:
        """检查队列是否存在"""
        return queue_id in self.queues

    def delete_queue(self, queue_id: str) -> bool:
        """删除队列"""
        if queue_id in self.queues:
            del self.queues[queue_id]
            return True
        return False

    def get_stats(self) -> dict[str, int]:
        """
        获取性能统计信息

        Returns:
            dict: 统计信息
        """
        return self._stats.copy()


# 全局队列管理器实例
_global_queue_manager = None


def get_global_queue_manager() -> "ray.actor.ActorHandle[Any]":
    """获取全局队列管理器"""
    import random
    import time

    # 先尝试获取现有的命名Actor
    try:
        return ray.get_actor("global_ray_queue_manager")  # type: ignore[return-value]
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
            return _global_queue_manager  # type: ignore[return-value]
        except ValueError as e:
            # 如果Actor已存在，再次尝试获取
            if "already exists" in str(e):
                try:
                    return ray.get_actor("global_ray_queue_manager")  # type: ignore[return-value]
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
    return ray.get_actor("global_ray_queue_manager")  # type: ignore[return-value]


class RayQueueDescriptor(BaseQueueDescriptor):
    """
    Ray分布式队列描述符

    支持：
    - ray.util.Queue (Ray原生分布式队列)
    """

    def __init__(self, maxsize: int = 1024 * 1024, queue_id: str | None = None):
        """
        初始化Ray队列描述符

        Args:
            maxsize: 队列最大大小，0表示无限制
            queue_id: 队列唯一标识符
        """
        self.maxsize = maxsize
        self._queue: Any = None  # 延迟初始化
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
            ray.get(manager.get_or_create_queue.remote(self.queue_id, self.maxsize))  # type: ignore
            # 返回一个队列代理对象
            self._queue = RayQueueProxy(manager, self.queue_id)
        return self._queue

    def to_dict(self, include_non_serializable: bool = False) -> dict[str, Any]:
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
