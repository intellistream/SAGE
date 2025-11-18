"""Base tool infrastructure for generic tool patterns."""

from .registry import ToolRegistry
from .tool import BaseTool

__all__ = ["BaseTool", "ToolRegistry"]

# Version information
try:
    from sage.libs._version import __author__, __email__, __version__
except ImportError:
    # 备用硬编码版本
    __version__ = "0.1.4"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"
