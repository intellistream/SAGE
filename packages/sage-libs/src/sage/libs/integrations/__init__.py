"""
Third-party integrations for SAGE

This module provides integration with external services and libraries:
- LLM clients (HuggingFace local inference)

Note:
    LLM inference components have been moved to the independent `isagellm` package.
    For LLM inference, SAGE uses vLLM as the backend engine.

    Vector store backends (ChromaBackend, MilvusBackend, ChromaVectorStoreAdapter)
    have been migrated to sage.middleware.components.vector_stores (L4).
    Please update imports:
        from sage.middleware.components.vector_stores import (
            ChromaBackend, MilvusBackend, ChromaVectorStoreAdapter
        )
"""

# LLM Clients (local inference, no external service required)
from sage.libs.integrations.huggingface import HFClient

__all__ = [
    # LLM Clients
    "HFClient",
]
