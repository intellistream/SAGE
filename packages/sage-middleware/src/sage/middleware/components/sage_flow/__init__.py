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

import warnings

# Import from PyPI package (isage-flow)
_SAGE_FLOW_AVAILABLE = False
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

    _SAGE_FLOW_AVAILABLE = True
except ImportError as e:
    # Don't fail immediately - allow graceful degradation
    warnings.warn(
        f"SAGE Flow not available: {e}\n"
        "Install with: pip install isage-flow\n"
        "Some advanced streaming features will be unavailable.",
        UserWarning,
        stacklevel=2,
    )
    # Provide stub exports to prevent ImportError
    DataType = None
    SimpleStreamSource = None
    Stream = None
    StreamEnvironment = None
    VectorData = None
    VectorRecord = None
    __version__ = "unavailable"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"

# SAGE-specific services (kept in SAGE repo)
# Only import if sage_flow is available
if _SAGE_FLOW_AVAILABLE:
    from .python.micro_service.sage_flow_service import SageFlowService
else:
    SageFlowService = None

__all__ = [
    # Core API from isage-flow (may be None if not installed)
    "StreamEnvironment",
    "Stream",
    "SimpleStreamSource",
    "VectorData",
    "VectorRecord",
    "DataType",
    "__version__",
    "__author__",
    "__email__",
    # SAGE-specific services (may be None if isage-flow not installed)
    "SageFlowService",
    # Availability flag
    "_SAGE_FLOW_AVAILABLE",
]
