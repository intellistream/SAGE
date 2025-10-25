"""
SAGE-Mem: Memory Management Component for SAGE

Provides memory management capabilities for RAG applications,
wrapping the neuromem sub-project.
"""

from .neuromem.memory_collection import (BaseMemoryCollection,
                                         GraphMemoryCollection,
                                         KVMemoryCollection,
                                         VDBMemoryCollection)
# Export core components from neuromem sub-project
from .neuromem.memory_manager import MemoryManager
# Export services
from .services.neuromem_vdb import NeuroMemVDB
from .services.neuromem_vdb_service import NeuroMemVDBService

__all__ = [
    # Core neuromem components
    "MemoryManager",
    "BaseMemoryCollection",
    "VDBMemoryCollection",
    "KVMemoryCollection",
    "GraphMemoryCollection",
    # Services
    "NeuroMemVDB",
    "NeuroMemVDBService",
]
