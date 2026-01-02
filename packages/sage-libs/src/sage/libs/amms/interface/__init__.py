"""AMM Interface Layer.

Provides abstract base classes and factory functions for AMM algorithms.
"""

from sage.libs.amms.interface.base import AmmIndex, AmmIndexMeta, StreamingAmmIndex
from sage.libs.amms.interface.factory import create, get_meta, registered
from sage.libs.amms.interface.registry import register, unregister

__all__ = [
    # Base classes
    "AmmIndex",
    "AmmIndexMeta",
    "StreamingAmmIndex",
    # Factory functions
    "create",
    "registered",
    "get_meta",
    # Registry functions
    "register",
    "unregister",
]
