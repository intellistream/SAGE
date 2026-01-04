"""
SAGE-Mem: Memory Management Component for SAGE

Provides memory management capabilities for RAG applications,
wrapping the neuromem package (isage-neuromem on PyPI).
"""

import warnings

# Import from isage-neuromem PyPI package
try:
    from neuromem.memory_collection import (
        BaseMemoryCollection,
        GraphMemoryCollection,
        KVMemoryCollection,
        VDBMemoryCollection,
    )
    from neuromem.memory_manager import MemoryManager
    from neuromem.services import (
        BaseMemoryService,
        MemoryServiceRegistry,
        NeuromemServiceFactory,
    )

    # SimpleGraphIndex is in search_engine, not memory_collection
    try:
        from neuromem.search_engine.graph_index import SimpleGraphIndex
    except ImportError:
        SimpleGraphIndex = None

    __all__ = [
        # Core neuromem components
        "MemoryManager",
        "BaseMemoryCollection",
        "VDBMemoryCollection",
        "KVMemoryCollection",
        "GraphMemoryCollection",
        # Services
        "BaseMemoryService",
        "MemoryServiceRegistry",
        "NeuromemServiceFactory",
    ]

    if SimpleGraphIndex is not None:
        __all__.append("SimpleGraphIndex")

    _NEUROMEM_AVAILABLE = True

except (ImportError, ModuleNotFoundError) as e:
    warnings.warn(
        f"isage-neuromem package not available: {e}. "
        "Memory management features will be limited. "
        "Install with: pip install isage-neuromem",
        UserWarning,
        stacklevel=2,
    )

    __all__ = []
    _NEUROMEM_AVAILABLE = False
