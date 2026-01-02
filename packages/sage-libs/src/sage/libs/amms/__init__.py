"""AMMS - Approximate Matrix Multiplication Algorithms.

This package provides a unified interface for various AMM algorithms,
similar to how ANNS provides interfaces for approximate nearest neighbor search.

Architecture:
    - interface/: Abstract base classes and factory
    - wrappers/: Python wrappers for algorithm implementations
    - implementations/: C++ source code for algorithms

Example:
    >>> from sage.libs.amms import create
    >>> amm = create("countsketch", sketch_size=1000)
    >>> result = amm.multiply(matrix_a, matrix_b)
"""

from sage.libs._version import __author__, __email__, __version__

# Import interface components
from sage.libs.amms.interface import (
    AmmIndex,
    AmmIndexMeta,
    StreamingAmmIndex,
    create,
    get_meta,
    register,
    registered,
    unregister,
)

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    # Base classes
    "AmmIndex",
    "AmmIndexMeta",
    "StreamingAmmIndex",
    # Factory functions
    "create",
    "registered",
    "get_meta",
    # Registry functions
    "register",
    "unregister",
]
