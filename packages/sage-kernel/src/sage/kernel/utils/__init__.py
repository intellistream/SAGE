"""
SAGE - Streaming-Augmented Generative Execution

Kernel utilities module containing helper functions and Ray utilities.
"""

# 直接从本包的_version模块加载版本信息
try:
    from sage.kernel._version import __author__, __email__, __version__
except ImportError:
    # 备用硬编码版本
    __version__ = "0.1.4"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"

# 导出 helper 函数
from sage.kernel.utils.helpers import (
    build_request,
    generate_request_id,
    generate_short_id,
    is_abstract_method,
    measure_time,
    retry_with_backoff,
    timed_execution,
    validate_function_type,
    validate_required_methods,
    wait_for_all_stopped,
    wait_with_timeout,
)

__all__ = [
    # 版本信息
    "__version__",
    "__author__",
    "__email__",
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
