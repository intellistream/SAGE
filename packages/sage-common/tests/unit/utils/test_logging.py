"""
Tests for SAGE logging utilities
"""
import logging
import tempfile
from pathlib import Path

import pytest

from sage.common.utils.logging.custom_logger import CustomLogger


class TestCustomLogger:
    """Test CustomLogger functionality"""
    
    def test_logger_creation(self):
        """Test basic logger creation"""
        logger = CustomLogger()
        assert logger is not None
        assert logger.logger is not None
    
    def test_logger_with_custom_name(self):
        """Test logger with custom name"""
        logger = CustomLogger(name="test_logger")
        assert logger.logger.name == "test_logger"
    
    def test_logger_default_level(self):
        """Test default logging level"""
        logger = CustomLogger()
        # Default should be INFO
        assert logger.logger.level <= logging.INFO
    
    def test_debug_logging(self):
        """Test debug level logging"""
        logger = CustomLogger(name="debug_test")
        logger.debug("Debug message")
        # Should not raise exception
    
    def test_info_logging(self):
        """Test info level logging"""
        logger = CustomLogger(name="info_test")
        logger.info("Info message")
        # Should not raise exception
    
    def test_warning_logging(self):
        """Test warning level logging"""
        logger = CustomLogger(name="warning_test")
        logger.warning("Warning message")
        # Should not raise exception
    
    def test_error_logging(self):
        """Test error level logging"""
        logger = CustomLogger(name="error_test")
        logger.error("Error message")
        # Should not raise exception
    
    def test_critical_logging(self):
        """Test critical level logging"""
        logger = CustomLogger(name="critical_test")
        logger.critical("Critical message")
        # Should not raise exception
    
    def test_exception_logging(self):
        """Test exception logging"""
        logger = CustomLogger(name="exception_test")
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("Caught exception")
            # Should not raise exception
    
    def test_simple_logger_creation(self):
        """测试最简单的logger创建方式"""
        logger = CustomLogger("TestLogger")
        
        assert logger.name == "TestLogger"
        assert logger.logger is not None
        assert isinstance(logger.logger, logging.Logger)

    def test_logger_with_custom_file(self, tmp_path):
        """测试带自定义日志文件的logger"""
        log_file = tmp_path / "test.log"
        logger = CustomLogger(
            name="FileLogger",
            outputs=[(str(log_file), "INFO")],
            log_base_folder=None  # 使用绝对路径
        )
        
        logger.info("Test message")
        
        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content

    def test_logger_with_level(self):
        """测试设置日志级别"""
        logger = CustomLogger(
            name="LevelLogger",
            outputs=[("console", logging.WARNING)]
        )
        
        # Logger的级别会设置为最低的handler级别
        assert logger.logger.level <= logging.WARNING

    def test_logger_with_level_string(self):
        """测试使用字符串设置日志级别"""
        logger = CustomLogger(
            name="StringLevelLogger",
            outputs=[("console", "ERROR")]
        )
    
    def test_get_available_levels(self):
        """测试获取可用日志级别"""
        levels = CustomLogger.get_available_levels()
        
        assert "DEBUG" in levels
        assert "INFO" in levels
        assert "WARNING" in levels
        assert "ERROR" in levels
        assert "CRITICAL" in levels

    def test_multiple_log_calls(self):
        """测试多次日志调用"""
        logger = CustomLogger(
            name="level_test",
            outputs=[("console", logging.DEBUG)]
        )
        
        # 测试各种级别的日志
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        # 验证可以多次调用
        logger2 = CustomLogger(
            name="level_test2",
            outputs=[("console", logging.ERROR)]
        )
        logger2.error("Another error")

    def test_file_handler_creation(self, tmp_path):
        """测试文件handler的创建"""
        log_file = tmp_path / "handler_test.log"
        
        logger = CustomLogger(
            name="HandlerLogger",
            outputs=[(str(log_file), "DEBUG")]
        )
    
    def test_logger_format(self):
        """Test logger output format"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "format_test.log"
            logger = CustomLogger(
                name="format_test",
                outputs=[(str(log_file), "INFO")]
            )
            logger.info("Format test message")
            
            content = log_file.read_text()
            # Should contain timestamp, level, and message
            assert "INFO" in content
            assert "Format test message" in content
    
    def test_multiple_loggers(self):
        """Test creating multiple independent loggers"""
        logger1 = CustomLogger(name="logger1")
        logger2 = CustomLogger(name="logger2")
        
        assert logger1.logger.name != logger2.logger.name
        assert logger1 is not logger2
    
    def test_logger_with_context(self):
        """Test logger with context information"""
        logger = CustomLogger(name="context_test")
        
        # Test logging with extra context
        logger.info("Message with context", extra={"user_id": 123})
        # Should not raise exception


class TestLoggingConfiguration:
    """Test logging configuration utilities"""
    
    def test_logging_import(self):
        """Test that logging module can be imported"""
        from sage.common.utils import logging as sage_logging
        assert sage_logging is not None
    
    def test_custom_logger_import(self):
        """Test CustomLogger can be imported from utils"""
        from sage.common.utils.logging import CustomLogger as CL
        assert CL is not None
        
        logger = CL()
        assert logger is not None


class TestLoggingIntegration:
    """Integration tests for logging"""
    
    def test_logger_in_class(self):
        """Test using logger in a class"""
        class TestClass:
            def __init__(self):
                self.logger = CustomLogger(name=self.__class__.__name__)
            
            def do_something(self):
                self.logger.info("Doing something")
                return True
        
        obj = TestClass()
        assert obj.do_something() is True
    
    def test_logger_exception_handling(self):
        """Test logger handles exceptions gracefully"""
        logger = CustomLogger(name="exception_handling_test")
        
        try:
            # Simulate an error
            result = 1 / 0
        except ZeroDivisionError as e:
            logger.error(f"Caught error: {e}")
            # Logger should not crash
        
        # Should continue working after exception
        logger.info("Still working")
    
    def test_concurrent_logging(self):
        """Test logger works with concurrent access"""
        logger = CustomLogger(name="concurrent_test")
        
        # Simulate multiple log calls
        for i in range(10):
            logger.debug(f"Message {i}")
            logger.info(f"Message {i}")
            logger.warning(f"Message {i}")
        
        # Should not raise exceptions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
