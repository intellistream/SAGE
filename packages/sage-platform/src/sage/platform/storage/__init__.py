"""SAGE Platform - Storage Abstractions

Layer: L2 (Platform Services - Storage Module)

Key-Value storage backend interfaces.

This module provides storage abstractions for key-value stores:
- BaseKVBackend: Abstract interface for KV backends
- DictKVBackend: In-memory dictionary-based implementation

Architecture:
- Pure L2 module, no cross-layer dependencies
- Provides backend-agnostic storage interface
"""

from .base_kv_backend import BaseKVBackend
from .dict_kv_backend import DictKVBackend

__all__ = [
    "BaseKVBackend",
    "DictKVBackend",
]
