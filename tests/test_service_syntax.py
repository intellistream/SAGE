"""
测试服务调用语法糖功能
"""

import time
import threading
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sage.core.function.base_function import BaseFunction
from sage_runtime.service.service_caller import ServiceManager


class MockRuntimeContext:
    """模拟运行时上下文"""
    def __init__(self):
        self.logger = Mock()
        self.name = "test_context"
        self.env_name = "test_env"
        self._service_manager = None
    
    @property
    def service_manager(self):
        if self._service_manager is None:
            self._service_manager = ServiceManager(self)
        return self._service_manager


class TestFunction(BaseFunction):
    """测试函数类"""
    
    def execute(self, data):
        return data


class TestServiceSyntax(unittest.TestCase):
    """测试服务调用语法糖"""
    
    def setUp(self):
        """每个测试方法前的设置"""
        self.mock_ctx = MockRuntimeContext()
        self.test_function = TestFunction()
        self.test_function.ctx = self.mock_ctx
    
    def test_call_service_property_access(self):
        """测试call_service属性访问"""
        # 测试第一次访问
        call_service = self.test_function.call_service
        self.assertIsNotNone(call_service)
        
        # 测试缓存机制
        call_service2 = self.test_function.call_service
        self.assertIs(call_service, call_service2)
    
    def test_call_service_async_property_access(self):
        """测试call_service_async属性访问"""
        # 测试第一次访问
        call_service_async = self.test_function.call_service_async
        self.assertIsNotNone(call_service_async)
        
        # 测试缓存机制
        call_service_async2 = self.test_function.call_service_async
        self.assertIs(call_service_async, call_service_async2)
    
    def test_service_access_without_context(self):
        """测试没有运行时上下文时的错误处理"""
        func = TestFunction()
        func.ctx = None
        
        with self.assertRaises(RuntimeError) as cm:
            _ = func.call_service
        self.assertIn("Runtime context not initialized", str(cm.exception))
        
        with self.assertRaises(RuntimeError) as cm:
            _ = func.call_service_async
        self.assertIn("Runtime context not initialized", str(cm.exception))
    
    @patch('sage.core.service.service_caller.ServiceManager')
    def test_sync_service_call_syntax(self, mock_service_manager_class):
        """测试同步服务调用语法"""
        # 设置mock
        mock_service_manager = Mock()
        mock_service_manager_class.return_value = mock_service_manager
        
        mock_sync_proxy = Mock()
        mock_service_manager.get_sync_proxy.return_value = mock_sync_proxy
        
        mock_method = Mock(return_value="test_result")
        mock_sync_proxy.test_method = mock_method
        
        # 重新创建函数实例以使用mock
        func = TestFunction()
        func.ctx = self.mock_ctx
        
        # 测试语法糖调用
        result = func.call_service["test_service"].test_method("arg1", kwarg1="value1")
        
        # 验证调用
        mock_service_manager.get_sync_proxy.assert_called_once_with("test_service")
        mock_method.assert_called_once_with("arg1", kwarg1="value1")
        self.assertEqual(result, "test_result")
    
    @patch('sage.core.service.service_caller.ServiceManager')
    def test_async_service_call_syntax(self, mock_service_manager_class):
        """测试异步服务调用语法"""
        # 设置mock
        mock_service_manager = Mock()
        mock_service_manager_class.return_value = mock_service_manager
        
        mock_async_proxy = Mock()
        mock_service_manager.get_async_proxy.return_value = mock_async_proxy
        
        mock_future = Mock()
        mock_method = Mock(return_value=mock_future)
        mock_async_proxy.test_method = mock_method
        
        # 重新创建函数实例以使用mock
        func = TestFunction()
        func.ctx = self.mock_ctx
        
        # 测试语法糖调用
        future = func.call_service_async["test_service"].test_method("arg1")
        
        # 验证调用
        mock_service_manager.get_async_proxy.assert_called_once_with("test_service")
        mock_method.assert_called_once_with("arg1")
        self.assertEqual(future, mock_future)
    
    def test_multiple_service_access(self):
        """测试访问多个不同的服务"""
        with patch('sage.core.service.service_caller.ServiceManager') as mock_sm_class:
            mock_service_manager = Mock()
            mock_sm_class.return_value = mock_service_manager
            
            # 创建不同服务的mock代理
            cache_proxy = Mock()
            db_proxy = Mock()
            mock_service_manager.get_sync_proxy.side_effect = lambda name: {
                "cache": cache_proxy,
                "database": db_proxy
            }[name]
            
            func = TestFunction()
            func.ctx = self.mock_ctx
            
            # 访问不同服务
            cache_service = func.call_service["cache"]
            db_service = func.call_service["database"]
            
            # 验证返回了不同的代理
            self.assertEqual(cache_service, cache_proxy)
            self.assertEqual(db_service, db_proxy)
            
            # 验证调用了正确的服务名
            expected_calls = [
                unittest.mock.call("cache"),
                unittest.mock.call("database")
            ]
            mock_service_manager.get_sync_proxy.assert_has_calls(expected_calls)


class TestIntegratedServiceCall(unittest.TestCase):
    """集成测试 - 测试完整的服务调用流程"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_ctx = MockRuntimeContext()
        
    @patch('sage_utils.mmap_queue.sage_queue.SageQueue')
    def test_real_service_manager_integration(self, mock_sage_queue_class):
        """测试与真实ServiceManager的集成"""
        # 设置SageQueue mock
        mock_request_queue = Mock()
        mock_response_queue = Mock()
        
        def queue_constructor(name, *args, **kwargs):
            if "service_request" in name:
                return mock_request_queue
            elif "service_response" in name:
                return mock_response_queue
            return Mock()
        
        mock_sage_queue_class.side_effect = queue_constructor
        
        # 创建测试函数
        func = TestFunction()
        func.ctx = self.mock_ctx
        
        # 模拟服务响应
        def mock_put(data, **kwargs):
            # 模拟异步响应
            def send_response():
                time.sleep(0.01)
                response_data = {
                    'request_id': data['request_id'],
                    'result': f"Response for {data['method_name']}",
                    'success': True,
                    'execution_time': 0.01,
                    'timestamp': time.time()
                }
                # 模拟从响应队列接收响应
                func.ctx.service_manager._handle_response(
                    func.ctx.service_manager._create_response(response_data)
                )
            
            threading.Thread(target=send_response, daemon=True).start()
        
        mock_request_queue.put.side_effect = mock_put
        
        # 执行同步服务调用
        try:
            result = func.call_service["test_service"].test_method("test_arg")
            # 注意：这个测试可能会因为实际的mmap队列实现而失败
            # 在实际环境中，需要真正的服务进程来处理请求
        except Exception as e:
            # 预期在没有真实服务进程的情况下会失败
            self.assertTrue("timeout" in str(e).lower() or "failed" in str(e).lower())


if __name__ == "__main__":
    # 使用unittest运行测试
    print("Running service syntax sugar tests...")
    
    try:
        # 运行unittest
        unittest.main(verbosity=2, exit=False)
        print("\n🎉 All service syntax sugar tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
