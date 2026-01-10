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

# NOTE: ANNS, AMMS, and Agentic have been externalized to independent PyPI packages:
# - isage-anns: ANNS algorithms (interface/registry remain here as ann/)
# - isage-amms: AMM algorithms (interface/registry remain here)
# - isage-agentic: Agent framework (interface/registry remain here)
# Install via extras: pip install -e packages/sage-libs[ann,amms,agentic]
#
# Module organization (2026-01-10):
# - Seven top-level domains: agentic, rag, ann, reasoning, dataops, eval, safety
# - anns → ann (unified singular naming)
# - New domains: reasoning (search algorithms), eval (metrics & telemetry)
from . import (
    agentic,  # Agent interfaces (impl in isage-agentic)
    amms,  # AMM interfaces (impl in isage-amms)
    ann,  # ANN interfaces (impl in isage-anns) - renamed from anns
    dataops,  # Data operations
    finetune,  # Fine-tuning interfaces (impl in isage-finetune)
    foundation,  # Foundation utilities
    integrations,  # Third-party integrations
    privacy,  # Privacy protection
    rag,  # RAG tools
    reasoning,  # Search & scoring algorithms
    safety,  # Safety checks
    sias,  # SIAS framework (pending migration to isage-agentic)
)

# New domains (2026-01-10)
from . import (
    eval as evaluation,  # Evaluation metrics & telemetry (renamed to avoid built-in)
)

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    # Seven top-level domains
    "agentic",  # Agent framework (interface layer)
    "rag",  # RAG tools
    "ann",  # ANN interface (renamed from anns)
    "reasoning",  # Search & scoring algorithms (NEW)
    "dataops",  # Data operations
    "evaluation",  # Metrics & telemetry (NEW, renamed from eval)
    "safety",  # Safety checks
    # Supporting modules
    "foundation",  # Foundation utilities
    "integrations",  # Third-party integrations
    "privacy",  # Privacy protection
    "sias",  # SIAS framework (pending migration)
    # Interface layers (external implementations)
    "amms",  # AMM interface
    "finetune",  # Fine-tuning interface
]
