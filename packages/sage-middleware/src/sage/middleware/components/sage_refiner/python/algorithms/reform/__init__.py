"""
REFORM Algorithm Implementation
================================

REFORM (Compress, Gather, and Recompute) algorithm for RAG context compression.

References:
    REFORM: Compress, Gather, and Recompute (Appendix B.5)
"""

from .compressor import REFORMCompressor
from .model_utils import AttentionHookExtractor
from .operator import REFORMRefinerOperator

__all__ = [
    "REFORMCompressor",
    "REFORMRefinerOperator",
    "AttentionHookExtractor",
]
