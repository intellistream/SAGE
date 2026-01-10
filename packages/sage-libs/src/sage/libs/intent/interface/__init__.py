"""Intent interface exports."""

from sage.libs.intent.interface.base import IntentCatalog, IntentClassifier, IntentRecognizer
from sage.libs.intent.interface.factory import (
    IntentRegistryError,
    create_catalog,
    create_classifier,
    create_recognizer,
    list_catalogs,
    list_classifiers,
    list_recognizers,
    register_catalog,
    register_classifier,
    register_recognizer,
)

__all__ = [
    # Base classes
    "IntentRecognizer",
    "IntentClassifier",
    "IntentCatalog",
    # Registry
    "IntentRegistryError",
    "register_recognizer",
    "register_classifier",
    "register_catalog",
    # Factory
    "create_recognizer",
    "create_classifier",
    "create_catalog",
    # Discovery
    "list_recognizers",
    "list_classifiers",
    "list_catalogs",
]
