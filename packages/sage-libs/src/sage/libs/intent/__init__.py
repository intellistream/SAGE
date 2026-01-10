"""Unified Intent Recognition interfaces.

Status: implementations have been externalized to the `isage-intent` package. This module now
exposes only the registry/interfaces. Install the external package to obtain concrete implementations:

    pip install isage-intent
    # or
    pip install -e packages/sage-libs[intent]

The external package will automatically register its implementations with the factory.
"""

from __future__ import annotations

import warnings

from sage.libs.intent.interface import (
    IntentCatalog,
    IntentClassifier,
    IntentRecognizer,
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

# Try to auto-import external package if available
try:
    import isage_intent  # noqa: F401

    _EXTERNAL_AVAILABLE = True
except ImportError:
    _EXTERNAL_AVAILABLE = False
    warnings.warn(
        "Intent implementations not available. Install 'isage-intent' package:\n"
        "  pip install isage-intent\n"
        "or: pip install isage-libs[intent]",
        ImportWarning,
        stacklevel=2,
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
