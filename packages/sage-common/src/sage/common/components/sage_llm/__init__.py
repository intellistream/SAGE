"""SAGE's integrated vLLM component package.

Layer: L1 (Foundation - Common Components)

This module provides service wrappers for vLLM (Very Large Language Model inference),
allowing SAGE to leverage high-performance LLM serving capabilities.

Services:
    - VLLMService: Simple single-instance vLLM service
    - ControlPlaneVLLMService: Advanced multi-instance service with intelligent scheduling
    - IntelligentLLMClient: Auto-detecting client with cloud fallback (NEW)

Architecture:
    - Designed to be used by L2 (Platform) and higher layers
    - Provides blocking service interface for LLM generation and embeddings
    - Must NOT import from sage.kernel, sage.middleware, sage.libs, or sage.apps
"""

from .api_server import LLMAPIServer, LLMServerConfig
from .client import IntelligentLLMClient, check_llm_service, get_llm_client
from .service import VLLMService, VLLMServiceConfig

# Optional: Advanced Control Plane service
try:
    from .control_plane_service import (
        ControlPlaneVLLMService,
        ControlPlaneVLLMServiceConfig,
    )

    __all__ = [
        "VLLMService",
        "VLLMServiceConfig",
        "LLMAPIServer",
        "LLMServerConfig",
        "ControlPlaneVLLMService",
        "ControlPlaneVLLMServiceConfig",
        "IntelligentLLMClient",
        "check_llm_service",
        "get_llm_client",
    ]
except ImportError:
    # Control Plane service not available
    __all__ = [
        "VLLMService",
        "VLLMServiceConfig",
        "LLMAPIServer",
        "LLMServerConfig",
        "IntelligentLLMClient",
        "check_llm_service",
        "get_llm_client",
    ]
