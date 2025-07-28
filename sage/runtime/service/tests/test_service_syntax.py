# """
# 测试服务调用语法糖功能
# """

# import time
# import threading
# import unittest
# from unittest.mock import Mock, patch, MagicMock
# import sys
# import os

# # 添加项目根目录到Python路径
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from sage.core.function.base_function import BaseFunction
# from sage.runtime.service.service_caller import ServiceManager


# class MockRuntimeContext:
#     """模拟运行时上下文"""
#     def __init__(self):
#         self.logger = Mock()
#         self.name = "test_context"
#         self.env_name = "test_env"
#         self._service_manager = None
    
#     @property
#     def service_manager(self):
#         if self._service_manager is None:
#             self._service_manager = ServiceManager(self)
#         return self._service_manager


# class TestFunction(BaseFunction):
#     """测试函数类"""
    
#     def execute(self, data):
#         return data


# class TestServiceSyntax(unittest.TestCase):
#     """测试服务调用语法糖"""
    
#     def setUp(self):
#         """每个测试方法前的设置"""
#         self.mock_ctx = MockRuntimeContext()
#         self.test_function = TestFunction()
#         self.test_function.ctx = self.mock_ctx
    
#     def test_call_service_property_access(self):
#         """测试call_service属性访问"""
#         # 测试第一次访问
#         call_service = self.test_function.call_service
#         self.assertIsNotNone(call_service)
        
#         # 测试缓存机制
#         call_service2 = self.test_function.call_service
#         self.assertIs(call_service, call_service2)
    
#     def test_call_service_async_property_access(self):
#         """测试call_service_async属性访问"""
#         # 测试第一次访问
#         call_service_async = self.test_function.call_service_async
#         self.assertIsNotNone(call_service_async)
        
#         # 测试缓存机制
#         call_service_async2 = self.test_function.call_service_async
#         self.assertIs(call_service_async, call_service_async2)
    
#     def test_service_access_without_context(self):
#         """测试没有运行时上下文时的错误处理"""
#         func = TestFunction()
#         func.ctx = None
        
#         with self.assertRaises(RuntimeError) as cm:
#             _ = func.call_service
#         self.assertIn("Runtime context not initialized", str(cm.exception))
        
#         with self.assertRaises(RuntimeError) as cm:
#             _ = func.call_service_async
#         self.assertIn("Runtime context not initialized", str(cm.exception))
    
#     @patch('sage.runtime.service.service_caller.ServiceManager')
#     def test_sync_service_call_syntax(self, mock_service_manager_class):
#         """测试同步服务调用语法"""
#         # 设置mock
#         mock_service_manager = Mock()
#         mock_service_manager_class.return_value = mock_service_manager
        
#         # Mock call_sync方法
#         mock_service_manager.call_sync.return_value = "test_result"
        
#         # 创建函数实例并手动设置service_manager
#         func = TestFunction()
#         mock_ctx = Mock()
#         mock_ctx.service_manager = mock_service_manager
#         func.ctx = mock_ctx
        
#         # 测试语法糖调用
#         result = func.call_service["test_service"].test_method("arg1", kwarg1="value1")
        
#         # 验证调用
#         mock_service_manager.call_sync.assert_called_once_with(
#             "test_service", "test_method", "arg1", timeout=30.0, kwarg1="value1"
#         )
#         self.assertEqual(result, "test_result")
    
#     @patch('sage.runtime.service.service_caller.ServiceManager')
#     def test_async_service_call_syntax(self, mock_service_manager_class):
#         """测试异步服务调用语法"""
#         # 设置mock
#         mock_service_manager = Mock()
#         mock_service_manager_class.return_value = mock_service_manager
        
#         # Mock call_async方法
#         mock_future = Mock()
#         mock_service_manager.call_async.return_value = mock_future
        
#         # 创建函数实例并手动设置service_manager
#         func = TestFunction()
#         mock_ctx = Mock()
#         mock_ctx.service_manager = mock_service_manager
#         func.ctx = mock_ctx
        
#         # 测试语法糖调用
#         future = func.call_service_async["test_service"].test_method("arg1")
        
#         # 验证调用
#         mock_service_manager.call_async.assert_called_once_with(
#             "test_service", "test_method", "arg1", timeout=30.0
#         )
#         self.assertEqual(future, mock_future)
    
#     def test_multiple_service_access(self):
#         """测试访问多个不同的服务"""
#         func = TestFunction()
#         func.ctx = self.mock_ctx
        
#         # 访问不同服务
#         cache_service = func.call_service["cache"]
#         db_service = func.call_service["database"]
        
#         # 验证返回了不同的代理对象（因为服务名不同）
#         self.assertNotEqual(cache_service, db_service)
        
#         # 验证它们都是ServiceCallProxy实例
#         from sage.runtime.service.service_caller import ServiceCallProxy
#         self.assertIsInstance(cache_service, ServiceCallProxy)
#         self.assertIsInstance(db_service, ServiceCallProxy)
        
#         # 验证服务名正确
#         self.assertEqual(cache_service._service_name, "cache")
#         self.assertEqual(db_service._service_name, "database")


# class TestIntegratedServiceCall(unittest.TestCase):
#     """集成测试 - 测试完整的服务调用流程"""
    
#     def setUp(self):
#         """设置测试环境"""
#         self.mock_ctx = MockRuntimeContext()
        
#     def test_real_service_manager_integration(self):
#         """测试与真实ServiceManager的集成 - 简化版本"""
#         # 创建测试函数
#         func = TestFunction()
#         func.ctx = self.mock_ctx
        
#         # 验证语法糖能够正确创建ServiceCallProxy
#         service_proxy = func.call_service["test_service"]
        
#         # 验证代理对象的基本属性
#         from sage.runtime.service.service_caller import ServiceCallProxy
#         self.assertIsInstance(service_proxy, ServiceCallProxy)
#         self.assertEqual(service_proxy._service_name, "test_service")
#         self.assertFalse(service_proxy._async_mode)
        
#         # 验证异步代理
#         async_proxy = func.call_service_async["test_service"]
#         self.assertIsInstance(async_proxy, ServiceCallProxy)
#         self.assertEqual(async_proxy._service_name, "test_service")
#         self.assertTrue(async_proxy._async_mode)
        
#         # 验证代理缓存
#         self.assertIs(func.call_service, func.call_service)
#         self.assertIs(func.call_service_async, func.call_service_async)


# if __name__ == "__main__":
#     # 使用unittest运行测试
#     print("Running service syntax sugar tests...")
    
#     try:
#         # 运行unittest
#         unittest.main(verbosity=2, exit=False)
#         print("\n🎉 All service syntax sugar tests completed!")
        
#     except Exception as e:
#         print(f"\n❌ Test failed: {e}")
#         import traceback
#         traceback.print_exc()
#         sys.exit(1)
