"""SAGE - Streaming-Augmented Generative Execution

Layer: L1 (Foundation - Common Utilities)

This package provides common utilities used across all SAGE packages.
Includes logging, serialization, system utilities, and configuration helpers.

Architecture:
    This is a L1 foundation package providing utility functions.
    Must NOT contain business logic, only reusable helper functions.
"""

# 直接从本包的_version模块加载版本信息
try:
    from sage.common._version import __author__, __email__, __version__
except ImportError:
    # 备用硬编码版本
    __version__ = "0.1.4"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"
