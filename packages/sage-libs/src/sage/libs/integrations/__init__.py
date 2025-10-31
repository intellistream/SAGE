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

from .chroma import *  # noqa: F403
from .huggingface import *  # noqa: F403
from .milvus import *  # noqa: F403

# Import from openaiclient which is the newer implementation
from .openaiclient import OpenAIClient  # noqa: F401

__all__: list[str] = [
    "OpenAIClient",
    # Re-export from submodules
    # Will be populated as modules are standardized
]

__version__ = "0.1.0"
