"""
SAGE-TSDB: Time Series Database Component for SAGE

Provides efficient time series data storage, querying, and processing capabilities
for streaming and historical data analysis.
"""

# Core Python API
from .python.sage_tsdb import SageTSDB, TimeSeriesData, QueryConfig, TimeRange

# Micro-service wrapper
from .python.micro_service.sage_tsdb_service import (
    SageTSDBService,
    SageTSDBServiceConfig,
)

# Algorithms
from .python.algorithms import (
    OutOfOrderStreamJoin,
    WindowAggregator,
    TimeSeriesAlgorithm,
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
