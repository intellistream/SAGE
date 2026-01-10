"""Unified ANN (Approximate Nearest Neighbor) interfaces.

Status: implementations have been externalized to the `isage-anns` package. This module now
exposes only the registry/interfaces. Consumers should install the external package (e.g.
`pip install -e packages/sage-libs[anns]` or `pip install isage-anns`) to obtain concrete
algorithms. Benchmarks remain in `sage-benchmark/benchmark_anns` (L5).

Architecture:
- This module provides the unified interface and factory for ANN algorithms
- Concrete implementations are in the external isage-anns package
- Used by: SageVDB (L4), benchmark_anns (L5), RAG pipelines
"""

from __future__ import annotations

import warnings

from sage.libs.ann.interface import (
    AnnIndex,
    AnnIndexMeta,
    AnnRegistryError,
    as_mapping,
    create,
    register,
    registered,
)

warnings.warn(
    "ANN implementations have moved to the external package 'isage-anns'. "
    "Install the optional extra [anns] or add 'isage-anns' to your environment.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "AnnIndex",
    "AnnIndexMeta",
    "AnnRegistryError",
    "create",
    "register",
    "registered",
    "as_mapping",
]
