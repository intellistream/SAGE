"""Fine-tuning interface layer for SAGE.

This module provides abstract interfaces for LLM fine-tuning components.
Concrete implementations are provided by external packages (e.g., isage-finetune).

Architecture:
    - base.py: Abstract base classes (FineTuner, DatasetLoader)
    - factory.py: Registry and factory functions
    - External packages register their implementations at import time

Usage:
    # Option 1: Direct instantiation (if you know the implementation)
    from isage_finetune import LoRATrainer
    trainer = LoRATrainer(model_name="gpt2")

    # Option 2: Factory pattern (more flexible)
    from sage.libs.finetune.interface import create_trainer
    trainer = create_trainer("lora", model_name="gpt2")

    # Train
    metrics = trainer.train(train_dataset, eval_dataset, config)
"""

# Base classes
from .base import (
    DatasetLoader,
    FineTuner,
    LoRAConfig,
    TrainingConfig,
)

# Factory functions
from .factory import (
    FineTuneRegistryError,
    create_loader,
    create_trainer,
    register_loader,
    register_trainer,
    registered_loaders,
    registered_trainers,
    unregister_loader,
    unregister_trainer,
)

__all__ = [
    # Base classes
    "FineTuner",
    "DatasetLoader",
    "TrainingConfig",
    "LoRAConfig",
    # Factory functions
    "register_trainer",
    "register_loader",
    "create_trainer",
    "create_loader",
    "registered_trainers",
    "registered_loaders",
    "unregister_trainer",
    "unregister_loader",
    "FineTuneRegistryError",
]
