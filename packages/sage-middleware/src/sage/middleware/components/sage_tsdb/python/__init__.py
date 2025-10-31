"""
Python package for SageTSDB

This package provides both high-performance C++ bindings and pure Python implementations
for time series database operations.
"""

try:
    # Try to import C++ bindings first
    from . import _sage_tsdb

    TSDB_BACKEND = "cpp"
except ImportError:
    # Fallback to pure Python implementation
    _sage_tsdb = None
    TSDB_BACKEND = "python"

# Import Python APIs (these wrap C++ or pure Python implementations)
from . import algorithms, sage_tsdb

__all__ = ["sage_tsdb", "algorithms", "_sage_tsdb", "TSDB_BACKEND"]
