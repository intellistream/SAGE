"""Base interfaces for Intent Recognition components.

This module defines the abstract interfaces for intent classification.
Implementations are provided by the external package 'isage-intent'.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IntentRecognizer(ABC):
    """Abstract base class for intent recognizers."""

    @abstractmethod
    def recognize(self, text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Recognize intent from text.

        Args:
            text: Input text
            context: Optional context information

        Returns:
            Dictionary with keys:
                - intent: Recognized intent label
                - confidence: Confidence score (0-1)
                - entities: Extracted entities (optional)
        """
        pass

    @abstractmethod
    def get_supported_intents(self) -> list[str]:
        """Get list of supported intent labels."""
        pass


class IntentClassifier(ABC):
    """Abstract base class for intent classifiers."""

    @abstractmethod
    def classify(self, text: str) -> str:
        """Classify text into an intent category.

        Args:
            text: Input text

        Returns:
            Intent label
        """
        pass

    @abstractmethod
    def classify_batch(self, texts: list[str]) -> list[str]:
        """Classify multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of intent labels
        """
        pass


class IntentCatalog(ABC):
    """Abstract base class for intent catalogs."""

    @abstractmethod
    def register_intent(self, name: str, description: str, examples: list[str]) -> None:
        """Register a new intent type.

        Args:
            name: Intent name
            description: Intent description
            examples: Example texts for this intent
        """
        pass

    @abstractmethod
    def get_intent(self, name: str) -> dict[str, Any]:
        """Get intent definition by name."""
        pass

    @abstractmethod
    def list_intents(self) -> list[str]:
        """List all registered intent names."""
        pass


__all__ = [
    "IntentRecognizer",
    "IntentClassifier",
    "IntentCatalog",
]
