"""Factory and registry for Intent Recognition components.

This module provides dynamic registration and creation of intent implementations.
"""

from __future__ import annotations

from typing import Any, Callable

from sage.libs.intent.interface.base import IntentCatalog, IntentClassifier, IntentRecognizer

# Registry for intent implementations
_RECOGNIZER_REGISTRY: dict[str, Callable[..., IntentRecognizer]] = {}
_CLASSIFIER_REGISTRY: dict[str, Callable[..., IntentClassifier]] = {}
_CATALOG_REGISTRY: dict[str, Callable[..., IntentCatalog]] = {}


class IntentRegistryError(Exception):
    """Error raised when registry operations fail."""

    pass


def register_recognizer(name: str, factory: Callable[..., IntentRecognizer]) -> None:
    """Register an intent recognizer implementation.

    Args:
        name: Recognizer name (e.g., "keyword", "llm", "bert")
        factory: Factory function that creates recognizer instances
    """
    _RECOGNIZER_REGISTRY[name] = factory


def register_classifier(name: str, factory: Callable[..., IntentClassifier]) -> None:
    """Register an intent classifier implementation."""
    _CLASSIFIER_REGISTRY[name] = factory


def register_catalog(name: str, factory: Callable[..., IntentCatalog]) -> None:
    """Register an intent catalog implementation."""
    _CATALOG_REGISTRY[name] = factory


def create_recognizer(name: str, **kwargs: Any) -> IntentRecognizer:
    """Create an intent recognizer instance by name.

    Args:
        name: Registered recognizer name
        **kwargs: Recognizer-specific configuration

    Returns:
        IntentRecognizer instance

    Raises:
        IntentRegistryError: If recognizer name not registered

    Example:
        >>> recognizer = create_recognizer("llm", model="gpt-4")
        >>> result = recognizer.recognize("Book a flight to Paris")
    """
    if name not in _RECOGNIZER_REGISTRY:
        available = list(_RECOGNIZER_REGISTRY.keys())
        raise IntentRegistryError(
            f"Recognizer '{name}' not registered. Available: {available}. "
            f"Install 'isage-intent' package for implementations."
        )
    return _RECOGNIZER_REGISTRY[name](**kwargs)


def create_classifier(name: str, **kwargs: Any) -> IntentClassifier:
    """Create an intent classifier instance by name."""
    if name not in _CLASSIFIER_REGISTRY:
        available = list(_CLASSIFIER_REGISTRY.keys())
        raise IntentRegistryError(
            f"Classifier '{name}' not registered. Available: {available}. "
            f"Install 'isage-intent' package for implementations."
        )
    return _CLASSIFIER_REGISTRY[name](**kwargs)


def create_catalog(name: str, **kwargs: Any) -> IntentCatalog:
    """Create an intent catalog instance by name."""
    if name not in _CATALOG_REGISTRY:
        available = list(_CATALOG_REGISTRY.keys())
        raise IntentRegistryError(
            f"Catalog '{name}' not registered. Available: {available}. "
            f"Install 'isage-intent' package for implementations."
        )
    return _CATALOG_REGISTRY[name](**kwargs)


def list_recognizers() -> list[str]:
    """List all registered recognizer names."""
    return list(_RECOGNIZER_REGISTRY.keys())


def list_classifiers() -> list[str]:
    """List all registered classifier names."""
    return list(_CLASSIFIER_REGISTRY.keys())


def list_catalogs() -> list[str]:
    """List all registered catalog names."""
    return list(_CATALOG_REGISTRY.keys())


__all__ = [
    "IntentRegistryError",
    "register_recognizer",
    "register_classifier",
    "register_catalog",
    "create_recognizer",
    "create_classifier",
    "create_catalog",
    "list_recognizers",
    "list_classifiers",
    "list_catalogs",
]
