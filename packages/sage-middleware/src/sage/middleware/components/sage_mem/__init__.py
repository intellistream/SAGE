"""
SAGE-Mem: Memory Management Component for SAGE

Provides memory management capabilities for RAG applications.
This is a namespace package that can contain multiple memory implementations:
- neuromem: Brain-inspired memory system (from isage-neuromem package)
- future implementations can be added here

Usage:
    # Method 1: Import from neuromem subpackage (recommended)
    from sage.middleware.components.sage_mem.neuromem import MemoryManager

    # Method 2: Convenience imports from sage_mem root (if neuromem is installed)
    from sage.middleware.components.sage_mem import MemoryManager
"""

# This is a namespace package - allow subpackages from different distributions
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

# Convenience re-exports from neuromem (optional, requires isage-neuromem installed)
# These are lazy-loaded to avoid import errors if neuromem is not installed
_NEUROMEM_AVAILABLE = False

try:
    # Try to import from the neuromem subpackage first (supports namespace merging)
    from sage.middleware.components.sage_mem.neuromem import (
        BaseMemoryCollection,
        GraphMemoryCollection,
        KVMemoryCollection,
        MemoryManager,
        VDBMemoryCollection,
    )

    try:
        from sage.middleware.components.sage_mem.neuromem.services import (
            BaseMemoryService,
            MemoryServiceRegistry,
            NeuromemServiceFactory,
        )
    except ImportError:
        # Services might not be available in all neuromem versions
        pass

    # SimpleGraphIndex is in search_engine, not memory_collection
    try:
        from sage.middleware.components.sage_mem.neuromem.search_engine.graph_index import (
            SimpleGraphIndex,
        )
    except ImportError:
        SimpleGraphIndex = None

    __all__ = [
        # Core neuromem components
        "MemoryManager",
        "BaseMemoryCollection",
        "VDBMemoryCollection",
        "KVMemoryCollection",
        "GraphMemoryCollection",
        # Services (if available)
        "BaseMemoryService",
        "MemoryServiceRegistry",
        "NeuromemServiceFactory",
    ]

    if SimpleGraphIndex is not None:
        __all__.append("SimpleGraphIndex")

    _NEUROMEM_AVAILABLE = True

except (ImportError, FileNotFoundError, ModuleNotFoundError):
    # Neuromem not installed - provide helpful error message via __getattr__
    def __getattr__(name):
        """Provide friendly error message when neuromem is not installed"""
        raise ImportError(
            f"Cannot import '{name}' from sage.middleware.components.sage_mem. "
            "NeuroMem is not installed. Please install it using:\n"
            "  pip install isage-neuromem\n"
            "or install sage-middleware with neuromem support:\n"
            "  pip install isage-middleware[neuromem]"
        )

    __all__ = []
    _NEUROMEM_AVAILABLE = False
