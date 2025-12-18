"""
Service layer for SAGE-Mem

Pre-defined services that combine neuromem functionality.
All services inherit from sage.platform.service.BaseService and use NeuroMem as backend.
"""

from .graph_memory_service import GraphMemoryService
from .hierarchical_memory_service import HierarchicalMemoryService
from .hybrid_memory_service import HybridMemoryService
from .key_value_memory_service import KeyValueMemoryService
from .memory_service_factory import MemoryServiceFactory
from .neuromem_vdb import NeuroMemVDB
from .neuromem_vdb_service import NeuroMemVDBService
from .parallel_vdb_service import ParallelInsertResult, ParallelVDBService, parallel_insert_to_vdb
from .short_term_memory_service import ShortTermMemoryService
from .vector_memory_service import VectorMemoryService

__all__ = [
    # Service implementations (all inherit from BaseService)
    "NeuroMemVDB",
    "NeuroMemVDBService",
    "ShortTermMemoryService",
    "VectorMemoryService",
    "GraphMemoryService",
    "HierarchicalMemoryService",
    "HybridMemoryService",
    "KeyValueMemoryService",
    "MemoryServiceFactory",
    # Parallel insertion support
    "ParallelVDBService",
    "ParallelInsertResult",
    "parallel_insert_to_vdb",
]
