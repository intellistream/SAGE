"""
SAGE Unlearning Library
========================

A modular framework for machine unlearning in RAG systems with differential privacy guarantees.

Core Modules:
- dp_unlearning: Differential privacy mechanisms for selective unlearning
- algorithms: Various unlearning algorithms (Laplace, Gaussian, etc.)
- evaluation: Metrics and benchmarking tools
- benchmarks: Standard datasets and evaluation protocols

Research Extensions:
Students can extend this library by:
1. Implementing new privacy mechanisms
2. Designing novel perturbation strategies
3. Developing adaptive budget allocation algorithms
4. Creating domain-specific unlearning methods
"""

from .dp_unlearning.base_mechanism import BasePrivacyMechanism
from .dp_unlearning.privacy_accountant import PrivacyAccountant
from .dp_unlearning.unlearning_engine import UnlearningEngine

__version__ = "0.1.0"
__all__ = [
    "BasePrivacyMechanism",
    "PrivacyAccountant",
    "UnlearningEngine",
]
