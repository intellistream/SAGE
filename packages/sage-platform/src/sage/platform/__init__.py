"""
SAGE Platform - Infrastructure Abstractions (L2)

This package provides core platform services that sit between the foundation
layer (sage-common) and the execution engine (sage-kernel).

Components:
- queue: Message queue abstractions (Python, Ray, RPC)
- storage: Key-Value storage backends
- service: Base service classes
"""

from sage.platform._version import __version__

# Public API
from sage.platform import queue, service, storage

__all__ = [
    "__version__",
    "queue",
    "service",
    "storage",
]
