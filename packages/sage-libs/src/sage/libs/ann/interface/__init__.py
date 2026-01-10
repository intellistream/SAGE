"""Approximate Nearest Neighbor (ANN) interfaces for SAGE.

This module defines shared abstractions and registry helpers so algorithms can
live in ``sage-libs`` and be reused by benchmark_anns, sage-db, and sage-flow.
"""

from __future__ import annotations

from .base import AnnIndex, AnnIndexMeta
from .factory import AnnRegistryError, as_mapping, create, register, registered

__all__ = [
    "AnnIndex",
    "AnnIndexMeta",
    "AnnRegistryError",
    "register",
    "create",
    "registered",
    "as_mapping",
]
