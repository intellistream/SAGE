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
        DPWrapper,
        IndexConfig,
        PartitionType,
        QueryConfig,
        QueryResult,
        SageFlow,
        SemanticQueryEngine,
    )
except ImportError as e:
    raise ImportError(
        "SAGE Flow requires the isage-flow package. Please install: pip install isage-flow"
    ) from e

# SAGE-specific services (kept in SAGE repo)
from .python.micro_service.sage_flow_service import (
    SageFlowService,
    SageFlowServiceConfig,
)

__all__ = [
    # Core API from isage-flow
    "SageFlow",
    "SemanticQueryEngine",
    "QueryConfig",
    "IndexConfig",
    "QueryResult",
    "DPWrapper",
    "PartitionType",
    # SAGE-specific services
    "SageFlowService",
    "SageFlowServiceConfig",
]
