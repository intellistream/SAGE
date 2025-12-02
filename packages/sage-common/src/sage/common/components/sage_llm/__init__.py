"""SAGE's integrated vLLM component package.

Layer: L1 (Foundation - Common Components)

This module provides service wrappers for vLLM (Very Large Language Model inference),
allowing SAGE to leverage high-performance LLM serving capabilities.

Services:
    - VLLMService: Simple single-instance vLLM service
    - ControlPlaneVLLMService: Advanced multi-instance service with intelligent scheduling
    - UnifiedInferenceClient: Unified client for both LLM and Embedding

Architecture:
    - Designed to be used by L2 (Platform) and higher layers
    - Provides blocking service interface for LLM generation and embeddings
    - Must NOT import from sage.kernel, sage.middleware, sage.libs, or sage.apps
"""

from .api_server import LLMAPIServer, LLMServerConfig, get_served_model_name
from .compat import (
    EmbeddingClientAdapter,
    LLMClientAdapter,
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
        "get_served_model_name",
        "ControlPlaneVLLMService",
        "ControlPlaneVLLMServiceConfig",
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
        "get_served_model_name",
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
    ]
