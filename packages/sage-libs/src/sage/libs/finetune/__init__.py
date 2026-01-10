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
    DatasetLoader,
    FineTuner,
    FineTuneRegistryError,
    LoRAConfig,
    TrainingConfig,
    create_loader,
    create_trainer,
    register_loader,
    register_trainer,
    registered_loaders,
    registered_trainers,
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
    "FineTuner",
    "DatasetLoader",
    "TrainingConfig",
    "LoRAConfig",
    # Registry
    "FineTuneRegistryError",
    "register_trainer",
    "register_loader",
    # Factory
    "create_trainer",
    "create_loader",
    # Discovery
    "registered_trainers",
    "registered_loaders",
]
