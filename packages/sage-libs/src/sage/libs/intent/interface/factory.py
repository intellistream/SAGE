"""Factory and registry for intent recognition implementations.

This module provides a registry pattern for intent recognition components.
External packages (like isage-intent) can register their implementations here.

Example:
    # Register implementations
    from sage.libs.intent.interface import (
        register_recognizer,
        register_classifier,
        register_catalog,
        register_extractor,
    )
    register_recognizer("keyword", KeywordRecognizer)
    register_classifier("bert", BERTClassifier)
    register_catalog("json", JSONCatalog)
    register_extractor("ner", NERSlotExtractor)

    # Create instances
    from sage.libs.intent.interface import (
        create_recognizer,
        create_classifier,
        create_catalog,
        create_extractor,
    )
    recognizer = create_recognizer("keyword")
    classifier = create_classifier("bert", model_name="bert-base-uncased")
    catalog = create_catalog("json", filepath="intents.json")
    extractor = create_extractor("ner")
"""

from typing import Any

from .base import IntentCatalog, IntentClassifier, IntentRecognizer, IntentSlotExtractor

_RECOGNIZER_REGISTRY: dict[str, type[IntentRecognizer]] = {}
_CLASSIFIER_REGISTRY: dict[str, type[IntentClassifier]] = {}
_CATALOG_REGISTRY: dict[str, type[IntentCatalog]] = {}
_EXTRACTOR_REGISTRY: dict[str, type[IntentSlotExtractor]] = {}


class IntentRegistryError(Exception):
    """Error raised when registry operations fail."""

    pass


# ========================================
# Intent Recognizer Registry
# ========================================


def register_recognizer(name: str, cls: type[IntentRecognizer]) -> None:
    """Register an intent recognizer implementation.

    Args:
        name: Unique identifier (e.g., "keyword", "bert", "llm")
        cls: Recognizer class (should inherit from IntentRecognizer)

    Raises:
        IntentRegistryError: If name already registered
    """
    if name in _RECOGNIZER_REGISTRY:
        raise IntentRegistryError(f"Recognizer '{name}' already registered")

    if not issubclass(cls, IntentRecognizer):
        raise TypeError(f"Class must inherit from IntentRecognizer, got {cls}")

    _RECOGNIZER_REGISTRY[name] = cls


def create_recognizer(name: str, **kwargs: Any) -> IntentRecognizer:
    """Create an intent recognizer instance by name.

    Args:
        name: Name of the registered recognizer
        **kwargs: Arguments to pass to the recognizer constructor

    Returns:
        Instance of the recognizer

    Raises:
        IntentRegistryError: If recognizer not found
    """
    if name not in _RECOGNIZER_REGISTRY:
        available = ", ".join(_RECOGNIZER_REGISTRY.keys()) if _RECOGNIZER_REGISTRY else "none"
        raise IntentRegistryError(
            f"Recognizer '{name}' not found. "
            f"Available: {available}. "
            f"Did you install 'isage-intent'?"
        )

    cls = _RECOGNIZER_REGISTRY[name]
    return cls(**kwargs)


def list_recognizers() -> list[str]:
    """Get list of registered recognizer names."""
    return list(_RECOGNIZER_REGISTRY.keys())


# ========================================
# Intent Classifier Registry
# ========================================


def register_classifier(name: str, cls: type[IntentClassifier]) -> None:
    """Register an intent classifier implementation.

    Args:
        name: Unique identifier (e.g., "svm", "bert", "zero_shot")
        cls: Classifier class (should inherit from IntentClassifier)

    Raises:
        IntentRegistryError: If name already registered
    """
    if name in _CLASSIFIER_REGISTRY:
        raise IntentRegistryError(f"Classifier '{name}' already registered")

    if not issubclass(cls, IntentClassifier):
        raise TypeError(f"Class must inherit from IntentClassifier, got {cls}")

    _CLASSIFIER_REGISTRY[name] = cls


def create_classifier(name: str, **kwargs: Any) -> IntentClassifier:
    """Create an intent classifier instance by name.

    Args:
        name: Name of the registered classifier
        **kwargs: Arguments to pass to the classifier constructor

    Returns:
        Instance of the classifier

    Raises:
        IntentRegistryError: If classifier not found
    """
    if name not in _CLASSIFIER_REGISTRY:
        available = ", ".join(_CLASSIFIER_REGISTRY.keys()) if _CLASSIFIER_REGISTRY else "none"
        raise IntentRegistryError(
            f"Classifier '{name}' not found. "
            f"Available: {available}. "
            f"Did you install 'isage-intent'?"
        )

    cls = _CLASSIFIER_REGISTRY[name]
    return cls(**kwargs)


