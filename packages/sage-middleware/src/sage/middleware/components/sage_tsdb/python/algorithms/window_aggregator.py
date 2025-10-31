"""
Window Aggregator Algorithm

Provides various windowing strategies for time series aggregation,
including tumbling, sliding, and session windows.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

from ..sage_tsdb import AggregationType, TimeSeriesData
from .base import TimeSeriesAlgorithm


class WindowType(Enum):
    """Window types for aggregation"""

    TUMBLING = "tumbling"  # Non-overlapping fixed-size windows
    SLIDING = "sliding"  # Overlapping fixed-size windows
    SESSION = "session"  # Dynamic windows based on inactivity gap


@dataclass
class WindowConfig:
    """Configuration for windowing"""

    window_type: WindowType
    window_size: int  # milliseconds
    slide_interval: int | None = None  # for sliding windows (ms)
    session_gap: int | None = None  # for session windows (ms)
    aggregation: AggregationType = AggregationType.AVG


class WindowAggregator(TimeSeriesAlgorithm):
    """
    Window-based aggregation algorithm.

    Supports multiple windowing strategies:
    - Tumbling windows: Non-overlapping fixed-size windows
    - Sliding windows: Overlapping windows with configurable slide interval
    - Session windows: Dynamic windows based on inactivity gaps

    Features:
    - Multiple aggregation functions (sum, avg, min, max, count, etc.)
    - Efficient incremental computation
    - Support for late data handling
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize window aggregator.

        Args:
            config: Configuration dictionary with:
                - window_type: Type of window (tumbling/sliding/session)
                - window_size: Window size in milliseconds
                - slide_interval: Slide interval for sliding windows (ms)
                - session_gap: Inactivity gap for session windows (ms)
                - aggregation: Aggregation function to apply
        """
        super().__init__(config)

        window_type_str = self.config.get("window_type", "tumbling")
        self.window_type = WindowType(window_type_str)
        self.window_size = self.config.get("window_size", 60000)  # 1 minute
        self.slide_interval = self.config.get("slide_interval", self.window_size)
        self.session_gap = self.config.get("session_gap", 30000)  # 30 seconds

        agg_str = self.config.get("aggregation", "avg")
        if isinstance(agg_str, str):
            self.aggregation = AggregationType(agg_str)
        else:
            self.aggregation = agg_str

        # State for incremental processing
        self.windows: dict[int, list[TimeSeriesData]] = {}
        self.stats = {
            "windows_created": 0,
            "windows_completed": 0,
            "data_points_processed": 0,
        }

    def process(self, data: list[TimeSeriesData], **kwargs) -> list[TimeSeriesData]:
        """
        Process time series data with windowing.

        Args:
            data: Input time series data points
            **kwargs: Additional parameters

        Returns:
            Aggregated time series data (one point per window)
        """
        if not data:
            return []

        # Sort data by timestamp
        sorted_data = sorted(data, key=lambda x: x.timestamp)

        # Apply windowing based on type
        if self.window_type == WindowType.TUMBLING:
            return self._tumbling_window(sorted_data)
        elif self.window_type == WindowType.SLIDING:
            return self._sliding_window(sorted_data)
        elif self.window_type == WindowType.SESSION:
            return self._session_window(sorted_data)

        return []

    def _tumbling_window(self, data: list[TimeSeriesData]) -> list[TimeSeriesData]:
        """Process with tumbling windows"""
        if not data:
            return []

        results = []
        window_start = self._align_to_window(data[0].timestamp)
        window_data = []

        for point in data:
            window_key = self._get_window_key(point.timestamp, window_start)

            # Check if point belongs to current window
            if window_key == window_start:
                window_data.append(point)
            else:
                # Complete current window
                if window_data:
                    agg_point = self._aggregate_window(window_data, window_start)
                    results.append(agg_point)
                    self.stats["windows_completed"] += 1

                # Start new window(s)
                # Handle potential gaps
                while window_key > window_start:
                    window_start += self.window_size

                window_data = [point]
                self.stats["windows_created"] += 1

        # Complete last window
        if window_data:
            agg_point = self._aggregate_window(window_data, window_start)
            results.append(agg_point)
            self.stats["windows_completed"] += 1

        self.stats["data_points_processed"] += len(data)
        return results

    def _sliding_window(self, data: list[TimeSeriesData]) -> list[TimeSeriesData]:
        """Process with sliding windows"""
        if not data:
            return []

        results = []

        # Get first window start
        first_timestamp = data[0].timestamp
        window_start = self._align_to_window(first_timestamp)

        # Create windows until we've covered all data
        last_timestamp = data[-1].timestamp

        while window_start <= last_timestamp:
            window_end = window_start + self.window_size

            # Get data points in this window
            window_data = [point for point in data if window_start <= point.timestamp < window_end]

            if window_data:
                agg_point = self._aggregate_window(window_data, window_start)
                results.append(agg_point)
                self.stats["windows_completed"] += 1

            # Slide to next window
            window_start += self.slide_interval
            self.stats["windows_created"] += 1

        self.stats["data_points_processed"] += len(data)
        return results

    def _session_window(self, data: list[TimeSeriesData]) -> list[TimeSeriesData]:
        """Process with session windows"""
        if not data:
            return []

        results = []
        session_data = []
        last_timestamp = data[0].timestamp
        session_start = data[0].timestamp

        for point in data:
            # Check if point is within session gap
            if point.timestamp - last_timestamp <= self.session_gap:
                session_data.append(point)
            else:
                # Complete current session
                if session_data:
                    agg_point = self._aggregate_window(session_data, session_start)
                    results.append(agg_point)
                    self.stats["windows_completed"] += 1

                # Start new session
                session_data = [point]
                session_start = point.timestamp
                self.stats["windows_created"] += 1

            last_timestamp = point.timestamp

        # Complete last session
        if session_data:
            agg_point = self._aggregate_window(session_data, session_start)
            results.append(agg_point)
            self.stats["windows_completed"] += 1

        self.stats["data_points_processed"] += len(data)
        return results

    def _align_to_window(self, timestamp: int) -> int:
        """Align timestamp to window boundary"""
        return (timestamp // self.window_size) * self.window_size

    def _get_window_key(self, timestamp: int, reference: int) -> int:
        """Get window key for timestamp"""
        return self._align_to_window(timestamp)

    def _aggregate_window(
        self, data: list[TimeSeriesData], window_timestamp: int
    ) -> TimeSeriesData:
        """Aggregate data in a window"""
        if not data:
            return TimeSeriesData(timestamp=window_timestamp, value=0.0)

        # Extract values
        values = []
        for point in data:
            # Flatten arrays/lists, append scalars
            if isinstance(point.value, (list, np.ndarray)):
                # Use np.ravel to flatten, then convert to list and extend
                values.extend(np.ravel(point.value).tolist())
            else:
                values.append(point.value)

        # Apply aggregation
        if self.aggregation == AggregationType.SUM:
            agg_value = sum(values)
        elif self.aggregation == AggregationType.AVG:
            agg_value = sum(values) / len(values)
        elif self.aggregation == AggregationType.MIN:
            agg_value = min(values)
        elif self.aggregation == AggregationType.MAX:
            agg_value = max(values)
        elif self.aggregation == AggregationType.COUNT:
            agg_value = len(values)
        elif self.aggregation == AggregationType.FIRST:
            agg_value = values[0]
        elif self.aggregation == AggregationType.LAST:
            agg_value = values[-1]
        elif self.aggregation == AggregationType.STDDEV:
            agg_value = float(np.std(values))
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
            fields={"window_size": len(data), "aggregation": self.aggregation.value},
        )

    def reset(self):
        """Reset algorithm state"""
        self.windows = {}
        self.stats = {
            "windows_created": 0,
            "windows_completed": 0,
            "data_points_processed": 0,
        }

    def get_stats(self) -> dict[str, Any]:
        """Get aggregator statistics"""
        return {
            **self.stats,
            "active_windows": len(self.windows),
        }


__all__ = ["WindowAggregator", "WindowType", "WindowConfig"]
