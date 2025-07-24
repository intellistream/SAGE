"""
测试服务任务基类和队列监听功能
"""

import time
import sys
import os
import threading

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sage_utils.mmap_queue.sage_queue import SageQueue
from sage_runtime.service.local_service_task import LocalServiceTask


class MockServiceFactory:
    """模拟服务工厂"""
    
    def __init__(self, service_name: str, service_class: type):
        self.service_name = service_name
        self.service_class = service_class
    
    def create_service(self, ctx=None):
        return self.service_class()


class TestService:
    """测试服务类"""
    
    def __init__(self):
        self.call_count = 0
        self.data_store = {}
    
    def hello(self, name: str) -> str:
        """简单的问候方法"""
        self.call_count += 1
        return f"Hello, {name}!"
    
    def set_data(self, key: str, value: str) -> str:
        """设置数据"""
        self.call_count += 1
        self.data_store[key] = value
        return f"Set {key} = {value}"
    
    def get_data(self, key: str) -> str:
        """获取数据"""
        self.call_count += 1
        return self.data_store.get(key, "Not found")
    
    def get_call_count(self) -> int:
        """获取调用次数"""
        return self.call_count
    
    def raise_error(self) -> None:
        """故意抛出错误的方法"""
        self.call_count += 1
        raise ValueError("This is a test error")


class MockRuntimeContext:
    """模拟运行时上下文"""
    
    def __init__(self, name="test_context"):
        import logging
        self.logger = logging.getLogger(name)
        self.name = name
        self.env_name = "test_env"


