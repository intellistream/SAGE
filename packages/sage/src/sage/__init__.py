"""
SAGE - Streaming-Augmented Generative Execution

This is a namespace package that includes:
- sage.common: Common utilities
- sage.kernel: Core kernel functionality
- sage.middleware: Middleware components
- sage.libs: Application libraries
- sage.tools: Development tools
"""

# 扩展命名空间包路径以支持子包
# 这必须在任何子包导入之前完成
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

# 动态加载版本信息
# 优先从 sage.common 导入（因为 sage-common 是基础包，总是会被安装）
try:
    from sage.common._version import __author__, __email__, __version__
except ImportError:
    # 如果 sage.common 不可用，尝试从本地 _version 导入
    try:
        from ._version import __author__, __email__, __version__
    except ImportError:
        __version__ = "unknown"
        __author__ = "IntelliStream Team"
        __email__ = "shuhao_zhang@hust.edu.cn"

__all__ = [
    "__version__",
    "__author__",
    "__email__",
]
