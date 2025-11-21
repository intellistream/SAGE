"""
Out-of-Order Stream Join Algorithm

This algorithm handles joining two time series streams that may arrive
out of order, using windowing and buffering strategies.
"""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..sage_tsdb import TimeSeriesData
from .base import TimeSeriesAlgorithm


@dataclass
class JoinConfig:
    """Configuration for stream join"""

    window_size: int  # milliseconds
    max_delay: int  # maximum out-of-order delay (ms)
    join_key: str | None = None  # tag key for join condition
    join_predicate: Callable[[TimeSeriesData, TimeSeriesData], bool] | None = None


class StreamBuffer:
    """Buffer for managing out-of-order streams"""

    def __init__(self, max_delay: int):
        """
        Initialize stream buffer.

        Args:
            max_delay: Maximum allowed delay (ms)
        """
        self.max_delay = max_delay
        self.buffer: list[TimeSeriesData] = []
        self.watermark = 0  # Current watermark timestamp

    def add(self, data: TimeSeriesData):
        """Add data to buffer"""
        self.buffer.append(data)
        self._update_watermark()

    def add_batch(self, data_list: list[TimeSeriesData]):
        """Add multiple data points to buffer"""
        self.buffer.extend(data_list)
        self._update_watermark()

    def _update_watermark(self):
        """Update watermark based on latest data"""
        if self.buffer:
            # Sort buffer by timestamp
            self.buffer.sort(key=lambda x: x.timestamp)
            # Watermark is the latest timestamp minus max delay
            latest = self.buffer[-1].timestamp
            self.watermark = latest - self.max_delay

    def get_ready_data(self) -> list[TimeSeriesData]:
        """Get data that's ready for processing (before watermark)"""
        ready = [d for d in self.buffer if d.timestamp <= self.watermark]
        # Remove ready data from buffer
        self.buffer = [d for d in self.buffer if d.timestamp > self.watermark]
        return ready

    def size(self) -> int:
        """Get buffer size"""
        return len(self.buffer)


class OutOfOrderStreamJoin(TimeSeriesAlgorithm):
    """
    Out-of-Order Stream Join Algorithm.

    This algorithm joins two time series streams that may arrive out of order.
    It uses windowing and watermarking to handle late data while maintaining
    join correctness.

    Features:
    - Handles out-of-order data arrival
    - Window-based join semantics
    - Configurable watermarking for late data
    - Support for custom join predicates
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize stream join algorithm.

        Args:
            config: Configuration dictionary with:
                - window_size: Join window size in milliseconds
                - max_delay: Maximum out-of-order delay in milliseconds
                - join_key: Optional tag key for equi-join
                - join_predicate: Optional custom join predicate function
        """
        super().__init__(config)

        self.window_size = self.config.get("window_size", 10000)  # 10 seconds
        self.max_delay = self.config.get("max_delay", 5000)  # 5 seconds
        self.join_key = self.config.get("join_key", None)
        self.join_predicate = self.config.get("join_predicate", None)

        # Buffers for two streams
        self.left_buffer = StreamBuffer(self.max_delay)
        self.right_buffer = StreamBuffer(self.max_delay)

        # Statistics
        self.stats = {
            "total_joined": 0,
            "late_arrivals": 0,
            "dropped_late": 0,
        }

    def add_left_stream(self, data: list[TimeSeriesData]):
        """Add data to left stream"""
        self.left_buffer.add_batch(data)

    def add_right_stream(self, data: list[TimeSeriesData]):
        """Add data to right stream"""
        self.right_buffer.add_batch(data)

    def process(
        self,
        data: list[TimeSeriesData] | None = None,
        left_stream: list[TimeSeriesData] | None = None,
        right_stream: list[TimeSeriesData] | None = None,
        **kwargs,
    ) -> list[tuple[TimeSeriesData, TimeSeriesData]]:
        """
        Process stream join.

        Args:
            data: Not used (for compatibility)
            left_stream: Data from left stream
            right_stream: Data from right stream
            **kwargs: Additional parameters

        Returns:
            List of joined data pairs
        """
        # Add data to buffers
        if left_stream:
            self.add_left_stream(left_stream)
        if right_stream:
            self.add_right_stream(right_stream)

        # Get ready data from both buffers
        left_ready = self.left_buffer.get_ready_data()
        right_ready = self.right_buffer.get_ready_data()

        # Perform join
        joined = self._join_data(left_ready, right_ready)

        # Update statistics
        self.stats["total_joined"] += len(joined)

        return joined

    def _join_data(
        self, left_data: list[TimeSeriesData], right_data: list[TimeSeriesData]
    ) -> list[tuple[TimeSeriesData, TimeSeriesData]]:
        """
        Join data from two streams.

        Args:
            left_data: Data from left stream
            right_data: Data from right stream

        Returns:
            List of joined pairs
        """
        joined = []

        # If join key is specified, use hash join
        if self.join_key:
            joined = self._hash_join(left_data, right_data)
        else:
            # Use nested loop join with window condition
            joined = self._nested_loop_join(left_data, right_data)

        return joined

    def _hash_join(
        self, left_data: list[TimeSeriesData], right_data: list[TimeSeriesData]
    ) -> list[tuple[TimeSeriesData, TimeSeriesData]]:
        """Hash join on specified key"""
        joined = []

        # Build hash table for right stream
        right_hash: dict[str, list[TimeSeriesData]] = defaultdict(list)
        for right in right_data:
            key_value = right.tags.get(self.join_key) if self.join_key else None
            if key_value:
                right_hash[key_value].append(right)

        # Probe with left stream
        for left in left_data:
            key_value = left.tags.get(self.join_key) if self.join_key else None
            if key_value and key_value in right_hash:
                for right in right_hash[key_value]:
                    # Check window condition
                    if abs(left.timestamp - right.timestamp) <= self.window_size:
                        # Check custom predicate if provided
                        if self.join_predicate is None or self.join_predicate(left, right):
                            joined.append((left, right))

        return joined

    def _nested_loop_join(
        self, left_data: list[TimeSeriesData], right_data: list[TimeSeriesData]
    ) -> list[tuple[TimeSeriesData, TimeSeriesData]]:
        """Nested loop join with window condition"""
        joined = []

        for left in left_data:
            for right in right_data:
                # Check window condition
                if abs(left.timestamp - right.timestamp) <= self.window_size:
                    # Check custom predicate if provided
                    if self.join_predicate is None or self.join_predicate(left, right):
                        joined.append((left, right))

        return joined

    def reset(self):
        """Reset algorithm state"""
        self.left_buffer = StreamBuffer(self.max_delay)
        self.right_buffer = StreamBuffer(self.max_delay)
        self.stats = {
            "total_joined": 0,
            "late_arrivals": 0,
            "dropped_late": 0,
        }

    def get_stats(self) -> dict[str, Any]:
        """Get join statistics"""
        return {
            **self.stats,
            "left_buffer_size": self.left_buffer.size(),
            "right_buffer_size": self.right_buffer.size(),
            "left_watermark": self.left_buffer.watermark,
            "right_watermark": self.right_buffer.watermark,
        }


__all__ = ["OutOfOrderStreamJoin", "JoinConfig", "StreamBuffer"]
