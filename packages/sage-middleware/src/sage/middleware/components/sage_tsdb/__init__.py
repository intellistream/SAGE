"""
SAGE-TSDB: Time Series Database Component for SAGE

Provides efficient time series data storage, querying, and processing capabilities
for streaming and historical data analysis.
"""

# Algorithms
from .python.algorithms import (OutOfOrderStreamJoin, TimeSeriesAlgorithm,
                                WindowAggregator)
# Micro-service wrapper
from .python.micro_service.sage_tsdb_service import (SageTSDBService,
                                                     SageTSDBServiceConfig)
# Core Python API
from .python.sage_tsdb import QueryConfig, SageTSDB, TimeRange, TimeSeriesData

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
