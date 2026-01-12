"""Built-in ANN implementations.

Heavy deps live behind optional imports; registration is explicit via
``register_builtin()`` to avoid side effects on import.
"""

from __future__ import annotations

from .dummy import register_dummy

__all__ = ["register_dummy", "register_builtin"]


def register_builtin() -> None:
    """Register lightweight built-in ANN implementations.

    Keep this cheap—heavy dependencies (faiss, diskann) should register in their
    own modules guarded by optional imports and extras.
    """

    register_dummy()