def list_classifiers() -> list[str]:
    """Get list of registered classifier names."""
    return list(_CLASSIFIER_REGISTRY.keys())


# ========================================
# Intent Catalog Registry
# ========================================


def register_catalog(name: str, cls: type[IntentCatalog]) -> None:
    """Register an intent catalog implementation.

    Args:
        name: Unique identifier (e.g., "json", "yaml", "database")
        cls: Catalog class (should inherit from IntentCatalog)

    Raises:
        IntentRegistryError: If name already registered
    """
    if name in _CATALOG_REGISTRY:
        raise IntentRegistryError(f"Catalog '{name}' already registered")

    if not issubclass(cls, IntentCatalog):
        raise TypeError(f"Class must inherit from IntentCatalog, got {cls}")

    _CATALOG_REGISTRY[name] = cls


def create_catalog(name: str, **kwargs: Any) -> IntentCatalog:
    """Create an intent catalog instance by name.

    Args:
        name: Name of the registered catalog
        **kwargs: Arguments to pass to the catalog constructor

    Returns:
        Instance of the catalog

    Raises:
        IntentRegistryError: If catalog not found
    """
    if name not in _CATALOG_REGISTRY:
        available = ", ".join(_CATALOG_REGISTRY.keys()) if _CATALOG_REGISTRY else "none"
        raise IntentRegistryError(
            f"Catalog '{name}' not found. Available: {available}. Did you install 'isage-intent'?"
        )

    cls = _CATALOG_REGISTRY[name]
    return cls(**kwargs)


def list_catalogs() -> list[str]:
    """Get list of registered catalog names."""
    return list(_CATALOG_REGISTRY.keys())


# ========================================
# Slot Extractor Registry
# ========================================


def register_extractor(name: str, cls: type[IntentSlotExtractor]) -> None:
    """Register a slot extractor implementation.

    Args:
        name: Unique identifier (e.g., "ner", "regex", "llm")
        cls: Extractor class (should inherit from IntentSlotExtractor)

    Raises:
        IntentRegistryError: If name already registered
    """
    if name in _EXTRACTOR_REGISTRY:
        raise IntentRegistryError(f"Extractor '{name}' already registered")

    if not issubclass(cls, IntentSlotExtractor):
        raise TypeError(f"Class must inherit from IntentSlotExtractor, got {cls}")

    _EXTRACTOR_REGISTRY[name] = cls


def create_extractor(name: str, **kwargs: Any) -> IntentSlotExtractor:
    """Create a slot extractor instance by name.

    Args:
        name: Name of the registered extractor
        **kwargs: Arguments to pass to the extractor constructor

    Returns:
        Instance of the extractor

    Raises:
        IntentRegistryError: If extractor not found
    """
    if name not in _EXTRACTOR_REGISTRY:
        available = ", ".join(_EXTRACTOR_REGISTRY.keys()) if _EXTRACTOR_REGISTRY else "none"
        raise IntentRegistryError(
            f"Extractor '{name}' not found. Available: {available}. Did you install 'isage-intent'?"
        )

    cls = _EXTRACTOR_REGISTRY[name]
    return cls(**kwargs)


def list_extractors() -> list[str]:
    """Get list of registered extractor names."""
    return list(_EXTRACTOR_REGISTRY.keys())


# ========================================
# Testing Utilities
# ========================================


def unregister_recognizer(name: str) -> None:
    """Unregister a recognizer (for testing)."""
    _RECOGNIZER_REGISTRY.pop(name, None)


def unregister_classifier(name: str) -> None:
    """Unregister a classifier (for testing)."""
    _CLASSIFIER_REGISTRY.pop(name, None)


def unregister_catalog(name: str) -> None:
    """Unregister a catalog (for testing)."""
    _CATALOG_REGISTRY.pop(name, None)


def unregister_extractor(name: str) -> None:
    """Unregister an extractor (for testing)."""
    _EXTRACTOR_REGISTRY.pop(name, None)


__all__ = [
    "IntentRegistryError",
    # Recognizer
    "register_recognizer",
    "create_recognizer",
    "list_recognizers",
    "unregister_recognizer",
    # Classifier
    "register_classifier",
    "create_classifier",
    "list_classifiers",
    "unregister_classifier",
    # Catalog
    "register_catalog",
    "create_catalog",
    "list_catalogs",
    "unregister_catalog",
    # Extractor
    "register_extractor",
    "create_extractor",
    "list_extractors",
    "unregister_extractor",
]
