"""Factory and registry for finetune implementations.

This module provides a registry pattern for fine-tuning implementations.
External packages (like isage-finetune) can register their implementations here.

Example:
    # Register an implementation
    from sage.libs.finetune.interface import register_trainer, register_loader
    register_trainer("lora", LoRATrainer)
    register_loader("hf_dataset", HuggingFaceLoader)

    # Create instances
    from sage.libs.finetune.interface import create_trainer, create_loader
    trainer = create_trainer("lora", model_name="gpt2")
    loader = create_loader("hf_dataset")
"""

from typing import Any

from .base import DatasetLoader, FineTuner, TrainingCallback, TrainingStrategy

_TRAINER_REGISTRY: dict[str, type[FineTuner]] = {}
_LOADER_REGISTRY: dict[str, type[DatasetLoader]] = {}
_CALLBACK_REGISTRY: dict[str, type[TrainingCallback]] = {}
_STRATEGY_REGISTRY: dict[str, type[TrainingStrategy]] = {}


class FineTuneRegistryError(Exception):
    """Error raised when registry operations fail."""

    pass


def register_trainer(name: str, cls: type[FineTuner]) -> None:
    """Register a fine-tuning trainer implementation.

    Args:
        name: Unique identifier for this trainer (e.g., "lora", "qlora", "full")
        cls: Trainer class (should inherit from FineTuner)

    Raises:
        FineTuneRegistryError: If name already registered
    """
    if name in _TRAINER_REGISTRY:
        raise FineTuneRegistryError(f"Trainer '{name}' already registered")

    if not issubclass(cls, FineTuner):
        raise TypeError(f"Class must inherit from FineTuner, got {cls}")

    _TRAINER_REGISTRY[name] = cls


def register_loader(name: str, cls: type[DatasetLoader]) -> None:
    """Register a dataset loader implementation.

    Args:
        name: Unique identifier for this loader (e.g., "hf_dataset", "jsonl")
        cls: Loader class (should inherit from DatasetLoader)

    Raises:
        FineTuneRegistryError: If name already registered
    """
    if name in _LOADER_REGISTRY:
        raise FineTuneRegistryError(f"Loader '{name}' already registered")

    if not issubclass(cls, DatasetLoader):
        raise TypeError(f"Class must inherit from DatasetLoader, got {cls}")

    _LOADER_REGISTRY[name] = cls


def create_trainer(name: str, **kwargs: Any) -> FineTuner:
    """Create a trainer instance by name.

    Args:
        name: Name of the registered trainer
        **kwargs: Arguments to pass to the trainer constructor

    Returns:
        Instance of the trainer

    Raises:
        FineTuneRegistryError: If trainer not found

    Example:
        >>> trainer = create_trainer("lora", model_name="gpt2", lora_r=8)
        >>> trainer.train(train_dataset)
    """
    if name not in _TRAINER_REGISTRY:
        available = ", ".join(_TRAINER_REGISTRY.keys()) if _TRAINER_REGISTRY else "none"
        raise FineTuneRegistryError(
            f"Trainer '{name}' not found. Available: {available}. Did you install 'isage-finetune'?"
        )

    cls = _TRAINER_REGISTRY[name]
    return cls(**kwargs)


def create_loader(name: str, **kwargs: Any) -> DatasetLoader:
    """Create a dataset loader instance by name.

    Args:
        name: Name of the registered loader
        **kwargs: Arguments to pass to the loader constructor

    Returns:
        Instance of the loader

    Raises:
        FineTuneRegistryError: If loader not found

    Example:
        >>> loader = create_loader("hf_dataset", dataset_name="alpaca")
        >>> dataset = loader.load("train")
    """
    if name not in _LOADER_REGISTRY:
        available = ", ".join(_LOADER_REGISTRY.keys()) if _LOADER_REGISTRY else "none"
        raise FineTuneRegistryError(
            f"Loader '{name}' not found. Available: {available}. Did you install 'isage-finetune'?"
        )

    cls = _LOADER_REGISTRY[name]
    return cls(**kwargs)


def registered_trainers() -> list[str]:
    """Get list of registered trainer names.

    Returns:
        List of registered trainer names
    """
    return list(_TRAINER_REGISTRY.keys())


def registered_loaders() -> list[str]:
    """Get list of registered loader names.

    Returns:
        List of registered loader names
    """
    return list(_LOADER_REGISTRY.keys())


