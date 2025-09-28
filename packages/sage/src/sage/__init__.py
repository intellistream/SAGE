"""
SAGE - Streaming-Augmented Generative Execution
"""

# 动态加载版本信息
from ._version import __author__, __email__, __version__  # noqa: F401

# 扩展命名空间包路径以支持子包
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
