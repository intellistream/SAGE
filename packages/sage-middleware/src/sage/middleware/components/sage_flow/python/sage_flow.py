"""
SAGE Flow - High-performance vector stream processing engine (Python wrapper)

This module re-exports SageFlow classes from the isage-flow PyPI package.
"""

# Re-export all classes from isage-flow
from sage_flow import (
    DPWrapper,
    IndexConfig,
    PartitionType,
    QueryConfig,
    QueryResult,
    SageFlow,
    SemanticQueryEngine,
    __author__,
    __email__,
    __version__,
)

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "SageFlow",
    "SemanticQueryEngine",
    "QueryConfig",
    "IndexConfig",
    "QueryResult",
    "DPWrapper",
    "PartitionType",
]
