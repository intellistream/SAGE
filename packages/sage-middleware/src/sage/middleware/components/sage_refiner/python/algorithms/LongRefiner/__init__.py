"""
LongRefiner Algorithm Implementation
====================================

LongRefiner: A three-stage context compression algorithm for long-context RAG.

Stages:
    1. Query Analysis: Determines if the query needs local or global information
    2. Document Structuring: Structures documents into hierarchical sections
    3. Global Selection: Selects relevant sections based on query analysis

References:
    LongRefiner: Compress, Structure, and Select for Long-Context RAG
"""

from .compressor import LongRefinerCompressor
from .operator import LongRefinerOperator

__all__ = [
    "LongRefinerCompressor",
    "LongRefinerOperator",
]
