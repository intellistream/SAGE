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
# 直接读取 _version.py 文件（命名空间包中最可靠的方式）
import os

_current_dir = os.path.dirname(os.path.abspath(__file__))
_version_file = os.path.join(_current_dir, "_version.py")

_version_globals = {}
with open(_version_file) as f:
    exec(f.read(), _version_globals)

__version__ = _version_globals["__version__"]
__author__ = _version_globals["__author__"]
__email__ = _version_globals["__email__"]

__all__ = [
    "__version__",
    "__author__",
    "__email__",
]
