"""Unified ANNS (Approximate Nearest Neighbor Search) module.

This module consolidates all ANNS core components into a single location:
- interface/: Abstract base classes and factory (AnnIndex, AnnIndexMeta, create(), register())
- wrappers/: Python implementations for various algorithms (FAISS, VSAG, DiskANN, CANDY, etc.)
- implementations/: C++ source code and bindings

Note: Benchmarks remain in sage-benchmark/benchmark_anns (L5 package).

Migration from old structure:
- sage.libs.ann -> sage.libs.anns.interface
- sage.libs.anns.<algo> -> sage.libs.anns.wrappers.<family>.<algo>
- benchmark_anns.algorithms_impl -> sage.libs.anns.implementations (C++ code moved to L3)
"""

from __future__ import annotations

__all__ = []

# Public API will be populated after migration is complete
