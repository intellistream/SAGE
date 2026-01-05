"""SageVDB compatibility layer for SAGE.

SageVDB has been migrated to an independent PyPI package.

Installation:
    pip install isage-vdb

This module re-exports SageVDB classes from the sagevdb package
for backward-compatible import paths within SAGE.

Important:
    - PyPI package name: isage-vdb (with hyphen and 'i' prefix)
    - Python import name: sagevdb (no 'i', no hyphen)

For detailed migration information, see:
    docs-public/docs_src/dev-notes/cross-layer/sagedb-independence-migration.md
"""

import warnings

# Re-export everything from sagevdb (Python import name, PyPI: isage-vdb)
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

    _SAGE_DB_AVAILABLE = True
except ImportError as e:
    # Don't warn on import - only when actually trying to use SageVDB
    # Store error message for later use
    _SAGE_DB_IMPORT_ERROR = str(e)
    pass
    # Provide stub exports to prevent ImportError
    SageVDB = None
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
    create_database = None
    add_numpy = None
    search_numpy = None
    distance_metric_to_string = None
    index_type_to_string = None
    string_to_distance_metric = None
    string_to_index_type = None

# Import backend adapters
try:
    from .backend import SageVDBBackend  # noqa: F401
except ImportError:
    SageVDBBackend = None

__all__ = [
    # Core classes (may be None if not installed)
    "SageVDB",
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
    # Availability flag
    "_SAGE_DB_AVAILABLE",
]


def __getattr__(name):
    """Provide friendly error message when SageVDB is not installed"""
    if name in __all__ and not _SAGE_DB_AVAILABLE:
        raise ImportError(
            f"Cannot import '{name}' from sage.middleware.components.sage_db. "
            "SageVDB is not installed. Please install it using:\n"
            "  pip install isage-vdb\n"
            "Note: PyPI package name is 'isage-vdb', Python import name is 'sagevdb'"
        )
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
