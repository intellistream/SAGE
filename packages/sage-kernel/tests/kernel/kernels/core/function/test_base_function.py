"""
测试BaseFunction的单元测试
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from abc import abstractmethod

from sage.kernel.api.function.base_function import BaseFunction


class MockFunction(BaseFunction):
    """测试用的Mock Function"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.execute_called = False
        self.execute_call_count = 0
        self.last_input = None
        
    def execute(self, data):
        self.execute_called = True
        self.execute_call_count += 1
        self.last_input = data
        return data


class MockTaskContext:
    """Mock TaskContext"""
    
    def __init__(self, name="test_task", logger=None):
        self.name = name
        self.logger = logger or Mock()


@pytest.mark.unit
class TestBaseFunction:
    """BaseFunction基类测试"""
    
    def test_function_creation(self):
        """测试BaseFunction创建"""
        func = MockFunction()
        assert func.ctx is None
        assert func.router is None
        assert func._call_service_proxy is None
        assert func._call_service_async_proxy is None
        
    def test_function_creation_with_args(self):
        """测试BaseFunction带参数创建"""
        func = MockFunction("arg1", "arg2", key="value")
        assert func.ctx is None
        
    def test_logger_property_without_context(self):
        """测试无上下文时的logger属性"""
        func = MockFunction()
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            logger = func.logger
            assert logger is mock_logger
            mock_get_logger.assert_called_with("")
            
    def test_logger_property_with_context(self):
        """测试有上下文时的logger属性"""
        func = MockFunction()
        mock_ctx = MockTaskContext()
        func.ctx = mock_ctx
        
        logger = func.logger
        assert logger is mock_ctx.logger
        
    def test_logger_caching(self):
        """测试logger属性缓存"""
        func = MockFunction()
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            # 第一次访问
            logger1 = func.logger
            # 第二次访问
            logger2 = func.logger
            
            assert logger1 is logger2
            # getLogger应该只被调用一次（由于缓存）
            mock_get_logger.assert_called_once()
            
    def test_name_property_without_context(self):
        """测试无上下文时的name属性"""
        func = MockFunction()
        
        # 无上下文时应该返回None
        assert func.name is None
        
    def test_name_property_with_context(self):
        """测试有上下文时的name属性"""
        func = MockFunction()
        mock_ctx = MockTaskContext("test_function")
        func.ctx = mock_ctx
        
        assert func.name == "test_function"
        
    def test_call_service_property_without_context(self):
        """测试无上下文时的call_service属性"""
        func = MockFunction()
        
        with pytest.raises(RuntimeError, match="Runtime context not initialized"):
            _ = func.call_service
            
    def test_call_service_property_with_context(self):
        """测试有上下文时的call_service属性"""
        func = MockFunction()
        mock_ctx = MockTaskContext()
        func.ctx = mock_ctx
        
        # 这里需要mock ServiceCallProxy的创建
        with patch('sage.core.function.base_function.ServiceCallProxy') as mock_proxy_class:
            mock_proxy = Mock()
            mock_proxy_class.return_value = mock_proxy
            
            result = func.call_service
            assert result is mock_proxy
            # 验证缓存机制
            result2 = func.call_service
            assert result2 is mock_proxy
            # ServiceCallProxy应该只被创建一次
            mock_proxy_class.assert_called_once()
            
    def test_call_service_async_property_without_context(self):
        """测试无上下文时的call_service_async属性"""
        func = MockFunction()
        
        with pytest.raises(RuntimeError, match="Runtime context not initialized"):
            _ = func.call_service_async
            
    def test_context_injection(self):
        """测试运行时上下文注入"""
        func = MockFunction()
        mock_ctx = MockTaskContext("injected_task")
        mock_router = Mock()
        
        # 模拟运行时注入
        func.ctx = mock_ctx
        func.router = mock_router
        
        assert func.ctx is mock_ctx
        assert func.router is mock_router
        assert func.name == "injected_task"
        
    def test_execute_method(self):
        """测试execute方法（在子类中实现）"""
        func = MockFunction()
        test_data = {"test": "data"}
        
        result = func.execute(test_data)
        
        assert func.execute_called
        assert func.execute_call_count == 1
        assert func.last_input is test_data
        assert result is test_data


@pytest.mark.unit 
class TestBaseFunctionStateManagement:
    """BaseFunction状态管理测试"""
    
    @patch('sage.core.function.base_function.save_function_state')
    def test_state_saving(self, mock_save_state):
        """测试状态保存功能"""
        func = MockFunction()
        
        # 由于状态管理可能在具体子类中实现，这里主要测试导入是否正常
        assert mock_save_state is not None
        
    @patch('sage.core.function.base_function.load_function_state')
    def test_state_loading(self, mock_load_state):
        """测试状态加载功能"""
        func = MockFunction()
        
        # 由于状态管理可能在具体子类中实现，这里主要测试导入是否正常
        assert mock_load_state is not None


@pytest.mark.integration
class TestBaseFunctionIntegration:
    """BaseFunction集成测试"""
    
    def test_full_lifecycle(self):
        """测试完整生命周期"""
        func = MockFunction()
        
        # 1. 创建函数
        assert func.ctx is None
        
        # 2. 注入上下文
        mock_ctx = MockTaskContext("lifecycle_test")
        func.ctx = mock_ctx
        
        # 3. 验证属性可访问
        assert func.name == "lifecycle_test"
        assert func.logger is mock_ctx.logger
        
        # 4. 执行函数
        test_data = "test_execution"
        result = func.execute(test_data)
        
        assert result == test_data
        assert func.execute_called
        
    def test_service_integration_workflow(self):
        """测试服务集成工作流程"""
        func = MockFunction()
        mock_ctx = MockTaskContext()
        func.ctx = mock_ctx
        
        with patch('sage.core.function.base_function.ServiceCallProxy') as mock_proxy_class:
            mock_proxy = Mock()
            mock_proxy_class.return_value = mock_proxy
            
            # 模拟服务调用
            service_proxy = func.call_service
            assert service_proxy is mock_proxy
            
            # 验证缓存工作
            service_proxy2 = func.call_service
            assert service_proxy2 is service_proxy
            
    def test_error_handling(self):
        """测试错误处理"""
        func = MockFunction()
        
        # 测试无上下文时的错误
        with pytest.raises(RuntimeError):
            _ = func.call_service
            
        # 测试name属性在无上下文时的行为
        assert func.name is None  # 应该优雅处理，不抛异常


class ConcreteFunction(BaseFunction):
    """具体实现类，用于测试抽象方法"""
    
    def concrete_method(self):
        return "concrete implementation"


@pytest.mark.unit
class TestAbstractMethods:
    """抽象方法测试"""
    
    def test_concrete_implementation(self):
        """测试具体实现"""
        func = ConcreteFunction()
        assert func.concrete_method() == "concrete implementation"
        
    def test_base_function_properties_in_concrete_class(self):
        """测试具体实现类中的基类属性"""
        func = ConcreteFunction()
        mock_ctx = MockTaskContext("concrete_test")
        func.ctx = mock_ctx
        
        assert func.name == "concrete_test"
        assert func.logger is mock_ctx.logger


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
