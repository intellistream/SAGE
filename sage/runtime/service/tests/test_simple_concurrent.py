# """
# 简化的并发测试：验证并发服务调用不冲突
# """

# import threading
# import time
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


# def test_concurrent_service_calls():
#     """测试并发服务调用"""
#     print("Testing concurrent service calls...")
    
#     num_threads = 3
#     calls_per_thread = 5
#     results = []
#     results_lock = threading.Lock()
    
#     def worker_function(worker_id):
#         """工作线程函数"""
#         try:
#             # 每个线程创建自己的function实例
#             func = TestFunction()
#             func.ctx = MockRuntimeContext(f"context_{worker_id}")
            
#             thread_results = []
            
#             for call_id in range(calls_per_thread):
#                 # 获取代理对象
#                 sync_proxy = func.call_service["test_service"]
#                 async_proxy = func.call_service_async["test_service"]
                
#                 thread_results.append({
#                     'worker_id': worker_id,
#                     'call_id': call_id,
#                     'sync_proxy_id': id(sync_proxy),
#                     'async_proxy_id': id(async_proxy),
#                     'thread_id': threading.current_thread().ident
#                 })
                
#                 # 小延迟模拟实际工作
#                 time.sleep(0.001)
            
#             # 安全地添加到全局结果
#             with results_lock:
#                 results.extend(thread_results)
#                 print(f"Worker {worker_id} completed {len(thread_results)} calls")
                
#         except Exception as e:
#             with results_lock:
#                 print(f"Worker {worker_id} failed with error: {e}")
#                 import traceback
#                 traceback.print_exc()
    
#     # 启动工作线程
#     threads = []
#     for i in range(num_threads):
#         thread = threading.Thread(target=worker_function, args=(i,))
#         threads.append(thread)
#         thread.start()
    
#     # 等待所有线程完成
#     for thread in threads:
#         thread.join()
    
#     # 分析结果
#     print(f"\n=== Results Analysis ===")
#     print(f"Total results collected: {len(results)}")
#     print(f"Expected results: {num_threads * calls_per_thread}")
    
#     if len(results) != num_threads * calls_per_thread:
#         print("❌ Not all calls completed successfully!")
#         return False
    
#     # 检查代理对象唯一性
#     all_sync_proxy_ids = set()
#     all_async_proxy_ids = set()
    
#     for result in results:
#         all_sync_proxy_ids.add(result['sync_proxy_id'])
#         all_async_proxy_ids.add(result['async_proxy_id'])
    
#     expected_unique_proxies = num_threads * calls_per_thread
    
#     print(f"Unique sync proxy IDs: {len(all_sync_proxy_ids)}")
#     print(f"Unique async proxy IDs: {len(all_async_proxy_ids)}")
#     print(f"Expected unique proxies: {expected_unique_proxies}")
    
#     sync_unique = len(all_sync_proxy_ids) == expected_unique_proxies
#     async_unique = len(all_async_proxy_ids) == expected_unique_proxies
    
#     if sync_unique and async_unique:
#         print("✅ All proxy objects are unique - no concurrency conflicts!")
#         return True
#     else:
#         print("❌ Some proxy objects were reused - concurrency issue detected!")
        
#         # 详细分析
#         if not sync_unique:
#             print(f"  Sync proxies: expected {expected_unique_proxies}, got {len(all_sync_proxy_ids)}")
#         if not async_unique:
#             print(f"  Async proxies: expected {expected_unique_proxies}, got {len(all_async_proxy_ids)}")
        
#         return False


# def test_single_function_multiple_calls():
#     """测试单个function实例的多次调用"""
#     print("\nTesting single function multiple calls...")
    
#     func = TestFunction()
#     func.ctx = MockRuntimeContext("single_context")
    
#     sync_proxies = []
#     async_proxies = []
    
#     # 多次调用
#     for i in range(10):
#         sync_proxies.append(func.call_service["test_service"])
#         async_proxies.append(func.call_service_async["test_service"])
    
#     # 检查唯一性
#     sync_ids = set(id(proxy) for proxy in sync_proxies)
#     async_ids = set(id(proxy) for proxy in async_proxies)
    
#     print(f"Sync proxy calls: {len(sync_proxies)}, unique IDs: {len(sync_ids)}")
#     print(f"Async proxy calls: {len(async_proxies)}, unique IDs: {len(async_ids)}")
    
#     if len(sync_ids) == len(sync_proxies) and len(async_ids) == len(async_proxies):
#         print("✅ Single function multiple calls - all unique!")
#         return True
#     else:
#         print("❌ Single function multiple calls - some reuse detected!")
#         return False


# if __name__ == "__main__":
#     print("Running simplified concurrent service call tests...\n")
    
#     # 测试1：单个function的多次调用
#     test1_success = test_single_function_multiple_calls()
    
#     # 测试2：并发调用
#     test2_success = test_concurrent_service_calls()
    
#     print(f"\n=== Final Results ===")
#     print(f"Single function test: {'✅ PASS' if test1_success else '❌ FAIL'}")
#     print(f"Concurrent test: {'✅ PASS' if test2_success else '❌ FAIL'}")
    
#     if test1_success and test2_success:
#         print("\n🎉 All tests passed! Service call concurrency is working correctly.")
#         sys.exit(0)
#     else:
#         print("\n❌ Some tests failed.")
#         sys.exit(1)
