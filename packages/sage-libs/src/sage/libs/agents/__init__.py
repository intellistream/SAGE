"""
SAGE Agents - Agent Framework and Implementations

Layer: L3 (Core - Algorithm Library)

This module provides the core agent framework and pre-built agent implementations.
"""

# 直接从本包的_version模块加载版本信息
try:
    from sage.libs._version import __author__, __email__, __version__
except ImportError:
    # 备用硬编码版本
    __version__ = "0.1.4"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"

# Import pre-built bots
from . import bots

__all__ = ["bots"]
