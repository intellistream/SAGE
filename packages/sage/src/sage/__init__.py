"""
SAGE - Streaming-Augmented Generative Execution
"""

# 动态加载版本信息
from ._version import __author__, __email__, __version__  # noqa: F401

# 扩展命名空间包路径以支持子包
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

# 确保版本信息在命名空间扩展后仍然可访问
# 这是为了解决在pip安装环境中版本信息可能丢失的问题
from .runtime.sugar import (
	bind_runtime_context,
	call_service,
	call_service_async,
	clear_runtime_context,
	get_current_runtime_context,
)

__all__ = [
	"__version__",
	"__author__",
	"__email__",
	"bind_runtime_context",
	"call_service",
	"call_service_async",
	"clear_runtime_context",
	"get_current_runtime_context",
]
