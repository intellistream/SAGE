"""SAGE Platform - Storage Abstractions

Layer: L2 (Platform Services - Storage Module)

Key-Value storage backend interfaces.

This module provides storage abstractions for key-value stores:
- BaseKVBackend: Abstract interface for KV backends
- DictKVBackend: In-memory dictionary-based implementation
- HDFSConfig: HDFS connection configuration (optional, requires pyarrow)
- HDFSFileSystem: HDFS filesystem operations (optional, requires pyarrow)

Architecture:
- Pure L2 module, no cross-layer dependencies
- Provides backend-agnostic storage interface
- HDFS support is optional and requires additional dependencies
"""

from .base_kv_backend import BaseKVBackend
from .dict_kv_backend import DictKVBackend

# HDFS 支持为可选功能,需要安装 pyarrow
# HDFS support is optional and requires pyarrow installation
HDFS_AVAILABLE = False
try:
    from .hdfs_config import HDFSConfig
    from .hdfs_filesystem import (
        HDFSConnectionError,
        HDFSConnectionPool,
        HDFSError,
        HDFSFileNotFoundError,
        HDFSFileSystem,
        HDFSIOError,
        HDFSPermissionError,
    )

    HDFS_AVAILABLE = True
except ImportError:
    # pyarrow 未安装,HDFS 功能不可用
    # pyarrow not installed, HDFS features unavailable
    pass

__all__ = [
    "BaseKVBackend",
    "DictKVBackend",
    "HDFS_AVAILABLE",
]

# 仅在 HDFS 可用时导出 HDFS 相关类
# Export HDFS classes only when available
if HDFS_AVAILABLE:
    __all__.extend(
        [
            "HDFSConfig",
            "HDFSFileSystem",
            "HDFSConnectionPool",
            "HDFSError",
            "HDFSConnectionError",
            "HDFSFileNotFoundError",
            "HDFSPermissionError",
            "HDFSIOError",
        ]
    )
