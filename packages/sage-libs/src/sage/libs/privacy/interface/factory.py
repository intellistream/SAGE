"""Factory and registry for privacy implementations.

This module provides a registry pattern for privacy components.
External packages (like isage-privacy) can register their implementations here.

Example:
    # Register implementations
    from sage.libs.privacy.interface import (
        register_unlearner,
        register_mechanism,
        register_optimizer,
        register_fed_client,
    )
    register_unlearner("sisa", SISAUnlearner)
    register_mechanism("laplace", LaplaceMechanism)
    register_optimizer("dp_sgd", DPSGDOptimizer)
    register_fed_client("fedavg", FedAvgClient)

    # Create instances
    from sage.libs.privacy.interface import (
        create_unlearner,
        create_mechanism,
        create_optimizer,
        create_fed_client,
    )
    unlearner = create_unlearner("sisa")
    mechanism = create_mechanism("laplace", epsilon=1.0)
    optimizer = create_optimizer("dp_sgd")
    client = create_fed_client("fedavg", client_id="client_1")
"""

from typing import Any

from .base import (
    BaseDPOptimizer,
    BaseFederatedClient,
    BaseFederatedServer,
    BasePrivacyMechanism,
    BaseUnlearner,
)

_UNLEARNER_REGISTRY: dict[str, type[BaseUnlearner]] = {}
_MECHANISM_REGISTRY: dict[str, type[BasePrivacyMechanism]] = {}
_OPTIMIZER_REGISTRY: dict[str, type[BaseDPOptimizer]] = {}
_FED_CLIENT_REGISTRY: dict[str, type[BaseFederatedClient]] = {}
_FED_SERVER_REGISTRY: dict[str, type[BaseFederatedServer]] = {}


class PrivacyRegistryError(Exception):
    """Error raised when registry operations fail."""

    pass


# ========================================
# Unlearner Registry
# ========================================


def register_unlearner(name: str, cls: type[BaseUnlearner]) -> None:
    """Register an unlearning implementation.

    Args:
        name: Unique identifier (e.g., "sisa", "gradient_ascent", "fisher")
        cls: Unlearner class (should inherit from BaseUnlearner)

    Raises:
        PrivacyRegistryError: If name already registered
    """
    if name in _UNLEARNER_REGISTRY:
        raise PrivacyRegistryError(f"Unlearner '{name}' already registered")

    if not issubclass(cls, BaseUnlearner):
        raise TypeError(f"Class must inherit from BaseUnlearner, got {cls}")

    _UNLEARNER_REGISTRY[name] = cls


def create_unlearner(name: str, **kwargs: Any) -> BaseUnlearner:
    """Create an unlearner instance by name.

    Args:
        name: Name of the registered unlearner
        **kwargs: Arguments to pass to the unlearner constructor

    Returns:
        Instance of the unlearner

    Raises:
        PrivacyRegistryError: If unlearner not found
    """
    if name not in _UNLEARNER_REGISTRY:
        available = ", ".join(_UNLEARNER_REGISTRY.keys()) if _UNLEARNER_REGISTRY else "none"
        raise PrivacyRegistryError(
            f"Unlearner '{name}' not found. Available: {available}. Did you install 'isage-privacy'?"
        )

    cls = _UNLEARNER_REGISTRY[name]
    return cls(**kwargs)


def registered_unlearners() -> list[str]:
    """Get list of registered unlearner names."""
    return list(_UNLEARNER_REGISTRY.keys())


def unregister_unlearner(name: str) -> None:
    """Unregister an unlearner (for testing)."""
    _UNLEARNER_REGISTRY.pop(name, None)


# ========================================
# Privacy Mechanism Registry
# ========================================


def register_mechanism(name: str, cls: type[BasePrivacyMechanism]) -> None:
    """Register a privacy mechanism implementation.

    Args:
        name: Unique identifier (e.g., "laplace", "gaussian", "exponential")
        cls: Mechanism class (should inherit from BasePrivacyMechanism)

    Raises:
        PrivacyRegistryError: If name already registered
    """
    if name in _MECHANISM_REGISTRY:
        raise PrivacyRegistryError(f"Mechanism '{name}' already registered")

    if not issubclass(cls, BasePrivacyMechanism):
        raise TypeError(f"Class must inherit from BasePrivacyMechanism, got {cls}")

    _MECHANISM_REGISTRY[name] = cls


def create_mechanism(name: str, **kwargs: Any) -> BasePrivacyMechanism:
    """Create a privacy mechanism instance by name.

    Args:
        name: Name of the registered mechanism
        **kwargs: Arguments to pass to the mechanism constructor

    Returns:
        Instance of the mechanism

    Raises:
        PrivacyRegistryError: If mechanism not found
    """
    if name not in _MECHANISM_REGISTRY:
        available = ", ".join(_MECHANISM_REGISTRY.keys()) if _MECHANISM_REGISTRY else "none"
        raise PrivacyRegistryError(
            f"Mechanism '{name}' not found. Available: {available}. Did you install 'isage-privacy'?"
        )

    cls = _MECHANISM_REGISTRY[name]
    return cls(**kwargs)


def registered_mechanisms() -> list[str]:
    """Get list of registered mechanism names."""
    return list(_MECHANISM_REGISTRY.keys())


def unregister_mechanism(name: str) -> None:
    """Unregister a mechanism (for testing)."""
    _MECHANISM_REGISTRY.pop(name, None)


# ========================================
# DP Optimizer Registry
# ========================================


