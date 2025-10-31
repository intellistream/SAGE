"""SAGE namespace package."""

# This is a namespace package
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

# 尝试导入版本信息（确保所有命名空间包都有 __version__）
if not hasattr(__import__(__name__), "__version__"):
    try:
        from sage.common._version import __author__, __email__, __version__
    except ImportError:
        __version__ = "unknown"
        __author__ = "IntelliStream Team"
        __email__ = "shuhao_zhang@hust.edu.cn"

    __all__ = ["__version__", "__author__", "__email__"]
