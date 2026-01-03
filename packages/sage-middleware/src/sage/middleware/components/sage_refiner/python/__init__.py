"""
SAGE Refiner Python Adapter Layer
==================================

This module provides the SAGE-specific adapter layer for sage_refiner.
It wraps the standalone sage_refiner library with SAGE framework integration.

For standalone usage of sage_refiner, import from:
    sage_refiner (PyPI package)
"""

# Import from sage_refiner submodule
from sage_refiner import (
    RefinerAlgorithm,
    RefinerConfig,
)

from sage.libs.foundation.context.compression.refiner import (
    BaseRefiner,
    RefineResult,
    RefinerMetrics,
)

# Global Context Service
from sage.middleware.components.sage_refiner.python.context_service import ContextService

# SAGE-specific adapter
from sage.middleware.components.sage_refiner.python.service import RefinerService

__all__ = [
    "BaseRefiner",
    "RefineResult",
    "RefinerMetrics",
    "RefinerConfig",
    "RefinerAlgorithm",
    "RefinerService",
    "ContextService",
]
