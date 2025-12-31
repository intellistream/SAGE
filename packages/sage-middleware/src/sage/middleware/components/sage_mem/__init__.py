"""
SAGE-Mem: Memory Management Component for SAGE

Provides memory management capabilities for RAG applications,
wrapping the neuromem sub-project.
"""

from .neuromem.memory_collection import (
    BaseMemoryCollection,
    GraphMemoryCollection,
    KVMemoryCollection,
    SimpleGraphIndex,
    VDBMemoryCollection,
)

# Export core components from neuromem sub-project
from .neuromem.memory_manager import MemoryManager

# Export services from neuromem sub-project
from .neuromem.services import BaseMemoryService, MemoryServiceRegistry, NeuromemServiceFactory

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
