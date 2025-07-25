"""
集成测试：使用真实的多进程服务任务测试语法糖调用
"""

import time
import threading
import unittest
from unittest.mock import Mock
from sage_runtime.runtime_context import RuntimeContext
from sage_runtime.service.local_service_task import LocalServiceTask
from sage_runtime.service.service_caller import ServiceManager
from sage.core.function.base_function import BaseFunction
from sage.jobmanager.factory.service_factory import ServiceFactory


# 创建Mock对象来初始化RuntimeContext
class MockGraphNode:
    def __init__(self, name: str):
        self.name = name
        self.parallel_index = 0
        self.parallelism = 1
        self.stop_signal_num = 1


class MockTransformation:
    def __init__(self):
        self.is_spout = False
        self.memory_collection = None


class MockEnvironment:
    def __init__(self, name: str):
        self.name = name
        self.env_base_dir = "/tmp/sage_test"
        self.uuid = "test-uuid"
        self.console_log_level = "INFO"


# 测试用的服务类
class TestCacheService:
    def __init__(self):
        self.cache_data = {}
    
    def get(self, key: str):
        return self.cache_data.get(key, f"default_value_for_{key}")
    
    def set(self, key: str, value: str):
        self.cache_data[key] = value
        return f"Set {key} = {value}"
    
    def delete(self, key: str):
        if key in self.cache_data:
            del self.cache_data[key]
            return f"Deleted {key}"
        return f"Key {key} not found"


class TestDatabaseService:
    def __init__(self):
        self.users = [
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"}
        ]
    
    def query(self, sql: str):
        if "SELECT" in sql.upper():
            return self.users
        return f"Executed: {sql}"
    
    def insert(self, table: str, data: dict):
        if table == "users":
            new_id = len(self.users) + 1
            user = {"id": new_id, **data}
            self.users.append(user)
            return user
        return f"Inserted into {table}: {data}"


# 测试用的Function类
class TestFunction(BaseFunction):
    def execute(self, data):
        return data


def test_integrated_service_call():
    """集成测试：真实的服务调用"""
    print("🚀 Starting integrated service call test...")
    
    try:
        # 1. 创建运行时上下文
        cache_graph_node = MockGraphNode("cache_service")
        cache_transformation = MockTransformation()
        cache_env = MockEnvironment("test_env")
        cache_ctx = RuntimeContext(cache_graph_node, cache_transformation, cache_env)
        
        db_graph_node = MockGraphNode("db_service")
        db_transformation = MockTransformation()
        db_env = MockEnvironment("test_env")
        db_ctx = RuntimeContext(db_graph_node, db_transformation, db_env)
        
        test_graph_node = MockGraphNode("test_function")
        test_transformation = MockTransformation()
        test_env = MockEnvironment("test_env")
        test_ctx = RuntimeContext(test_graph_node, test_transformation, test_env)
        
        # 2. 创建服务工厂
        cache_factory = ServiceFactory("cache_service", TestCacheService)
        db_factory = ServiceFactory("db_service", TestDatabaseService)
        
        # 3. 创建服务任务
        cache_task = LocalServiceTask(cache_factory, cache_ctx)
        db_task = LocalServiceTask(db_factory, db_ctx)
        
        # 4. 启动服务任务
        cache_task.start_running()
        db_task.start_running()
        
        # 等待服务启动
        time.sleep(2.0)
        
        # 5. 创建测试函数并设置上下文
        test_func = TestFunction()
        test_func.ctx = test_ctx
        
        print("✅ Services started, testing synchronous calls...")
        
        # 6. 测试同步服务调用
        
        # 测试缓存服务
        result1 = test_func.call_service["cache_service"].get("user_123")
        print(f"Cache get result: {result1}")
        
        result2 = test_func.call_service["cache_service"].set("user_123", "Alice")
        print(f"Cache set result: {result2}")
        
        result3 = test_func.call_service["cache_service"].get("user_123")
        print(f"Cache get after set: {result3}")
        
        # 测试数据库服务
        result4 = test_func.call_service["db_service"].query("SELECT * FROM users")
        print(f"DB query result: {result4}")
        
        result5 = test_func.call_service["db_service"].insert("users", {"name": "Charlie", "email": "charlie@example.com"})
        print(f"DB insert result: {result5}")
        
        print("✅ Synchronous calls completed, testing asynchronous calls...")
        
        # 7. 测试异步服务调用
        
        # 异步缓存调用
        future1 = test_func.call_service_async["cache_service"].get("async_key")
        future2 = test_func.call_service_async["cache_service"].set("async_key", "async_value")
        
        # 异步数据库调用
        future3 = test_func.call_service_async["db_service"].query("SELECT COUNT(*) FROM users")
        
        # 等待结果
        async_result1 = future1.result(timeout=10.0)
        async_result2 = future2.result(timeout=10.0)
        async_result3 = future3.result(timeout=10.0)
        
        print(f"Async cache get: {async_result1}")
        print(f"Async cache set: {async_result2}")
        print(f"Async DB query: {async_result3}")
        
        print("✅ Asynchronous calls completed!")
        
        # 8. 测试并发异步调用
        print("🔄 Testing concurrent async calls...")
        
        futures = []
        for i in range(5):
            future = test_func.call_service_async["cache_service"].set(f"concurrent_key_{i}", f"value_{i}")
            futures.append(future)
        
        # 等待所有并发调用完成
        results = []
        for i, future in enumerate(futures):
            result = future.result(timeout=10.0)
            results.append(result)
            print(f"Concurrent call {i}: {result}")
        
        print("✅ Concurrent async calls completed!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # 清理资源
        try:
            if 'cache_task' in locals():
                cache_task.stop()
            if 'db_task' in locals():
                db_task.stop()
            print("🧹 Cleanup completed")
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("SAGE Service Call Integration Test")
    print("=" * 60)
    
    success = test_integrated_service_call()
    
    if success:
        print("\n🎉 All tests passed! Service call system is working correctly.")
    else:
        print("\n💥 Tests failed! Please check the logs above.")
        exit(1)
