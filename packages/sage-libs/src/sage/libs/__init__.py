"""SAGE Libs - Layered algorithm library for SAGE Framework.

Layer: L3 (Core Libraries)
Dependencies: sage.common (L1), sage.platform (L2), sage.kernel (L3)

High-level layout:
- ``foundation``: Lowest-level utilities (tools, io, context, filters)
- ``agentic``: LangChain-style agent framework + workflow optimizer
- ``rag``: Retrieval-Augmented Generation building blocks (migrating from middleware)
- ``integrations``: Third-party service adapters (LLMs, vector DBs, observability)
- ``privacy``: Machine unlearning and privacy-preserving algorithms
- ``finetune``: Model fine-tuning utilities (moved from sage-tools for broader access)

This structure makes coarse-grained systems (agents, RAG) live beside
infrastructure concerns while keeping fine-grained utilities in ``foundation``.
"""

# Load version information (fail fast if missing to avoid silent fallbacks)
from sage.libs._version import __author__, __email__, __version__

# Export submodules
__layer__ = "L3"

# NOTE: ANNS and AMMS have been externalized to independent PyPI packages:
# - isage-anns: ANNS algorithms (interface/registry remain here)
# - isage-amms: AMM algorithms (interface/registry remain here)
# Install via extras: pip install -e packages/sage-libs[anns,amms]
#
# Module reorganization (2026-01):
# - sias, reasoning, eval → moved into agentic/ for consolidation
from . import (
    agentic,
    amms,
    anns,
    dataops,
    finetune,
    foundation,
    integrations,
    privacy,
    rag,
    safety,
)

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    # Core domains
    "foundation",
    "agentic",  # Includes: agents, planning, sias, reasoning, eval
    "rag",
    "dataops",
    "safety",
    # Interface layers (external implementations)
    "anns",  # ANNS interface
    "amms",  # AMM interface
    # Specialized
    "integrations",
    "privacy",
    "finetune",
]
