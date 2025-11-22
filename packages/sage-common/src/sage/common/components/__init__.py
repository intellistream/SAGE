"""Shared SAGE components available across packages.

Layer: L1 (Foundation - Common Components)

This package contains reusable components that provide specific functionalities:
- sage_embedding: Unified embedding interface for multiple providers
- sage_llm: vLLM service integration for high-performance LLM serving

These components are designed to be used by L2 (Platform) and higher layers.
They must NOT import from sage.kernel, sage.middleware, sage.libs, or sage.apps.
"""

# Try to import sage_llm, but don't fail if vllm dependencies are not available
try:
    from . import sage_llm

    __all__ = ["sage_llm"]
except (ImportError, AttributeError) as e:
    # vllm or its dependencies (torch) might not be installed or compatible
    # This is acceptable for development tools that don't need vllm
    import warnings

    warnings.warn(f"sage_llm component not available: {e}", ImportWarning, stacklevel=2)
    __all__ = []
