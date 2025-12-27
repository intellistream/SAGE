"""SAGE's integrated vLLM component package (MOVED to sage-llm-core).

⚠️ BREAKING CHANGE (Flag-Day Refactor):
This module has been completely moved to sage-llm-core. Imports will fail.

Please update your imports:

OLD (removed):
    from sage.common.components.sage_llm import VLLMService

NEW (correct):
    from sage.llm import VLLMService

Layer: L1 (Foundation - Common Components)

All LLM-related functionality has been consolidated into the sage-llm-core package
for better organization and clearer architecture.
"""

# Flag-Day refactor: Explicitly fail imports to force migration
# No backward compatibility - external code MUST update to sage.llm

__all__ = []


def __getattr__(name: str):
    """Explicitly fail all attribute access with a clear error message."""
    raise ImportError(
        f"sage.common.components.sage_llm.{name} has been moved to sage-llm-core.\n"
        f"Please update your import to: from sage.llm import {name}"
    )
