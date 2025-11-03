"""
Third-party integrations for SAGE

This module provides integration with external services and libraries:
- Vector databases (Chroma, Milvus)
- LLM clients (OpenAI, HuggingFace)
"""

# Vector Database Backends
from sage.libs.integrations.chroma import ChromaBackend, ChromaUtils
from sage.libs.integrations.huggingface import HuggingFaceClient
from sage.libs.integrations.milvus import MilvusBackend, MilvusUtils

# LLM Clients
from sage.libs.integrations.openai import OpenAIClient
from sage.libs.integrations.openaiclient import OpenAIClientWrapper

__all__ = [
    # Vector DB
    "ChromaBackend",
    "ChromaUtils",
    "MilvusBackend",
    "MilvusUtils",
    # LLM Clients
    "OpenAIClient",
    "OpenAIClientWrapper",
    "HuggingFaceClient",
]
