"""
Middleware Services Aggregator
统一导出KV、VDB、Memory、Graph服务与工厂函数，便于示例和外部调用。
"""

# KV Service
from .kv import KVService, create_kv_service_factory

# VDB Service
from .vdb import VDBService, create_vdb_service_factory

# Memory Orchestration Service
from .memory import MemoryService, create_memory_service_factory

# Graph Service
from .graph import GraphService, create_graph_service_factory

__all__ = [
    # 服务类
    "KVService",
    "VDBService",
    "MemoryService",
    "GraphService",
    # 工厂函数
    "create_kv_service_factory",
    "create_vdb_service_factory",
    "create_memory_service_factory",
    "create_graph_service_factory",
]
