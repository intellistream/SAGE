"""
测试服务调用功能
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch
from sage.runtime.service.service_caller import (
    ServiceManager, ServiceRequest, ServiceResponse, 
    CallMode, ServiceCallProxy, AsyncServiceCallProxy
)


class MockRuntimeContext:
    """模拟运行时上下文"""
    def __init__(self):
        self.logger = Mock()
        self.name = "test_context"


class TestServiceManager:
    """测试服务管理器"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.mock_ctx = MockRuntimeContext()
        self.service_manager = ServiceManager(self.mock_ctx)
    
    def teardown_method(self):
        """每个测试方法后的清理"""
        self.service_manager.shutdown()
    
    def test_service_manager_initialization(self):
        """测试服务管理器初始化"""
        assert self.service_manager.runtime_context == self.mock_ctx
        assert self.service_manager.logger == self.mock_ctx.logger
        assert isinstance(self.service_manager._pending_requests, dict)
        assert isinstance(self.service_manager._request_results, dict)
    
    def test_get_sync_proxy(self):
        """测试获取同步代理"""
        proxy = self.service_manager.get_sync_proxy("test_service")
        assert isinstance(proxy, ServiceCallProxy)
        assert proxy.service_name == "test_service"
        
        # 测试缓存
        proxy2 = self.service_manager.get_sync_proxy("test_service")
        assert proxy is proxy2
    
    def test_get_async_proxy(self):
        """测试获取异步代理"""
        proxy = self.service_manager.get_async_proxy("test_service")
        assert isinstance(proxy, AsyncServiceCallProxy)
        assert proxy.service_name == "test_service"
        
        # 测试缓存
        proxy2 = self.service_manager.get_async_proxy("test_service")
        assert proxy is proxy2
    
    def test_sync_service_call(self):
        """测试同步服务调用"""
        # 模拟成功响应
        expected_result = "test_result"
        
        def mock_send_request(request):
            # 模拟异步响应
            def respond():
                time.sleep(0.1)
                response = ServiceResponse(
                    request_id=request.request_id,
                    result=expected_result,
                    success=True,
                    execution_time=0.1
                )
                self.service_manager._handle_response(response)
            
            threading.Thread(target=respond, daemon=True).start()
        
        with patch.object(self.service_manager, '_send_request', side_effect=mock_send_request):
            result = self.service_manager.call_service_sync(
                "test_service", "test_method", "arg1", kwarg1="value1"
            )
            assert result == expected_result
    
    def test_sync_service_call_timeout(self):
        """测试同步服务调用超时"""
        def mock_send_request(request):
            # 不发送响应，模拟超时
            pass
        
        with patch.object(self.service_manager, '_send_request', side_effect=mock_send_request):
            with pytest.raises(TimeoutError):
                self.service_manager.call_service_sync(
                    "test_service", "test_method", timeout=0.1
                )
    
    def test_sync_service_call_error(self):
        """测试同步服务调用错误"""
        def mock_send_request(request):
            def respond():
                time.sleep(0.05)
                response = ServiceResponse(
                    request_id=request.request_id,
                    success=False,
                    error="Service error occurred"
                )
                self.service_manager._handle_response(response)
            
            threading.Thread(target=respond, daemon=True).start()
        
        with patch.object(self.service_manager, '_send_request', side_effect=mock_send_request):
            with pytest.raises(RuntimeError, match="Service call failed"):
                self.service_manager.call_service_sync("test_service", "test_method")
    
    def test_async_service_call(self):
        """测试异步服务调用"""
        expected_result = "async_test_result"
        
        def mock_send_request(request):
            def respond():
                time.sleep(0.1)
                response = ServiceResponse(
                    request_id=request.request_id,
                    result=expected_result,
                    success=True,
                    execution_time=0.1
                )
                self.service_manager._handle_response(response)
            
            threading.Thread(target=respond, daemon=True).start()
        
        with patch.object(self.service_manager, '_send_request', side_effect=mock_send_request):
            future = self.service_manager.call_service_async(
                "test_service", "test_method", "arg1"
            )
            
            # 验证返回Future对象
            assert hasattr(future, 'result')
            assert hasattr(future, 'done')
            
            # 获取结果
            result = future.result(timeout=1.0)
            assert result == expected_result
    
    def test_service_proxy_method_call(self):
        """测试服务代理方法调用"""
        expected_result = "proxy_result"
        
        def mock_call_service_sync(service_name, method_name, *args, **kwargs):
            assert service_name == "test_service"
            assert method_name == "test_method"
            assert args == ("arg1", "arg2")
            assert kwargs == {"kwarg1": "value1"}
            return expected_result
        
        with patch.object(self.service_manager, 'call_service_sync', side_effect=mock_call_service_sync):
            proxy = self.service_manager.get_sync_proxy("test_service")
            result = proxy.test_method("arg1", "arg2", kwarg1="value1")
            assert result == expected_result
    
    def test_async_service_proxy_method_call(self):
        """测试异步服务代理方法调用"""
        mock_future = Mock()
        
        def mock_call_service_async(service_name, method_name, *args, **kwargs):
            assert service_name == "test_service"
            assert method_name == "test_method"
            return mock_future
        
        with patch.object(self.service_manager, 'call_service_async', side_effect=mock_call_service_async):
            proxy = self.service_manager.get_async_proxy("test_service")
            result = proxy.test_method("arg1")
            assert result == mock_future


