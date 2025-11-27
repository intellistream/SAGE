"""SAGE's integrated vLLM component package.

Layer: L1 (Foundation - Common Components)

This module provides service wrappers for vLLM (Very Large Language Model inference),
allowing SAGE to leverage high-performance LLM serving capabilities.

Services:
    - VLLMService: Simple single-instance vLLM service (in-process)
    - ControlPlaneVLLMService: Advanced multi-instance service with intelligent scheduling
    - UnifiedInferenceClient: Unified client for LLM, Embedding, and mixed inference

Modes:
    - API Mode: Connect to external vLLM server or cloud API
    - Embedded Mode: In-process GPU inference (no external server needed)
    - Control Plane Mode: Multi-instance load balancing

Architecture:
    - Designed to be used by L2 (Platform) and higher layers
    - Provides blocking service interface for LLM generation and embeddings
    - Must NOT import from sage.kernel, sage.middleware, sage.libs, or sage.apps

IMPORTANT: Use UnifiedInferenceClient for all new code. Do NOT use deprecated
IntelligentLLMClient or IntelligentEmbeddingClient.
"""

# =============================================================================
# DEPRECATED: Backward-compatible aliases (will be removed in future versions)
# Use UnifiedInferenceClient instead.
# =============================================================================
import warnings

from .api_server import LLMAPIServer, LLMServerConfig
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


class IntelligentLLMClient(UnifiedInferenceClient):
    """DEPRECATED: Use UnifiedInferenceClient instead.

    This class is provided for backward compatibility only and will be
    removed in a future version.

    Migration guide:
        # Old (deprecated):
        from sage.common.components.sage_llm import IntelligentLLMClient
        client = IntelligentLLMClient.get_instance()

        # New (recommended):
        from sage.common.components.sage_llm import UnifiedInferenceClient
        client = UnifiedInferenceClient.create_auto()
    """

    def __init__(self, *args, **kwargs):
        """Initialize with deprecation warning."""
        warnings.warn(
            "IntelligentLLMClient is deprecated. Use UnifiedInferenceClient instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        # Convert old-style arguments to new format
        if "model_name" in kwargs:
            kwargs["llm_model"] = kwargs.pop("model_name")
        if "base_url" in kwargs:
            kwargs["llm_base_url"] = kwargs.pop("base_url")
        if "api_key" in kwargs:
            kwargs["llm_api_key"] = kwargs.pop("api_key")
        super().__init__(*args, **kwargs)

    @classmethod
    def create_auto(cls, **kwargs):
        """DEPRECATED: Use UnifiedInferenceClient.create_auto() instead."""
        warnings.warn(
            "IntelligentLLMClient.create_auto() is deprecated. "
            "Use UnifiedInferenceClient.create_auto() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return UnifiedInferenceClient.create_auto(**kwargs)

    @classmethod
    def get_instance(cls, cache_key: str = "default", **kwargs):
        """DEPRECATED: Use UnifiedInferenceClient.get_instance() instead."""
        warnings.warn(
            "IntelligentLLMClient.get_instance() is deprecated. "
            "Use UnifiedInferenceClient.get_instance() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return UnifiedInferenceClient.get_instance(instance_key=cache_key, **kwargs)

    @staticmethod
    def _probe_vllm_service(endpoint: str, timeout: float = 2.0) -> str | None:
        """DEPRECATED: Probe vLLM service for available models."""
        warnings.warn(
            "IntelligentLLMClient._probe_vllm_service() is deprecated. "
            "Use UnifiedInferenceClient._check_endpoint_health() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        import httpx

        try:
            response = httpx.get(f"{endpoint}/models", timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])
                if models:
                    return models[0].get("id", "")
        except Exception:
            pass
        return None


def check_llm_service(
    base_url: str = "http://localhost:8001/v1",
    timeout: float = 2.0,
) -> bool:
    """DEPRECATED: Check if LLM service is available.

    Use UnifiedInferenceClient._check_endpoint_health() instead.
    """
    warnings.warn(
        "check_llm_service() is deprecated. "
        "Use UnifiedInferenceClient._check_endpoint_health() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return UnifiedInferenceClient._check_endpoint_health(base_url)


def get_llm_client(**kwargs) -> UnifiedInferenceClient:
    """DEPRECATED: Get a configured LLM client.

    Use UnifiedInferenceClient.create_auto() instead.
    """
    warnings.warn(
        "get_llm_client() is deprecated. Use UnifiedInferenceClient.create_auto() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return UnifiedInferenceClient.create_auto(**kwargs)


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
        # Unified Client (recommended)
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
        # DEPRECATED: Backward-compatible aliases (will be removed)
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
        # Unified Client (recommended)
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
        # DEPRECATED: Backward-compatible aliases (will be removed)
        "IntelligentLLMClient",
        "check_llm_service",
        "get_llm_client",
    ]
