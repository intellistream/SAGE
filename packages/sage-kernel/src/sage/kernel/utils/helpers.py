"""
SAGE Kernel 通用 Helper 函数

这个模块包含了在 sage-kernel 中重复使用的通用工具函数，
包括：
- ID 生成
- 请求构建
- 超时等待
- 时间测量
- 函数验证
"""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from logging import Logger


# ==================== ID 生成 ====================


def generate_request_id() -> str:
    """
    生成唯一的请求 ID

    Returns:
        str: UUID4 格式的请求 ID
    """
    return str(uuid.uuid4())


def generate_short_id(length: int = 8) -> str:
    """
    生成短格式的唯一 ID

    Args:
        length: ID 长度 (默认 8)

    Returns:
        str: 短格式 UUID
    """
    return uuid.uuid4().hex[:length]


# ==================== 请求构建 ====================


def build_request(action: str, **kwargs: Any) -> dict[str, Any]:
    """
    构建标准格式的请求字典

    Args:
        action: 请求动作名称
        **kwargs: 额外的请求参数

    Returns:
        dict: 包含 action 和 request_id 的请求字典

    Example:
        >>> build_request("submit_job", job_uuid="xxx", data={"key": "value"})
        {"action": "submit_job", "request_id": "...", "job_uuid": "xxx", "data": {"key": "value"}}
    """
    return {
        "action": action,
        "request_id": generate_request_id(),
        **kwargs,
    }


# ==================== 超时等待 ====================


