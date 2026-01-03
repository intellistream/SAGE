"""SageDB compatibility layer for SAGE.

SageDB has been migrated to an independent PyPI package.

Installation:
    pip install isagedb

This module re-exports SageDB classes from the isagedb package
for backward-compatible import paths within SAGE.

For detailed migration information, see:
    docs-public/docs_src/dev-notes/cross-layer/sagedb-independence-migration.md
"""

# Re-export everything from isagedb
from sagedb import (
    DatabaseConfig,
    DistanceMetric,
    IndexType,
    QueryResult,
    SageDB,
    SageDBException,
    SearchParams,
    create_database,
    create_database_from_config,
)

__all__ = [
    # Core classes
    "SageDB",
    "IndexType",
    "DistanceMetric",
    "QueryResult",
    "SearchParams",
    "DatabaseConfig",
    "SageDBException",
    # Factory functions
    "create_database",
    "create_database_from_config",
]
