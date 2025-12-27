"""Compatibility shim for ``sage.llm.speculative``.

Bridges to ``sage.common.components.sage_llm.speculative`` where the
implementations live.
"""

from sage.common.components.sage_llm.speculative import (  # noqa: F401
    DraftModelStrategy,
    SpeculativeStrategy,
)

__all__ = ["DraftModelStrategy", "SpeculativeStrategy"]
