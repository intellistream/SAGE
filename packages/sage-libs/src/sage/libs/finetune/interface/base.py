"""Base interfaces for fine-tuning components.

This module defines the abstract interfaces for model fine-tuning.
Implementations are provided by the external package 'isage-finetune'.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Trainer(ABC):
    """Abstract base class for model trainers."""

    @abstractmethod
    def train(
        self,
        model: Any,
        train_data: Any,
        val_data: Any | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Train the model.

        Args:
            model: Model to train
            train_data: Training dataset
            val_data: Validation dataset (optional)
            **kwargs: Training-specific parameters

        Returns:
            Training metrics and results
        """
        pass

    @abstractmethod
    def save_checkpoint(self, path: str) -> None:
        """Save training checkpoint."""
        pass

    @abstractmethod
    def load_checkpoint(self, path: str) -> None:
        """Load training checkpoint."""
        pass


class FinetuneConfig(ABC):
    """Abstract base class for fine-tuning configurations."""

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        pass

    @abstractmethod
    def validate(self) -> None:
        """Validate configuration."""
        pass


class DataFormatter(ABC):
    """Abstract base class for data formatters."""

    @abstractmethod
    def format(self, raw_data: Any) -> Any:
        """Format raw data for training.

        Args:
            raw_data: Raw input data

        Returns:
            Formatted training data
        """
        pass


__all__ = [
    "Trainer",
    "FinetuneConfig",
    "DataFormatter",
]
