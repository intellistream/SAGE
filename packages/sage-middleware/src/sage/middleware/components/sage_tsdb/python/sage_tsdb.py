"""
SAGE TSDB - High-performance time series database for streaming data

This module provides Python APIs for time series data storage, querying,
and processing with support for out-of-order data and various algorithms.

Uses C++ implementation for high performance when available, with pure Python fallback.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np

# Try to import C++ bindings
try:
    from . import _sage_tsdb

    HAS_CPP_BACKEND = True
except ImportError:
    _sage_tsdb = None
    HAS_CPP_BACKEND = False


class AggregationType(Enum):
    """Time series aggregation types"""

    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    FIRST = "first"
    LAST = "last"
    STDDEV = "stddev"


class InterpolationType(Enum):
    """Interpolation methods for missing data"""

    NONE = "none"
    LINEAR = "linear"
    FORWARD_FILL = "forward_fill"
    BACKWARD_FILL = "backward_fill"
    ZERO = "zero"


@dataclass
class TimeRange:
    """Time range for queries"""

    start_time: int | datetime
    end_time: int | datetime

    def __post_init__(self):
        """Convert datetime to timestamp if necessary"""
        if isinstance(self.start_time, datetime):
            self.start_time = int(self.start_time.timestamp() * 1000)
        if isinstance(self.end_time, datetime):
            self.end_time = int(self.end_time.timestamp() * 1000)


@dataclass
class TimeSeriesData:
    """Time series data point"""

    timestamp: int  # milliseconds since epoch
    value: float | np.ndarray
    tags: dict[str, str] | None = None
    fields: dict[str, Any] | None = None

    def __post_init__(self):
        """Initialize default values"""
        if self.tags is None:
            self.tags = {}
        if self.fields is None:
            self.fields = {}


@dataclass
class QueryConfig:
    """Configuration for time series queries"""

    time_range: TimeRange
    tags: dict[str, str] | None = None
    aggregation: AggregationType | None = None
    window_size: int | None = None  # milliseconds
    interpolation: InterpolationType = InterpolationType.NONE
    limit: int | None = None
    downsample_factor: int | None = None


class TimeSeriesIndex:
    """
    Index structure for efficient time series queries.
    Supports fast lookup by timestamp and tags.
    """

    def __init__(self):
        self._data: list[TimeSeriesData] = []
        self._tag_index: dict[str, dict[str, list[int]]] = {}
        self._sorted = True

    def add(self, data: TimeSeriesData) -> int:
        """Add a time series data point"""
        idx = len(self._data)
        self._data.append(data)

        # Update tag index
        for key, value in data.tags.items():
            if key not in self._tag_index:
                self._tag_index[key] = {}
            if value not in self._tag_index[key]:
                self._tag_index[key][value] = []
            self._tag_index[key][value].append(idx)

        # Mark as unsorted if new data is out of order
        if idx > 0 and data.timestamp < self._data[idx - 1].timestamp:
            self._sorted = False

        return idx

    def add_batch(self, data_list: list[TimeSeriesData]) -> list[int]:
        """Add multiple time series data points"""
        return [self.add(data) for data in data_list]

    def _ensure_sorted(self):
        """Sort data by timestamp if needed"""
        if not self._sorted:
            # Sort data and rebuild tag index
            sorted_data = sorted(self._data, key=lambda x: x.timestamp)
            self._data = sorted_data
            self._rebuild_tag_index()
            self._sorted = True

    def _rebuild_tag_index(self):
        """Rebuild tag index after sorting"""
        self._tag_index = {}
        for idx, data in enumerate(self._data):
            for key, value in data.tags.items():
                if key not in self._tag_index:
                    self._tag_index[key] = {}
                if value not in self._tag_index[key]:
                    self._tag_index[key][value] = []
                self._tag_index[key][value].append(idx)

    def query(self, config: QueryConfig) -> list[TimeSeriesData]:
        """Query time series data"""
        self._ensure_sorted()

        # Binary search for time range
        # Note: TimeRange.__post_init__ converts datetime to int
        start_idx = self._binary_search(config.time_range.start_time)  # type: ignore[arg-type]
        end_idx = self._binary_search(config.time_range.end_time, find_upper=True)  # type: ignore[arg-type]

        # Filter by tags if specified
        if config.tags:
            matching_indices = self._filter_by_tags(config.tags)
            # Intersect with time range
            result_indices = [i for i in range(start_idx, end_idx + 1) if i in matching_indices]
        else:
            result_indices = list(range(start_idx, end_idx + 1))

        # Get data points
        results = [self._data[i] for i in result_indices]

        # Apply limit if specified
        if config.limit is not None:
            results = results[: config.limit]

        return results

    def _binary_search(self, timestamp: int, find_upper: bool = False) -> int:
        """
        Binary search for timestamp.
        If find_upper is False, returns the first index with timestamp >= target (lower bound).
        If find_upper is True, returns the last index with timestamp <= target (upper bound).
        """
        low, high = 0, len(self._data) - 1
        if not self._data:
            return -1

        if not find_upper:
            # Lower bound: first index with timestamp >= target
            while low <= high:
                mid = (low + high) // 2
                mid_time = self._data[mid].timestamp
                if mid_time < timestamp:
                    low = mid + 1
                else:
                    high = mid - 1
            return low if low < len(self._data) else len(self._data) - 1
        else:
            # Upper bound: last index with timestamp <= target
            while low <= high:
                mid = (low + high) // 2
                mid_time = self._data[mid].timestamp
                if mid_time > timestamp:
                    high = mid - 1
                else:
                    low = mid + 1
            return high if high >= 0 else 0

    def _filter_by_tags(self, tags: dict[str, str]) -> set:
        """Filter indices by tags"""
        matching_sets = []
        for key, value in tags.items():
            if key in self._tag_index and value in self._tag_index[key]:
                matching_sets.append(set(self._tag_index[key][value]))
            else:
                return set()  # No match found

        # Intersect all matching sets
        if matching_sets:
            return set.intersection(*matching_sets)
        return set()

    def size(self) -> int:
        """Get number of data points"""
        return len(self._data)


class SageTSDB:
    """
    High-performance time series database for streaming data.

    Features:
    - Efficient storage and indexing of time series data
    - Support for out-of-order data ingestion
    - Fast queries with time range and tag filtering
    - Pluggable algorithms for stream processing
    - Window-based aggregations

    Uses C++ backend when available for optimal performance.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize time series database.

        Args:
            config: Optional configuration dictionary
        """
        self._config = config or {}

        # Use C++ backend if available
        if HAS_CPP_BACKEND:
            self._db = _sage_tsdb.TimeSeriesDB()  # type: ignore[attr-defined]
            self._backend = "cpp"
        else:
            # Fallback to pure Python implementation
            self._index = TimeSeriesIndex()
            self._backend = "python"

        self._algorithms: dict[str, Any] = {}

    def add(
        self,
        timestamp: int | datetime,
        value: float | np.ndarray,
        tags: dict[str, str] | None = None,
        fields: dict[str, Any] | None = None,
    ) -> int:
        """
        Add a single time series data point.

        Args:
            timestamp: Unix timestamp in milliseconds or datetime
            value: Numeric value or array
            tags: Optional tags for indexing
            fields: Optional additional fields

        Returns:
            Index of the added data point
        """
        if isinstance(timestamp, datetime):
            timestamp = int(timestamp.timestamp() * 1000)

        if self._backend == "cpp":
            # Use C++ backend
            if isinstance(value, np.ndarray):
                value_list = value.tolist()
            elif isinstance(value, (list, tuple)):
                value_list = list(value)
            else:
                value_list = value

            # C++ backend handles tags/fields differently
            return self._db.add(
                timestamp,
                value_list if isinstance(value_list, list) else value_list,
                tags or {},
                fields or {},
            )
        else:
            # Pure Python implementation
            data = TimeSeriesData(timestamp=timestamp, value=value, tags=tags, fields=fields)
            return self._index.add(data)

    def add_batch(
        self,
        timestamps: list[int] | list[datetime] | np.ndarray,
        values: list[float] | np.ndarray,
        tags_list: list[dict[str, str]] | None = None,
        fields_list: list[dict[str, Any]] | None = None,
    ) -> list[int]:
        """
        Add multiple time series data points.

        Args:
            timestamps: List of timestamps
            values: List of values
            tags_list: Optional list of tags
            fields_list: Optional list of fields

        Returns:
            List of indices for added data points
        """
        # Convert to consistent format
        if isinstance(timestamps, np.ndarray):
            timestamps = timestamps.tolist()
        if isinstance(values, np.ndarray):
            values = values.tolist()

        # Convert datetime to timestamps
        ts_list = []
        for ts in timestamps:
            if isinstance(ts, datetime):
                ts_list.append(int(ts.timestamp() * 1000))
            else:
                ts_list.append(ts)

        # Create data points
        n = len(ts_list)
        tags_list = tags_list or [None] * n  # type: ignore[list-item]
        fields_list = fields_list or [None] * n  # type: ignore[list-item]

        data_list = [
            TimeSeriesData(
                timestamp=ts_list[i],
                value=values[i],
                tags=tags_list[i],
                fields=fields_list[i],
            )
            for i in range(n)
        ]

        return self._index.add_batch(data_list)

    def query(
        self,
        time_range: TimeRange,
        tags: dict[str, str] | None = None,
        aggregation: AggregationType | None = None,
        window_size: int | None = None,
        limit: int | None = None,
    ) -> list[TimeSeriesData]:
        """
        Query time series data.

        Args:
            time_range: Time range for query
            tags: Optional tags to filter by
            aggregation: Optional aggregation type
            window_size: Optional window size for aggregation (ms)
            limit: Optional limit on number of results

        Returns:
            List of matching time series data points
        """
        config = QueryConfig(
            time_range=time_range,
            tags=tags,
            aggregation=aggregation,
            window_size=window_size,
            limit=limit,
        )

        results = self._index.query(config)

        # Apply aggregation if specified
        if aggregation and window_size:
            results = self._apply_aggregation(results, aggregation, window_size)

        return results

    def _apply_aggregation(
        self,
        data: list[TimeSeriesData],
        aggregation: AggregationType,
        window_size: int,
    ) -> list[TimeSeriesData]:
        """Apply window-based aggregation"""
        if not data:
            return []

        aggregated = []
        window_start = data[0].timestamp
        window_data = []

        for point in data:
            # Check if still in current window
            if point.timestamp < window_start + window_size:
                window_data.append(point)
            else:
                # Aggregate current window
                if window_data:
                    agg_point = self._aggregate_window(window_data, aggregation, window_start)
                    aggregated.append(agg_point)

                # Start new window
                window_start = point.timestamp
                window_data = [point]

        # Aggregate last window
        if window_data:
            agg_point = self._aggregate_window(window_data, aggregation, window_start)
            aggregated.append(agg_point)

        return aggregated

    def _aggregate_window(
        self,
        data: list[TimeSeriesData],
        aggregation: AggregationType,
        window_timestamp: int,
    ) -> TimeSeriesData:
        """Aggregate a window of data"""
        values = [point.value for point in data]

        if aggregation == AggregationType.SUM:
            agg_value = sum(values)
        elif aggregation == AggregationType.AVG:
            agg_value = sum(values) / len(values)
        elif aggregation == AggregationType.MIN:
            agg_value = min(values)
        elif aggregation == AggregationType.MAX:
            agg_value = max(values)
        elif aggregation == AggregationType.COUNT:
            agg_value = len(values)
        elif aggregation == AggregationType.FIRST:
            agg_value = values[0]
        elif aggregation == AggregationType.LAST:
            agg_value = values[-1]
        elif aggregation == AggregationType.STDDEV:
            agg_value = float(np.std(values))  # type: ignore[arg-type]
        else:
            agg_value = sum(values) / len(values)

        # Merge tags from all data points
        merged_tags = {}
        for point in data:
            if point.tags:
                merged_tags.update(point.tags)

        return TimeSeriesData(
            timestamp=window_timestamp,
            value=agg_value,
            tags=merged_tags,
            fields={"window_size": len(data)},
        )

    def register_algorithm(self, name: str, algorithm: Any):
        """
        Register a custom algorithm.

        Args:
            name: Algorithm name
            algorithm: Algorithm instance
        """
        self._algorithms[name] = algorithm

    def apply_algorithm(self, name: str, data: list[TimeSeriesData], **kwargs) -> Any:
        """
        Apply a registered algorithm.

        Args:
            name: Algorithm name
            data: Input data
            **kwargs: Algorithm-specific parameters

        Returns:
            Algorithm output
        """
        if name not in self._algorithms:
            raise ValueError(f"Algorithm '{name}' not registered")

        return self._algorithms[name].process(data, **kwargs)

    @property
    def size(self) -> int:
        """Get number of data points"""
        if self._backend == "cpp":
            return self._db.size()
        else:
            return self._index.size()

    def get_stats(self) -> dict[str, Any]:
        """Get database statistics"""
        stats = {
            "size": self.size,
            "backend": self._backend,
            "algorithms": list(self._algorithms.keys()),
        }

        if self._backend == "cpp":
            # Get C++ specific stats
            cpp_stats = self._db.get_stats()
            stats.update(cpp_stats)

        return stats


__all__ = [
    "SageTSDB",
    "TimeSeriesData",
    "TimeRange",
    "QueryConfig",
    "AggregationType",
    "InterpolationType",
]
