"""
SAGE Refiner Python Adapter Layer
==================================

This module provides the SAGE-specific adapter layer for sageRefiner.
It wraps the standalone sageRefiner library with SAGE framework integration.

For standalone usage of sageRefiner, import from:
    sage.middleware.components.sage_refiner.sageRefiner
"""

from sage.libs.foundation.context.compression.refiner import (
    BaseRefiner,
    RefineResult,
    RefinerMetrics,
)

# Import from sageRefiner submodule
from sage.middleware.components.sage_refiner.sageRefiner.config import (
    RefinerAlgorithm,
    RefinerConfig,
)

# SAGE-specific adapter
from sage.middleware.components.sage_refiner.python.service import RefinerService

__all__ = [
    "BaseRefiner",
    "RefineResult",
    "RefinerMetrics",
    "RefinerConfig",
    "RefinerAlgorithm",
    "RefinerService",
]
