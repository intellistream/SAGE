"""
Algorithms for time series processing.

This module provides a pluggable algorithm interface for various
time series processing tasks including stream joins, aggregations,
and complex event processing.
"""

from .base import TimeSeriesAlgorithm
from .out_of_order_join import OutOfOrderStreamJoin
from .window_aggregator import WindowAggregator

__all__ = [
    "TimeSeriesAlgorithm",
    "OutOfOrderStreamJoin",
    "WindowAggregator",
]
