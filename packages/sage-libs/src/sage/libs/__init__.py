"""SAGE Libs - Layered algorithm library for SAGE Framework.

Layer: L3 (Core Libraries)
Dependencies: sage.common (L1), sage.platform (L2), sage.kernel (L3)

High-level layout:
- ``foundation``: Lowest-level utilities (tools, io, context, filters)
- ``agentic``: LangChain-style agent framework + workflow optimizer
- ``rag``: Retrieval-Augmented Generation building blocks (migrating from middleware)
- ``integrations``: Third-party service adapters (LLMs, vector DBs, observability)
- ``privacy``: Machine unlearning and privacy-preserving algorithms

This structure makes coarse-grained systems (agents, RAG) live beside
infrastructure concerns while keeping fine-grained utilities in ``foundation``.
"""

# Load version information
try:
    from sage.libs._version import __author__, __email__, __version__
except ImportError:
    # Fallback to hardcoded version
    __version__ = "0.1.4"
    __author__ = "IntelliStream Team"
    __email__ = "shuhao_zhang@hust.edu.cn"

# Export submodules
__layer__ = "L3"

from . import agentic, foundation, integrations, privacy, rag

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "foundation",
    "agentic",
    "rag",
    "integrations",
    "privacy",
]
