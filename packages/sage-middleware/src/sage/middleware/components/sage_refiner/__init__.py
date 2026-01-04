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

import warnings

# Import from PyPI package (isage-refiner)
_SAGE_REFINER_AVAILABLE = False
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

    _SAGE_REFINER_AVAILABLE = True
except ImportError as e:
    # Don't fail immediately - allow graceful degradation
    warnings.warn(
        f"SAGE Refiner not available: {e}\n"
        "Install with: pip install isage-refiner\n"
        "Context compression features will be unavailable.",
        UserWarning,
        stacklevel=2,
    )
    # Provide stub exports
    LongRefinerCompressor = None
    ProvenceCompressor = None
    RefinerAlgorithm = None
    RefinerConfig = None
    REFORMCompressor = None
    __version__ = "unavailable"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"

# SAGE-specific services (kept in SAGE repo)
# Only import if base package is available
if _SAGE_REFINER_AVAILABLE:
    from .python.service import RefinerService
else:
    RefinerService = None

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
    # Core API from isage-refiner (may be None if not installed)
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
    # Availability flags
    "_SAGE_REFINER_AVAILABLE",
    "_SAGE_LIBS_AVAILABLE",
]
