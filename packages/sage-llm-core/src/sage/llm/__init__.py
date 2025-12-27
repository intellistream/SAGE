"""SAGE LLM Core - Control Plane and Unified Client

Layer: L1 (Foundation)

This namespace is the unified entry point for all LLM-related functionality.

Architecture rules:
- ✅ Can be imported by: L2-L6
- ❌ Must NOT import from: sage.kernel, sage.middleware, sage.libs, sage.apps

Design principle (Flag-Day refactor):
- sage.llm is the PUBLIC API namespace for LLM functionality
- Implementation may live in sage.common.components.sage_llm (internal)
- All external code should import from sage.llm, not sage.common.components.sage_llm
"""

# Namespace package support
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

__layer__ = "L1"

# Re-export service classes from sage.common (implementation detail)
# These are re-exported here to provide a unified sage.llm.* import path
from sage.common.components.sage_llm import (
    ControlPlaneVLLMService,
    ControlPlaneVLLMServiceConfig,
    LLMAPIServer,
    LLMLauncher,
    LLMLauncherResult,
    LLMServerConfig,
    VLLMService,
    VLLMServiceConfig,
    get_served_model_name,
)

from ._version import __version__

# Primary unified client (new simplified version in this package)
from .unified_client import UnifiedInferenceClient

__all__ = [
    "__version__",
    # Primary API
    "UnifiedInferenceClient",
    # Service classes (re-exported from sage.common)
    "ControlPlaneVLLMService",
    "ControlPlaneVLLMServiceConfig",
    "LLMAPIServer",
    "LLMLauncher",
    "LLMLauncherResult",
    "LLMServerConfig",
    "VLLMService",
    "VLLMServiceConfig",
    "get_served_model_name",
]
