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

__layer__ = "L2"

# Public API
from sage.platform import queue, service, storage, utils
from sage.platform._version import __version__
from sage.platform.utils import (
    LazyLoggerProxy,
    get_component_logger,
    retry_with_backoff,
    retry_with_config,
    share_queue_instance_on_clone,
)

__all__ = [
    "__version__",
    "queue",
    "service",
    "storage",
    "utils",
    # Utility functions
    "retry_with_backoff",
    "retry_with_config",
    "get_component_logger",
    "LazyLoggerProxy",
    "share_queue_instance_on_clone",
]
