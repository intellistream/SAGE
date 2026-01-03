"""
Ray Queue Descriptor - Ray分布式队列描述符

支持Ray分布式队列和Ray Actor队列
"""

import os
import queue
from typing import TYPE_CHECKING, Any, Optional

import ray

from .base_queue_descriptor import BaseQueueDescriptor

if TYPE_CHECKING:
    from sage.common.utils.logging.custom_logger import CustomLogger

# 使用 SAGE 的 CustomLogger，输出到统一的日志目录
_logger: "CustomLogger | None" = None


def _get_logger() -> "CustomLogger":
    """获取或创建 CustomLogger 实例"""
    global _logger
    if _logger is None:
        from sage.common.utils.logging.custom_logger import CustomLogger

        # 获取日志目录：
        # 1. 优先使用环境变量 SAGE_LOG_DIR（运行时设置，通常由 TaskContext 设置）
        # 2. 否则使用当前工作目录下的 .sage/logs/ 目录
        log_base_dir = os.environ.get("SAGE_LOG_DIR")
        if not log_base_dir:
            # 转换为绝对路径（CustomLogger 要求）
            log_base_dir = os.path.abspath(".sage/logs")

        os.makedirs(log_base_dir, exist_ok=True)

        _logger = CustomLogger(
            [
                ("console", "DEBUG"),  # 控制台显示 DEBUG 及以上（与其他组件一致）
                (os.path.join(log_base_dir, "ray_queue_debug.log"), "DEBUG"),  # 详细调试日志
                (os.path.join(log_base_dir, "ray_queue_info.log"), "INFO"),  # 信息日志
                (os.path.join(log_base_dir, "Error.log"), "ERROR"),  # 错误日志（统一文件名）
            ],
            name="RayQueue",
        )
    return _logger


# 兼容性：提供 logger 变量，但实际使用时会调用 _get_logger()
class _LoggerProxy:
    """Logger 代理，延迟初始化 CustomLogger"""

    def __getattr__(self, name):
        return getattr(_get_logger(), name)


logger = _LoggerProxy()


