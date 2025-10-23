"""
SAGE Benchmark Package
======================

Layer: L5 (Applications - Benchmarking)
Dependencies: sage.middleware (L4), sage.libs (L3), sage.kernel (L3), sage.platform (L2), sage.common (L1)

This package contains benchmarking tools and examples for the SAGE framework,
including RAG (Retrieval-Augmented Generation) examples and benchmark experiments.

Components:
-----------
- benchmark_memory: Memory performance benchmarking
- benchmark_rag: RAG performance benchmarking and evaluation tools
- benchmark_agent: (Future) Agent performance benchmarking
- benchmark_anns: (Future) Approximate Nearest Neighbor Search benchmarking

Architecture:
- L5 应用层，专注性能评估和基准测试
- 使用完整的 SAGE 技术栈进行性能测试
- 提供各种场景的基准测试工具
"""

from . import benchmark_memory, benchmark_rag
from ._version import __version__

__all__ = [
    "__version__",
    "benchmark_memory",
    "benchmark_rag",
]
