"""
SAGE Flow - High-performance vector stream processing engine (Python wrapper)

This module re-exports SageFlow classes from the isage-flow PyPI package.
"""

# Re-export all classes from isage-flow
from sage_flow import (
    DataType,
    SimpleStreamSource,
    Stream,
    StreamEnvironment,
    VectorData,
    VectorRecord,
    __author__,
    __email__,
    __version__,
)

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "StreamEnvironment",
    "Stream",
    "SimpleStreamSource",
    "VectorData",
    "VectorRecord",
    "DataType",
]