def register_optimizer(name: str, cls: type[BaseDPOptimizer]) -> None:
    """Register a DP optimizer implementation.

    Args:
        name: Unique identifier (e.g., "dp_sgd", "dp_adam", "pate")
        cls: Optimizer class (should inherit from BaseDPOptimizer)

    Raises:
        PrivacyRegistryError: If name already registered
    """
    if name in _OPTIMIZER_REGISTRY:
        raise PrivacyRegistryError(f"Optimizer '{name}' already registered")

    if not issubclass(cls, BaseDPOptimizer):
        raise TypeError(f"Class must inherit from BaseDPOptimizer, got {cls}")

    _OPTIMIZER_REGISTRY[name] = cls


def create_optimizer(name: str, **kwargs: Any) -> BaseDPOptimizer:
    """Create a DP optimizer instance by name.

    Args:
        name: Name of the registered optimizer
        **kwargs: Arguments to pass to the optimizer constructor

    Returns:
        Instance of the optimizer

    Raises:
        PrivacyRegistryError: If optimizer not found
    """
    if name not in _OPTIMIZER_REGISTRY:
        available = ", ".join(_OPTIMIZER_REGISTRY.keys()) if _OPTIMIZER_REGISTRY else "none"
        raise PrivacyRegistryError(
            f"Optimizer '{name}' not found. Available: {available}. Did you install 'isage-privacy'?"
        )

    cls = _OPTIMIZER_REGISTRY[name]
    return cls(**kwargs)


def registered_optimizers() -> list[str]:
    """Get list of registered optimizer names."""
    return list(_OPTIMIZER_REGISTRY.keys())


def unregister_optimizer(name: str) -> None:
    """Unregister an optimizer (for testing)."""
    _OPTIMIZER_REGISTRY.pop(name, None)


# ========================================
# Federated Client Registry
# ========================================


def register_fed_client(name: str, cls: type[BaseFederatedClient]) -> None:
    """Register a federated learning client implementation.

    Args:
        name: Unique identifier (e.g., "fedavg", "fedprox", "dp_fed")
        cls: Client class (should inherit from BaseFederatedClient)

    Raises:
        PrivacyRegistryError: If name already registered
    """
    if name in _FED_CLIENT_REGISTRY:
        raise PrivacyRegistryError(f"Federated client '{name}' already registered")

    if not issubclass(cls, BaseFederatedClient):
        raise TypeError(f"Class must inherit from BaseFederatedClient, got {cls}")

    _FED_CLIENT_REGISTRY[name] = cls


def create_fed_client(name: str, **kwargs: Any) -> BaseFederatedClient:
    """Create a federated client instance by name.

    Args:
        name: Name of the registered client
        **kwargs: Arguments to pass to the client constructor

    Returns:
        Instance of the client

    Raises:
        PrivacyRegistryError: If client not found
    """
    if name not in _FED_CLIENT_REGISTRY:
        available = ", ".join(_FED_CLIENT_REGISTRY.keys()) if _FED_CLIENT_REGISTRY else "none"
        raise PrivacyRegistryError(
            f"Federated client '{name}' not found. Available: {available}. Did you install 'isage-privacy'?"
        )

    cls = _FED_CLIENT_REGISTRY[name]
    return cls(**kwargs)


def registered_fed_clients() -> list[str]:
    """Get list of registered federated client names."""
    return list(_FED_CLIENT_REGISTRY.keys())


def unregister_fed_client(name: str) -> None:
    """Unregister a federated client (for testing)."""
    _FED_CLIENT_REGISTRY.pop(name, None)


# ========================================
# Federated Server Registry
# ========================================


def register_fed_server(name: str, cls: type[BaseFederatedServer]) -> None:
    """Register a federated learning server implementation.

    Args:
        name: Unique identifier (e.g., "fedavg", "secagg", "dp_fed")
        cls: Server class (should inherit from BaseFederatedServer)

    Raises:
        PrivacyRegistryError: If name already registered
    """
    if name in _FED_SERVER_REGISTRY:
        raise PrivacyRegistryError(f"Federated server '{name}' already registered")

    if not issubclass(cls, BaseFederatedServer):
        raise TypeError(f"Class must inherit from BaseFederatedServer, got {cls}")

    _FED_SERVER_REGISTRY[name] = cls


def create_fed_server(name: str, **kwargs: Any) -> BaseFederatedServer:
    """Create a federated server instance by name.

    Args:
        name: Name of the registered server
        **kwargs: Arguments to pass to the server constructor

    Returns:
        Instance of the server

    Raises:
        PrivacyRegistryError: If server not found
    """
    if name not in _FED_SERVER_REGISTRY:
        available = ", ".join(_FED_SERVER_REGISTRY.keys()) if _FED_SERVER_REGISTRY else "none"
        raise PrivacyRegistryError(
            f"Federated server '{name}' not found. Available: {available}. Did you install 'isage-privacy'?"
        )

    cls = _FED_SERVER_REGISTRY[name]
    return cls(**kwargs)


def registered_fed_servers() -> list[str]:
    """Get list of registered federated server names."""
    return list(_FED_SERVER_REGISTRY.keys())


def unregister_fed_server(name: str) -> None:
    """Unregister a federated server (for testing)."""
    _FED_SERVER_REGISTRY.pop(name, None)


__all__ = [
    "PrivacyRegistryError",
    # Unlearner
    "register_unlearner",
    "create_unlearner",
    "registered_unlearners",
    "unregister_unlearner",
    # Mechanism
    "register_mechanism",
    "create_mechanism",
    "registered_mechanisms",
    "unregister_mechanism",
    # Optimizer
    "register_optimizer",
    "create_optimizer",
    "registered_optimizers",
    "unregister_optimizer",
    # Federated Client
    "register_fed_client",
    "create_fed_client",
    "registered_fed_clients",
    "unregister_fed_client",
    # Federated Server
    "register_fed_server",
    "create_fed_server",
    "registered_fed_servers",
    "unregister_fed_server",
]
