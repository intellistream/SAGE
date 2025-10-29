"""SAGE namespace package."""

# This is a namespace package
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

# 版本信息（在 sage-common 中定义，确保所有安装模式都能访问）
try:
    from sage.common._version import __author__, __email__, __version__
except ImportError:
    # 如果没有安装 sage-common，使用默认值
    __version__ = "unknown"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"

__all__ = ["__version__", "__author__", "__email__"]
