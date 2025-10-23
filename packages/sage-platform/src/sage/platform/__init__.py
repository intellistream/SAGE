"""SAGE Platform - Infrastructure Abstractions (L2)

Layer: L2 (Platform Services)

This package provides core platform services that sit between the foundation
layer (sage-common) and the execution engine (sage-kernel).

Components:
- queue: Message queue abstractions (Python, Ray, RPC)
- storage: Key-Value storage backends
- service: Base service classes

Architecture:
- ✅ Can import from: L1 (sage-common)
- ✅ Can be imported by: L3-L6 (sage-kernel, sage-middleware, sage-libs, sage-apps)
- ✅ Clean design: Uses factory pattern for L3 dependencies (RPCQueue)
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
