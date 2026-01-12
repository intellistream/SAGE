"""Privacy layer - Privacy-preserving algorithms.

This module provides privacy-related algorithms:
- unlearning: Machine unlearning and privacy-preserving mechanisms
- interface: Abstract interfaces for privacy components

Concrete implementations are provided by external packages (e.g., isage-privacy).
"""

from . import interface, unlearning

# Re-export key interfaces for convenience
from .interface import (
    # Base classes
    BaseDPOptimizer,
    BaseFederatedClient,
    BaseFederatedServer,
    BasePrivacyMechanism,
    BaseUnlearner,
    # Data types
    PrivacyBudget,
    # Enums
    PrivacyLevel,
    UnlearningMethod,
    UnlearningResult,
    # Factories
    create_mechanism,
    create_unlearner,
    register_mechanism,
    register_unlearner,
    registered_mechanisms,
    registered_unlearners,
)

__all__ = [
    # Submodules
    "unlearning",
    "interface",
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
    # Factories
    "register_unlearner",
    "create_unlearner",
    "registered_unlearners",
    "register_mechanism",
    "create_mechanism",
    "registered_mechanisms",
]