class TestServiceRequestResponse:
    """测试服务请求和响应数据结构"""
    
    def test_service_request_creation(self):
        """测试服务请求创建"""
        request = ServiceRequest(
            request_id="test-123",
            service_name="test_service",
            method_name="test_method",
            args=("arg1", "arg2"),
            kwargs={"key": "value"},
            call_mode=CallMode.SYNC
        )
        
        assert request.request_id == "test-123"
        assert request.service_name == "test_service"
        assert request.method_name == "test_method"
        assert request.args == ("arg1", "arg2")
        assert request.kwargs == {"key": "value"}
        assert request.call_mode == CallMode.SYNC
        assert request.timestamp is not None
    
    def test_service_response_creation(self):
        """测试服务响应创建"""
        response = ServiceResponse(
            request_id="test-123",
            result="test_result",
            success=True,
            execution_time=0.5
        )
        
        assert response.request_id == "test-123"
        assert response.result == "test_result"
        assert response.success is True
        assert response.execution_time == 0.5
        assert response.error is None
        assert response.timestamp is not None
    
    def test_service_response_error(self):
        """测试服务错误响应"""
        response = ServiceResponse(
            request_id="test-123",
            success=False,
            error="Something went wrong"
        )
        
        assert response.request_id == "test-123"
        assert response.success is False
        assert response.error == "Something went wrong"
        assert response.result is None


if __name__ == "__main__":
    # 简单的测试运行器
    import sys
    
    # 创建测试实例
    test_manager = TestServiceManager()
    test_data = TestServiceRequestResponse()
    
    print("Running service caller tests...")
    
    try:
        # 测试服务管理器
        test_manager.setup_method()
        
        print("✓ Testing service manager initialization...")
        test_manager.test_service_manager_initialization()
        
        print("✓ Testing sync proxy...")
        test_manager.test_get_sync_proxy()
        
        print("✓ Testing async proxy...")  
        test_manager.test_get_async_proxy()
        
        print("✓ Testing sync service call...")
        test_manager.test_sync_service_call()
        
        print("✓ Testing async service call...")
        test_manager.test_async_service_call()
        
        test_manager.teardown_method()
        
        # 测试数据结构
        print("✓ Testing service request creation...")
        test_data.test_service_request_creation()
        
        print("✓ Testing service response creation...")
        test_data.test_service_response_creation()
        
        print("✓ Testing service error response...")
        test_data.test_service_response_error()
        
        print("\n🎉 All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
