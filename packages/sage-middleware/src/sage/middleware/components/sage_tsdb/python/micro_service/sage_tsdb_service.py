from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np

from ..algorithms import OutOfOrderStreamJoin, WindowAggregator
from ..sage_tsdb import AggregationType, SageTSDB, TimeRange


@dataclass
class SageTSDBServiceConfig:
    """Configuration for SageTSDB service"""

    # Database configuration
    enable_compression: bool = False
    max_memory_mb: int = 1024

    # Algorithm defaults
    default_window_size: int = 60000  # 1 minute in milliseconds
    default_aggregation: str = "avg"


class SageTSDBService:
    """
    A micro-service style wrapper for SageTSDB.

    This service provides a simplified interface for time series operations
    and integrates with SAGE's service ecosystem.

    Methods:
      - add(timestamp, value, tags, fields) -> int
      - add_batch(timestamps, values, tags_list, fields_list) -> list[int]
      - query(start_time, end_time, tags, aggregation, window_size) -> list[dict]
      - stream_join(left_stream, right_stream, window_size, join_key) -> list[dict]
      - window_aggregate(data, window_type, window_size, aggregation) -> list[dict]
    """

    def __init__(self, config: SageTSDBServiceConfig | None = None) -> None:
        """
        Initialize SageTSDB service.

        Args:
            config: Optional service configuration
        """
        self._config = config or SageTSDBServiceConfig()
        self._db = SageTSDB()

        # Register default algorithms
        self._register_default_algorithms()

        # Statistics
        self._stats = {
            "total_writes": 0,
            "total_queries": 0,
            "total_joins": 0,
            "total_aggregations": 0,
        }

    def _register_default_algorithms(self):
        """Register commonly used algorithms"""
        # Out-of-order stream join
        join_algo = OutOfOrderStreamJoin(
            {
                "window_size": self._config.default_window_size,
                "max_delay": 5000,  # 5 seconds
            }
        )
        self._db.register_algorithm("stream_join", join_algo)

        # Window aggregator
        window_algo = WindowAggregator(
            {
                "window_type": "tumbling",
                "window_size": self._config.default_window_size,
                "aggregation": self._config.default_aggregation,
            }
        )
        self._db.register_algorithm("window_aggregate", window_algo)

    def add(
        self,
        timestamp: int | datetime,
        value: float | np.ndarray | list[float],
        tags: dict[str, str] | None = None,
        fields: dict[str, Any] | None = None,
    ) -> int:
        """
        Add a single time series data point.

        Args:
            timestamp: Unix timestamp (ms) or datetime object
            value: Numeric value or array
            tags: Optional tags for indexing
            fields: Optional additional fields

        Returns:
            Index of the added data point
        """
        if isinstance(value, list):
            value = np.array(value, dtype=np.float32)

        idx = self._db.add(timestamp=timestamp, value=value, tags=tags, fields=fields)

        self._stats["total_writes"] += 1
        return idx

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
        indices = self._db.add_batch(
            timestamps=timestamps,
            values=values,
            tags_list=tags_list,
            fields_list=fields_list,
        )

        self._stats["total_writes"] += len(indices)
        return indices

    def query(
        self,
        start_time: int | datetime,
        end_time: int | datetime,
        tags: dict[str, str] | None = None,
        aggregation: str | None = None,
        window_size: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query time series data.

        Args:
            start_time: Start of time range
            end_time: End of time range
            tags: Optional tags to filter by
            aggregation: Optional aggregation type (sum/avg/min/max/count/etc.)
            window_size: Optional window size for aggregation (ms)
            limit: Optional limit on number of results

        Returns:
            List of matching time series data as dictionaries
        """
        # Create time range
        time_range = TimeRange(start_time=start_time, end_time=end_time)

        # Convert aggregation string to enum if provided
        agg_type = None
        if aggregation:
            agg_type = AggregationType(aggregation)

        # Query database
        results = self._db.query(
            time_range=time_range,
            tags=tags,
            aggregation=agg_type,
            window_size=window_size,
            limit=limit,
        )

        # Convert to dictionary format
        formatted = []
        for r in results:
            formatted.append(
                {
                    "timestamp": r.timestamp,
                    "value": (
                        float(r.value)
                        if isinstance(r.value, (int, float))
                        else (r.value.tolist() if isinstance(r.value, np.ndarray) else r.value)
                    ),
                    "tags": dict(r.tags) if r.tags else {},
                    "fields": dict(r.fields) if r.fields else {},
                }
            )

        self._stats["total_queries"] += 1
        return formatted

    def stream_join(
        self,
        left_stream: list[dict[str, Any]],
        right_stream: list[dict[str, Any]],
        window_size: int | None = None,
        max_delay: int | None = None,
        join_key: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Perform out-of-order stream join.

        Args:
            left_stream: Data from left stream (list of dicts with timestamp, value, tags)
            right_stream: Data from right stream
            window_size: Join window size in milliseconds
            max_delay: Maximum out-of-order delay in milliseconds
            join_key: Optional tag key for equi-join

        Returns:
            List of joined results
        """
        # Create or update join algorithm
        config = {
            "window_size": window_size or self._config.default_window_size,
            "max_delay": max_delay or 5000,
            "join_key": join_key,
        }

        join_algo = OutOfOrderStreamJoin(config)

        # Convert input dictionaries to TimeSeriesData
        from ..sage_tsdb import TimeSeriesData

        left_data = [
            TimeSeriesData(
                timestamp=item["timestamp"],
                value=item["value"],
                tags=item.get("tags"),
                fields=item.get("fields"),
            )
            for item in left_stream
        ]

        right_data = [
            TimeSeriesData(
                timestamp=item["timestamp"],
                value=item["value"],
                tags=item.get("tags"),
                fields=item.get("fields"),
            )
            for item in right_stream
        ]

        # Perform join
        joined = join_algo.process(left_stream=left_data, right_stream=right_data)

        # Format results
        results = []
        for left, right in joined:
            results.append(
                {
                    "left": {
                        "timestamp": left.timestamp,
                        "value": (
                            float(left.value)
                            if isinstance(left.value, (int, float))
                            else left.value
                        ),
                        "tags": dict(left.tags) if left.tags else {},
                    },
                    "right": {
                        "timestamp": right.timestamp,
                        "value": (
                            float(right.value)
                            if isinstance(right.value, (int, float))
                            else right.value
                        ),
                        "tags": dict(right.tags) if right.tags else {},
                    },
                }
            )

        self._stats["total_joins"] += 1
        return results

    def window_aggregate(
        self,
        start_time: int | datetime,
        end_time: int | datetime,
        window_type: str = "tumbling",
        window_size: int | None = None,
        aggregation: str = "avg",
        tags: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Perform window-based aggregation.

        Args:
            start_time: Start of time range
            end_time: End of time range
            window_type: Type of window (tumbling/sliding/session)
            window_size: Window size in milliseconds
            aggregation: Aggregation function (sum/avg/min/max/count/etc.)
            tags: Optional tags to filter by

        Returns:
            List of aggregated results
        """
        # Query data first
        time_range = TimeRange(start_time=start_time, end_time=end_time)
        data = self._db.query(time_range=time_range, tags=tags)

        # Create aggregator
        config = {
            "window_type": window_type,
            "window_size": window_size or self._config.default_window_size,
            "aggregation": aggregation,
        }

        aggregator = WindowAggregator(config)

        # Perform aggregation
        aggregated = aggregator.process(data)

        # Format results
        results = []
        for item in aggregated:
            results.append(
                {
                    "timestamp": item.timestamp,
                    "value": (
                        float(item.value) if isinstance(item.value, (int, float)) else item.value
                    ),
                    "tags": dict(item.tags) if item.tags else {},
                    "fields": dict(item.fields) if item.fields else {},
                }
            )

        self._stats["total_aggregations"] += 1
        return results

    def stats(self) -> dict[str, Any]:
        """
        Get service statistics.

        Returns:
            Dictionary with service statistics
        """
        db_stats = self._db.get_stats()
        return {
            **self._stats,
            "db_size": db_stats["size"],
            "registered_algorithms": db_stats["algorithms"],
        }

    def reset(self):
        """Reset service state"""
        self._db = SageTSDB()
        self._register_default_algorithms()
        self._stats = {
            "total_writes": 0,
            "total_queries": 0,
            "total_joins": 0,
            "total_aggregations": 0,
        }


__all__ = ["SageTSDBService", "SageTSDBServiceConfig"]
