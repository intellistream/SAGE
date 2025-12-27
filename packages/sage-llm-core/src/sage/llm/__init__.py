"""SAGE LLM Core - Control Plane and Unified Client

Layer: L1 (Foundation)

This namespace hosts LLM/embedding control plane logic and the unified inference client.
Future modules are split from the legacy SAGE LLM components as part of the flag-day refactor.

Architecture rules:
- ✅ Can be imported by: L2-L6
- ❌ Must NOT import from: sage.kernel, sage.middleware, sage.libs, sage.apps
"""

# Namespace package support (needed for contributions from other distributions)
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

__layer__ = "L1"

from ._version import __version__
from .unified_client import UnifiedInferenceClient

__all__ = ["__version__", "UnifiedInferenceClient"]
