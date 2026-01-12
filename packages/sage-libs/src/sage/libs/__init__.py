"""SAGE Libs - Interface Layer for SAGE Framework.

Layer: L3 (Core Libraries)
Dependencies: sage.common (L1), sage.platform (L2), sage.kernel (L3)

Architecture:
sage-libs provides abstract interfaces and registries. Implementations
are in external PyPI packages (isage-*).

Five Core Domains:
- ``agentic``: Agent framework (isage-agentic)
- ``rag``: RAG toolkit (isage-rag)
- ``finetune``: Fine-tuning (isage-finetune)
- ``eval``: Evaluation (isage-eval)
- ``privacy``: Privacy/Unlearning (isage-privacy)
- ``safety``: Safety/Guardrails (isage-safety)

Built-in Modules (no external deps):
- ``foundation``: Low-level utilities
- ``dataops``: Data operations
- ``integrations``: Third-party adapters

Algorithm Interfaces:
- ``anns``: ANNS algorithms (isage-anns)
- ``amms``: AMM algorithms (isage-amms)
"""

# Load version information (fail fast if missing to avoid silent fallbacks)
from sage.libs._version import __author__, __email__, __version__

# Export submodules
__layer__ = "L3"

# Use lazy imports to avoid circular import issues during module initialization
_submodules = {
    # Five core domains (interface layers)
    "agentic",  # Agent framework interface
    "rag",  # RAG interface
    "finetune",  # Fine-tuning interface
    "eval",  # Evaluation interface
    "privacy",  # Privacy interface
    "safety",  # Safety interface
    # Algorithm interfaces
    "ann",  # ANNS interface (isage-anns)
    "amms",  # AMM interface (isage-amms)
    # Built-in modules
    "foundation",  # Foundation utilities
    "dataops",  # Data operations
    "integrations",  # Third-party integrations
}


def __getattr__(name: str):
    """Lazy import submodules to avoid circular import issues."""
    if name in _submodules:
        import importlib

        mod = importlib.import_module(f".{name}", __name__)
        globals()[name] = mod
        return mod
    # Provide helpful alias for anns -> ann
    if name == "anns":
        import warnings

        warnings.warn(
            "'sage.libs.anns' is deprecated, use 'sage.libs.ann' instead",
            DeprecationWarning,
            stacklevel=2,
        )
        import importlib

        mod = importlib.import_module(".ann", __name__)
        globals()[name] = mod
        return mod
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "__version__",
    "__author__",
    "__email__",
    # Five core domains
    "agentic",  # Agent framework
    "rag",  # RAG toolkit
    "finetune",  # Fine-tuning
    "eval",  # Evaluation
    "privacy",  # Privacy/Unlearning
    "safety",  # Safety/Guardrails
    # Algorithm interfaces
    "ann",  # ANNS algorithms (isage-anns)
    "amms",  # AMM algorithms (isage-amms)
    # Built-in modules
    "foundation",  # Utilities
    "dataops",  # Data operations
    "integrations",  # Integrations
]
