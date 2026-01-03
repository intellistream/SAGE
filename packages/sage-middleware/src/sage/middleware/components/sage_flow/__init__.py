"""SageFlow compatibility layer for SAGE.

SageFlow has been migrated to an independent PyPI package.

Installation:
    pip install isage-flow

This module re-exports SageFlow classes from the isage-flow package
for backward-compatible import paths within SAGE, and provides
SAGE-specific services and wrappers.

For detailed migration information, see:
    docs-public/docs_src/dev-notes/cross-layer/sageflow-independence-migration.md
"""

# Import from PyPI package (isage-flow)
try:
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
except ImportError as e:
    raise ImportError(
        "SAGE Flow requires the isage-flow package. Please install: pip install isage-flow"
    ) from e

# SAGE-specific services (kept in SAGE repo)
from .python.micro_service.sage_flow_service import SageFlowService

__all__ = [
    # Core API from isage-flow
    "StreamEnvironment",
    "Stream",
    "SimpleStreamSource",
    "VectorData",
    "VectorRecord",
    "DataType",
    "__version__",
    "__author__",
    "__email__",
    # SAGE-specific services
    "SageFlowService",
]
