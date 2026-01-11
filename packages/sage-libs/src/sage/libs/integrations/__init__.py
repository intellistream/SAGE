"""
Third-party integrations for SAGE

This module provides integration with external services and libraries:
- LLM clients (HuggingFace local inference)

Note:
    OpenAIClient has been migrated to sage.llm.UnifiedInferenceClient (L1).
    Please update imports:
        from sage.llm import UnifiedInferenceClient

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
