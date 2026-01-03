"""
SAGE Refiner - Context compression and refinement component
===========================================================

SageRefiner has been migrated to an independent PyPI package.

Installation:
    pip install isage-refiner

This module re-exports SageRefiner classes from the isage-refiner package
for backward-compatible import paths within SAGE, and provides
SAGE-specific services and wrappers.

For detailed migration information, see:
    docs-public/docs_src/dev-notes/cross-layer/sagerefiner-independence-migration.md
"""

# Import from PyPI package (isage-refiner)
try:
    from sage_refiner import (
        LongRefinerCompressor,
        ProvenceCompressor,
        RefinerAlgorithm,
        RefinerConfig,
        REFORMCompressor,
        __author__,
        __email__,
        __version__,
    )
except ImportError as e:
    raise ImportError(
        "SAGE Refiner requires the isage-refiner package. Please install: pip install isage-refiner"
    ) from e

# SAGE-specific services (kept in SAGE repo)
from .python.service import RefinerService

# SAGE framework dependencies (optional, for integration)
try:
    from sage.libs.foundation.context.compression.algorithms import (
        LongRefinerAlgorithm,
        SimpleRefiner,
    )
    from sage.libs.foundation.context.compression.refiner import (
        BaseRefiner,
        RefineResult,
        RefinerMetrics,
    )

    _SAGE_LIBS_AVAILABLE = True
except ImportError:
    _SAGE_LIBS_AVAILABLE = False
    LongRefinerAlgorithm = None
    SimpleRefiner = None
    BaseRefiner = None
    RefineResult = None
    RefinerMetrics = None

__all__ = [
    # Core API from isage-refiner
    "LongRefinerCompressor",
    "REFORMCompressor",
    "ProvenceCompressor",
    "RefinerConfig",
    "RefinerAlgorithm",
    "__version__",
    "__author__",
    "__email__",
    # SAGE-specific services
    "RefinerService",
    # SAGE framework integration (optional)
    "LongRefinerAlgorithm",
    "SimpleRefiner",
    "BaseRefiner",
    "RefineResult",
    "RefinerMetrics",
]
