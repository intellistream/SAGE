"""Factory and registry for SIAS components.

This module provides dynamic registration and creation of SIAS implementations.
"""

from __future__ import annotations

from typing import Any, Callable

from sage.libs.sias.interface.base import ContinualLearner, CoresetSelector

# Registry for SIAS implementations
_LEARNER_REGISTRY: dict[str, Callable[..., ContinualLearner]] = {}
_SELECTOR_REGISTRY: dict[str, Callable[..., CoresetSelector]] = {}


class SiasRegistryError(Exception):
    """Error raised when registry operations fail."""

    pass


def register_learner(name: str, factory: Callable[..., ContinualLearner]) -> None:
    """Register a continual learner implementation.

    Args:
        name: Learner name
        factory: Factory function that creates learner instances
    """
    _LEARNER_REGISTRY[name] = factory


def register_selector(name: str, factory: Callable[..., CoresetSelector]) -> None:
    """Register a coreset selector implementation.

    Args:
        name: Selector name
        factory: Factory function that creates selector instances
    """
    _SELECTOR_REGISTRY[name] = factory


def create_learner(name: str, **kwargs: Any) -> ContinualLearner:
    """Create a continual learner instance by name.

    Args:
        name: Registered learner name
        **kwargs: Learner-specific configuration

    Returns:
        ContinualLearner instance

    Raises:
        SiasRegistryError: If learner name not registered
    """
    if name not in _LEARNER_REGISTRY:
        available = list(_LEARNER_REGISTRY.keys())
        raise SiasRegistryError(
            f"Learner '{name}' not registered. Available: {available}. "
            f"Install 'isage-sias' package for implementations."
        )
    return _LEARNER_REGISTRY[name](**kwargs)


def create_selector(name: str, **kwargs: Any) -> CoresetSelector:
    """Create a coreset selector instance by name.

    Args:
        name: Registered selector name
        **kwargs: Selector-specific configuration

    Returns:
        CoresetSelector instance

    Raises:
        SiasRegistryError: If selector name not registered
    """
    if name not in _SELECTOR_REGISTRY:
        available = list(_SELECTOR_REGISTRY.keys())
        raise SiasRegistryError(
            f"Selector '{name}' not registered. Available: {available}. "
            f"Install 'isage-sias' package for implementations."
        )
    return _SELECTOR_REGISTRY[name](**kwargs)


def list_learners() -> list[str]:
    """List all registered learner names."""
    return list(_LEARNER_REGISTRY.keys())


def list_selectors() -> list[str]:
    """List all registered selector names."""
    return list(_SELECTOR_REGISTRY.keys())


__all__ = [
    "SiasRegistryError",
    "register_learner",
    "register_selector",
    "create_learner",
    "create_selector",
    "list_learners",
    "list_selectors",
]
