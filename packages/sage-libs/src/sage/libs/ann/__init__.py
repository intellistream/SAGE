"""Unified ANNS (Approximate Nearest Neighbor Search) interfaces.

Status: implementations have been externalized to the `isage-anns` package. This module now
exposes only the registry/interfaces. Consumers should install the external package (e.g.
`pip install -e packages/sage-libs[anns]` or `pip install isage-anns`) to obtain concrete
algorithms. Benchmarks remain in `sage-benchmark/benchmark_anns` (L5).
"""

from __future__ import annotations

from sage.libs.ann.interface import (
    AnnIndex,
    AnnIndexMeta,
    AnnRegistryError,
    as_mapping,
    create,
    register,
    registered,
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
