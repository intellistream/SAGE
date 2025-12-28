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
# 策略：优先使用本包的版本，而不是依赖 sage.common
try:
    from sage._version import __author__, __email__, __version__
except ImportError:
    # Fallback 1: 尝试从 sage.common 导入（如果可用）
    try:
        from sage.common._version import __author__, __email__, __version__
    except ImportError:
        # Fallback 2: 设置默认值
        __version__ = "unknown"
        __author__ = "IntelliStream Team"
        __email__ = "shuhao_zhang@hust.edu.cn"

__all__ = [
    "__version__",
    "__author__",
    "__email__",
]
