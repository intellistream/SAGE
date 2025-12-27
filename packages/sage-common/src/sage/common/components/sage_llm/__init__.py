"""SAGE's integrated vLLM component package (DEPRECATED - moved to sage-llm-core).

⚠️ DEPRECATION WARNING:
This module has been moved to sage-llm-core. Please update your imports:

OLD (deprecated):
    from sage.common.components.sage_llm import VLLMService

NEW (correct):
    from sage.llm import VLLMService

Layer: L1 (Foundation - Common Components)

All LLM-related functionality has been consolidated into the sage-llm-core package
for better organization and clearer architecture.
"""

import warnings

# Emit deprecation warning on module import
warnings.warn(
    "sage.common.components.sage_llm has been moved to sage-llm-core. "
    "Please update your imports to use 'from sage.llm import ...' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Flag-Day refactor: Re-export from new location for internal sage-common use only
# External code MUST use sage.llm namespace
from sage.llm import (
    ControlPlaneVLLMService,
    ControlPlaneVLLMServiceConfig,
    LLMAPIServer,
    LLMLauncher,
    LLMLauncherResult,
    LLMServerConfig,
    UnifiedInferenceClient,
    VLLMService,
    VLLMServiceConfig,
    get_served_model_name,
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
    "UnifiedInferenceClient",
]