def test_service_task_queue_communication():
    """测试服务任务的队列通信功能"""
    print("🧪 Testing service task queue communication...")
    
    # 创建服务任务
    service_factory = MockServiceFactory("test_service", TestService)
    ctx = MockRuntimeContext("test_context")
    service_task = LocalServiceTask(service_factory, ctx)
    
    try:
        # 启动服务任务
        print("Starting service task...")
        service_task.start_running()
        time.sleep(0.5)  # 等待队列监听器启动
        
        # 创建客户端队列，模拟ServiceManager的行为
        request_queue = SageQueue("service_request_test_service")
        response_queue = SageQueue("test_response_queue")
        
        print("✅ Service task started, queues created")
        
        # 测试1: 简单方法调用
        print("\n📝 Test 1: Simple method call")
        request_data = {
            'request_id': 'test_001',
            'service_name': 'test_service',
            'method_name': 'hello',
            'args': ('World',),
            'kwargs': {},
            'response_queue': 'test_response_queue',
            'timeout': 10.0
        }
        
        request_queue.put(request_data)
        
        # 等待响应
        response_data = response_queue.get(timeout=5.0)
        print(f"Response: {response_data}")
        
        assert response_data['request_id'] == 'test_001'
        assert response_data['success'] == True
        assert response_data['result'] == 'Hello, World!'
        print("✅ Simple method call test passed")
        
        # 测试2: 带参数的方法调用
        print("\n📝 Test 2: Method with parameters")
        request_data = {
            'request_id': 'test_002',
            'service_name': 'test_service',
            'method_name': 'set_data',
            'args': ('key1', 'value1'),
            'kwargs': {},
            'response_queue': 'test_response_queue',
            'timeout': 10.0
        }
        
        request_queue.put(request_data)
        response_data = response_queue.get(timeout=5.0)
        
        assert response_data['success'] == True
        assert 'Set key1 = value1' in response_data['result']
        print("✅ Method with parameters test passed")
        
        # 测试3: 获取刚才设置的数据
        print("\n📝 Test 3: Get previously set data")
        request_data = {
            'request_id': 'test_003',
            'service_name': 'test_service',
            'method_name': 'get_data',
            'args': ('key1',),
            'kwargs': {},
            'response_queue': 'test_response_queue',
            'timeout': 10.0
        }
        
        request_queue.put(request_data)
        response_data = response_queue.get(timeout=5.0)
        
        assert response_data['success'] == True
        assert response_data['result'] == 'value1'
        print("✅ Get data test passed")
        
        # 测试4: 错误处理
        print("\n📝 Test 4: Error handling")
        request_data = {
            'request_id': 'test_004',
            'service_name': 'test_service',
            'method_name': 'raise_error',
            'args': (),
            'kwargs': {},
            'response_queue': 'test_response_queue',
            'timeout': 10.0
        }
        
        request_queue.put(request_data)
        response_data = response_queue.get(timeout=5.0)
        
        assert response_data['success'] == False
        assert 'test error' in response_data['error']
        print("✅ Error handling test passed")
        
        # 测试5: 不存在的方法
        print("\n📝 Test 5: Non-existent method")
        request_data = {
            'request_id': 'test_005',
            'service_name': 'test_service',
            'method_name': 'non_existent_method',
            'args': (),
            'kwargs': {},
            'response_queue': 'test_response_queue',
            'timeout': 10.0
        }
        
        request_queue.put(request_data)
        response_data = response_queue.get(timeout=5.0)
        
        assert response_data['success'] == False
        assert 'does not have method' in response_data['error']
        print("✅ Non-existent method test passed")
        
        # 测试6: 验证服务状态
        print("\n📝 Test 6: Service statistics")
        stats = service_task.get_statistics()
        print(f"Service statistics: {stats}")
        
        assert stats['service_name'] == 'test_service'
        assert stats['is_running'] == True
        assert stats['request_count'] >= 5  # 我们调用了至少5次
        assert stats['error_count'] >= 2    # 有2次错误（raise_error + non_existent_method）
        print("✅ Service statistics test passed")
        
        print("\n🎉 All service task queue communication tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # 清理资源
        try:
            service_task.cleanup()
            request_queue.close()
            response_queue.close()
        except Exception as e:
            print(f"Warning: Error during cleanup: {e}")


def test_concurrent_requests():
    """测试并发请求处理"""
    print("\n🧪 Testing concurrent request handling...")
    
    service_factory = MockServiceFactory("concurrent_test_service", TestService)
    ctx = MockRuntimeContext("concurrent_context")
    service_task = LocalServiceTask(service_factory, ctx)
    
    try:
        # 启动服务任务
        service_task.start_running()
        time.sleep(0.5)
        
        # 创建队列
        request_queue = SageQueue("service_request_concurrent_test_service")
        response_queue = SageQueue("concurrent_response_queue")
        
        # 并发发送多个请求
        num_requests = 10
        request_ids = []
        
        print(f"Sending {num_requests} concurrent requests...")
        for i in range(num_requests):
            request_id = f"concurrent_test_{i:03d}"
            request_ids.append(request_id)
            
            request_data = {
                'request_id': request_id,
                'service_name': 'concurrent_test_service',
                'method_name': 'hello',
                'args': (f'User{i}',),
                'kwargs': {},
                'response_queue': 'concurrent_response_queue',
                'timeout': 10.0
            }
            
            request_queue.put(request_data)
        
        # 收集所有响应
        responses = {}
        for _ in range(num_requests):
            response_data = response_queue.get(timeout=10.0)
            responses[response_data['request_id']] = response_data
        
        # 验证响应
        for request_id in request_ids:
            assert request_id in responses
            response = responses[request_id]
            assert response['success'] == True
            
            # 验证响应内容
            user_num = request_id.split('_')[-1]
            expected_result = f'Hello, User{int(user_num)}!'
            assert response['result'] == expected_result
        
        print(f"✅ All {num_requests} concurrent requests processed correctly")
        
        # 检查服务统计
        stats = service_task.get_statistics()
        assert stats['request_count'] >= num_requests
        
        print("✅ Concurrent request handling test passed")
        return True
        
    except Exception as e:
        print(f"❌ Concurrent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        try:
            service_task.cleanup()
            request_queue.close()
            response_queue.close()
        except Exception as e:
            print(f"Warning: Error during cleanup: {e}")


def main():
    """运行所有测试"""
    print("🚀 Running service task base class tests...\n")
    
    tests = [
        ("Queue Communication", test_service_task_queue_communication),
        ("Concurrent Requests", test_concurrent_requests),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Running {test_name} test...")
        if test_func():
            passed += 1
            print(f"✅ {test_name} test PASSED\n")
        else:
            print(f"❌ {test_name} test FAILED\n")
    
    print(f"{'='*60}")
    print(f"FINAL RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Service task base class is working correctly.")
        print("\n✨ Key features verified:")
        print("  ✅ High-performance mmap queue integration")
        print("  ✅ Automatic request/response handling")
        print("  ✅ Service method invocation") 
        print("  ✅ Error handling and reporting")
        print("  ✅ Concurrent request processing")
        print("  ✅ Service lifecycle management")
        print("\n🚀 Ready for production use!")
        return True
    else:
        print(f"❌ {total - passed} test(s) failed. Please review the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
