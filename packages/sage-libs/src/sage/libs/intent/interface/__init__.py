"""Intent recognition interface layer for SAGE.

This module provides abstract interfaces for intent recognition and NLU components.
Concrete implementations are provided by external packages (e.g., isage-intent).

Architecture:
    - base.py: Abstract base classes (IntentRecognizer, IntentClassifier, etc.)
    - factory.py: Registry and factory functions for each component type
    - External packages register their implementations at import time

Usage:
    # Option 1: Direct instantiation (if you know the implementation)
    from isage_intent import KeywordRecognizer, BERTClassifier
    recognizer = KeywordRecognizer()
    classifier = BERTClassifier(model_name="bert-base-uncased")

    # Option 2: Factory pattern (more flexible)
    from sage.libs.intent.interface import create_recognizer, create_classifier
    recognizer = create_recognizer("keyword")
    classifier = create_classifier("bert", model_name="bert-base-uncased")

    # Use components
    intent = recognizer.recognize("Book a flight to Paris")
    category = classifier.classify("What's the weather today?")
"""

# Base classes and data types
from .base import (
    Intent,
    IntentCatalog,
    IntentClassifier,
    IntentDefinition,
    IntentRecognizer,
    IntentSlotExtractor,
    Slot,
)

# Factory functions
from .factory import (
    IntentRegistryError,
    create_catalog,
    create_classifier,
    create_extractor,
    create_recognizer,
    list_catalogs,
    list_classifiers,
    list_extractors,
    list_recognizers,
    register_catalog,
    register_classifier,
    register_extractor,
    register_recognizer,
    unregister_catalog,
    unregister_classifier,
    unregister_extractor,
    unregister_recognizer,
)

__all__ = [
    # Data types
    "Intent",
    "IntentDefinition",
    "Slot",
    # Base classes
    "IntentRecognizer",
    "IntentClassifier",
    "IntentCatalog",
    "IntentSlotExtractor",
    # Recognizer registry
    "register_recognizer",
    "create_recognizer",
    "list_recognizers",
    "unregister_recognizer",
    # Classifier registry
    "register_classifier",
    "create_classifier",
    "list_classifiers",
    "unregister_classifier",
    # Catalog registry
    "register_catalog",
    "create_catalog",
    "list_catalogs",
    "unregister_catalog",
    # Extractor registry
    "register_extractor",
    "create_extractor",
    "list_extractors",
    "unregister_extractor",
    # Exception
    "IntentRegistryError",
]
