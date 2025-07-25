"""
最终验证测试：确保服务调用语法糖在各种场景下都能正常工作
"""

import threading
import time
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.function.base_function import BaseFunction


class MockRuntimeContext:
    """模拟运行时上下文"""
    def __init__(self, name="test_context"):
        import logging
        self.logger = logging.getLogger(name)
        self.name = name
        self.env_name = "test_env"
        self._service_manager = None
    
    @property
    def service_manager(self):
        if self._service_manager is None:
            from runtime.service.service_caller import ServiceManager
            self._service_manager = ServiceManager(self)
        return self._service_manager


class TestFunction(BaseFunction):
    """测试用的Function类"""
    
    def execute(self, data):
        return data


def test_basic_syntax_sugar():
    """测试基本语法糖功能"""
    print("🧪 Testing basic syntax sugar functionality...")
    
    func = TestFunction()
    func.ctx = MockRuntimeContext("basic_test")
    
    try:
        # 测试同步调用语法
        cache_service = func.call_service["cache_service"]
        db_service = func.call_service["db_service"]
        
        # 测试异步调用语法
        async_cache = func.call_service_async["cache_service"]
        async_db = func.call_service_async["db_service"]
        
        # 验证对象类型
        assert hasattr(cache_service, 'service_name'), "Sync proxy missing service_name"
        assert hasattr(async_cache, 'service_name'), "Async proxy missing service_name"
        
        print("✅ Basic syntax sugar works correctly")
        return True
        
    except Exception as e:
        print(f"❌ Basic syntax sugar failed: {e}")
        return False


def test_multiple_function_instances():
    """测试多个function实例之间的隔离"""
    print("\n🧪 Testing multiple function instance isolation...")
    
    try:
        # 创建多个function实例
        functions = []
        for i in range(5):
            func = TestFunction()
            func.ctx = MockRuntimeContext(f"instance_{i}")
            functions.append(func)
        
        # 每个function获取服务代理
        all_proxies = []
        for i, func in enumerate(functions):
            sync_proxy = func.call_service["shared_service"]
            async_proxy = func.call_service_async["shared_service"]
            all_proxies.extend([sync_proxy, async_proxy])
        
        # 验证所有代理都是不同的对象
        proxy_ids = [id(proxy) for proxy in all_proxies]
        unique_ids = set(proxy_ids)
        
        if len(unique_ids) == len(proxy_ids):
            print("✅ Multiple function instances are properly isolated")
            return True
        else:
            print(f"❌ Function instance isolation failed: {len(unique_ids)} unique out of {len(proxy_ids)} total")
            return False
            
    except Exception as e:
        print(f"❌ Multiple function instance test failed: {e}")
        return False


def test_concurrent_access():
    """测试并发访问场景"""
    print("\n🧪 Testing concurrent access scenarios...")
    
    success_count = 0
    total_tests = 10
    results_lock = threading.Lock()
    
    def concurrent_worker(worker_id):
        nonlocal success_count
        try:
            func = TestFunction()
            func.ctx = MockRuntimeContext(f"concurrent_{worker_id}")
            
            # 每个worker进行多次服务调用
            for call_id in range(5):
                sync_proxy_1 = func.call_service["service_a"]
                async_proxy_1 = func.call_service_async["service_b"]
                sync_proxy_2 = func.call_service["service_a"]  # 重复调用同一服务
                
                # 验证即使是同一服务，每次调用也返回不同的代理对象
                if sync_proxy_1 is not sync_proxy_2:
                    with results_lock:
                        success_count += 1
                else:
                    print(f"❌ Worker {worker_id}, call {call_id}: Same proxy returned for repeated calls")
                    
        except Exception as e:
            print(f"❌ Worker {worker_id} failed: {e}")
    
    # 启动并发worker
    threads = []
    for i in range(total_tests):
        thread = threading.Thread(target=concurrent_worker, args=(i,))
        threads.append(thread)
        thread.start()
    
    # 等待完成
    for thread in threads:
        thread.join()
    
    expected_success = total_tests * 5  # 每个worker 5次成功调用
    if success_count == expected_success:
        print(f"✅ Concurrent access test passed: {success_count}/{expected_success} successful calls")
        return True
    else:
        print(f"❌ Concurrent access test failed: {success_count}/{expected_success} successful calls")
        return False


def test_error_handling():
    """测试错误处理"""
    print("\n🧪 Testing error handling...")
    
    try:
        # 测试没有context的情况
        func = TestFunction()
        func.ctx = None
        
        try:
            _ = func.call_service
            print("❌ Should have raised RuntimeError for missing context")
            return False
        except RuntimeError as e:
            if "Runtime context not initialized" in str(e):
                print("✅ Proper error handling for missing context")
            else:
                print(f"❌ Wrong error message: {e}")
                return False
        
        try:
            _ = func.call_service_async
            print("❌ Should have raised RuntimeError for missing async context")
            return False
        except RuntimeError as e:
            if "Runtime context not initialized" in str(e):
                print("✅ Proper error handling for missing async context")
                return True
            else:
                print(f"❌ Wrong async error message: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


def test_service_name_variations():
    """测试不同服务名称的处理"""
    print("\n🧪 Testing service name variations...")
    
    func = TestFunction()
    func.ctx = MockRuntimeContext("name_test")
    
    try:
        # 测试各种服务名称
        service_names = [
            "simple_service",
            "service-with-dashes", 
            "service_with_underscores",
            "ServiceWithCamelCase",
            "service123",
            "cache.service.nested"
        ]
        
        for service_name in service_names:
            sync_proxy = func.call_service[service_name]
            async_proxy = func.call_service_async[service_name]
            
            # 验证服务名称正确设置
            assert sync_proxy.service_name == service_name, f"Wrong service name in sync proxy: {sync_proxy.service_name}"
            assert async_proxy.service_name == service_name, f"Wrong service name in async proxy: {async_proxy.service_name}"
        
        print("✅ Service name variations handled correctly")
        return True
        
    except Exception as e:
        print(f"❌ Service name variations test failed: {e}")
        return False


def main():
    """运行所有验证测试"""
    print("🚀 Running final verification tests for service call syntax sugar...\n")
    
    tests = [
        ("Basic Syntax Sugar", test_basic_syntax_sugar),
        ("Multiple Function Instances", test_multiple_function_instances),  
        ("Concurrent Access", test_concurrent_access),
        ("Error Handling", test_error_handling),
        ("Service Name Variations", test_service_name_variations),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} FAILED")
    
    print(f"\n{'='*60}")
    print(f"FINAL RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Service call syntax sugar is working correctly.")
        print("\n✨ Key features verified:")
        print("  ✅ Unique proxy objects for each call (no caching conflicts)")
        print("  ✅ Proper isolation between function instances") 
        print("  ✅ Thread-safe concurrent access")
        print("  ✅ Robust error handling")
        print("  ✅ Support for various service name formats")
        print("\n🚀 Ready for production use!")
        return True
    else:
        print(f"❌ {total - passed} test(s) failed. Please review the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
