"""
Base algorithm interface for time series processing.
"""

from abc import ABC, abstractmethod
from typing import Any

from ..sage_tsdb import TimeSeriesData


class TimeSeriesAlgorithm(ABC):
    """
    Base class for time series processing algorithms.

    All algorithm implementations should inherit from this class and
    implement the process method.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize algorithm.

        Args:
            config: Algorithm-specific configuration
        """
        self.config = config or {}

    @abstractmethod
    def process(self, data: list[TimeSeriesData], **kwargs) -> Any:
        """
        Process time series data.

        Args:
            data: Input time series data points
            **kwargs: Additional algorithm-specific parameters

        Returns:
            Processed results (algorithm-specific format)
        """
        pass

    def reset(self):  # noqa: B027
        """Reset algorithm state (for stateful algorithms)"""
        pass

    def get_stats(self) -> dict[str, Any]:
        """Get algorithm statistics"""
        return {}


__all__ = ["TimeSeriesAlgorithm"]
