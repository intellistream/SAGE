"""Unified SIAS (Stream-based Intent-Aware Selection) interfaces.

Status: implementations have been externalized to the `isage-sias` package. This module now
exposes only the registry/interfaces. Install the external package to obtain concrete implementations:

    pip install isage-sias
    # or
    pip install -e packages/sage-libs[sias]

The external package will automatically register its implementations with the factory.
"""

from __future__ import annotations

import warnings

from sage.libs.sias.interface import (
    ContinualLearner,
    CoresetSelector,
    SiasRegistryError,
    create_learner,
    create_selector,
    list_learners,
    list_selectors,
    register_learner,
    register_selector,
)

# Try to auto-import external package if available
try:
    import isage_sias  # noqa: F401

    _EXTERNAL_AVAILABLE = True
except ImportError:
    _EXTERNAL_AVAILABLE = False
    warnings.warn(
        "SIAS implementations not available. Install 'isage-sias' package:\n"
        "  pip install isage-sias\n"
        "or: pip install isage-libs[sias]",
        ImportWarning,
        stacklevel=2,
    )

__all__ = [
    # Base classes
    "ContinualLearner",
    "CoresetSelector",
    # Registry
    "SiasRegistryError",
    "register_learner",
    "register_selector",
    # Factory
    "create_learner",
    "create_selector",
    # Discovery
    "list_learners",
    "list_selectors",
]
