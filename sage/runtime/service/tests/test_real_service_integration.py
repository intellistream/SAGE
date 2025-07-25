"""
完整的服务调用集成测试
使用真实的多进程服务任务和语法糖调用
"""

import time
import threading
import multiprocessing
from concurrent.futures import Future
from typing import Any

from sage.core.function.base_function import BaseFunction
from sage.runtime.service.service_caller import ServiceManager
from sage.runtime.service.local_service_task import LocalServiceTask
from sage.jobmanager.factory.service_factory import ServiceFactory
from sage_utils.mmap_queue.sage_queue import SageQueue


class MockEnvironment:
    """模拟环境"""
    def __init__(self):
        self.env_name = "test_env"


class MockRuntimeContext:
    """模拟运行时上下文"""
    def __init__(self):
        self.logger = None
        self.name = "test_context"
        self.env = MockEnvironment()
        self._service_manager = None
    
    @property
    def service_manager(self):
        if self._service_manager is None:
            self._service_manager = ServiceManager(self.env)
        return self._service_manager


# 测试服务类
class TestCacheService:
    """测试缓存服务"""
    
    def __init__(self, ctx=None):
        self.ctx = ctx
        self.cache = {}
        
    def get(self, key: str) -> str:
        """获取缓存值"""
        result = self.cache.get(key, f"cached_value_for_{key}")
        print(f"CacheService.get({key}) -> {result}")
        return result
    
    def set(self, key: str, value: str) -> bool:
        """设置缓存值"""
        self.cache[key] = value
        print(f"CacheService.set({key}, {value})")
        return True
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        deleted = key in self.cache
        if deleted:
            del self.cache[key]
        print(f"CacheService.delete({key}) -> {deleted}")
        return deleted


class TestDatabaseService:
    """测试数据库服务"""
    
    def __init__(self, ctx=None):
        self.ctx = ctx
        self.data = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"}
        ]
    
    def query(self, sql: str) -> list:
        """执行查询"""
        result = self.data.copy()
        print(f"DatabaseService.query({sql}) -> {len(result)} rows")
        return result
    
    def insert(self, record: dict) -> int:
        """插入记录"""
        new_id = max(item["id"] for item in self.data) + 1
        record["id"] = new_id
        self.data.append(record)
        print(f"DatabaseService.insert({record}) -> {new_id}")
        return new_id


# 测试函数类
class TestFunction(BaseFunction):
    """测试函数类"""
    
    def execute(self, data):
        return data


def run_service_task(service_class, service_name):
    """在单独进程中运行服务任务"""
    try:
        # 创建服务工厂
        service_factory = ServiceFactory(
            service_name=service_name,
            service_class=service_class
        )
        
        # 创建本地服务任务
        ctx = MockRuntimeContext()
        service_task = LocalServiceTask(service_factory, ctx)
        
        print(f"Starting service task: {service_name}")
        
        # 启动服务任务（阻塞运行）
        service_task.run()
        
    except Exception as e:
        print(f"Error in service task {service_name}: {e}")
        import traceback
        traceback.print_exc()


def test_real_service_integration():
    """测试真实的服务集成"""
    print("🚀 Starting real service integration test...")
    
    # 启动缓存服务进程
    cache_process = multiprocessing.Process(
        target=run_service_task,
        args=(TestCacheService, "cache_service"),
        name="CacheServiceProcess"
    )
    
    # 启动数据库服务进程
    db_process = multiprocessing.Process(
        target=run_service_task,
        args=(TestDatabaseService, "database_service"),
        name="DatabaseServiceProcess"
    )
    
    try:
        # 启动服务进程
        cache_process.start()
        db_process.start()
        
        # 等待服务启动
        print("⏱️  Waiting for services to start...")
        time.sleep(2)
        
        # 创建测试函数和上下文
        ctx = MockRuntimeContext()
        test_function = TestFunction()
        test_function.ctx = ctx
        
        print("\n📞 Testing synchronous service calls...")
        
        # 测试同步服务调用
        try:
            # 调用缓存服务
            cache_result = test_function.call_service["cache_service"].get("test_key")
            print(f"✅ Cache get result: {cache_result}")
            
            # 设置缓存
            set_result = test_function.call_service["cache_service"].set("user_123", "Alice")
            print(f"✅ Cache set result: {set_result}")
            
            # 再次获取缓存
            cache_result2 = test_function.call_service["cache_service"].get("user_123")
            print(f"✅ Cache get result after set: {cache_result2}")
            
        except Exception as e:
            print(f"❌ Sync call error: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n📞 Testing asynchronous service calls...")
        
        # 测试异步服务调用
        try:
            # 异步调用数据库服务
            future = test_function.call_service_async["database_service"].query("SELECT * FROM users")
            print(f"✅ Async call started, future: {future}")
            
            # 获取结果
            db_result = future.result(timeout=10.0)
            print(f"✅ Database query result: {db_result}")
            
            # 并发异步调用
            futures = []
            for i in range(3):
                future = test_function.call_service_async["cache_service"].get(f"key_{i}")
                futures.append(future)
            
            # 收集结果
            results = []
            for i, future in enumerate(futures):
                result = future.result(timeout=10.0)
                results.append(result)
                print(f"✅ Concurrent call {i} result: {result}")
            
        except Exception as e:
            print(f"❌ Async call error: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n🎉 Integration test completed!")
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 清理进程
        print("\n🧹 Cleaning up processes...")
        if cache_process.is_alive():
            cache_process.terminate()
            cache_process.join(timeout=5)
        
        if db_process.is_alive():
            db_process.terminate()
            db_process.join(timeout=5)
        
        print("✅ Cleanup completed!")


if __name__ == "__main__":
    # 设置多进程启动方法
    multiprocessing.set_start_method('spawn', force=True)
    
    # 运行测试
    test_real_service_integration()
