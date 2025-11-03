"""
Third-party integrations for SAGE

This module provides integration with external services and libraries:
- Vector databases (Chroma, Milvus)
- LLM clients (OpenAI, HuggingFace)
"""

# Vector Database Backends
from sage.libs.integrations.chroma import ChromaBackend, ChromaUtils

# LLM Clients
from sage.libs.integrations.huggingface import HFClient
from sage.libs.integrations.milvus import MilvusBackend, MilvusUtils
from sage.libs.integrations.openai import OpenAIClient as OpenAIClientFromOpenai
from sage.libs.integrations.openaiclient import OpenAIClient

__all__ = [
    # Vector DB
    "ChromaBackend",
    "ChromaUtils",
    "MilvusBackend",
    "MilvusUtils",
    # LLM Clients
    "HFClient",
    "OpenAIClient",
    "OpenAIClientFromOpenai",
]
