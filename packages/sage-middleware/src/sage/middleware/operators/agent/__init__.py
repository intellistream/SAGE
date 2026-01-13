"""
Agent components for SAGE middleware.

Provides agent runtime and planning capabilities.

Note: This module requires `isage-agentic` package. Install with:
    pip install isage-agentic

If the package is not installed, agent operators will not be available.
"""

# Check if sage_agentic is available
try:
    import sage_agentic  # noqa: F401

    _HAS_SAGE_AGENTIC = True
except ImportError:
    _HAS_SAGE_AGENTIC = False

__all__: list[str] = []

if _HAS_SAGE_AGENTIC:
    from sage.middleware.operators.agent import runtime

    __all__ = ["runtime"]
