"""Base interfaces for SIAS (Stream-based Intent-Aware Selection) components.

This module defines the abstract interfaces for tool selection reasoning.
Implementations are provided by the external package 'isage-sias'.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ContinualLearner(ABC):
    """Abstract base class for continual learning components."""

    @abstractmethod
    def update(self, new_data: Any) -> None:
        """Update the learner with new data.

        Args:
            new_data: New training samples
        """
        pass

    @abstractmethod
    def predict(self, input_data: Any) -> Any:
        """Make predictions on input data.

        Args:
            input_data: Input for prediction

        Returns:
            Prediction results
        """
        pass

    @abstractmethod
    def forget(self, data_to_forget: Any) -> None:
        """Forget specific data (for privacy/compliance).

        Args:
            data_to_forget: Data to remove from memory
        """
        pass


class CoresetSelector(ABC):
    """Abstract base class for coreset selection."""

    @abstractmethod
    def select(self, data: Any, budget: int) -> Any:
        """Select a representative subset (coreset) from data.

        Args:
            data: Full dataset
            budget: Maximum number of samples to select

        Returns:
            Selected coreset samples
        """
        pass

    @abstractmethod
    def importance_score(self, sample: Any) -> float:
        """Calculate importance score for a sample.

        Args:
            sample: Data sample

        Returns:
            Importance score (higher = more important)
        """
        pass


__all__ = [
    "ContinualLearner",
    "CoresetSelector",
]
