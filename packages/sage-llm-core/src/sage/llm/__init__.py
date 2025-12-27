"""SAGE LLM Core - Control Plane and Unified Client

Layer: L1 (Foundation)

This namespace is the unified entry point for all LLM-related functionality.

Architecture rules:
- ✅ Can be imported by: L2-L6
- ❌ Must NOT import from: sage.kernel, sage.middleware, sage.libs, sage.apps

Design principle (Flag-Day refactor):
- sage.llm is the PUBLIC API namespace for LLM functionality
- All LLM service implementations live in sage-llm-core package
- External code should import from sage.llm, not internal paths
"""

# Namespace package support
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

__layer__ = "L1"

from ._version import __version__

# vLLM service wrappers (now in sage-llm-core)
from .api_server import LLMAPIServer, LLMServerConfig, get_served_model_name

# Advanced Control Plane service
from .control_plane_service import (
    ControlPlaneVLLMService,
    ControlPlaneVLLMServiceConfig,
)
from .launcher import LLMLauncher, LLMLauncherResult
from .service import VLLMService, VLLMServiceConfig

# Primary unified client
from .unified_client import UnifiedInferenceClient

__all__ = [
    "__version__",
    # Primary API
    "UnifiedInferenceClient",
    # Service classes (vLLM wrappers)
    "VLLMService",
    "VLLMServiceConfig",
    "LLMAPIServer",
    "LLMServerConfig",
    "LLMLauncher",
    "LLMLauncherResult",
    "get_served_model_name",
    # Advanced services
    "ControlPlaneVLLMService",
    "ControlPlaneVLLMServiceConfig",
]
