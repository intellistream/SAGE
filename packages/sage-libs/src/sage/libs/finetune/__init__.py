"""SAGE Fine-tuning Module - Training Interfaces.

This module provides the **interface layer** (abstract base classes and factory)
for fine-tuning implementations. Concrete trainers are in the external package
`isage-finetune`.

Architecture:
    sage.libs.finetune (this module) - Interface layer (ABCs, factory, configs)
    isage-finetune (external PyPI)   - Implementations (SFT, LoRA, DPO trainers)

Installation:
    pip install isage-finetune    # Install implementations
    # or
    pip install isage-libs[finetune]

Usage:
    from sage.libs.finetune.interface import (
        FineTuner, DatasetLoader, TrainingConfig, LoRAConfig,
        create_trainer, create_loader, registered_trainers,
    )

    # Create trainer (requires isage-finetune installed)
    trainer = create_trainer("sft", config=TrainingConfig(...))
    trainer.train(dataset)

External implementations auto-register when imported.
See: https://github.com/intellistream/sage-finetune
"""

from __future__ import annotations

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
except ImportError:
    pass  # Implementations not installed, factory will raise if user tries to create

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
