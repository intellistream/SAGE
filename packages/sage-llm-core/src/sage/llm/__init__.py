"""SAGE LLM Core - Control Plane and Multi-Engine Integration

Layer: L1 (Foundation)

This namespace is the unified entry point for all LLM-related functionality.

Architecture:
```
sage.llm/
├── control_plane/           # Unified scheduling & routing (engine-agnostic)
│   ├── manager.py           # Control plane manager
│   ├── strategies/          # Scheduling strategies
│   └── executors/           # Execution coordinators
├── engines/                 # Multiple engine integrations
│   ├── vllm/                # vLLM engine (✅ Production)
│   │   ├── service.py
│   │   ├── api_server.py
│   │   └── launcher.py
│   └── sagellm/             # sageLLM engine (🚧 Submodule)
│       └── [submodule: intellistream/sageLLM.git]
├── unified_client.py        # Unified client API
└── control_plane_service.py # Advanced Control Plane service
```

Architecture rules:
- ✅ Can be imported by: L2-L6
- ❌ Must NOT import from: sage.kernel, sage.middleware, sage.libs, sage.apps

Design principle:
- sage.llm is the PUBLIC API namespace for LLM functionality
- Control Plane is engine-agnostic (manages vLLM, sageLLM, and future engines)
- Each engine has its own implementation (vLLM: direct code, sageLLM: submodule)
- External code should import from sage.llm, not internal paths
"""

# Namespace package support
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

__layer__ = "L1"

from ._version import __version__

# Advanced Control Plane service
from .control_plane_service import (
    ControlPlaneVLLMService,
    ControlPlaneVLLMServiceConfig,
)

# vLLM engine integration (now in sage-llm-core/engines/vllm/)
from .engines.vllm import (
    DraftModelStrategy,
    LLMAPIServer,
    LLMLauncher,
    LLMLauncherResult,
    LLMServerConfig,
    SpeculativeStrategy,
    VLLMService,
    VLLMServiceConfig,
    get_served_model_name,
)

# Primary unified client
from .unified_client import UnifiedInferenceClient

__all__ = [
    "__version__",
    # Primary API
    "UnifiedInferenceClient",
    # vLLM Engine (from engines/vllm/)
    "VLLMService",
    "VLLMServiceConfig",
    "LLMAPIServer",
    "LLMServerConfig",
    "LLMLauncher",
    "LLMLauncherResult",
    "get_served_model_name",
    "SpeculativeStrategy",
    "DraftModelStrategy",
    # Advanced services
    "ControlPlaneVLLMService",
    "ControlPlaneVLLMServiceConfig",
]