def wait_with_timeout(
    condition: Callable[[], bool],
    timeout: float,
    interval: float = 0.1,
    on_timeout: Callable[[], None] | None = None,
) -> bool:
    """
    带超时的条件等待

    Args:
        condition: 返回 True 表示条件满足的可调用对象
        timeout: 最大等待时间（秒）
        interval: 检查间隔（秒），默认 0.1
        on_timeout: 超时时调用的回调函数

    Returns:
        bool: True 如果条件满足，False 如果超时

    Example:
        >>> def is_ready():
        ...     return some_service.is_initialized()
        >>> if wait_with_timeout(is_ready, timeout=10.0):
        ...     print("Service is ready")
        ... else:
        ...     print("Timeout waiting for service")
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        if condition():
            return True
        time.sleep(interval)

    if on_timeout:
        on_timeout()

    return False


def wait_for_all_stopped(
    items: dict[str, Any],
    timeout: float = 10.0,
    interval: float = 0.1,
    logger: Logger | None = None,
) -> bool:
    """
    等待所有项目停止运行

    Args:
        items: 项目字典，每个项目应有 is_running 属性
        timeout: 最大等待时间（秒）
        interval: 检查间隔（秒）
        logger: 可选的日志记录器

    Returns:
        bool: True 如果所有项目都已停止，False 如果超时

    Example:
        >>> if wait_for_all_stopped(tasks, timeout=10.0, logger=self.logger):
        ...     logger.info("All tasks stopped")
        ... else:
        ...     logger.warning("Timeout waiting for tasks")
    """

    def all_stopped() -> bool:
        for _key, item in items.items():
            if hasattr(item, "is_running") and item.is_running:
                return False
        return True

    def on_timeout() -> None:
        if logger:
            logger.warning(f"Timeout waiting for items to stop after {timeout}s")

    result = wait_with_timeout(
        condition=all_stopped,
        timeout=timeout,
        interval=interval,
        on_timeout=on_timeout,
    )

    if result and logger:
        logger.debug("All items stopped")

    return result


# ==================== 时间测量 ====================


@contextmanager
def measure_time():
    """
    上下文管理器用于测量代码块执行时间

    Yields:
        一个对象，包含 elapsed 属性（执行完成后可用）

    Example:
        >>> with measure_time() as timer:
        ...     do_something()
        >>> print(f"Elapsed: {timer.elapsed:.3f}s")
    """

    class Timer:
        def __init__(self):
            self.start_time = time.time()
            self.elapsed = 0.0

        def stop(self):
            self.elapsed = time.time() - self.start_time

    timer = Timer()
    try:
        yield timer
    finally:
        timer.stop()


def timed_execution(func: Callable[..., Any]) -> Callable[..., tuple[Any, float]]:
    """
    装饰器：测量函数执行时间

    Args:
        func: 要测量的函数

    Returns:
        包装后的函数，返回 (原始返回值, 执行时间秒数)

    Example:
        >>> @timed_execution
        ... def slow_function():
        ...     time.sleep(1)
        ...     return "done"
        >>> result, elapsed = slow_function()
        >>> print(f"Result: {result}, Time: {elapsed:.2f}s")
    """

    def wrapper(*args: Any, **kwargs: Any) -> tuple[Any, float]:
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        return result, elapsed

    return wrapper


# ==================== 函数验证 ====================


def is_abstract_method(method: Any) -> bool:
    """
    检查方法是否为抽象方法

    Args:
        method: 要检查的方法

    Returns:
        bool: True 如果是抽象方法
    """
    return getattr(method, "__isabstractmethod__", False)


def validate_required_methods(
    cls: type,
    required_methods: list[str],
    class_name: str | None = None,
) -> None:
    """
    验证类是否实现了必需的方法

    Args:
        cls: 要验证的类
        required_methods: 必需方法名称列表
        class_name: 用于错误消息的类名（可选，默认使用 cls.__name__）

    Raises:
        ValueError: 如果缺少必需的方法或方法是抽象的

    Example:
        >>> validate_required_methods(
        ...     MyFunction,
        ...     required_methods=["execute", "setup"],
        ...     class_name="MyFunction"
        ... )
    """
    if class_name is None:
        class_name = cls.__name__

    missing_methods = []

    for method_name in required_methods:
        if not hasattr(cls, method_name):
            missing_methods.append(method_name)
        else:
            method = getattr(cls, method_name)
            if is_abstract_method(method):
                missing_methods.append(method_name)

    if missing_methods:
        raise ValueError(
            f"{class_name} must implement required methods: {', '.join(missing_methods)}"
        )


def validate_function_type(
    function: Any,
    type_attr: str,
    expected_value: bool = True,
    function_type_name: str = "Function",
) -> None:
    """
    验证函数是否具有特定类型标记

    Args:
        function: 要验证的函数对象
        type_attr: 类型标记属性名 (如 "is_join", "is_comap")
        expected_value: 期望的属性值 (默认 True)
        function_type_name: 函数类型名称，用于错误消息

    Raises:
        TypeError: 如果函数不具有预期的类型标记

    Example:
        >>> validate_function_type(
        ...     my_function,
        ...     type_attr="is_join",
        ...     function_type_name="Join"
        ... )
    """
    if not hasattr(function, type_attr) or getattr(function, type_attr) != expected_value:
        func_name = (
            type(function).__name__ if hasattr(function, "__name__") else str(type(function))
        )
        raise TypeError(
            f"{function_type_name} function requires {type_attr}={expected_value}, got {func_name}"
        )


# ==================== 重试逻辑 ====================


def retry_with_backoff(
    func: Callable[..., Any],
    max_retries: int = 3,
    base_delay: float = 0.5,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Any:
    """
    带指数退避的重试执行

    Args:
        func: 要执行的函数（无参数）
        max_retries: 最大重试次数
        base_delay: 基础延迟时间（秒），每次重试翻倍
        exceptions: 需要重试的异常类型

    Returns:
        函数的返回值

    Raises:
        最后一次重试失败的异常

    Example:
        >>> def unstable_operation():
        ...     # 可能失败的操作
        ...     return requests.get(url)
        >>> result = retry_with_backoff(unstable_operation, max_retries=3)
    """

    for attempt in range(max_retries):
        try:
            return func()
        except exceptions:
            if attempt < max_retries - 1:
                time.sleep(base_delay * (attempt + 1))
            else:
                raise


__all__ = [
    # ID 生成
    "generate_request_id",
    "generate_short_id",
    # 请求构建
    "build_request",
    # 超时等待
    "wait_with_timeout",
    "wait_for_all_stopped",
    # 时间测量
    "measure_time",
    "timed_execution",
    # 函数验证
    "is_abstract_method",
    "validate_required_methods",
    "validate_function_type",
    # 重试逻辑
    "retry_with_backoff",
]
