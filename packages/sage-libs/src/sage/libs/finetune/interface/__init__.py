"""Fine-tuning interface layer for SAGE.

This module provides abstract interfaces for LLM fine-tuning components.
Concrete implementations are provided by external packages (e.g., isage-finetune).

Architecture:
    - base.py: Abstract base classes (FineTuner, DatasetLoader, TrainingCallback, TrainingStrategy)
    - factory.py: Registry and factory functions
    - External packages register their implementations at import time

Usage:
    # Option 1: Direct instantiation (if you know the implementation)
    from isage_finetune import LoRATrainer
    trainer = LoRATrainer(model_name="gpt2")

    # Option 2: Factory pattern (more flexible)
    from sage.libs.finetune.interface import create_trainer, create_strategy
    strategy = create_strategy("lora")
    trainer = create_trainer("lora", model_name="gpt2")

    # Train
    metrics = trainer.train(train_dataset, eval_dataset, config)
"""

# Base classes
from .base import (
    DatasetLoader,
    FineTuner,
    LoRAConfig,
    TrainingCallback,
    TrainingConfig,
    TrainingStrategy,
)

# Factory functions
from .factory import (
    FineTuneRegistryError,
    create_callback,
    create_loader,
    create_strategy,
    create_trainer,
    register_callback,
    register_loader,
    register_strategy,
    register_trainer,
    registered_callbacks,
    registered_loaders,
    registered_strategies,
    registered_trainers,
    unregister_callback,
    unregister_loader,
    unregister_strategy,
    unregister_trainer,
)

__all__ = [
    # Base classes
    "FineTuner",
    "DatasetLoader",
    "TrainingConfig",
    "LoRAConfig",
    "TrainingCallback",
    "TrainingStrategy",
    # Trainer factory
    "register_trainer",
    "create_trainer",
    "registered_trainers",
    "unregister_trainer",
    # Loader factory
    "register_loader",
    "create_loader",
    "registered_loaders",
    "unregister_loader",
    # Callback factory
    "register_callback",
    "create_callback",
    "registered_callbacks",
    "unregister_callback",
    # Strategy factory
    "register_strategy",
    "create_strategy",
    "registered_strategies",
    "unregister_strategy",
    # Exception
    "FineTuneRegistryError",
]
