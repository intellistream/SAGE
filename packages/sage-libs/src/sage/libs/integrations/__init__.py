"""
SAGE Integrations - Third-party Service Integrations

Layer: L3 (Core - Algorithm Library)

This module provides integrations with third-party services and APIs,
including vector databases, LLM providers, and other AI services.

Available Integrations:
- OpenAI: OpenAI API client and utilities
- Milvus: Milvus vector database integration
- Chroma: ChromaDB vector database integration
- Hugging Face: Hugging Face model hub integration
"""

from .chroma import *
from .huggingface import *
from .milvus import *
from .openai import *
from .openaiclient import *

__all__ = [
    # Re-export from submodules
    # Will be populated as modules are standardized
]

__version__ = "0.1.0"
