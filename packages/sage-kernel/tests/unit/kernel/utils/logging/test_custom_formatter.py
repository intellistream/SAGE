"""
Tests for sage.common.utils.logging.custom_formatter module
==================================================

单元测试自定义日志格式化器模块的功能，包括：
- 日志格式化输出
- 颜色显示功能
- 多行格式处理
- 异常信息格式化
"""

import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from sage.common.utils.logging.custom_formatter import CustomFormatter


@pytest.mark.unit
class TestCustomFormatter:
    """CustomFormatter类测试"""

    def setup_method(self):
        """测试前准备"""
        self.formatter = CustomFormatter()

        # 创建测试日志记录
        self.logger = logging.getLogger("test_logger")
        self.handler = logging.StreamHandler()
        self.handler.setFormatter(self.formatter)
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.DEBUG)

    def teardown_method(self):
        """测试后清理"""
        self.logger.handlers.clear()

    def test_formatter_initialization(self):
        """测试格式化器初始化"""
        assert hasattr(self.formatter, "COLOR_RESET")
        assert hasattr(self.formatter, "COLOR_DEBUG")
        assert hasattr(self.formatter, "COLOR_INFO")
        assert hasattr(self.formatter, "COLOR_WARNING")
        assert hasattr(self.formatter, "COLOR_ERROR")
        assert hasattr(self.formatter, "COLOR_CRITICAL")

        # 验证颜色代码
        assert self.formatter.COLOR_RESET == "\033[0m"
        assert self.formatter.COLOR_DEBUG == "\033[36m"
        assert self.formatter.COLOR_INFO == "\033[32m"
        assert self.formatter.COLOR_WARNING == "\033[33m"
        assert self.formatter.COLOR_ERROR == "\033[31m"
        assert self.formatter.COLOR_CRITICAL == "\033[35m"

    def test_format_debug_level(self):
        """测试DEBUG级别日志格式化"""
        record = logging.LogRecord(
            name="test.module",
            level=logging.DEBUG,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Debug message",
            args=(),
            exc_info=None,
        )

        formatted = self.formatter.format(record)

        # 验证格式结构
        assert "DEBUG" in formatted
        assert "test.module" in formatted
        assert "/path/to/test.py:42" in formatted
        assert "Debug message" in formatted
        assert "→" in formatted
        assert "\t" in formatted

        # 验证颜色代码
        assert self.formatter.COLOR_DEBUG in formatted
        assert self.formatter.COLOR_RESET in formatted

    def test_format_info_level(self):
        """测试INFO级别日志格式化"""
        record = logging.LogRecord(
            name="app.service",
            level=logging.INFO,
            pathname="/app/service.py",
            lineno=100,
            msg="Service started successfully",
            args=(),
            exc_info=None,
        )

        formatted = self.formatter.format(record)

        assert "INFO" in formatted
        assert "app.service" in formatted
        assert "/app/service.py:100" in formatted
        assert "Service started successfully" in formatted
        assert self.formatter.COLOR_INFO in formatted

    def test_format_warning_level(self):
        """测试WARNING级别日志格式化"""
        record = logging.LogRecord(
            name="warning.logger",
            level=logging.WARNING,
            pathname="/warn.py",
            lineno=25,
            msg="This is a warning",
            args=(),
            exc_info=None,
        )

        formatted = self.formatter.format(record)

        assert "WARNING" in formatted
        assert "This is a warning" in formatted
        assert self.formatter.COLOR_WARNING in formatted

    def test_format_error_level(self):
        """测试ERROR级别日志格式化"""
        record = logging.LogRecord(
            name="error.handler",
            level=logging.ERROR,
            pathname="/error.py",
            lineno=88,
            msg="An error occurred",
            args=(),
            exc_info=None,
        )

        formatted = self.formatter.format(record)

        assert "ERROR" in formatted
        assert "An error occurred" in formatted
        assert self.formatter.COLOR_ERROR in formatted

    def test_format_critical_level(self):
        """测试CRITICAL级别日志格式化"""
        record = logging.LogRecord(
            name="critical.system",
            level=logging.CRITICAL,
            pathname="/critical.py",
            lineno=999,
            msg="Critical system failure",
            args=(),
            exc_info=None,
        )

        formatted = self.formatter.format(record)

        assert "CRITICAL" in formatted
        assert "Critical system failure" in formatted
        assert self.formatter.COLOR_CRITICAL in formatted

    def test_format_unknown_level(self):
        """测试未知级别日志格式化"""
        record = logging.LogRecord(
            name="unknown.logger",
            level=999,  # 未知级别
            pathname="/unknown.py",
            lineno=1,
            msg="Unknown level message",
            args=(),
            exc_info=None,
        )

        formatted = self.formatter.format(record)

        assert "Unknown level message" in formatted
        assert self.formatter.COLOR_RESET in formatted

    @patch("logging.Formatter.formatTime")
    def test_format_timestamp(self, mock_format_time):
        """测试时间戳格式化"""
        mock_format_time.return_value = "2025-08-04 10:30:45"

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = self.formatter.format(record)

        assert "2025-08-04 10:30:45" in formatted
        mock_format_time.assert_called_once_with(record, "%Y-%m-%d %H:%M:%S")

    def test_format_with_exception_info(self):
        """测试包含异常信息的日志格式化"""
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            record = logging.LogRecord(
                name="test.exception",
                level=logging.ERROR,
                pathname="/test_exception.py",
                lineno=10,
                msg="An error occurred",
                args=(),
                exc_info=(type(e), e, e.__traceback__),
            )

        with patch.object(self.formatter, "formatException") as mock_format_exc:
            mock_format_exc.return_value = (
                "Traceback (most recent call last):\n  ValueError: Test exception"
            )

            formatted = self.formatter.format(record)

            assert "An error occurred" in formatted
            assert "Traceback (most recent call last):" in formatted
            assert "ValueError: Test exception" in formatted
            mock_format_exc.assert_called_once()

    def test_format_with_stack_info(self):
        """测试包含堆栈信息的日志格式化"""
        record = logging.LogRecord(
            name="test.stack",
            level=logging.DEBUG,
            pathname="/test_stack.py",
            lineno=5,
            msg="Debug with stack",
            args=(),
            exc_info=None,
        )
        record.stack_info = "Stack info:\n  File test.py, line 1\n    test_function()"

        with patch.object(self.formatter, "formatStack") as mock_format_stack:
            mock_format_stack.return_value = record.stack_info

            formatted = self.formatter.format(record)

            assert "Debug with stack" in formatted
            assert "Stack info:" in formatted
            assert "test_function()" in formatted

    def test_format_message_args(self):
        """测试消息参数格式化"""
        record = logging.LogRecord(
            name="test.args",
            level=logging.INFO,
            pathname="/test_args.py",
            lineno=20,
            msg="User %s logged in with ID %d",
            args=("john_doe", 12345),
            exc_info=None,
        )

        formatted = self.formatter.format(record)

        assert "User john_doe logged in with ID 12345" in formatted

    def test_format_multiline_message(self):
        """测试多行消息格式化"""
        multiline_msg = """This is a multiline message
        Line 2 of the message
        Line 3 of the message"""

        record = logging.LogRecord(
            name="test.multiline",
            level=logging.INFO,
            pathname="/test_multiline.py",
            lineno=30,
            msg=multiline_msg,
            args=(),
            exc_info=None,
        )

        formatted = self.formatter.format(record)

        assert "This is a multiline message" in formatted
        assert "Line 2 of the message" in formatted
        assert "Line 3 of the message" in formatted

    def test_format_output_structure(self):
        """测试输出格式结构"""
        record = logging.LogRecord(
            name="test.structure",
            level=logging.INFO,
            pathname="/app/module.py",
            lineno=50,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = self.formatter.format(record)
        lines = formatted.split("\n")

        # 验证格式结构：第一行包含元数据，第二行包含消息，第三行为空
        assert len(lines) >= 3

        # 第一行：时间 | 级别 | 名称 | 路径:行号 →
        first_line = lines[0]
        assert "|" in first_line
        assert "INFO" in first_line
        assert "test.structure" in first_line
        assert "/app/module.py:50" in first_line
        assert "→" in first_line

        # 第二行：\t 消息内容
        second_line = lines[1]
        assert second_line.startswith("\t")
        assert "Test message" in second_line

        # 第三行：空行
        third_line = lines[2]
        assert third_line == ""

    def test_format_level_alignment(self):
        """测试日志级别对齐"""
        levels = [
            (logging.DEBUG, "DEBUG"),
            (logging.INFO, "INFO"),
            (logging.WARNING, "WARNING"),
            (logging.ERROR, "ERROR"),
            (logging.CRITICAL, "CRITICAL"),
        ]

        for level_num, level_name in levels:
            record = logging.LogRecord(
                name="test",
                level=level_num,
                pathname="/test.py",
                lineno=1,
                msg="Test",
                args=(),
                exc_info=None,
            )

            formatted = self.formatter.format(record)

            # 验证级别名称使用了左对齐格式（<5）
            assert f"{level_name:<5}" in formatted

    def test_format_ide_compatibility(self):
        """测试IDE兼容性（可点击的文件路径）"""
        record = logging.LogRecord(
            name="test.ide",
            level=logging.ERROR,
            pathname="/home/user/project/src/module.py",
            lineno=123,
            msg="IDE clickable test",
            args=(),
            exc_info=None,
        )

        formatted = self.formatter.format(record)

        # 验证文件路径:行号格式，IDE可以识别并允许点击
        assert "/home/user/project/src/module.py:123" in formatted


@pytest.mark.integration
class TestCustomFormatterIntegration:
    """CustomFormatter集成测试"""

    def test_real_logging_scenario(self):
        """测试真实日志场景"""
        import sys
        from io import StringIO

        # 创建字符串缓冲区来捕获日志输出
        log_capture = StringIO()

        logger = logging.getLogger("integration_test")
        handler = logging.StreamHandler(log_capture)
        formatter = CustomFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        try:
            # 模拟实际应用中的日志记录
            logger.debug("Application starting...")
            logger.info("Service initialized successfully")
            logger.warning("Configuration file not found, using defaults")

            try:
                # 模拟异常
                result = 10 / 0
            except ZeroDivisionError:
                logger.error("Division by zero error", exc_info=True)

            logger.critical("System shutdown initiated")

            # 获取日志输出
            log_output = log_capture.getvalue()

            # 验证日志内容
            assert "Application starting..." in log_output
            assert "Service initialized successfully" in log_output
            assert "Configuration file not found" in log_output
            assert "Division by zero error" in log_output
            assert "ZeroDivisionError" in log_output
            assert "System shutdown initiated" in log_output

            # 验证格式结构
            lines = log_output.strip().split("\n")

            # 每个日志记录应该产生多行输出（元数据行 + 消息行 + 空行）
            # 但异常日志会有更多行
            assert len(lines) > 10  # 至少应有多行输出

        finally:
            logger.handlers.clear()

    def test_formatter_with_different_loggers(self):
        """测试格式化器在不同logger中的表现"""
        from io import StringIO

        log_capture = StringIO()
        formatter = CustomFormatter()

        # 创建多个不同的logger
        loggers = [
            logging.getLogger("app.database"),
            logging.getLogger("app.service.user"),
            logging.getLogger("app.middleware.auth"),
            logging.getLogger("system.monitoring"),
        ]

        for logger in loggers:
            handler = logging.StreamHandler(log_capture)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

        try:
            # 各个logger记录日志
            loggers[0].info("Database connection established")
            loggers[1].warning("User session expired")
            loggers[2].error("Authentication failed")
            loggers[3].critical("System memory usage critical")

            log_output = log_capture.getvalue()

            # 验证不同logger的名称都正确显示
            assert "app.database" in log_output
            assert "app.service.user" in log_output
            assert "app.middleware.auth" in log_output
            assert "system.monitoring" in log_output

            # 验证消息内容
            assert "Database connection established" in log_output
            assert "User session expired" in log_output
            assert "Authentication failed" in log_output
            assert "System memory usage critical" in log_output

        finally:
            for logger in loggers:
                logger.handlers.clear()


@pytest.mark.unit
class TestCustomFormatterEdgeCases:
    """CustomFormatter边界情况测试"""

    def test_format_empty_message(self):
        """测试空消息格式化"""
        formatter = CustomFormatter()

        record = logging.LogRecord(
            name="test.empty",
            level=logging.INFO,
            pathname="/test.py",
            lineno=1,
            msg="",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        # 即使消息为空，格式结构也应该保持
        assert "test.empty" in formatted
        assert "/test.py:1" in formatted
        assert "→" in formatted

    def test_format_very_long_message(self):
        """测试超长消息格式化"""
        formatter = CustomFormatter()

        long_message = "A" * 1000  # 1000字符的消息

        record = logging.LogRecord(
            name="test.long",
            level=logging.INFO,
            pathname="/test.py",
            lineno=1,
            msg=long_message,
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        assert long_message in formatted
        assert len(formatted) > 1000

    def test_format_special_characters(self):
        """测试特殊字符处理"""
        formatter = CustomFormatter()

        special_msg = "Message with special chars: \n\t\r\x00\xff"

        record = logging.LogRecord(
            name="test.special",
            level=logging.INFO,
            pathname="/test.py",
            lineno=1,
            msg=special_msg,
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        # 格式化应该能处理特殊字符而不崩溃
        assert "test.special" in formatted
        assert isinstance(formatted, str)

    def test_format_unicode_message(self):
        """测试Unicode消息格式化"""
        formatter = CustomFormatter()

        unicode_msg = "Unicode测试: 你好世界 🌍 émojis 📝"

        record = logging.LogRecord(
            name="test.unicode",
            level=logging.INFO,
            pathname="/test.py",
            lineno=1,
            msg=unicode_msg,
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        assert unicode_msg in formatted
        assert "test.unicode" in formatted
        assert "🌍" in formatted
        assert "📝" in formatted


# 性能测试
@pytest.mark.slow
class TestCustomFormatterPerformance:
    """CustomFormatter性能测试"""

    def test_format_performance(self):
        """测试格式化性能"""
        import time

        formatter = CustomFormatter()

        # 创建测试记录
        records = []
        for i in range(1000):
            record = logging.LogRecord(
                name=f"test.performance.{i}",
                level=logging.INFO,
                pathname=f"/test/performance_{i}.py",
                lineno=i,
                msg=f"Performance test message {i}",
                args=(),
                exc_info=None,
            )
            records.append(record)

        # 测试格式化性能
        start_time = time.time()
        for record in records:
            formatter.format(record)

        format_time = time.time() - start_time

        # 1000条日志记录的格式化应该在合理时间内完成
        assert format_time < 1.0  # 应在1秒内完成

        # 计算平均每条记录的格式化时间
        avg_time_per_record = format_time / len(records)
        assert avg_time_per_record < 0.001  # 每条记录应在1毫秒内完成
