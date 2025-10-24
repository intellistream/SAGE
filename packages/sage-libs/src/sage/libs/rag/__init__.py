"""
SAGE RAG - Retrieval-Augmented Generation Utilities

Note: RAG operators have been moved to sage.middleware.operators.rag
Please import operators from sage.middleware.operators.rag instead.

This module now only contains RAG utility functions and non-operator components.
"""

# 直接从本包的_version模块加载版本信息
try:
    from sage.libs._version import __author__, __email__, __version__
except ImportError:
    # 备用硬编码版本
    __version__ = "0.1.4"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"
