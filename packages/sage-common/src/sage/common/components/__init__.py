"""Shared SAGE components available across packages.

Layer: L1 (Foundation - Common Components)

This package contains reusable components that provide specific functionalities:
- sage_embedding: Unified embedding interface for multiple providers
- sage_vllm: vLLM service integration for high-performance LLM serving

These components are designed to be used by L2 (Platform) and higher layers.
They must NOT import from sage.kernel, sage.middleware, sage.libs, or sage.apps.
"""

from . import sage_vllm

__all__ = ["sage_vllm"]
