"""vLLM Engine Integration for SAGE.

Layer: L1 (Foundation - LLM Core)

This module provides SAGE integration for the vLLM inference engine:
- VLLMService: Blocking vLLM service wrapper
- LLMAPIServer: OpenAI-compatible API server
- LLMLauncher: Process launcher for vLLM servers
- SpeculativeStrategy: Speculative decoding support

vLLM is a third-party high-performance LLM inference engine.
Website: https://github.com/vllm-project/vllm
"""

from .api_server import LLMAPIServer, LLMServerConfig, get_served_model_name
from .launcher import LLMLauncher, LLMLauncherResult
from .service import VLLMService, VLLMServiceConfig
from .speculative import (
    DraftModelStrategy,
    DynamicLookaheadStrategy,
    NgramStrategy,
    SpeculativeStrategy,
)

__all__ = [
    # Service
    "VLLMService",
    "VLLMServiceConfig",
    # API Server
    "LLMAPIServer",
    "LLMServerConfig",
    "get_served_model_name",
    # Launcher
    "LLMLauncher",
    "LLMLauncherResult",
    # Speculative Decoding
    "SpeculativeStrategy",
    "DraftModelStrategy",
    "NgramStrategy",
    "DynamicLookaheadStrategy",
]
