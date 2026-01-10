"""Unified Fine-tuning interfaces.

Status: implementations have been externalized to the `isage-finetune` package. This module now
exposes only the registry/interfaces. Install the external package to obtain concrete trainers:

    pip install isage-finetune
    # or
    pip install -e packages/sage-libs[finetune]

The external package will automatically register its implementations with the factory.
"""

from __future__ import annotations

import warnings

from sage.libs.finetune.interface import (
    DataFormatter,
    FinetuneConfig,
    FinetuneRegistryError,
    Trainer,
    create_config,
    create_formatter,
    create_trainer,
    list_configs,
    list_formatters,
    list_trainers,
    register_config,
    register_formatter,
    register_trainer,
)

# Try to auto-import external package if available
try:
    import isage_finetune  # noqa: F401

    _EXTERNAL_AVAILABLE = True
except ImportError:
    _EXTERNAL_AVAILABLE = False
    warnings.warn(
        "Fine-tuning implementations not available. Install 'isage-finetune' package:\n"
        "  pip install isage-finetune\n"
        "or: pip install isage-libs[finetune]",
        ImportWarning,
        stacklevel=2,
    )

__all__ = [
    # Base classes
    "Trainer",
    "FinetuneConfig",
    "DataFormatter",
    # Registry
    "FinetuneRegistryError",
    "register_trainer",
    "register_config",
    "register_formatter",
    # Factory
    "create_trainer",
    "create_config",
    "create_formatter",
    # Discovery
    "list_trainers",
    "list_configs",
    "list_formatters",
]
