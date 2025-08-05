"""
测试BaseService的单元测试
"""

import pytest
from unittest.mock import Mock, patch
from abc import ABC, abstractmethod
import logging

from sage.api.service.base_service import BaseService


class MockService(BaseService):
    """测试用的Mock Service"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_called = False
        self.cleanup_called = False
        self.start_called = False
        self.stop_called = False
        self.setup_call_count = 0
        self.cleanup_call_count = 0
        self.start_call_count = 0
        self.stop_call_count = 0
        
    def setup(self):
        super().setup()
        self.setup_called = True
        self.setup_call_count += 1
        
    def cleanup(self):
        super().cleanup()
        self.cleanup_called = True
        self.cleanup_call_count += 1
        
    def start(self):
        super().start()
        self.start_called = True
        self.start_call_count += 1
        
    def stop(self):
        super().stop()
        self.stop_called = True
        self.stop_call_count += 1


class MockServiceContext:
    """Mock ServiceContext"""
    
    def __init__(self, name="test_service", logger=None):
        self.name = name
        self.logger = logger or Mock()


class ComplexService(BaseService):
    """复杂服务示例"""
    
    def __init__(self, config=None):
        super().__init__()
        self.config = config or {}
        self.is_running = False
        self.resources = []
        
    def setup(self):
        """初始化资源"""
        super().setup()
        self.resources = ["resource1", "resource2", "resource3"]
        self.logger.info("Service setup completed")
        
    def start(self):
        """启动服务"""
        super().start()
        if not self.is_running:
            self.is_running = True
            self.logger.info("Service started")
            
    def stop(self):
        """停止服务"""
        super().stop()
        if self.is_running:
            self.is_running = False
            self.logger.info("Service stopped")
            
    def cleanup(self):
        """清理资源"""
        super().cleanup()
        self.resources.clear()
        self.logger.info("Service cleanup completed")


@pytest.mark.unit
class TestBaseService:
    """BaseService基类测试"""
    
    def test_service_creation(self):
        """测试BaseService创建"""
        service = MockService()
        assert service.ctx is None
        assert service._logger is None
        
    def test_service_creation_with_args_kwargs(self):
        """测试BaseService带参数创建"""
        service = MockService("arg1", "arg2", key1="value1", key2="value2")
        assert service.ctx is None
        
    def test_logger_property_without_context(self):
        """测试无上下文时的logger属性"""
        service = MockService()
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            logger = service.logger
            assert logger is mock_logger
            mock_get_logger.assert_called_with("MockService")
            
    def test_logger_property_with_context(self):
        """测试有上下文时的logger属性"""
        service = MockService()
        mock_ctx = MockServiceContext()
        service.ctx = mock_ctx
        
        logger = service.logger
        assert logger is mock_ctx.logger
        
    def test_logger_caching(self):
        """测试logger属性缓存"""
        service = MockService()
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            # 第一次访问
            logger1 = service.logger
            # 第二次访问
            logger2 = service.logger
            
            assert logger1 is logger2
            # getLogger应该只被调用一次（由于缓存）
            mock_get_logger.assert_called_once()
            
    def test_name_property_without_context(self):
        """测试无上下文时的name属性"""
        service = MockService()
        
        # 无上下文时应该返回类名
        assert service.name == "MockService"
        
    def test_name_property_with_context(self):
        """测试有上下文时的name属性"""
        service = MockService()
        mock_ctx = MockServiceContext("custom_service_name")
        service.ctx = mock_ctx
        
        assert service.name == "custom_service_name"
        
    def test_setup_method(self):
        """测试setup方法"""
        service = MockService()
        
        service.setup()
        
        assert service.setup_called
        assert service.setup_call_count == 1
        
    def test_cleanup_method(self):
        """测试cleanup方法"""
        service = MockService()
        
        service.cleanup()
        
        assert service.cleanup_called
        assert service.cleanup_call_count == 1
        
    def test_start_method(self):
        """测试start方法"""
        service = MockService()
        
        service.start()
        
        assert service.start_called
        assert service.start_call_count == 1
        
    def test_stop_method(self):
        """测试stop方法"""
        service = MockService()
        
        service.stop()
        
        assert service.stop_called
        assert service.stop_call_count == 1
        
    def test_multiple_lifecycle_calls(self):
        """测试多次生命周期方法调用"""
        service = MockService()
        
        # 多次调用各方法
        service.setup()
        service.setup()
        service.start()
        service.start()
        service.stop()
        service.cleanup()
        
        assert service.setup_call_count == 2
        assert service.start_call_count == 2
        assert service.stop_call_count == 1
        assert service.cleanup_call_count == 1
        
    def test_abstract_base_class(self):
        """测试抽象基类特性"""
        # BaseService是抽象基类，但没有抽象方法，所以可以实例化
        # 但在实际使用中，应该被子类化
        try:
            service = BaseService()
            # 这应该可以正常工作
            assert service.ctx is None
        except TypeError:
            # 如果将来添加了抽象方法，这里会失败
            pass


@pytest.mark.unit
class TestComplexService:
    """ComplexService测试"""
    
    def test_complex_service_creation(self):
        """测试ComplexService创建"""
        config = {"key": "value"}
        service = ComplexService(config)
        
        assert service.config == config
        assert not service.is_running
        assert service.resources == []
        
    def test_complex_service_creation_without_config(self):
        """测试ComplexService无配置创建"""
        service = ComplexService()
        
        assert service.config == {}
        
    def test_complex_service_setup(self):
        """测试ComplexService setup"""
        service = ComplexService()
        mock_ctx = MockServiceContext()
        service.ctx = mock_ctx
        
        service.setup()
        
        assert service.resources == ["resource1", "resource2", "resource3"]
        mock_ctx.logger.info.assert_called_with("Service setup completed")
        
    def test_complex_service_start(self):
        """测试ComplexService start"""
        service = ComplexService()
        mock_ctx = MockServiceContext()
        service.ctx = mock_ctx
        
        # 第一次启动
        service.start()
        assert service.is_running
        mock_ctx.logger.info.assert_called_with("Service started")
        
        # 重复启动不应该重复执行
        mock_ctx.logger.reset_mock()
        service.start()
        mock_ctx.logger.info.assert_not_called()
        
    def test_complex_service_stop(self):
        """测试ComplexService stop"""
        service = ComplexService()
        mock_ctx = MockServiceContext()
        service.ctx = mock_ctx
        
        # 先启动
        service.start()
        assert service.is_running
        
        # 停止
        service.stop()
        assert not service.is_running
        mock_ctx.logger.info.assert_called_with("Service stopped")
        
        # 重复停止不应该重复执行
        mock_ctx.logger.reset_mock()
        service.stop()
        mock_ctx.logger.info.assert_not_called()
        
    def test_complex_service_cleanup(self):
        """测试ComplexService cleanup"""
        service = ComplexService()
        mock_ctx = MockServiceContext()
        service.ctx = mock_ctx
        
        # 先setup
        service.setup()
        assert len(service.resources) == 3
        
        # cleanup
        service.cleanup()
        assert service.resources == []
        mock_ctx.logger.info.assert_called_with("Service cleanup completed")


@pytest.mark.integration
class TestBaseServiceIntegration:
    """BaseService集成测试"""
    
    def test_service_full_lifecycle(self):
        """测试服务完整生命周期"""
        service = MockService()
        mock_ctx = MockServiceContext("lifecycle_test")
        service.ctx = mock_ctx
        
        # 验证初始状态
        assert service.name == "lifecycle_test"
        assert service.logger is mock_ctx.logger
        
        # 执行完整生命周期
        service.setup()
        service.start()
        service.stop()
        service.cleanup()
        
        # 验证所有方法都被调用
        assert service.setup_called
        assert service.start_called
        assert service.stop_called
        assert service.cleanup_called
        
    def test_service_context_injection(self):
        """测试服务上下文注入"""
        service = MockService()
        
        # 注入前
        assert service.name == "MockService"
        
        # 注入上下文
        mock_ctx = MockServiceContext("injected_service")
        service.ctx = mock_ctx
        
        # 注入后
        assert service.name == "injected_service"
        assert service.logger is mock_ctx.logger
        
    def test_service_error_handling(self):
        """测试服务错误处理"""
        
        class ErrorService(BaseService):
            def setup(self):
                super().setup()
                raise RuntimeError("Setup failed")
                
            def start(self):
                super().start()
                raise RuntimeError("Start failed")
                
        service = ErrorService()
        
        # setup错误
        with pytest.raises(RuntimeError, match="Setup failed"):
            service.setup()
            
        # start错误
        with pytest.raises(RuntimeError, match="Start failed"):
            service.start()
            
        # cleanup和stop应该正常工作
        try:
            service.cleanup()
            service.stop()
        except Exception:
            pytest.fail("cleanup and stop should not raise exceptions")
            
    def test_service_logging_integration(self):
        """测试服务日志集成"""
        service = ComplexService()
        mock_logger = Mock()
        mock_ctx = MockServiceContext("log_test", mock_logger)
        service.ctx = mock_ctx
        
        # 执行会产生日志的操作
        service.setup()
        service.start()
        service.stop()
        service.cleanup()
        
        # 验证日志调用
        assert mock_logger.info.call_count == 4
        mock_logger.info.assert_any_call("Service setup completed")
        mock_logger.info.assert_any_call("Service started")
        mock_logger.info.assert_any_call("Service stopped")
        mock_logger.info.assert_any_call("Service cleanup completed")


class DatabaseService(BaseService):
    """数据库服务示例"""
    
    def __init__(self, connection_string="sqlite:///:memory:"):
        super().__init__()
        self.connection_string = connection_string
        self.connection = None
        self.is_connected = False
        
    def setup(self):
        super().setup()
        self.logger.info(f"Setting up database connection: {self.connection_string}")
        
    def start(self):
        super().start()
        if not self.is_connected:
            # 模拟数据库连接
            self.connection = Mock()
            self.is_connected = True
            self.logger.info("Database connected")
            
    def stop(self):
        super().stop()
        if self.is_connected:
            # 模拟关闭连接
            self.connection = None
            self.is_connected = False
            self.logger.info("Database disconnected")
            
    def cleanup(self):
        super().cleanup()
        self.logger.info("Database service cleanup completed")
        
    def query(self, sql):
        """执行SQL查询"""
        if not self.is_connected:
            raise RuntimeError("Database not connected")
        return f"Result for: {sql}"


class CacheService(BaseService):
    """缓存服务示例"""
    
    def __init__(self, max_size=100):
        super().__init__()
        self.max_size = max_size
        self.cache = {}
        
    def setup(self):
        super().setup()
        self.cache.clear()
        self.logger.info(f"Cache service setup with max_size={self.max_size}")
        
    def get(self, key):
        """获取缓存值"""
        return self.cache.get(key)
        
    def set(self, key, value):
        """设置缓存值"""
        if len(self.cache) >= self.max_size:
            # 简单的LRU逻辑：删除第一个键
            first_key = next(iter(self.cache))
            del self.cache[first_key]
        self.cache[key] = value
        
    def cleanup(self):
        super().cleanup()
        self.cache.clear()
        self.logger.info("Cache service cleanup completed")


@pytest.mark.integration
class TestRealWorldServicePatterns:
    """真实世界服务模式测试"""
    
    def test_database_service(self):
        """测试数据库服务"""
        service = DatabaseService("postgresql://test")
        mock_ctx = MockServiceContext("db_service")
        service.ctx = mock_ctx
        
        # 完整生命周期
        service.setup()
        service.start()
        
        # 使用服务
        result = service.query("SELECT * FROM users")
        assert result == "Result for: SELECT * FROM users"
        
        service.stop()
        service.cleanup()
        
        # 验证状态
        assert not service.is_connected
        assert service.connection is None
        
    def test_cache_service(self):
        """测试缓存服务"""
        service = CacheService(max_size=2)
        mock_ctx = MockServiceContext("cache_service")
        service.ctx = mock_ctx
        
        service.setup()
        
        # 测试缓存操作
        service.set("key1", "value1")
        service.set("key2", "value2")
        
        assert service.get("key1") == "value1"
        assert service.get("key2") == "value2"
        
        # 测试LRU行为
        service.set("key3", "value3")  # 应该移除key1
        assert service.get("key1") is None
        assert service.get("key2") == "value2"
        assert service.get("key3") == "value3"
        
        service.cleanup()
        assert len(service.cache) == 0
        
    def test_multiple_services_coordination(self):
        """测试多个服务协调"""
        db_service = DatabaseService()
        cache_service = CacheService()
        
        db_ctx = MockServiceContext("db")
        cache_ctx = MockServiceContext("cache")
        
        db_service.ctx = db_ctx
        cache_service.ctx = cache_ctx
        
        # 启动服务
        for service in [db_service, cache_service]:
            service.setup()
            service.start()
            
        # 使用服务
        assert db_service.is_connected
        assert len(cache_service.cache) == 0
        
        cache_service.set("test", "data")
        assert cache_service.get("test") == "data"
        
        # 停止服务
        for service in [db_service, cache_service]:
            service.stop()
            service.cleanup()
            
        assert not db_service.is_connected
        assert len(cache_service.cache) == 0


class StatefulService(BaseService):
    """有状态服务示例"""
    
    def __init__(self):
        super().__init__()
        self.state = {"counter": 0, "data": []}
        self.state_file = "service_state.json"
        
    def increment_counter(self):
        self.state["counter"] += 1
        
    def add_data(self, data):
        self.state["data"].append(data)
        
    def get_state(self):
        return self.state.copy()
        
    def setup(self):
        super().setup()
        # 模拟状态恢复
        self.logger.info("Loading service state")
        
    def cleanup(self):
        super().cleanup()
        # 模拟状态保存
        self.logger.info("Saving service state")


@pytest.mark.integration
class TestAdvancedServicePatterns:
    """高级服务模式测试"""
    
    def test_stateful_service(self):
        """测试有状态服务"""
        service = StatefulService()
        mock_ctx = MockServiceContext("stateful")
        service.ctx = mock_ctx
        
        service.setup()
        
        # 修改状态
        initial_state = service.get_state()
        assert initial_state["counter"] == 0
        assert initial_state["data"] == []
        
        service.increment_counter()
        service.add_data("item1")
        service.add_data("item2")
        
        final_state = service.get_state()
        assert final_state["counter"] == 1
        assert final_state["data"] == ["item1", "item2"]
        
        service.cleanup()
        
        # 验证日志调用
        mock_ctx.logger.info.assert_any_call("Loading service state")
        mock_ctx.logger.info.assert_any_call("Saving service state")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
