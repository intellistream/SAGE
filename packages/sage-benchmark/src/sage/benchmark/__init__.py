"""
SAGE Benchmark Package
======================

This package contains benchmarking tools and examples for the SAGE framework,
including RAG (Retrieval-Augmented Generation) examples and benchmark experiments.

Components:
-----------
- benchmark_memory: Memory performance benchmarking
- benchmark_rag: RAG performance benchmarking and evaluation tools
- benchmark_agent: (Future) Agent performance benchmarking
- benchmark_anns: (Future) Approximate Nearest Neighbor Search benchmarking
"""

from . import benchmark_memory, benchmark_rag
from ._version import __version__

__all__ = [
    "__version__",
    "benchmark_memory",
    "benchmark_rag",
]
