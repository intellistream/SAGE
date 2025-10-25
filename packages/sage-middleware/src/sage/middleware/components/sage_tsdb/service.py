"""
SageTSDB Middleware Service

This module provides the middleware service interface for SageTSDB,
wrapping the Python implementation for time series data processing.
"""

# Micro-service wrapper
from .python.micro_service.sage_tsdb_service import (
    SageTSDBService,
    SageTSDBServiceConfig,
)

# Core Python API
from .python.sage_tsdb import SageTSDB

__all__ = ["SageTSDB", "SageTSDBService", "SageTSDBServiceConfig"]
