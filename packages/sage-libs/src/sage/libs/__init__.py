"""SAGE Libs - Layered algorithm library for SAGE Framework.

Layer: L3 (Core Libraries)
Dependencies: sage.common (L1), sage.platform (L2), sage.kernel (L3)

High-level layout:
- ``foundation``: Lowest-level utilities (tools, io, context, filters)
- ``dataops``: Data operations and transformations
- ``safety``: Safety checks and content filtering
- ``privacy``: Machine unlearning and privacy-preserving algorithms
- ``integrations``: Third-party service adapters (LLMs, vector DBs, observability)
- ``intent``: Intent recognition and classification
- ``finetune``: Model fine-tuning utilities (interface layer, impl in isage-finetune)
- ``ann``: ANN algorithms interface (impl in isage-anns)
- ``amms``: AMM algorithms interface (impl in isage-amms)

Externalized modules (install via extras):
- ``agentic``: Agent framework → isage-agentic (pip install isage-libs[agentic])
- ``rag``: RAG tools → isage-rag (pip install isage-libs[rag])

This structure keeps core utilities in sage-libs while allowing optional
installation of heavier application-layer modules.
"""

# Load version information (fail fast if missing to avoid silent fallbacks)
from sage.libs._version import __author__, __email__, __version__

# Export submodules
__layer__ = "L3"

# NOTE: Agentic and RAG have been externalized to independent PyPI packages:
# - isage-agentic: Agent framework (agents, planning, tool selection, workflows)
# - isage-rag: RAG tools (document loaders, chunkers, retrievers, rerankers)
# - isage-anns: ANNS algorithms (interface/registry remain here as ann/)
# - isage-amms: AMM algorithms (interface/registry remain here)
# - isage-finetune: Fine-tuning toolkit (interface/registry remain here)
#
# Install via extras: pip install isage-libs[agentic,rag,ann,amms,finetune]
# Or install all: pip install isage-libs[all]

# Use lazy imports to avoid circular import issues during module initialization
_submodules = {
    "amms",  # AMM interfaces (impl in isage-amms)
    "ann",  # ANN interfaces (impl in isage-anns) - renamed from anns
    "dataops",  # Data operations
    "finetune",  # Fine-tuning interfaces (impl in isage-finetune)
    "foundation",  # Foundation utilities
    "integrations",  # Third-party integrations
    "intent",  # Intent recognition
    "privacy",  # Privacy protection
    "safety",  # Safety checks
}


def __getattr__(name: str):
    """Lazy import submodules to avoid circular import issues."""
    if name in _submodules:
        # Standard submodule import
        import importlib

        mod = importlib.import_module(f".{name}", __name__)
        globals()[name] = mod
        return mod
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "__version__",
    "__author__",
    "__email__",
    # Core modules
    "ann",  # ANN interface (renamed from anns)
    "dataops",  # Data operations
    "foundation",  # Foundation utilities
    "integrations",  # Third-party integrations
    "intent",  # Intent recognition
    "privacy",  # Privacy protection
    "safety",  # Safety checks
    # Interface layers (external implementations)
    "amms",  # AMM interface
    "finetune",  # Fine-tuning interface
]
