"""
Platform Utilities - 统一的工具函数

Layer: L2 (Platform Services - Utilities)

提供 sage-platform 包中常用的工具函数和装饰器。
"""

import logging
import os
import time
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Optional, TypeVar

if TYPE_CHECKING:
    from sage.common.utils.logging.custom_logger import CustomLogger

logger = logging.getLogger(__name__)

# Type variable for generic retry decorator
T = TypeVar("T")


# =============================================================================
# 重试装饰器
# =============================================================================


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
):
    """通用重试装饰器 - 失败时自动重试，支持指数退避

    Args:
        max_attempts: 最大尝试次数（包括首次）
        initial_delay: 初始重试延迟（秒）
        backoff_factor: 退避因子，每次重试延迟乘以此值
        exceptions: 需要重试的异常类型元组
        on_retry: 重试时的回调函数，接收 (attempt_number, exception)

    Returns:
        装饰后的函数

    Example:
        @retry_with_backoff(max_attempts=3, initial_delay=1.0)
        def fetch_data():
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception: Optional[Exception] = None
            delay = initial_delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        if on_retry:
                            on_retry(attempt + 1, e)
                        else:
                            logger.warning(
                                f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                                f"Retrying in {delay:.2f}s..."
                            )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}")

            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected: no exception but all attempts failed")

        return wrapper

    return decorator


def retry_with_config(
    max_attempts_attr: str = "retry_attempts",
    delay_attr: str = "retry_delay",
    backoff_attr: str = "retry_backoff",
):
    """从对象配置读取重试参数的装饰器

    用于类方法，从 self.config 读取重试配置。

    Args:
        max_attempts_attr: config 中最大尝试次数的属性名
        delay_attr: config 中初始延迟的属性名
        backoff_attr: config 中退避因子的属性名

    Example:
        class MyService:
            @retry_with_config()
            def fetch_data(self):
                ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            config = getattr(self, "config", None)
            if config is None:
                # 没有配置，直接调用
                return func(self, *args, **kwargs)

            max_attempts = getattr(config, max_attempts_attr, 3)
            delay = getattr(config, delay_attr, 1.0)
            backoff = getattr(config, backoff_attr, 2.0)

            last_exception: Optional[Exception] = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(self, *args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                            f"Retrying in {current_delay:.2f}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}")

            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected: no exception but all attempts failed")

        return wrapper

    return decorator


# =============================================================================
# 日志工具
# =============================================================================

# 缓存的 logger 实例
_cached_loggers: dict[str, "CustomLogger"] = {}


def get_component_logger(
    component_name: str,
    log_levels: Optional[list[tuple[str, str]]] = None,
) -> "CustomLogger":
    """获取组件专用的 CustomLogger

    使用 SAGE 的 CustomLogger，自动配置日志目录。

    Args:
        component_name: 组件名称，用于日志文件名
        log_levels: 日志级别配置列表，格式为 [(output, level), ...]
                   output 可以是 "console" 或文件路径

    Returns:
        CustomLogger 实例

    Example:
        logger = get_component_logger("RayQueue")
        logger.info("Queue initialized")
    """
    global _cached_loggers

    if component_name in _cached_loggers:
        return _cached_loggers[component_name]

    from sage.common.utils.logging.custom_logger import CustomLogger

    # 获取日志目录
    log_base_dir = os.environ.get("SAGE_LOG_DIR")
    if not log_base_dir:
        log_base_dir = os.path.abspath(".sage/logs")

    os.makedirs(log_base_dir, exist_ok=True)

    # 默认日志配置
    if log_levels is None:
        log_levels = [
            ("console", "DEBUG"),
            (os.path.join(log_base_dir, f"{component_name.lower()}_debug.log"), "DEBUG"),
            (os.path.join(log_base_dir, f"{component_name.lower()}_info.log"), "INFO"),
            (os.path.join(log_base_dir, "Error.log"), "ERROR"),
        ]

    custom_logger = CustomLogger(log_levels, name=component_name)
    _cached_loggers[component_name] = custom_logger
    return custom_logger


class LazyLoggerProxy:
    """延迟初始化的 Logger 代理

    避免在模块导入时就初始化 CustomLogger。

    Example:
        logger = LazyLoggerProxy("MyComponent")
        logger.info("This works")  # Logger 在首次使用时初始化
    """

    def __init__(self, component_name: str):
        self._component_name = component_name
        self._logger: Optional[CustomLogger] = None

    def _get_logger(self) -> "CustomLogger":
        if self._logger is None:
            self._logger = get_component_logger(self._component_name)
        return self._logger

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get_logger(), name)


# =============================================================================
# 队列描述符工具
# =============================================================================


def share_queue_instance_on_clone(clone_func: Callable) -> Callable:
    """装饰器：确保 clone() 方法共享队列实例

    用于队列描述符的 clone() 方法，确保已初始化的队列实例被共享，
    避免服务通信中的竞态条件。

    Example:
        class MyQueueDescriptor(BaseQueueDescriptor):
            @share_queue_instance_on_clone
            def clone(self, new_queue_id=None):
                return MyQueueDescriptor(
                    queue_id=new_queue_id,
                    ...
                )
    """

    @wraps(clone_func)
    def wrapper(self, new_queue_id: Optional[str] = None):
        # 调用原始 clone 方法创建新实例
        cloned = clone_func(self, new_queue_id)

        # 如果原实例已初始化，共享队列实例
        if getattr(self, "_initialized", False):
            if hasattr(self, "_queue_instance"):
                cloned._queue_instance = self._queue_instance
            if hasattr(self, "_queue"):
                cloned._queue = self._queue
            cloned._initialized = True

        return cloned

    return wrapper


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    "retry_with_backoff",
    "retry_with_config",
    "get_component_logger",
    "LazyLoggerProxy",
    "share_queue_instance_on_clone",
]
