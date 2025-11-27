# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""DEPRECATED: Backward-compatible client module.

This module is provided for backward compatibility only. Use UnifiedInferenceClient
from sage.common.components.sage_llm instead.

Migration guide:
    # Old (deprecated):
    from sage.common.components.sage_embedding.client import IntelligentEmbeddingClient
    client = IntelligentEmbeddingClient.create_auto()

    # New (recommended):
    from sage.common.components.sage_llm import UnifiedInferenceClient
    client = UnifiedInferenceClient.create_auto()
    vectors = client.embed(["text1", "text2"])
"""

import warnings

# Re-export from parent module for backward compatibility
from . import IntelligentEmbeddingClient, get_embedding_client

# Emit deprecation warning when this module is imported
warnings.warn(
    "Importing from sage.common.components.sage_embedding.client is deprecated. "
    "Use UnifiedInferenceClient from sage.common.components.sage_llm instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "IntelligentEmbeddingClient",
    "get_embedding_client",
]
