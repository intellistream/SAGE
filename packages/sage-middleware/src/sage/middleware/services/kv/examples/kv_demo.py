"""
from sage.common.utils.logging.custom_logger import CustomLogger
KV Service API 使用示例
展示如何正确使用KV微服务的API接口
"""

import time

from sage.core.api.local_environment import LocalEnvironment
from sage.middleware.api.kv_api import KVServiceAPI
from sage.middleware.services import create_kv_service_factory


def test_kv_service_api():
    """测试KV服务API的正确使用方式"""
    self.logger.info("🚀 KV Service API Demo")
    self.logger.info("=" * 50)

    # 创建环境
    env = LocalEnvironment("kv_service_demo")

    # 注册KV服务 - 内存后端
    kv_factory = create_kv_service_factory(
        service_name="demo_kv_service",
        backend_type="memory",
        max_size=1000,
        ttl_seconds=300,  # 5分钟过期
    )
    env.register_service_factory("demo_kv_service", kv_factory)

    self.logger.info("✅ KV Service registered with memory backend")

    # 在实际应用中，你需要启动环境并获取服务代理
    # env.submit()  # 启动环境
    # kv_service = env.get_service_proxy("demo_kv_service")

    # 这里我们演示API接口的预期使用方式
    demonstrate_kv_api_usage()


def demonstrate_kv_api_usage():
    """演示KV服务API的标准使用模式"""
    self.logger.info("\n📝 KV Service API Usage Patterns:")
    self.logger.info("-" * 40)

    # 展示API接口
    self.logger.info("💡 KV Service API Interface:")
    self.logger.info("   class KVServiceAPI:")
    self.logger.info("     - put(key: str, value: Any) -> bool")
    self.logger.info("     - get(key: str) -> Optional[Any]")
    self.logger.info("     - delete(key: str) -> bool")
    self.logger.info("     - exists(key: str) -> bool")
    self.logger.info("     - list_keys(prefix: Optional[str] = None) -> List[str]")
    self.logger.info("     - size() -> int")
    self.logger.info("     - clear() -> bool")

    self.logger.info("\n📋 Standard Usage Example:")
    usage_code = """
# 1. 获取服务代理
kv_service = env.get_service_proxy("demo_kv_service")

# 2. 基本CRUD操作
# 存储数据
success = kv_service.put("user:123", {
    "name": "Alice", 
    "age": 30, 
    "email": "alice@example.com"
})

# 读取数据
user_data = kv_service.get("user:123")
exists = kv_service.exists("user:123")

# 3. 批量操作
# 存储会话数据
session_data = {
    "user_id": "123",
    "timestamp": time.time(),
    "activity": "browsing_products"
}
kv_service.put("session:abc", session_data)

# 列出所有用户相关的键
user_keys = kv_service.list_keys("user:")
session_keys = kv_service.list_keys("session:")

# 4. 管理操作
total_items = kv_service.size()
cleanup_success = kv_service.delete("session:abc")

# 5. 错误处理
try:
    result = kv_service.get("non_existent_key")
    if result is None:
        self.logger.info("Key not found")
except Exception as e:
    self.logger.info(f"Error accessing KV service: {e}")
"""
    self.logger.info(usage_code)

    # 模拟执行结果
    self.logger.info("🎯 Expected Results:")
    operations = [
        ("put('user:123', user_data)", "True"),
        ("get('user:123')", "{'name': 'Alice', 'age': 30, 'email': '...'}"),
        ("exists('user:123')", "True"),
        ("list_keys('user:')", "['user:123']"),
        ("size()", "2"),
        ("delete('session:abc')", "True"),
        ("get('non_existent_key')", "None"),
    ]

    for operation, result in operations:
        self.logger.info(f"   {operation:<30} -> {result}")


def test_kv_advanced_patterns():
    """演示KV服务的高级使用模式"""
    self.logger.info("\n🔧 Advanced KV Usage Patterns:")
    self.logger.info("-" * 40)

    advanced_patterns = """
# 1. 缓存模式
class UserCache:
    def __init__(self, kv_service: KVServiceAPI):
        self.kv = kv_service
        self.cache_ttl = 300  # 5分钟
    
    def get_user(self, user_id: str):
        cache_key = f"user_cache:{user_id}"
        cached_user = self.kv.get(cache_key)
        
        if cached_user is None:
            # 从数据库加载
            user = load_user_from_db(user_id)
            # 存入缓存
            self.kv.put(cache_key, user)
            return user
        return cached_user

# 2. 分布式锁模式
class DistributedLock:
    def __init__(self, kv_service: KVServiceAPI):
        self.kv = kv_service
    
    def acquire_lock(self, resource_id: str, timeout: int = 30):
        lock_key = f"lock:{resource_id}"
        lock_value = {"acquired_at": time.time(), "timeout": timeout}
        
        if not self.kv.exists(lock_key):
            return self.kv.put(lock_key, lock_value)
        return False
    
    def release_lock(self, resource_id: str):
        lock_key = f"lock:{resource_id}"
        return self.kv.delete(lock_key)

# 3. 配置管理模式
class ConfigManager:
    def __init__(self, kv_service: KVServiceAPI):
        self.kv = kv_service
        self.config_prefix = "config:"
    
    def get_config(self, key: str, default=None):
        config_key = f"{self.config_prefix}{key}"
        value = self.kv.get(config_key)
        return value if value is not None else default
    
    def set_config(self, key: str, value):
        config_key = f"{self.config_prefix}{key}"
        return self.kv.put(config_key, value)
    
    def list_all_configs(self):
        return self.kv.list_keys(self.config_prefix)
"""
    self.logger.info(advanced_patterns)


def test_kv_with_redis():
    """演示KV服务的Redis后端配置"""
    self.logger.info("\n🔧 Redis Backend Configuration:")

    redis_config_example = """
# Redis后端配置示例
redis_kv_factory = create_kv_service_factory(
    service_name="redis_kv_service",
    backend_type="redis",
    redis_url="redis://localhost:6379",
    redis_db=0,
    connection_pool_size=10,
    ttl_seconds=3600,  # 1小时默认TTL
    max_size=1000000   # 最大键数量
)

# 使用方式完全相同
env.register_service_factory("redis_kv", redis_kv_factory)

# API调用方式不变
redis_kv = env.get_service_proxy("redis_kv")
redis_kv.put("persistent_key", {"data": "stored_in_redis"})
"""

    self.logger.info(redis_config_example)
    self.logger.info("✅ Redis KV factory configuration shown")
    self.logger.info("   - 连接: redis://localhost:6379")
    self.logger.info("   - TTL: 1小时")
    self.logger.info("   - 持久化存储")
    self.logger.info("   - 相同的API接口")


if __name__ == "__main__":
    test_kv_service_api()
    test_kv_advanced_patterns()
    test_kv_with_redis()
    self.logger.info("\n🎯 KV Service API demo completed!")
    self.logger.info("\n📚 Next: Check VDB and Memory service API examples")
