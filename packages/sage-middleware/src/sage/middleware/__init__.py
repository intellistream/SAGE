"""
SAGE Middleware Framework

This module provides middleware components including API services, database
integrations, and messaging infrastructure.
"""

__version__ = "1.0.1"

# Core middleware components
try:
    from .api import *
except ImportError:
    pass

try:
    from .services import *
except ImportError:
    pass

try:
    from .utils import *
except ImportError:
    pass

# Enterprise features (if available and licensed)
try:
    from .enterprise import *
except ImportError:
    # Enterprise features not available or not licensed
    pass

__all__ = [
    "__version__",
]

__version__ = "2.0.0"
__author__ = "SAGE Team"
__description__ = "SAGE Microservices as Service Tasks"

# 微服务组件 - 基于BaseServiceTask的服务任务
try:
    # KV服务
    from .services.kv.kv_service import KVService, create_kv_service_factory
    
    # VDB服务
    from .services.vdb.vdb_service import VDBService, create_vdb_service_factory
    
    # Memory服务
    from .services.memory.memory_service import MemoryService, create_memory_service_factory
    
    # Graph服务
    from .services.graph.graph_service import GraphService, create_graph_service_factory

    __all__ = [
        # 服务任务类
        "KVService",
        "VDBService", 
        "MemoryService",
        "GraphService",
        
        # 工厂函数
        "create_kv_service_factory",
        "create_vdb_service_factory",
        "create_memory_service_factory",
        "create_graph_service_factory"
    ]
    
except ImportError as e:
    print(f"⚠️ Microservices components not available: {e}")
    print("Some dependencies may be missing for the new microservices architecture")
    __all__ = []

# 兼容性：保留原有的memory service导入
try:
    from .services.memory.memory_service import MemoryService as LegacyMemoryService
    
    # 添加到导出列表
    if 'LegacyMemoryService' not in locals().get('__all__', []):
        __all__.extend(['LegacyMemoryService'])
        
except ImportError:
    pass