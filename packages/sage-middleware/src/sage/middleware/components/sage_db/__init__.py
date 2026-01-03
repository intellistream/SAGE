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
    MetadataStore,
    QueryEngine,
    QueryResult,
    SageDB,
    SageDBException,
    SearchParams,
    SearchStats,
    VectorStore,
    add_numpy,
    create_database,
    distance_metric_to_string,
    index_type_to_string,
    search_numpy,
    string_to_distance_metric,
    string_to_index_type,
)

__all__ = [
    # Core classes
    "SageDB",
    "IndexType",
    "DistanceMetric",
    "QueryResult",
    "SearchParams",
    "SearchStats",
    "DatabaseConfig",
    "MetadataStore",
    "QueryEngine",
    "VectorStore",
    "SageDBException",
    # Factory functions
    "create_database",
    # Numpy utilities
    "add_numpy",
    "search_numpy",
    # Conversion utilities
    "distance_metric_to_string",
    "index_type_to_string",
    "string_to_distance_metric",
    "string_to_index_type",
]