def unregister_trainer(name: str) -> None:
    """Unregister a trainer (for testing).

    Args:
        name: Name of the trainer to unregister
    """
    _TRAINER_REGISTRY.pop(name, None)


def unregister_loader(name: str) -> None:
    """Unregister a loader (for testing).

    Args:
        name: Name of the loader to unregister
    """
    _LOADER_REGISTRY.pop(name, None)


# ========================================
# Callback Registry
# ========================================


def register_callback(name: str, cls: type[TrainingCallback]) -> None:
    """Register a training callback implementation.

    Args:
        name: Unique identifier for this callback (e.g., "wandb", "tensorboard", "early_stop")
        cls: Callback class (should inherit from TrainingCallback)

    Raises:
        FineTuneRegistryError: If name already registered
    """
    if name in _CALLBACK_REGISTRY:
        raise FineTuneRegistryError(f"Callback '{name}' already registered")

    if not issubclass(cls, TrainingCallback):
        raise TypeError(f"Class must inherit from TrainingCallback, got {cls}")

    _CALLBACK_REGISTRY[name] = cls


def create_callback(name: str, **kwargs: Any) -> TrainingCallback:
    """Create a callback instance by name.

    Args:
        name: Name of the registered callback
        **kwargs: Arguments to pass to the callback constructor

    Returns:
        Instance of the callback

    Raises:
        FineTuneRegistryError: If callback not found
    """
    if name not in _CALLBACK_REGISTRY:
        available = ", ".join(_CALLBACK_REGISTRY.keys()) if _CALLBACK_REGISTRY else "none"
        raise FineTuneRegistryError(
            f"Callback '{name}' not found. Available: {available}. Did you install 'isage-finetune'?"
        )

    cls = _CALLBACK_REGISTRY[name]
    return cls(**kwargs)


def registered_callbacks() -> list[str]:
    """Get list of registered callback names."""
    return list(_CALLBACK_REGISTRY.keys())


def unregister_callback(name: str) -> None:
    """Unregister a callback (for testing)."""
    _CALLBACK_REGISTRY.pop(name, None)


# ========================================
# Strategy Registry
# ========================================


def register_strategy(name: str, cls: type[TrainingStrategy]) -> None:
    """Register a training strategy implementation.

    Args:
        name: Unique identifier for this strategy (e.g., "lora", "qlora", "full", "prefix")
        cls: Strategy class (should inherit from TrainingStrategy)

    Raises:
        FineTuneRegistryError: If name already registered
    """
    if name in _STRATEGY_REGISTRY:
        raise FineTuneRegistryError(f"Strategy '{name}' already registered")

    if not issubclass(cls, TrainingStrategy):
        raise TypeError(f"Class must inherit from TrainingStrategy, got {cls}")

    _STRATEGY_REGISTRY[name] = cls


def create_strategy(name: str, **kwargs: Any) -> TrainingStrategy:
    """Create a strategy instance by name.

    Args:
        name: Name of the registered strategy
        **kwargs: Arguments to pass to the strategy constructor

    Returns:
        Instance of the strategy

    Raises:
        FineTuneRegistryError: If strategy not found
    """
    if name not in _STRATEGY_REGISTRY:
        available = ", ".join(_STRATEGY_REGISTRY.keys()) if _STRATEGY_REGISTRY else "none"
        raise FineTuneRegistryError(
            f"Strategy '{name}' not found. Available: {available}. Did you install 'isage-finetune'?"
        )

    cls = _STRATEGY_REGISTRY[name]
    return cls(**kwargs)


def registered_strategies() -> list[str]:
    """Get list of registered strategy names."""
    return list(_STRATEGY_REGISTRY.keys())


def unregister_strategy(name: str) -> None:
    """Unregister a strategy (for testing)."""
    _STRATEGY_REGISTRY.pop(name, None)


__all__ = [
    "FineTuneRegistryError",
    # Trainer
    "register_trainer",
    "create_trainer",
    "registered_trainers",
    "unregister_trainer",
    # Loader
    "register_loader",
    "create_loader",
    "registered_loaders",
    "unregister_loader",
    # Callback
    "register_callback",
    "create_callback",
    "registered_callbacks",
    "unregister_callback",
    # Strategy
    "register_strategy",
    "create_strategy",
    "registered_strategies",
    "unregister_strategy",
]
