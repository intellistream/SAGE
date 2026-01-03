"""
SAGE TSDB Python Bindings
High-performance time series database for streaming data
"""

from ._sage_tsdb import *  # noqa: F403, F401 - C++ extension module

__all__ = [  # noqa: F405 - Names exported from C++ extension
    "TimeSeriesData",
    "TimeSeriesDB",
    "TimeSeriesIndex",
    "TimeRange",
    "QueryConfig",
]

# Import version
from ._version import __version__, __author__, __email__

__all__ += ["__version__", "__author__", "__email__"]
