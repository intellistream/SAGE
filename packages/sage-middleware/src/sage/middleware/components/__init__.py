"""
SAGE Middleware Components

Core middleware components including databases, flow engines, and other services.

Note: sage_refiner has been migrated to the independent isage-refiner package.
      Install with: pip install isage-refiner
      Use: from sage_refiner import LongRefinerCompressor
"""

# Lazy imports to avoid loading heavy dependencies (FAISS, etc.) at module load time
from . import sage_db, sage_flow, sage_sias, sage_tsdb
from .extensions_compat import *  # noqa: F403

# Import sage_mem - it's a namespace package that handles its own lazy loading
try:
    from . import sage_mem
except ImportError:
    # sage_mem namespace package might not be available
    sage_mem = None


__all__ = [
    "sage_db",
    "sage_flow",
    "sage_mem",
    "sage_sias",
    "sage_tsdb",
    "extensions_compat",
]