class SimpleArrayQueue:
    """使用list实现的简单FIFO队列

    由于RayQueueManager是Ray Actor，本身就是单线程处理请求，
    因此不需要线程锁，使用简单的list即可。
    """

    def __init__(self, maxsize=0):
        """
        初始化队列

        Args:
            maxsize: 队列最大大小，0表示无限制
        """
        self._items = []
        self._maxsize = maxsize

    def put(self, item, timeout=None):
        """
        添加项目到队列尾部（先进先出）

        Args:
            item: 要添加的项目
            timeout: 超时时间（保持接口兼容性，实际不使用）

        Raises:
            queue.Full: 队列已满时抛出
        """
        if self._maxsize > 0 and len(self._items) >= self._maxsize:
            raise queue.Full("Queue is full")
        self._items.append(item)

    def get(self, timeout=None):
        """
        从队列头部获取项目（先进先出）

        Args:
            timeout: 超时时间（保持接口兼容性，实际不使用）

        Returns:
            队列中的第一个项目

        Raises:
            queue.Empty: 队列为空时抛出
        """
        if len(self._items) == 0:
            raise queue.Empty("Queue is empty")
        return self._items.pop(0)

    def size(self):
        """获取当前队列中的元素数量"""
        return len(self._items)

    def qsize(self):
        """获取队列大小（兼容标准queue.Queue接口）"""
        return len(self._items)

    def empty(self):
        """检查队列是否为空"""
        return len(self._items) == 0

    def full(self):
        """检查队列是否已满"""
        if self._maxsize <= 0:
            return False
        return len(self._items) >= self._maxsize


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

    def put(self, item, block=True, timeout=None):
        """向队列添加项

        Args:
            item: 要添加的项目
            block: 是否阻塞等待（为了API兼容性，但Ray队列始终是阻塞的）
            timeout: 超时时间（秒）
        """
        import time

        _start = time.time()
        logger.debug(
            f"[PROXY-PUT-START] queue_id={self.queue_id}, block={block}, timeout={timeout}"
        )

        _remote_start = time.time()
        result = ray.get(self.manager.put.remote(self.queue_id, item))
        _remote_duration = time.time() - _remote_start
        _total_duration = time.time() - _start

        logger.debug(
            f"[PROXY-PUT-END] queue_id={self.queue_id}, "
            f"remote_call_time={_remote_duration * 1000:.3f}ms, "
            f"total_time={_total_duration * 1000:.3f}ms"
        )
        return result

    def put_nowait(self, item):
        """非阻塞添加项目到队列（实际上Ray队列始终是阻塞的）"""
        return ray.get(self.manager.put.remote(self.queue_id, item))

    def get(self, block=True, timeout=None):
        """从队列获取项目

        Args:
            block: 是否阻塞等待（为了API兼容性，但Ray队列始终是阻塞的）
            timeout: 超时时间（秒）
        """
        import time

        _start = time.time()
        logger.debug(f"[PROXY-GET-START] queue_id={self.queue_id}, timeout={timeout}")

        # Ray队列不支持非阻塞模式，block参数仅用于API兼容性
        _remote_start = time.time()
        result = ray.get(self.manager.get.remote(self.queue_id, timeout))
        _remote_duration = time.time() - _remote_start
        _total_duration = time.time() - _start

        logger.debug(
            f"[PROXY-GET-END] queue_id={self.queue_id}, "
            f"remote_call_time={_remote_duration * 1000:.3f}ms, "
            f"total_time={_total_duration * 1000:.3f}ms"
        )
        return result

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
    """Ray队列管理器，管理全局队列实例

    注意：为了避免序列化问题，此类不能使用模块级的 logger 变量。
    所有日志记录都通过 _get_logger() 方法动态创建本地 logger。
    """

    def __init__(self):
        self.queues = {}
        self._logger = None  # 延迟初始化

    def _get_logger(self):
        """获取本地 logger 实例（避免序列化问题）"""
        if self._logger is None:
            # 在 Actor 内部动态创建 logger，避免序列化问题
            import logging

            self._logger = logging.getLogger("RayQueueManager")
        return self._logger

    def get_or_create_queue(self, queue_id: str, maxsize: int):
        """获取或创建队列，返回队列ID而不是队列对象"""
        log = self._get_logger()
        if queue_id not in self.queues:
            # 统一使用数组实现的简单队列，避免Ray对象存储内存问题
            self.queues[queue_id] = SimpleArrayQueue(maxsize=maxsize if maxsize > 0 else 0)
            log.debug(f"Created new SimpleArrayQueue {queue_id}")
        else:
            log.debug(f"Retrieved existing queue {queue_id}")
        return queue_id  # 返回队列ID而不是队列对象

    def put(self, queue_id: str, item):
        """向指定队列添加项目"""
        import time

        log = self._get_logger()
        _start = time.time()
        log.debug(f"[MANAGER-PUT-START] queue_id={queue_id}")

        if queue_id in self.queues:
            _queue_put_start = time.time()
            result = self.queues[queue_id].put(item)
            _queue_put_duration = time.time() - _queue_put_start
            _total_duration = time.time() - _start

            if _queue_put_duration > 0.01:  # >10ms
                log.warning(
                    f"[MANAGER-PUT-SLOW] queue_id={queue_id}, "
                    f"queue_put_time={_queue_put_duration * 1000:.3f}ms"
                )

            log.debug(
                f"[MANAGER-PUT-END] queue_id={queue_id}, "
                f"queue_put_time={_queue_put_duration * 1000:.3f}ms, "
                f"total_time={_total_duration * 1000:.3f}ms"
            )
            return result
        else:
            log.error(f"[MANAGER-PUT-ERROR] Queue {queue_id} does not exist")
            raise ValueError(f"Queue {queue_id} does not exist")

    def get(self, queue_id: str, timeout=None):
        """从指定队列获取项目"""
        import time

        log = self._get_logger()
        _start = time.time()
        log.debug(f"[MANAGER-GET-START] queue_id={queue_id}, timeout={timeout}")

        if queue_id in self.queues:
            try:
                _queue_get_start = time.time()
                result = self.queues[queue_id].get(timeout=timeout)
                _queue_get_duration = time.time() - _queue_get_start
                _total_duration = time.time() - _start

                log.debug(
                    f"[MANAGER-GET-END] queue_id={queue_id}, "
                    f"queue_get_time={_queue_get_duration * 1000:.3f}ms, "
                    f"total_time={_total_duration * 1000:.3f}ms"
                )
                return result
            except Exception as e:
                _total_duration = time.time() - _start
                log.warning(
                    f"[MANAGER-GET-ERROR] queue_id={queue_id}, "
                    f"error={type(e).__name__}, "
                    f"total_time={_total_duration * 1000:.3f}ms"
                )
                raise
        else:
            log.error(f"[MANAGER-GET-ERROR] Queue {queue_id} does not exist")
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

    _start = time.time()
    logger.debug("[GET-MANAGER-START] Attempting to get global queue manager")

    # 使用固定的 namespace，确保所有 job 都能访问同一个 Actor
    QUEUE_MANAGER_NAMESPACE = "sage_global"

    # 使用固定的 namespace，确保所有 job 都能访问同一个 Actor
    QUEUE_MANAGER_NAMESPACE = "sage_global"

    # 先尝试获取现有的命名Actor
    try:
        _get_actor_start = time.time()
        manager = ray.get_actor("global_ray_queue_manager", namespace=QUEUE_MANAGER_NAMESPACE)
        _get_actor_duration = time.time() - _get_actor_start
        _total_duration = time.time() - _start
        logger.debug(
            f"[GET-MANAGER-FOUND] Found existing manager in namespace {QUEUE_MANAGER_NAMESPACE}, "
            f"get_actor_time={_get_actor_duration * 1000:.3f}ms, "
            f"total_time={_total_duration * 1000:.3f}ms"
        )
        return manager
    except ValueError:
        logger.debug("[GET-MANAGER-NOT-FOUND] Manager does not exist, will create")
        pass

    # 多次尝试创建命名Actor，处理并发冲突
    max_attempts = 5  # 增加重试次数
    for attempt in range(max_attempts):
        try:
            # 添加随机延迟，避免多个进程同时创建
            if attempt > 0:
                delay = random.uniform(0.1, 0.5) * (attempt + 1)
                logger.debug(
                    f"[GET-MANAGER-RETRY] Waiting {delay:.3f}s before retry "
                    f"{attempt + 1}/{max_attempts}"
                )
                time.sleep(delay)

            # 如果不存在，创建新的命名Actor
            logger.debug(
                f"[GET-MANAGER-CREATE] Attempt {attempt + 1}/{max_attempts} to create manager in namespace {QUEUE_MANAGER_NAMESPACE}"
            )
            _create_start = time.time()
            global _global_queue_manager
            _global_queue_manager = RayQueueManager.options(
                name="global_ray_queue_manager",
                namespace=QUEUE_MANAGER_NAMESPACE,  # 使用固定 namespace
                lifetime="detached",  # 独立于创建者进程，避免 owner 死亡导致 Actor 失效
                max_restarts=-1,  # 无限重启
                max_task_retries=-1,  # 无限重试
            ).remote()
            _create_duration = time.time() - _create_start
            _total_duration = time.time() - _start
            logger.debug(
                f"[GET-MANAGER-CREATED] Successfully created manager in namespace {QUEUE_MANAGER_NAMESPACE}, "
                f"create_time={_create_duration * 1000:.3f}ms, "
                f"total_time={_total_duration * 1000:.3f}ms"
            )
            return _global_queue_manager
        except ValueError as e:
            # 如果Actor已存在，再次尝试获取
            if "already exists" in str(e):
                logger.debug(
                    f"[GET-MANAGER-CONFLICT] Attempt {attempt + 1}: Actor already exists, retrying get"
                )
                try:
                    manager = ray.get_actor("global_ray_queue_manager")
                    _total_duration = time.time() - _start
                    logger.debug(
                        f"[GET-MANAGER-FOUND-RETRY] Found manager after conflict in namespace {QUEUE_MANAGER_NAMESPACE}, "
                        f"total_time={_total_duration * 1000:.3f}ms"
                    )
                    return manager
                except ValueError:
                    # 短暂等待后重试
                    wait_time = random.uniform(0.1, 0.5)
                    logger.debug(
                        f"[GET-MANAGER-WAIT] Waiting {wait_time * 1000:.1f}ms before retry"
                    )
                    time.sleep(wait_time)
                    continue
            else:
                logger.error(f"[GET-MANAGER-ERROR] Unexpected ValueError: {e}")
                raise
        except Exception as e:
            # 其他错误，短暂等待后重试
            logger.warning(
                f"[GET-MANAGER-RETRY] Attempt {attempt + 1} failed: {type(e).__name__}: {e}"
            )
            wait_time = random.uniform(0.1, 0.5)
            time.sleep(wait_time)
            if attempt == 2:  # 最后一次尝试
                logger.error(
                    f"[GET-MANAGER-FAILED] All attempts failed after {time.time() - _start:.3f}s"
                )
                raise

    # 如果仍然失败，尝试最后一次获取
    logger.debug("[GET-MANAGER-FINAL-ATTEMPT] Making final attempt to get manager")
    manager = ray.get_actor("global_ray_queue_manager", namespace=QUEUE_MANAGER_NAMESPACE)
    _total_duration = time.time() - _start
    logger.debug(
        f"[GET-MANAGER-FINAL-SUCCESS] Got manager on final attempt in namespace {QUEUE_MANAGER_NAMESPACE}, "
        f"total_time={_total_duration * 1000:.3f}ms"
    )
    return manager


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
            logger.debug(f"Initializing RayQueueProxy for queue_id={self.queue_id}")
            manager = get_global_queue_manager()
            logger.debug(f"Obtained global RayQueueManager for queue_id={self.queue_id}")
            # 确保队列被创建，但不获取队列对象本身
            ray.get(manager.get_or_create_queue.remote(self.queue_id, self.maxsize))
            logger.debug(f"Ensured queue exists in manager for queue_id={self.queue_id}")
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

    def clone(self, new_queue_id: Optional[str] = None) -> "RayQueueDescriptor":
        """克隆描述符（共享队列实例以避免竞态条件）

        重要：如果原描述符已初始化队列实例，克隆体将共享同一个队列代理。
        这对于服务通信至关重要 - 服务端和客户端必须使用相同的队列实例，
        否则会导致间歇性超时（竞态条件）。

        Args:
            new_queue_id: 新的队列ID，如果为None则自动生成

        Returns:
            新的描述符实例，如果原实例已初始化则共享队列实例
        """
        # 创建同类型的新实例
        cloned = RayQueueDescriptor(
            maxsize=self.maxsize,
            queue_id=new_queue_id,
        )

        # 【关键修复】共享队列代理实例，避免竞态条件
        # 如果原描述符已经初始化了队列实例，克隆体应该共享同一个实例
        # 这确保服务端和客户端使用相同的队列，防止响应丢失
        if self._queue is not None:
            cloned._queue = self._queue
            cloned._initialized = True

        return cloned
