"""Vector store backends for SAGE middleware.

This module provides adapters for various vector databases:
- Milvus / Milvus Lite
- ChromaDB
- (SageVDB is in separate sage_db component)

These were promoted from sage-libs/integrations because they depend on
external database services (violates L3 → L4 layering).

Usage:
    from sage.middleware.components.vector_stores import MilvusBackend, ChromaBackend
"""

from sage.middleware.components.vector_stores.chroma import ChromaBackend, ChromaUtils
from sage.middleware.components.vector_stores.chroma_adapter import ChromaVectorStoreAdapter
from sage.middleware.components.vector_stores.milvus import MilvusBackend, MilvusUtils

__all__ = [
    "MilvusBackend",
    "MilvusUtils",
    "ChromaBackend",
    "ChromaUtils",
    "ChromaVectorStoreAdapter",
]
