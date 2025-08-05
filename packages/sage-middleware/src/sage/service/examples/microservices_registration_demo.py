"""
SAGE 微服务集成示例
展示如何正确注册和使用KV、VDB、Graph和Memory服务
"""
import time
from sage.core.api.local_environment import LocalEnvironment
from sage.service import register_all_services
from sage.service import (
    create_kv_service_factory, 
    create_vdb_service_factory,
    create_graph_service_factory,
    create_memory_service_factory
)


def test_microservices_registration():
    """测试微服务注册"""
    print("🚀 SAGE Microservices Registration Test")
    print("=" * 60)
    
    # 创建环境
    env = LocalEnvironment("sage_microservices_test")
    
    # 方式1: 使用便捷函数注册所有服务
    print("\n📋 Method 1: Register all services using convenience function")
    registered_services = register_all_services(env)
    print(f"Registered services: {list(registered_services.keys())}")
    
    # 方式2: 手动注册单个服务（更灵活的配置）
    print("\n📋 Method 2: Manual registration with custom configuration")
    
    # 创建环境2用于手动注册
    env2 = LocalEnvironment("sage_microservices_manual")
    
    # KV服务 - 使用Redis后端
    kv_factory = create_kv_service_factory(
        service_name="redis_kv_service",
        backend_type="memory",  # 可以改为"redis"
        # redis_url="redis://localhost:6379",
        max_size=50000,
        ttl_seconds=3600
    )
    env2.register_service("redis_kv_service", kv_factory)
    print("   ✅ Registered redis_kv_service")
    
    # VDB服务 - 使用ChromaDB后端
    vdb_factory = create_vdb_service_factory(
        service_name="chroma_vdb_service", 
        backend_type="memory",  # 可以改为"chroma"
        # chroma_host="localhost",
        # chroma_port=8000,
        collection_name="sage_knowledge_base",
        embedding_dimension=768,
        distance_metric="cosine"
    )
    env2.register_service("chroma_vdb_service", vdb_factory)
    print("   ✅ Registered chroma_vdb_service")
    
    # Graph服务 - 支持知识图谱
    graph_factory = create_graph_service_factory(
        service_name="knowledge_graph_service",
        backend_type="memory",  # 可以改为"neo4j"
        # neo4j_uri="bolt://localhost:7687",
        # neo4j_user="neo4j",
        # neo4j_password="password",
        max_nodes=500000,
        max_relationships=2000000
    )
    env2.register_service("knowledge_graph_service", graph_factory)
    print("   ✅ Registered knowledge_graph_service")
    
    # Memory服务 - 协调所有服务
    memory_factory = create_memory_service_factory(
        service_name="unified_memory_service",
        kv_service_name="redis_kv_service",
        vdb_service_name="chroma_vdb_service",
        graph_service_name="knowledge_graph_service",
        default_vector_dimension=768,
        max_search_results=100,
        enable_caching=True,
        enable_knowledge_graph=True
    )
    env2.register_service("unified_memory_service", memory_factory)
    print("   ✅ Registered unified_memory_service")
    
    print("\n🎯 Service registration completed successfully!")
    print("\n💡 Key points:")
    print("   - Services are registered using env.register_service(name, factory)")
    print("   - Service factories are created using create_*_service_factory() functions")
    print("   - Services can be configured with different backends (memory, redis, chroma, neo4j)")
    print("   - Memory service coordinates KV, VDB, and Graph services")
    print("   - Services inherit from BaseServiceTask for SAGE DAG integration")
    
    return env, env2


def demonstrate_service_configuration():
    """展示不同的服务配置选项"""
    print("\n🔧 Service Configuration Options")
    print("=" * 60)
    
    configurations = {
        "Development": {
            "kv": {"backend_type": "memory", "max_size": 10000},
            "vdb": {"backend_type": "memory", "embedding_dimension": 384},
            "graph": {"backend_type": "memory", "max_nodes": 100000},
        },
        "Production": {
            "kv": {"backend_type": "redis", "redis_url": "redis://prod-redis:6379"},
            "vdb": {"backend_type": "chroma", "chroma_host": "prod-chroma", "embedding_dimension": 768},
            "graph": {"backend_type": "neo4j", "neo4j_uri": "bolt://prod-neo4j:7687"},
        },
        "Hybrid": {
            "kv": {"backend_type": "redis", "redis_url": "redis://localhost:6379"},
            "vdb": {"backend_type": "memory", "embedding_dimension": 512}, 
            "graph": {"backend_type": "memory", "max_nodes": 200000},
        }
    }
    
    for config_name, config in configurations.items():
        print(f"\n📊 {config_name} Configuration:")
        print(f"   KV:    {config['kv']}")
        print(f"   VDB:   {config['vdb']}")  
        print(f"   Graph: {config['graph']}")


if __name__ == "__main__":
    env1, env2 = test_microservices_registration()
    demonstrate_service_configuration()
    
    print("\n🏁 Example completed successfully!")
    print("You can now use these environments in your SAGE applications.")
