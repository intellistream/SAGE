"""
SAGE-Mem: Memory Management Component for SAGE

Provides memory management capabilities for RAG applications,
wrapping the neuromem sub-project.
"""

import warnings

# Try to import from neuromem submodule, but don't fail if it's not available
try:
    from .neuromem.memory_collection import (
        BaseMemoryCollection,
        GraphMemoryCollection,
        KVMemoryCollection,
        SimpleGraphIndex,
        VDBMemoryCollection,
    )
    from .neuromem.memory_manager import MemoryManager
    from .neuromem.services import (
        BaseMemoryService,
        MemoryServiceRegistry,
        NeuromemServiceFactory,
    )

    __all__ = [
        # Core neuromem components
        "MemoryManager",
        "BaseMemoryCollection",
        "VDBMemoryCollection",
        "KVMemoryCollection",
        "GraphMemoryCollection",
        "SimpleGraphIndex",
        # Services
        "BaseMemoryService",
        "MemoryServiceRegistry",
        "NeuromemServiceFactory",
    ]

    _NEUROMEM_AVAILABLE = True

except (ImportError, ModuleNotFoundError) as e:
    warnings.warn(
        f"neuromem submodule not available: {e}. "
        "Memory management features will be limited. "
        "Run './manage.sh' or 'git submodule update --init' to initialize submodules.",
        UserWarning,
        stacklevel=2,
    )

    __all__ = []
    _NEUROMEM_AVAILABLE = False
