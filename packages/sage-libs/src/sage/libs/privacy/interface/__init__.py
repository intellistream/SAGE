"""Privacy interface layer for SAGE.

This module provides abstract interfaces for privacy-preserving components.
Concrete implementations are provided by external packages (e.g., isage-privacy).

Architecture:
    - base.py: Abstract base classes (BaseUnlearner, BasePrivacyMechanism, etc.)
    - factory.py: Registry and factory functions
    - External packages register their implementations at import time

Usage:
    # Option 1: Direct instantiation (if you know the implementation)
    from isage_privacy import SISAUnlearner, LaplaceMechanism
    unlearner = SISAUnlearner(num_shards=5)
    mechanism = LaplaceMechanism(epsilon=1.0)

    # Option 2: Factory pattern (more flexible)
    from sage.libs.privacy.interface import create_unlearner, create_mechanism
    unlearner = create_unlearner("sisa", num_shards=5)
    mechanism = create_mechanism("laplace", epsilon=1.0)

    # Unlearn data
    result = unlearner.unlearn(model, forget_data)
"""

# Base classes and data types
from .base import (
    BaseDPOptimizer,
    BaseFederatedClient,
    BaseFederatedServer,
    BasePrivacyMechanism,
    BaseUnlearner,
    PrivacyBudget,
    PrivacyLevel,
    UnlearningMethod,
    UnlearningResult,
)

# Factory functions
from .factory import (
    PrivacyRegistryError,
    # Federated Client
    create_fed_client,
    # Federated Server
    create_fed_server,
    # Mechanism
    create_mechanism,
    # Optimizer
    create_optimizer,
    # Unlearner
    create_unlearner,
    register_fed_client,
    register_fed_server,
    register_mechanism,
    register_optimizer,
    register_unlearner,
    registered_fed_clients,
    registered_fed_servers,
    registered_mechanisms,
    registered_optimizers,
    registered_unlearners,
    unregister_fed_client,
    unregister_fed_server,
    unregister_mechanism,
    unregister_optimizer,
    unregister_unlearner,
)

__all__ = [
    # Enums
    "UnlearningMethod",
    "PrivacyLevel",
    # Data types
    "PrivacyBudget",
    "UnlearningResult",
    # Base classes
    "BasePrivacyMechanism",
    "BaseUnlearner",
    "BaseDPOptimizer",
    "BaseFederatedClient",
    "BaseFederatedServer",
    # Unlearner registry
    "register_unlearner",
    "create_unlearner",
    "registered_unlearners",
    "unregister_unlearner",
    # Mechanism registry
    "register_mechanism",
    "create_mechanism",
    "registered_mechanisms",
    "unregister_mechanism",
    # Optimizer registry
    "register_optimizer",
    "create_optimizer",
    "registered_optimizers",
    "unregister_optimizer",
    # Federated Client registry
    "register_fed_client",
    "create_fed_client",
    "registered_fed_clients",
    "unregister_fed_client",
    # Federated Server registry
    "register_fed_server",
    "create_fed_server",
    "registered_fed_servers",
    "unregister_fed_server",
    # Exception
    "PrivacyRegistryError",
]
