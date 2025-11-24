"""
Comprehensive tests for BaseService

Tests cover:
- Initialization and context management
- Logger property (with/without context)
- Name property (with/without context)
- call_service and call_service_async methods
- Lifecycle methods (setup, cleanup, start, stop)
- Error handling
"""

import logging
from unittest.mock import MagicMock

import pytest

from sage.common.service.base_service import BaseService


class ConcreteService(BaseService):
    """Concrete implementation for testing"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class TestBaseServiceInitialization:
    """Test BaseService initialization"""

    def test_initialization_without_ctx(self):
        """Test initialization without context"""
        service = ConcreteService()

        assert hasattr(service, "ctx")
        assert service.ctx is None
        assert hasattr(service, "_logger")

    def test_initialization_with_existing_ctx(self):
        """Test initialization when ctx already exists"""
        service = ConcreteService()
        mock_ctx = MagicMock()
        service.ctx = mock_ctx

        # Re-initialize
        service.__init__()

        # ctx should be preserved
        assert service.ctx is mock_ctx

    def test_initialization_with_args(self):
        """Test initialization with arguments"""
        service = ConcreteService("arg1", "arg2", kwarg1="value1")

        assert service.ctx is None


class TestBaseServiceLogger:
    """Test logger property"""

    def test_logger_without_context(self):
        """Test logger returns default logger when no context"""
        service = ConcreteService()

        logger = service.logger

        assert isinstance(logger, logging.Logger)
        assert logger.name == "ConcreteService"

    def test_logger_with_context(self):
        """Test logger uses context logger when available"""
        service = ConcreteService()
        mock_ctx = MagicMock()
        mock_ctx_logger = MagicMock()
        mock_ctx.logger = mock_ctx_logger
        service.ctx = mock_ctx

        logger = service.logger

        assert logger is mock_ctx_logger

    def test_logger_caching(self):
        """Test logger is cached"""
        service = ConcreteService()

        logger1 = service.logger
        logger2 = service.logger

        assert logger1 is logger2

    def test_logger_switch_to_context(self):
        """Test logger switches when context is added"""
        service = ConcreteService()

        # First get default logger
        default_logger = service.logger
        assert default_logger.name == "ConcreteService"

        # Add context
        mock_ctx = MagicMock()
        mock_ctx_logger = MagicMock()
        mock_ctx.logger = mock_ctx_logger
        service.ctx = mock_ctx
        service._logger = None  # Clear cache

        # Now should use context logger
        ctx_logger = service.logger
        assert ctx_logger is mock_ctx_logger


class TestBaseServiceName:
    """Test name property"""

    def test_name_without_context(self):
        """Test name returns class name when no context"""
        service = ConcreteService()

        assert service.name == "ConcreteService"

    def test_name_with_context(self):
        """Test name uses context name when available"""
        service = ConcreteService()
        mock_ctx = MagicMock()
        mock_ctx.name = "custom_service_name"
        service.ctx = mock_ctx

        assert service.name == "custom_service_name"

    def test_name_priority(self):
        """Test context name takes priority over class name"""
        service = ConcreteService()

        # Without context
        assert service.name == "ConcreteService"

        # With context
        mock_ctx = MagicMock()
        mock_ctx.name = "runtime_name"
        service.ctx = mock_ctx
        assert service.name == "runtime_name"


class TestBaseServiceCallService:
    """Test call_service method"""

    def test_call_service_without_context_raises_error(self):
        """Test call_service raises error without context"""
        service = ConcreteService()

        with pytest.raises(RuntimeError, match="Service context not initialized"):
            service.call_service("some_service")

    def test_call_service_with_context(self):
        """Test call_service delegates to context"""
        service = ConcreteService()
        mock_ctx = MagicMock()
        service.ctx = mock_ctx

        result = service.call_service("test_service", "arg1", "arg2", kwarg1="value1")

        mock_ctx.call_service.assert_called_once_with(
            "test_service", "arg1", "arg2", timeout=None, method=None, kwarg1="value1"
        )
        assert result == mock_ctx.call_service.return_value

    def test_call_service_with_timeout(self):
        """Test call_service with timeout parameter"""
        service = ConcreteService()
        mock_ctx = MagicMock()
        service.ctx = mock_ctx

        service.call_service("test_service", timeout=5.0)

        mock_ctx.call_service.assert_called_once_with("test_service", timeout=5.0, method=None)

    def test_call_service_with_method(self):
        """Test call_service with method parameter"""
        service = ConcreteService()
        mock_ctx = MagicMock()
        service.ctx = mock_ctx

        service.call_service("test_service", "data", method="process")

        mock_ctx.call_service.assert_called_once_with(
            "test_service", "data", timeout=None, method="process"
        )

    def test_call_service_with_all_params(self):
        """Test call_service with all parameters"""
        service = ConcreteService()
        mock_ctx = MagicMock()
        service.ctx = mock_ctx

        service.call_service(
            "test_service", "arg1", timeout=10.0, method="execute", custom_param="value"
        )

        mock_ctx.call_service.assert_called_once_with(
            "test_service", "arg1", timeout=10.0, method="execute", custom_param="value"
        )


class TestBaseServiceCallServiceAsync:
    """Test call_service_async method"""

    def test_call_service_async_without_context_raises_error(self):
        """Test call_service_async raises error without context"""
        service = ConcreteService()

        with pytest.raises(RuntimeError, match="Service context not initialized"):
            service.call_service_async("some_service")

    def test_call_service_async_with_context(self):
        """Test call_service_async delegates to context"""
        service = ConcreteService()
        mock_ctx = MagicMock()
        service.ctx = mock_ctx

        result = service.call_service_async("test_service", "arg1", kwarg1="value1")

        mock_ctx.call_service_async.assert_called_once_with(
            "test_service", "arg1", timeout=None, method=None, kwarg1="value1"
        )
        assert result == mock_ctx.call_service_async.return_value

    def test_call_service_async_with_timeout(self):
        """Test call_service_async with timeout parameter"""
        service = ConcreteService()
        mock_ctx = MagicMock()
        service.ctx = mock_ctx

        service.call_service_async("test_service", timeout=3.0)

        mock_ctx.call_service_async.assert_called_once_with(
            "test_service", timeout=3.0, method=None
        )

    def test_call_service_async_with_method(self):
        """Test call_service_async with method parameter"""
        service = ConcreteService()
        mock_ctx = MagicMock()
        service.ctx = mock_ctx

        service.call_service_async("test_service", method="async_process")

        mock_ctx.call_service_async.assert_called_once_with(
            "test_service", timeout=None, method="async_process"
        )


class TestBaseServiceLifecycle:
    """Test lifecycle methods"""

    def test_setup_default_implementation(self):
        """Test setup method has default implementation"""
        service = ConcreteService()

        # Should not raise
        result = service.setup()

        assert result is None

    def test_cleanup_default_implementation(self):
        """Test cleanup method has default implementation"""
        service = ConcreteService()

        # Should not raise
        result = service.cleanup()

        assert result is None

    def test_start_default_implementation(self):
        """Test start method has default implementation"""
        service = ConcreteService()

        # Should not raise
        result = service.start()

        assert result is None

    def test_stop_default_implementation(self):
        """Test stop method has default implementation"""
        service = ConcreteService()

        # Should not raise
        result = service.stop()

        assert result is None

    def test_lifecycle_override(self):
        """Test lifecycle methods can be overridden"""

        class CustomService(BaseService):
            def __init__(self):
                super().__init__()
                self.setup_called = False
                self.cleanup_called = False
                self.start_called = False
                self.stop_called = False

            def setup(self):
                self.setup_called = True

            def cleanup(self):
                self.cleanup_called = True

            def start(self):
                self.start_called = True

            def stop(self):
                self.stop_called = True

        service = CustomService()
        service.setup()
        service.start()
        service.stop()
        service.cleanup()

        assert service.setup_called
        assert service.cleanup_called
        assert service.start_called
        assert service.stop_called


class TestBaseServiceIntegration:
    """Integration tests for BaseService"""

    def test_full_lifecycle_with_context(self):
        """Test complete lifecycle with context"""
        service = ConcreteService()

        # Add context
        mock_ctx = MagicMock()
        mock_ctx.name = "integration_service"
        mock_ctx.logger = logging.getLogger("integration")
        service.ctx = mock_ctx

        # Verify properties
        assert service.name == "integration_service"
        assert service.logger.name == "integration"

        # Call lifecycle methods
        service.setup()
        service.start()

        # Call service
        mock_ctx.call_service.return_value = "result"
        result = service.call_service("dependency_service", "data")
        assert result == "result"

        # Stop
        service.stop()
        service.cleanup()

    def test_multiple_service_instances(self):
        """Test multiple service instances are independent"""
        service1 = ConcreteService()
        service2 = ConcreteService()

        mock_ctx1 = MagicMock()
        mock_ctx1.name = "service1"
        service1.ctx = mock_ctx1

        mock_ctx2 = MagicMock()
        mock_ctx2.name = "service2"
        service2.ctx = mock_ctx2

        assert service1.name == "service1"
        assert service2.name == "service2"
        assert service1.ctx is not service2.ctx

    def test_service_without_context_logging(self, caplog):
        """Test service can log without context"""
        service = ConcreteService()

        with caplog.at_level(logging.INFO):
            service.logger.info("Test message")

        assert "Test message" in caplog.text

    def test_custom_service_with_business_logic(self):
        """Test custom service with business logic"""

        class BusinessService(BaseService):
            def __init__(self):
                super().__init__()
                self.processed_count = 0

            def process_data(self, data):
                self.logger.info(f"Processing data: {data}")
                self.processed_count += 1
                return f"processed_{data}"

        service = BusinessService()
        result1 = service.process_data("item1")
        result2 = service.process_data("item2")

        assert result1 == "processed_item1"
        assert result2 == "processed_item2"
        assert service.processed_count == 2


class TestBaseServiceEdgeCases:
    """Test edge cases and error handling"""

    def test_call_service_with_none_context(self):
        """Test call_service handles None context properly"""
        service = ConcreteService()
        service.ctx = None

        with pytest.raises(RuntimeError, match="Service context not initialized"):
            service.call_service("test")

    def test_logger_reinitialization(self):
        """Test logger can be reinitialized"""
        service = ConcreteService()

        logger1 = service.logger
        service._logger = None  # Force reinitialization
        logger2 = service.logger

        # Python logging returns same logger instance for same name
        assert logger1 is logger2
        assert logger1.name == logger2.name

    def test_context_injection_pattern(self):
        """Test context injection pattern"""
        service = ConcreteService()

        # Simulate ServiceFactory injection
        mock_ctx = MagicMock()
        mock_ctx.name = "injected_service"
        service.ctx = mock_ctx

        assert service.ctx is mock_ctx
        assert service.name == "injected_service"

    def test_args_kwargs_forwarding(self):
        """Test args and kwargs are handled properly"""

        class ParamsService(BaseService):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.args = args
                self.kwargs = kwargs

        service = ParamsService("arg1", "arg2", param1="value1", param2="value2")

        assert service.args == ("arg1", "arg2")
        assert service.kwargs == {"param1": "value1", "param2": "value2"}
