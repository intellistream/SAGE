"""Registry for AMM algorithm implementations.

Provides a centralized registry for discovering and instantiating
AMM algorithms, similar to the ANNS registry pattern.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from sage.libs.amms.interface.base import AmmIndex, AmmIndexMeta

# Global registry mapping algorithm names to factory functions
_REGISTRY: dict[str, Callable[..., AmmIndex]] = {}

# Metadata cache
_META_CACHE: dict[str, AmmIndexMeta] = {}


def register(
    name: str,
    factory: Callable[..., AmmIndex],
    meta: Optional[AmmIndexMeta] = None,
) -> None:
    """Register an AMM algorithm implementation.

    Args:
        name: Algorithm name (e.g., "countsketch", "fastjlt")
        factory: Factory function that creates an AmmIndex instance
        meta: Optional metadata about the algorithm
    """
    if name in _REGISTRY:
        raise ValueError(f"AMM algorithm '{name}' is already registered")

    _REGISTRY[name] = factory
    if meta is not None:
        _META_CACHE[name] = meta


def unregister(name: str) -> None:
    """Unregister an AMM algorithm.

    Args:
        name: Algorithm name to unregister
    """
    _REGISTRY.pop(name, None)
    _META_CACHE.pop(name, None)


def registered() -> list[str]:
    """Return list of registered algorithm names.

    Returns:
        List of algorithm names
    """
    return sorted(_REGISTRY.keys())


def get_factory(name: str) -> Callable[..., AmmIndex]:
    """Get factory function for an algorithm.

    Args:
        name: Algorithm name

    Returns:
        Factory function

    Raises:
        KeyError: If algorithm is not registered
    """
    if name not in _REGISTRY:
        available = ", ".join(registered())
        raise KeyError(f"AMM algorithm '{name}' not found. Available: {available or 'none'}")
    return _REGISTRY[name]


def get_meta(name: str) -> Optional[AmmIndexMeta]:
    """Get metadata for an algorithm.

    Args:
        name: Algorithm name

    Returns:
        Algorithm metadata or None if not cached
    """
    return _META_CACHE.get(name)


def create_amm_index(name: str, **kwargs: Any) -> AmmIndex:
    """Create an AMM index instance.

    Args:
        name: Algorithm name
        **kwargs: Algorithm-specific configuration

    Returns:
        Configured AmmIndex instance

    Raises:
        KeyError: If algorithm is not registered
    """
    factory = get_factory(name)
    return factory(**kwargs)


# Alias for backward compatibility
create = create_amm_index
