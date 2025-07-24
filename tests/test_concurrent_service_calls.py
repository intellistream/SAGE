"""
测试并发服务调用
验证多个function实例并发调用服务时不会冲突
"""

import time
import threading
import unittest
from unittest.mock import Mock, patch
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sage_core.function.base_function import BaseFunction


class MockRuntimeContext:
    """模拟运行时上下文"""
    def __init__(self, name="test_context"):
        self.logger = Mock()
        self.name = name
        self.env_name = "test_env"
        self._service_manager = None
    
    @property
    def service_manager(self):
        if self._service_manager is None:
            from sage_runtime.service.service_caller import ServiceManager
            self._service_manager = ServiceManager(self)
        return self._service_manager


class TestConcurrentFunction(BaseFunction):
    """测试用的Function类"""
    
    def __init__(self, function_id):
        super().__init__()
        self.function_id = function_id
        self.results = []
        
    def execute(self, data):
        return data


class TestConcurrentServiceCalls(unittest.TestCase):
    """测试并发服务调用"""
    
    def setUp(self):
        """设置测试环境"""
        self.num_functions = 5
        self.num_calls_per_function = 10
        
    def test_concurrent_sync_service_calls(self):
        """测试并发同步服务调用"""
        
        # 创建多个Function实例
        functions = []
        for i in range(self.num_functions):
            func = TestConcurrentFunction(f"func_{i}")
            func.ctx = MockRuntimeContext(f"context_{i}")
            functions.append(func)
        
        # 记录所有调用结果
        all_results = []
        lock = threading.Lock()
        
        def make_service_calls(func):
            """每个function进行多次服务调用"""
            try:
                for call_id in range(self.num_calls_per_function):
                    # 测试不同的服务调用语法
                    service_proxy_1 = func.call_service["cache_service"]
                    service_proxy_2 = func.call_service["db_service"] 
                    service_proxy_3 = func.call_service["cache_service"]  # 再次调用相同服务
                    
                    # 验证每次调用都得到新的代理对象
                    self.assertIsNot(service_proxy_1, service_proxy_2)
                    self.assertIsNot(service_proxy_1, service_proxy_3)
                    
                    with lock:
                        all_results.append({
                            'function_id': func.function_id,
                            'call_id': call_id,
                            'proxy_1_id': id(service_proxy_1),
                            'proxy_2_id': id(service_proxy_2),
                            'proxy_3_id': id(service_proxy_3),
                            'thread_id': threading.current_thread().ident,
                            'success': True
                        })
                        
            except Exception as e:
                with lock:
                    all_results.append({
                        'function_id': func.function_id,
                        'error': str(e),
                        'thread_id': threading.current_thread().ident,
                        'success': False
                    })
        
        # 创建并启动线程
        threads = []
        for func in functions:
            thread = threading.Thread(target=make_service_calls, args=(func,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证结果
        successful_results = [r for r in all_results if r.get('success', False)]
        failed_results = [r for r in all_results if not r.get('success', True)]
        
        if failed_results:
            print(f"Failed results: {failed_results}")
            
        self.assertEqual(len(successful_results), self.num_functions * self.num_calls_per_function,
                        f"Expected {self.num_functions * self.num_calls_per_function} successful calls, got {len(successful_results)}")
        
        # 验证所有代理对象ID都不同（确保每次都创建新对象）
        all_proxy_ids = set()
        for result in successful_results:
            all_proxy_ids.add(result['proxy_1_id'])
            all_proxy_ids.add(result['proxy_2_id'])
            all_proxy_ids.add(result['proxy_3_id'])
        
        # 期望的唯一代理对象数量 = functions数量 * 每个function的调用次数 * 每次调用创建的代理数量
        expected_unique_proxies = self.num_functions * self.num_calls_per_function * 3
        self.assertEqual(len(all_proxy_ids), expected_unique_proxies, 
                        f"Expected {expected_unique_proxies} unique proxy objects, got {len(all_proxy_ids)}")
        
        print(f"✓ Successfully created {len(all_proxy_ids)} unique proxy objects across {len(threads)} concurrent threads")
    
    def test_concurrent_async_service_calls(self):
        """测试并发异步服务调用"""
        
        # 创建多个Function实例
        functions = []
        for i in range(self.num_functions):
            func = TestConcurrentFunction(f"async_func_{i}")
            func.ctx = MockRuntimeContext(f"async_context_{i}")
            functions.append(func)
        
        # 记录所有调用结果
        all_results = []
        lock = threading.Lock()
        
        def make_async_service_calls(func):
            """每个function进行多次异步服务调用"""
            try:
                for call_id in range(self.num_calls_per_function):
                    # 测试不同的异步服务调用语法
                    async_proxy_1 = func.call_service_async["cache_service"]
                    async_proxy_2 = func.call_service_async["db_service"]
                    async_proxy_3 = func.call_service_async["cache_service"]  # 再次调用相同服务
                    
                    # 验证每次调用都得到新的代理对象
                    self.assertIsNot(async_proxy_1, async_proxy_2)
                    self.assertIsNot(async_proxy_1, async_proxy_3)
                    
                    with lock:
                        all_results.append({
                            'function_id': func.function_id,
                            'call_id': call_id,
                            'async_proxy_1_id': id(async_proxy_1),
                            'async_proxy_2_id': id(async_proxy_2),
                            'async_proxy_3_id': id(async_proxy_3),
                            'thread_id': threading.current_thread().ident,
                            'success': True
                        })
                        
            except Exception as e:
                with lock:
                    all_results.append({
                        'function_id': func.function_id,
                        'error': str(e),
                        'thread_id': threading.current_thread().ident,
                        'success': False
                    })
        
        # 创建并启动线程
        threads = []
        for func in functions:
            thread = threading.Thread(target=make_async_service_calls, args=(func,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证结果
        successful_results = [r for r in all_results if r.get('success', False)]
        failed_results = [r for r in all_results if not r.get('success', True)]
        
        if failed_results:
            print(f"Failed async results: {failed_results}")
            
        self.assertEqual(len(successful_results), self.num_functions * self.num_calls_per_function,
                        f"Expected {self.num_functions * self.num_calls_per_function} successful async calls, got {len(successful_results)}")
        
        # 验证所有代理对象ID都不同
        all_async_proxy_ids = set()
        for result in successful_results:
            all_async_proxy_ids.add(result['async_proxy_1_id'])
            all_async_proxy_ids.add(result['async_proxy_2_id'])
            all_async_proxy_ids.add(result['async_proxy_3_id'])
        
        expected_unique_async_proxies = self.num_functions * self.num_calls_per_function * 3
        self.assertEqual(len(all_async_proxy_ids), expected_unique_async_proxies,
                        f"Expected {expected_unique_async_proxies} unique async proxy objects, got {len(all_async_proxy_ids)}")
        
        print(f"✓ Successfully created {len(all_async_proxy_ids)} unique async proxy objects across {len(threads)} concurrent threads")
    
    def test_mixed_sync_async_concurrent_calls(self):
        """测试混合同步和异步并发调用"""
        
        functions = []
        for i in range(3):
            func = TestConcurrentFunction(f"mixed_func_{i}")
            func.ctx = MockRuntimeContext(f"mixed_context_{i}")
            functions.append(func)
        
        all_results = []
        lock = threading.Lock()
        
        def make_mixed_calls(func):
            """混合使用同步和异步调用"""
            try:
                for call_id in range(5):
                    # 交替使用同步和异步调用
                    if call_id % 2 == 0:
                        proxy = func.call_service["test_service"]
                        call_type = "sync"
                    else:
                        proxy = func.call_service_async["test_service"] 
                        call_type = "async"
                    
                    with lock:
                        all_results.append({
                            'function_id': func.function_id,
                            'call_id': call_id,
                            'call_type': call_type,
                            'proxy_id': id(proxy),
                            'thread_id': threading.current_thread().ident
                        })
                        
            except Exception as e:
                with lock:
                    all_results.append({
                        'function_id': func.function_id,
                        'error': str(e),
                        'thread_id': threading.current_thread().ident
                    })
        
        # 启动并发线程
        threads = []
        for func in functions:
            thread = threading.Thread(target=make_mixed_calls, args=(func,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 验证结果
        self.assertEqual(len(all_results), 3 * 5)  # 3个functions * 5次调用
        
        errors = [r for r in all_results if 'error' in r]
        if errors:
            self.fail(f"Found errors in mixed concurrent calls: {errors}")
        
        # 验证同步和异步调用都正常工作
        sync_calls = [r for r in all_results if r.get('call_type') == 'sync']
        async_calls = [r for r in all_results if r.get('call_type') == 'async']
        
        self.assertGreater(len(sync_calls), 0, "Should have sync calls")
        self.assertGreater(len(async_calls), 0, "Should have async calls")
        
        # 验证所有代理对象都是唯一的
        all_proxy_ids = {r['proxy_id'] for r in all_results if 'proxy_id' in r}
        self.assertEqual(len(all_proxy_ids), len(all_results), 
                        "All proxy objects should be unique")
        
        print(f"✓ Successfully executed {len(sync_calls)} sync and {len(async_calls)} async calls with unique proxies")


if __name__ == "__main__":
    print("Running concurrent service call tests...")
    unittest.main(verbosity=2)
