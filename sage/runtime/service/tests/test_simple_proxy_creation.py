# """
# 简单测试：验证每次服务调用是否创建新的代理对象
# """

# import sys
# import os

# # 添加项目根目录到Python路径
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from sage.core.function.base_function import BaseFunction


# class MockRuntimeContext:
#     """模拟运行时上下文"""
#     def __init__(self, name="test_context"):
#         import logging
#         self.logger = logging.getLogger(name)
#         self.name = name
#         self.env_name = "test_env"
#         self._service_manager = None
    
#     @property
#     def service_manager(self):
#         if self._service_manager is None:
#             from sage.runtime.service.service_caller import ServiceManager
#             self._service_manager = ServiceManager(self)
#         return self._service_manager


# class TestFunction(BaseFunction):
#     """测试用的Function类"""
    
#     def execute(self, data):
#         return data


# def test_proxy_creation():
#     """测试代理对象创建"""
#     print("Testing proxy object creation...")
    
#     # 创建function实例
#     func = TestFunction()
#     func.ctx = MockRuntimeContext("test_context")
    
#     # 测试同步代理
#     print("\n=== Testing sync proxies ===")
    
#     # 多次调用同一个服务，应该得到不同的代理对象
#     sync_proxy_1 = func.call_service["test_service"]
#     sync_proxy_2 = func.call_service["test_service"]
#     sync_proxy_3 = func.call_service["test_service"]
    
#     print(f"sync_proxy_1 id: {id(sync_proxy_1)}")
#     print(f"sync_proxy_2 id: {id(sync_proxy_2)}")
#     print(f"sync_proxy_3 id: {id(sync_proxy_3)}")
    
#     print(f"sync_proxy_1 is sync_proxy_2: {sync_proxy_1 is sync_proxy_2}")
#     print(f"sync_proxy_1 is sync_proxy_3: {sync_proxy_1 is sync_proxy_3}")
#     print(f"sync_proxy_2 is sync_proxy_3: {sync_proxy_2 is sync_proxy_3}")
    
#     # 测试不同服务的代理
#     cache_proxy = func.call_service["cache_service"]
#     db_proxy = func.call_service["db_service"]
    
#     print(f"cache_proxy id: {id(cache_proxy)}")
#     print(f"db_proxy id: {id(db_proxy)}")
#     print(f"cache_proxy is db_proxy: {cache_proxy is db_proxy}")
    
#     # 测试异步代理
#     print("\n=== Testing async proxies ===")
    
#     async_proxy_1 = func.call_service_async["test_service"]
#     async_proxy_2 = func.call_service_async["test_service"]
#     async_proxy_3 = func.call_service_async["test_service"]
    
#     print(f"async_proxy_1 id: {id(async_proxy_1)}")
#     print(f"async_proxy_2 id: {id(async_proxy_2)}")
#     print(f"async_proxy_3 id: {id(async_proxy_3)}")
    
#     print(f"async_proxy_1 is async_proxy_2: {async_proxy_1 is async_proxy_2}")
#     print(f"async_proxy_1 is async_proxy_3: {async_proxy_1 is async_proxy_3}")
#     print(f"async_proxy_2 is async_proxy_3: {async_proxy_2 is async_proxy_3}")
    
#     # 测试ServiceManager基本功能
#     print("\n=== Testing ServiceManager basic functionality ===")
    
#     service_manager = func.ctx.service_manager
    
#     # 验证ServiceManager实例
#     from sage.runtime.service.service_caller import ServiceManager
#     assert isinstance(service_manager, ServiceManager), "service_manager should be ServiceManager instance"
    
#     print(f"ServiceManager type: {type(service_manager)}")
#     print(f"ServiceManager id: {id(service_manager)}")
    
#     # 验证所有代理都是唯一的
#     all_proxies = [
#         sync_proxy_1, sync_proxy_2, sync_proxy_3,
#         cache_proxy, db_proxy,
#         async_proxy_1, async_proxy_2, async_proxy_3
#     ]
    
#     unique_ids = set(id(proxy) for proxy in all_proxies)
    
#     print(f"\n=== Summary ===")
#     print(f"Total proxy objects created: {len(all_proxies)}")
#     print(f"Unique proxy IDs: {len(unique_ids)}")
#     print(f"All proxies are unique: {len(unique_ids) == len(all_proxies)}")
    
#     if len(unique_ids) != len(all_proxies):
#         print("❌ Some proxy objects are being reused!")
#         return False
#     else:
#         print("✅ All proxy objects are unique!")
#         return True


# if __name__ == "__main__":
#     success = test_proxy_creation()
#     if not success:
#         sys.exit(1)
