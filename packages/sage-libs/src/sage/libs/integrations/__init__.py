"""
Third-party integrations for SAGE

This module provides integration with external services and libraries:
- Vector databases (Chroma, Milvus)
- LLM clients (HuggingFace)

Note:
    OpenAIClient has been migrated to sage.llm.UnifiedInferenceClient (L1).
    Please update imports:
        from sage.llm import UnifiedInferenceClient
"""

# Vector Database Backends
from sage.libs.integrations.chroma import ChromaBackend, ChromaUtils
from sage.libs.integrations.chroma_adapter import ChromaVectorStoreAdapter

# LLM Clients
from sage.libs.integrations.huggingface import HFClient
from sage.libs.integrations.milvus import MilvusBackend, MilvusUtils

__all__ = [
    # Vector DB
    "ChromaBackend",
    "ChromaUtils",
    "ChromaVectorStoreAdapter",
    "MilvusBackend",
    "MilvusUtils",
    # LLM Clients
    "HFClient",
]
