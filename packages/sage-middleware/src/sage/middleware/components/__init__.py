"""
SAGE Middleware Components

Core middleware components including databases, flow engines, and other services.
"""

# Lazy imports to avoid loading heavy dependencies (FAISS, etc.) at module load time
from . import sage_db, sage_flow, sage_refiner, sage_tsdb
from .extensions_compat import *  # noqa: F403


def __getattr__(name: str):
    """Lazy load sage_mem to avoid FAISS initialization at import time"""
    if name == "sage_mem":
        from . import sage_mem

        return sage_mem
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "sage_db",
    "sage_flow",
    "sage_mem",
    "sage_refiner",
    "sage_tsdb",
    "extensions_compat",
]
