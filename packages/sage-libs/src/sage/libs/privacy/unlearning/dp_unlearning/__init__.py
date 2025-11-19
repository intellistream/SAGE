"""
Differential Privacy Unlearning Module
=======================================

Core components for privacy-preserving machine unlearning.

Architecture:
    BasePrivacyMechanism (abstract)
        ↓
    [Laplace, Gaussian, Exponential] (concrete implementations)
        ↓
    UnlearningEngine (orchestrator)
        ↓
    PrivacyAccountant (budget tracking)
"""

from .base_mechanism import BasePrivacyMechanism
from .neighbor_compensation import NeighborCompensation
from .privacy_accountant import PrivacyAccountant
from .unlearning_engine import UnlearningEngine
from .vector_perturbation import VectorPerturbation

__all__ = [
    "BasePrivacyMechanism",
    "PrivacyAccountant",
    "UnlearningEngine",
    "VectorPerturbation",
    "NeighborCompensation",
]
