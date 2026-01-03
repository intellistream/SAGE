"""
SAGE-TSDB: Time Series Database Component for SAGE

Provides efficient time series data storage, querying, and processing capabilities
for streaming and historical data analysis.

Note: SAGE TSDB core is now an independent PyPI package (isage-tsdb).
This module provides backward-compatible wrappers and SAGE-specific services.
"""

# Import from PyPI package (isage-tsdb)
try:
    from sage_tsdb import QueryConfig, SageTSDB, TimeRange, TimeSeriesData
except ImportError as e:
    raise ImportError("SAGE TSDB 需要 isage-tsdb 包。请安装: pip install isage-tsdb") from e

# Algorithms (SAGE-specific extensions)
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

__all__ = [
    # Core API
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
]
