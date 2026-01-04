"""
SAGE-TSDB: Time Series Database Component for SAGE

Provides efficient time series data storage, querying, and processing capabilities
for streaming and historical data analysis.

Note: SAGE TSDB core is now an independent PyPI package (isage-tsdb).
This module provides backward-compatible wrappers and SAGE-specific services.
"""

import warnings

# Import from PyPI package (isage-tsdb)
_SAGE_TSDB_AVAILABLE = False
try:
    from sage_tsdb import (
        QueryConfig,
        TimeRange,
        TimeSeriesData,
        TimeSeriesDB,
        TimeSeriesIndex,
    )

    # Backward compatibility alias
    SageTSDB = TimeSeriesDB
    _SAGE_TSDB_AVAILABLE = True
except ImportError as e:
    # Don't fail immediately - allow graceful degradation
    warnings.warn(
        f"SAGE TSDB not available: {e}\n"
        "Install with: pip install isage-tsdb\n"
        "Time series features will be unavailable.",
        UserWarning,
        stacklevel=2,
    )
    # Provide stub exports
    SageTSDB = None
    TimeSeriesDB = None
    TimeSeriesData = None
    QueryConfig = None
    TimeRange = None
    TimeSeriesIndex = None

# Algorithms (SAGE-specific extensions)
# Only import if base package is available
if _SAGE_TSDB_AVAILABLE:
    from .python.algorithms import (
        OutOfOrderStreamJoin,
        TimeSeriesAlgorithm,
        WindowAggregator,
    )

    # Micro-service wrapper (SAGE-specific)
    from .python.micro_service.sage_tsdb_service import (
        SageTSDBService,
        SageTSDBServiceConfig,
    )
else:
    # Stub classes if TSDB not available
    TimeSeriesAlgorithm = None
    OutOfOrderStreamJoin = None
    WindowAggregator = None
    SageTSDBService = None
    SageTSDBServiceConfig = None

__all__ = [
    # Core API (may be None if not installed)
    "SageTSDB",
    "TimeSeriesData",
    "QueryConfig",
    "TimeRange",
    # Service
    "SageTSDBService",
    "SageTSDBServiceConfig",
    # Algorithms
    "TimeSeriesAlgorithm",
    "OutOfOrderStreamJoin",
    "WindowAggregator",
    # Availability flag
    "_SAGE_TSDB_AVAILABLE",
]
