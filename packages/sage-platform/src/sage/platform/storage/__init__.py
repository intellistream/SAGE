"""
SAGE Platform - Storage Abstractions

Key-Value storage backend interfaces.
"""

from .base_kv_backend import BaseKVBackend
from .dict_kv_backend import DictKVBackend

__all__ = [
    "BaseKVBackend",
    "DictKVBackend",
]
