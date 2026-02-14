"""
SAGE Middleware Components

Core middleware components including databases, flow engines, and other services.

Note: sage_refiner has been migrated to the independent isage-refiner package.
      Install with: pip install isage-refiner
      Use: from sage_refiner import LongRefinerCompressor
"""

# Lazy imports to avoid loading heavy dependencies (FAISS, etc.) at module load time
# Use individual try-except blocks to make imports optional
_available_components = []

try:
    from . import sage_vdb

    _available_components.append("sage_vdb")
except (ImportError, OSError):
    # OSError can occur when .so libraries are missing (e.g., libfaiss.so)
    sage_vdb = None

try:
    from . import sage_flow

    _available_components.append("sage_flow")
except (ImportError, OSError):
    sage_flow = None

try:
    from . import sage_sias

    _available_components.append("sage_sias")
except (ImportError, OSError):
    sage_sias = None

try:
    from . import sage_tsdb

    _available_components.append("sage_tsdb")
except (ImportError, OSError):
    sage_tsdb = None

from .extensions_compat import *  # noqa: F403

# Import sage_mem - it's a namespace package that handles its own lazy loading
try:
    from . import sage_mem

    _available_components.append("sage_mem")
except ImportError:
    # sage_mem namespace package might not be available
    sage_mem = None


__all__ = [
    "sage_vdb",
    "sage_flow",
    "sage_mem",
    "sage_sias",
    "sage_tsdb",
    "extensions_compat",
]
