"""
SAGE 微服务架构
提供解耦的KV、VDB和Memory编排服务，集成到SAGE DAG中
"""

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

# CLI模块在需要时导入
def get_cli():
    """获取CLI应用"""
    try:
        from sage.kernel.cli.main import app
        return app
    except ImportError as e:
        print(f"CLI dependencies not installed: {e}")
        print("Run: python sage/cli/setup.py")
        return None
