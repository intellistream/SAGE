"""
SAGE Middleware Framework

This module provides middleware components including API services, database
integrations, and messaging infrastructure.
"""

__version__ = "0.1.4"

# 精简导出，避免 * 导入导致命名冲突
from .services import (
    KVService,
    VDBService,
    MemoryService,
    GraphService,
    create_kv_service_factory,
    create_vdb_service_factory,
    create_memory_service_factory,
    create_graph_service_factory,
)

__all__ = [
    "__version__",
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

__author__ = "SAGE Team"
__description__ = "SAGE Microservices as Service Tasks"

# 兼容性别名（如需要保留历史别名）
LegacyMemoryService = MemoryService