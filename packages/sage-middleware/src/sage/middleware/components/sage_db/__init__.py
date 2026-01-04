"""SageVDB compatibility layer for SAGE.

SageVDB has been migrated to an independent PyPI package.

Installation:
    pip install isagevdb

This module re-exports SageVDB classes from the isagevdb package
for backward-compatible import paths within SAGE.

For detailed migration information, see:
    docs-public/docs_src/dev-notes/cross-layer/sagedb-independence-migration.md
"""

import warnings

# Re-export everything from isagevdb
_SAGE_DB_AVAILABLE = False
try:
    from sagevdb import (
        DatabaseConfig,
        DistanceMetric,
        IndexType,
        MetadataStore,
        QueryEngine,
        QueryResult,
        SageVDB,
        SageVDBException,
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

    # Backward compatibility aliases
    SageDB = SageVDB
    SageDBException = SageVDBException

    _SAGE_DB_AVAILABLE = True
except ImportError as e:
    # Don't fail immediately - allow graceful degradation
    warnings.warn(
        f"SageVDB not available: {e}\n"
        "Install with: pip install isagevdb\n"
        "Vector database features will be unavailable.",
        UserWarning,
        stacklevel=2,
    )
    # Provide stub exports to prevent ImportError
    SageVDB = None
    SageDB = None
    IndexType = None
    DistanceMetric = None
    QueryResult = None
    SearchParams = None
    SearchStats = None
    DatabaseConfig = None
    MetadataStore = None
    QueryEngine = None
    VectorStore = None
    SageVDBException = None
    SageDBException = None
    create_database = None
    add_numpy = None
    search_numpy = None
    distance_metric_to_string = None
    index_type_to_string = None
    string_to_distance_metric = None
    string_to_index_type = None

# Import backend adapters
try:
    from .backend import SageDBBackend, SageVDBBackend  # noqa: F401
except ImportError:
    SageVDBBackend = None
    SageDBBackend = None

__all__ = [
    # Core classes (may be None if not installed)
    "SageVDB",
    "SageDB",  # Backward compatibility
    "IndexType",
    "DistanceMetric",
    "QueryResult",
    "SearchParams",
    "SearchStats",
    "DatabaseConfig",
    "MetadataStore",
    "QueryEngine",
    "VectorStore",
    "SageVDBException",
    "SageDBException",  # Backward compatibility
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
    # Backend adapters
    "SageVDBBackend",
    "SageDBBackend",  # Backward compatibility
    # Availability flag
    "_SAGE_DB_AVAILABLE",
]
