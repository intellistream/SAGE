"""Registration and creation for ANN implementations.

This registry will back benchmark_anns and other modules to resolve algorithms
without direct imports, keeping dependencies flowing downward.
"""

from __future__ import annotations

from typing import Callable, Iterable, Mapping

from .base import AnnIndex


class AnnRegistryError(RuntimeError):
    """Raised when registry operations fail."""


_registry: dict[str, Callable[..., AnnIndex]] = {}


def register(name: str, builder: Callable[..., AnnIndex]) -> None:
    """Register a new ANN implementation.

    Raises:
        ValueError: if name is empty.
        AnnRegistryError: if name already exists.
    """

    if not name:
        raise ValueError("ANN name must be non-empty")
    if name in _registry:
        raise AnnRegistryError(f"ANN algorithm '{name}' is already registered")
    _registry[name] = builder


def create(name: str, /, **kwargs) -> AnnIndex:
    """Create an ANN instance by name.

    Raises:
        AnnRegistryError: if name is missing or builder returns invalid type.
    """

    try:
        builder = _registry[name]
    except KeyError as exc:  # pragma: no cover - defensive path
        available = ", ".join(sorted(_registry)) or "<empty>"
        raise AnnRegistryError(
            f"ANN algorithm '{name}' is not registered; available: {available}"
        ) from exc

    instance = builder(**kwargs)
    if not isinstance(instance, AnnIndex):
        raise AnnRegistryError(
            f"Builder for '{name}' did not return AnnIndex (got {type(instance)!r})"
        )
    return instance


def registered() -> Iterable[str]:
    """Return registered ANN names (sorted)."""

    return tuple(sorted(_registry))


def as_mapping() -> Mapping[str, Callable[..., AnnIndex]]:
    """Return a read-only view of the registry."""

    return dict(_registry)
