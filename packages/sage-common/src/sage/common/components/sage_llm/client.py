# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""DEPRECATED: Backward-compatible client module.

This module is provided for backward compatibility only. Use UnifiedInferenceClient
from sage.common.components.sage_llm instead.

Migration guide:
    # Old (deprecated):
    from sage.common.components.sage_llm.client import IntelligentLLMClient
    client = IntelligentLLMClient.get_instance()

    # New (recommended):
    from sage.common.components.sage_llm import UnifiedInferenceClient
    client = UnifiedInferenceClient.create_auto()
"""

import warnings

# Re-export from parent module for backward compatibility
from . import (
    IntelligentLLMClient,
    UnifiedInferenceClient,
    check_llm_service,
    get_llm_client,
)

# Emit deprecation warning when this module is imported
warnings.warn(
    "Importing from sage.common.components.sage_llm.client is deprecated. "
    "Import from sage.common.components.sage_llm directly instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "IntelligentLLMClient",
    "UnifiedInferenceClient",
    "check_llm_service",
    "get_llm_client",
]
