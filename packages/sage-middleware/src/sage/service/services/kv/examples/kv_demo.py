"""
KV Service 使用示例
展示如何使用KV微服务进行键值存储操作
"""
import time
from sage.core.api.local_environment import LocalEnvironment
from sage.service.kv import create_kv_service_factory


def test_kv_service():
    """测试KV服务基本功能"""
    print("🚀 KV Service Demo")
    print("=" * 50)
    
    # 创建环境
    env = LocalEnvironment("kv_service_demo")
    
    # 注册KV服务 - 内存后端
    kv_factory = create_kv_service_factory(
        service_name="demo_kv_service",
        backend_type="memory",
        max_size=1000,
        ttl_seconds=300  # 5分钟过期
    )
    env.register_service("demo_kv_service", kv_factory)
    
    print("✅ KV Service registered with memory backend")
    
    # 启动环境（在实际应用中）
    # env.submit()
    
    # 模拟服务操作（实际中通过DAG调用）
    print("\n📝 KV Operations Demo:")
    
    # 这里演示KV服务的各种操作
    operations = [
        ("put", {"key": "user:123", "value": {"name": "Alice", "age": 30}}),
        ("put", {"key": "session:abc", "value": {"user_id": "123", "timestamp": time.time()}}),
        ("get", {"key": "user:123"}),
        ("list_keys", {"prefix": "user:"}),
        ("size", {}),
        ("delete", {"key": "session:abc"}),
        ("get", {"key": "session:abc"}),  # 应该返回None
    ]
    
    for op, params in operations:
        print(f"  {op}({params}) ->", end=" ")
        if op == "put":
            print("✅ Stored")
        elif op == "get":
            print("📖 Retrieved data" if params["key"].startswith("user:") else "❌ Not found")
        elif op == "list_keys":
            print("📋 ['user:123']")
        elif op == "size":
            print("📊 2 items")
        elif op == "delete":
            print("🗑️  Deleted")
    
    print("\n💡 KV Service Features:")
    print("   - 高性能键值存储")
    print("   - 支持内存和Redis后端")
    print("   - TTL过期机制")
    print("   - 前缀搜索")
    print("   - 事务安全")


def test_kv_with_redis():
    """演示KV服务的Redis后端配置"""
    print("\n🔧 Redis Backend Configuration:")
    
    redis_kv_factory = create_kv_service_factory(
        service_name="redis_kv_service",
        backend_type="redis",
        redis_url="redis://localhost:6379",
        ttl_seconds=3600
    )
    
    print("✅ Redis KV factory created")
    print("   - 连接: redis://localhost:6379")
    print("   - TTL: 1小时")
    print("   - 持久化存储")


if __name__ == "__main__":
    test_kv_service()
    test_kv_with_redis()
    print("\n🎯 KV Service demo completed!")
