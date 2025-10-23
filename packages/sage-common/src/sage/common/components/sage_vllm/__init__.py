"""SAGE's integrated vLLM component package.

Layer: L1 (Foundation - Common Components)

This module provides a service wrapper for vLLM (Very Large Language Model inference),
allowing SAGE to leverage high-performance LLM serving capabilities.

Architecture:
    - Designed to be used by L2 (Platform) and higher layers
    - Provides blocking service interface for LLM generation and embeddings
    - Must NOT import from sage.kernel, sage.middleware, sage.libs, or sage.apps
"""

from .service import VLLMService, VLLMServiceConfig, register_vllm_service

__all__ = ["VLLMService", "VLLMServiceConfig", "register_vllm_service"]
