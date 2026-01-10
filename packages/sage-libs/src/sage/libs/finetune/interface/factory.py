"""Factory and registry for fine-tuning components.

This module provides dynamic registration and creation of trainer implementations.
"""

from __future__ import annotations

from typing import Any, Callable

from sage.libs.finetune.interface.base import DataFormatter, FinetuneConfig, Trainer

# Registry for trainer implementations
_TRAINER_REGISTRY: dict[str, Callable[..., Trainer]] = {}
_CONFIG_REGISTRY: dict[str, Callable[..., FinetuneConfig]] = {}
_FORMATTER_REGISTRY: dict[str, Callable[..., DataFormatter]] = {}


class FinetuneRegistryError(Exception):
    """Error raised when registry operations fail."""

    pass


def register_trainer(name: str, factory: Callable[..., Trainer]) -> None:
    """Register a trainer implementation.

    Args:
        name: Trainer name (e.g., "lora", "qlora", "dpo")
        factory: Factory function that creates trainer instances
    """
    _TRAINER_REGISTRY[name] = factory


def register_config(name: str, factory: Callable[..., FinetuneConfig]) -> None:
    """Register a config implementation."""
    _CONFIG_REGISTRY[name] = factory


def register_formatter(name: str, factory: Callable[..., DataFormatter]) -> None:
    """Register a data formatter implementation."""
    _FORMATTER_REGISTRY[name] = factory


def create_trainer(name: str, **kwargs: Any) -> Trainer:
    """Create a trainer instance by name.

    Args:
        name: Registered trainer name
        **kwargs: Trainer-specific configuration

    Returns:
        Trainer instance

    Raises:
        FinetuneRegistryError: If trainer name not registered

    Example:
        >>> trainer = create_trainer("lora", rank=8, alpha=16)
        >>> results = trainer.train(model, train_data)
    """
    if name not in _TRAINER_REGISTRY:
        available = list(_TRAINER_REGISTRY.keys())
        raise FinetuneRegistryError(
            f"Trainer '{name}' not registered. Available: {available}. "
            f"Install 'isage-finetune' package for implementations."
        )
    return _TRAINER_REGISTRY[name](**kwargs)


def create_config(name: str, **kwargs: Any) -> FinetuneConfig:
    """Create a config instance by name."""
    if name not in _CONFIG_REGISTRY:
        available = list(_CONFIG_REGISTRY.keys())
        raise FinetuneRegistryError(
            f"Config '{name}' not registered. Available: {available}. "
            f"Install 'isage-finetune' package for implementations."
        )
    return _CONFIG_REGISTRY[name](**kwargs)


def create_formatter(name: str, **kwargs: Any) -> DataFormatter:
    """Create a formatter instance by name."""
    if name not in _FORMATTER_REGISTRY:
        available = list(_FORMATTER_REGISTRY.keys())
        raise FinetuneRegistryError(
            f"Formatter '{name}' not registered. Available: {available}. "
            f"Install 'isage-finetune' package for implementations."
        )
    return _FORMATTER_REGISTRY[name](**kwargs)


def list_trainers() -> list[str]:
    """List all registered trainer names."""
    return list(_TRAINER_REGISTRY.keys())


def list_configs() -> list[str]:
    """List all registered config names."""
    return list(_CONFIG_REGISTRY.keys())


def list_formatters() -> list[str]:
    """List all registered formatter names."""
    return list(_FORMATTER_REGISTRY.keys())


__all__ = [
    "FinetuneRegistryError",
    "register_trainer",
    "register_config",
    "register_formatter",
    "create_trainer",
    "create_config",
    "create_formatter",
    "list_trainers",
    "list_configs",
    "list_formatters",
]
