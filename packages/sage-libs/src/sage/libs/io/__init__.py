"""
SAGE IO - Input/Output Abstractions

Layer: L3 (Core - Algorithm Library)

This module provides unified input/output interfaces for data streams,
batches, sources, and sinks.

Components:
- Source: Data source abstractions
- Sink: Data sink abstractions
- Batch: Batch processing utilities
"""

# 直接从本包的_version模块加载版本信息
try:
    from sage.libs._version import __author__, __email__, __version__
except ImportError:
    # 备用硬编码版本
    __version__ = "0.1.4"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"

# TODO: Import and export specific classes
# from .source import *
# from .sink import *
# from .batch import *

__all__ = []
