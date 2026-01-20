"""Context management for LLMs.

Note:
    Context compression algorithms have been migrated to isage-refiner.
    Install with: pip install isage-refiner

    For SAGE middleware integration with context compression,
    see sage.middleware.components.sage_refiner.
"""

from . import compression

__all__ = ["compression"]
