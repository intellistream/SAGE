"""SAGE's integrated vLLM component package.

Layer: L1 (Foundation - Common Components)

This module provides service wrappers for vLLM (Very Large Language Model inference),
allowing SAGE to leverage high-performance LLM serving capabilities.

Services:
    - VLLMService: Simple single-instance vLLM service
    - ControlPlaneVLLMService: Advanced multi-instance service with intelligent scheduling
    - IntelligentLLMClient: Auto-detecting client with cloud fallback
    - UnifiedInferenceClient: Unified client for both LLM and Embedding (NEW)

Architecture:
    - Designed to be used by L2 (Platform) and higher layers
    - Provides blocking service interface for LLM generation and embeddings
    - Must NOT import from sage.kernel, sage.middleware, sage.libs, or sage.apps
"""

from .api_server import LLMAPIServer, LLMServerConfig
from .client import IntelligentLLMClient, check_llm_service, get_llm_client
from .compat import (
    EmbeddingClientAdapter,
    LLMClientAdapter,
    create_embedding_client_compat,
    create_llm_client_compat,
)
from .launcher import LLMLauncher, LLMLauncherResult
from .service import VLLMService, VLLMServiceConfig
from .unified_api_server import (
    BackendInstanceConfig,
    SchedulingPolicyType,
    UnifiedAPIServer,
    UnifiedServerConfig,
    create_unified_server,
)
from .unified_client import (
    InferenceResult,
    UnifiedClient,
    UnifiedClientConfig,
    UnifiedClientMode,
    UnifiedInferenceClient,
)

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
        "LLMLauncher",
        "LLMLauncherResult",
        "ControlPlaneVLLMService",
        "ControlPlaneVLLMServiceConfig",
        "IntelligentLLMClient",
        "check_llm_service",
        "get_llm_client",
        # Unified Client
        "UnifiedInferenceClient",
        "UnifiedClient",
        "UnifiedClientConfig",
        "UnifiedClientMode",
        "InferenceResult",
        # Unified API Server
        "UnifiedAPIServer",
        "UnifiedServerConfig",
        "BackendInstanceConfig",
        "SchedulingPolicyType",
        "create_unified_server",
        # Compatibility adapters
        "LLMClientAdapter",
        "EmbeddingClientAdapter",
        "create_llm_client_compat",
        "create_embedding_client_compat",
    ]
except ImportError:
    # Control Plane service not available
    __all__ = [
        "VLLMService",
        "VLLMServiceConfig",
        "LLMAPIServer",
        "LLMServerConfig",
        "LLMLauncher",
        "LLMLauncherResult",
        "IntelligentLLMClient",
        "check_llm_service",
        "get_llm_client",
        # Unified Client
        "UnifiedInferenceClient",
        "UnifiedClient",
        "UnifiedClientConfig",
        "UnifiedClientMode",
        "InferenceResult",
        # Unified API Server
        "UnifiedAPIServer",
        "UnifiedServerConfig",
        "BackendInstanceConfig",
        "SchedulingPolicyType",
        "create_unified_server",
        # Compatibility adapters
        "LLMClientAdapter",
        "EmbeddingClientAdapter",
        "create_llm_client_compat",
        "create_embedding_client_compat",
    ]
