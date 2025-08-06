"""
Tests for sage.utils.logging.custom_logger module
===============================================

单元测试自定义日志记录器模块的功能，包括：
- CustomLogger类的所有方法
- 多输出目标配置
- 动态配置更新
- 全局console debug控制
- 路径解析和处理
"""

import pytest
import tempfile
import logging
import os
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from contextlib import contextmanager

from sage.kernel.utils.logging.custom_logger import CustomLogger


@contextmanager
def sage_temp_directory():
    """使用 ~/.sage/test_tmp 创建临时目录的上下文管理器"""
    sage_test_dir = os.path.expanduser("~/.sage/test_tmp")
    os.makedirs(sage_test_dir, exist_ok=True)
    temp_dir = tempfile.mkdtemp(dir=sage_test_dir)
    try:
        yield temp_dir
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.unit
class TestCustomLogger:
    """CustomLogger类基本功能测试"""
    
    def setup_method(self):
        """测试前准备"""
        # 使用 ~/.sage/test_tmp 而不是系统临时目录
        sage_test_dir = os.path.expanduser("~/.sage/test_tmp")
        os.makedirs(sage_test_dir, exist_ok=True)
        self.temp_dir = tempfile.mkdtemp(dir=sage_test_dir)
        # 确保每个测试开始时重置全局状态
        CustomLogger.enable_global_console_debug()
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        # 重置全局状态
        CustomLogger.enable_global_console_debug()
    
    def test_logger_initialization_console_only(self):
        """测试仅控制台输出的logger初始化"""
        logger = CustomLogger(
            outputs=[("console", "INFO")],
            name="TestLogger"
        )
        
        assert logger.name == "TestLogger"
        assert logger.log_base_folder is None
        assert len(logger.output_configs) == 1
        assert logger.output_configs[0]['target'] == "console"
        assert logger.output_configs[0]['level'] == logging.INFO
        assert logger.logger.level == logging.INFO
    
    def test_logger_initialization_with_base_folder(self):
        """测试带基础文件夹的logger初始化"""
        logger = CustomLogger(
            outputs=[
                ("console", "INFO"),
                ("app.log", "DEBUG")
            ],
            name="TestLoggerBaseFolder",
            log_base_folder=self.temp_dir
        )
        
        assert logger.log_base_folder == self.temp_dir
        output_configs = logger.get_output_configs()
        assert len(output_configs) == 2
        
        # 验证路径解析
        file_config = next(c for c in output_configs if c['target'] == "app.log")
        expected_path = os.path.join(self.temp_dir, "app.log")
        assert file_config['resolved_path'] == expected_path
        
        # 验证最低日志级别设置
        assert logger.logger.level == logging.DEBUG
    
    def test_logger_initialization_mixed_paths(self):
        """测试混合路径的logger初始化"""
        absolute_path = os.path.join(self.temp_dir, "absolute.log")
        
        logger = CustomLogger(
            outputs=[
                ("console", "INFO"),
                ("relative.log", "DEBUG"),
                (absolute_path, "ERROR")
            ],
            name="MixedLogger",
            log_base_folder=self.temp_dir
        )
        
        configs = logger.output_configs
        assert len(configs) == 3
        
        # 控制台配置
        console_config = next(c for c in configs if c['target'] == "console")
        assert console_config['resolved_path'] == "console"
        
        # 相对路径配置
        relative_config = next(c for c in configs if c['target'] == "relative.log")
        assert relative_config['resolved_path'] == os.path.join(self.temp_dir, "relative.log")
        
        # 绝对路径配置
        absolute_config = next(c for c in configs if c['target'] == absolute_path)
        assert absolute_config['resolved_path'] == absolute_path
    
    def test_logger_initialization_default_name(self):
        """测试默认名称的logger初始化"""
        logger = CustomLogger()
        assert logger.name == "Logger"
        assert len(logger.output_configs) == 1  # 默认是console INFO
    
    def test_level_mapping(self):
        """测试日志级别映射"""
        level_tests = [
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
            ("WARN", logging.WARNING),
            ("ERROR", logging.ERROR),
            ("CRITICAL", logging.CRITICAL),
            ("FATAL", logging.CRITICAL),
        ]
        
        for i, (level_str, expected_level) in enumerate(level_tests):
            logger = CustomLogger([("console", level_str)], name=f"TestLogger_{i}")
            # Use internal config to test the integer level mapping
            config = logger.output_configs[0]
            assert config['level'] == expected_level
    
    def test_invalid_log_level(self):
        """测试无效日志级别处理"""
        with pytest.raises(ValueError, match="Invalid log level"):
            CustomLogger([("console", "INVALID_LEVEL")], name="TestInvalidLevel")
    
    def test_invalid_level_type(self):
        """测试无效级别类型处理"""
        with pytest.raises(TypeError, match="level_setting must be str or int"):
            CustomLogger([("console", [])], name="TestInvalidType")  # 列表类型无效


@pytest.mark.unit
class TestPathResolution:
    """路径解析测试"""
    
    def setup_method(self):
        """测试前准备"""
        # 使用 ~/.sage/test_tmp 而不是系统临时目录
        sage_test_dir = os.path.expanduser("~/.sage/test_tmp")
        os.makedirs(sage_test_dir, exist_ok=True)
        self.temp_dir = tempfile.mkdtemp(dir=sage_test_dir)
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_resolve_console_path(self):
        """测试控制台路径解析"""
        logger = CustomLogger([("console", "INFO")])
        resolved = logger._resolve_path("console")
        assert resolved == "console"
    
    def test_resolve_absolute_path(self):
        """测试绝对路径解析"""
        absolute_path = "/tmp/test.log"
        logger = CustomLogger()
        resolved = logger._resolve_path(absolute_path)
        assert resolved == absolute_path
    
    def test_resolve_relative_path_with_base_folder(self):
        """测试有基础文件夹的相对路径解析"""
        logger = CustomLogger(log_base_folder=self.temp_dir)
        resolved = logger._resolve_path("app.log")
        expected = os.path.join(self.temp_dir, "app.log")
        assert resolved == expected
    
    def test_resolve_relative_path_without_base_folder(self):
        """测试无基础文件夹的相对路径解析失败"""
        logger = CustomLogger()
        
        with pytest.raises(ValueError, match="Cannot use relative path.*without log_base_folder"):
            logger._resolve_path("app.log")
    
    def test_resolve_nested_relative_path(self):
        """测试嵌套相对路径解析"""
        logger = CustomLogger(log_base_folder=self.temp_dir)
        resolved = logger._resolve_path("logs/app/debug.log")
        expected = os.path.join(self.temp_dir, "logs", "app", "debug.log")
        assert resolved == expected


@pytest.mark.unit
class TestLoggingMethods:
    """日志记录方法测试"""
    
    def setup_method(self):
        """测试前准备"""
        # 使用 ~/.sage/test_tmp 而不是系统临时目录
        sage_test_dir = os.path.expanduser("~/.sage/test_tmp")
        os.makedirs(sage_test_dir, exist_ok=True)
        self.temp_dir = tempfile.mkdtemp(dir=sage_test_dir)
        self.log_file = os.path.join(self.temp_dir, "test.log")
        
        self.logger = CustomLogger(
            outputs=[("console", "DEBUG"), (self.log_file, "DEBUG")],
            name="TestLogger"
        )
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_debug_logging(self):
        """测试DEBUG级别日志记录"""
        self.logger.debug("Debug message")
        
        # 检查文件是否创建并包含日志
        assert os.path.exists(self.log_file)
        with open(self.log_file, 'r') as f:
            content = f.read()
            assert "DEBUG" in content
            assert "Debug message" in content
    
    def test_info_logging(self):
        """测试INFO级别日志记录"""
        self.logger.info("Info message")
        
        with open(self.log_file, 'r') as f:
            content = f.read()
            assert "INFO" in content
            assert "Info message" in content
    
    def test_warning_logging(self):
        """测试WARNING级别日志记录"""
        self.logger.warning("Warning message")
        
        with open(self.log_file, 'r') as f:
            content = f.read()
            assert "WARNING" in content
            assert "Warning message" in content
    
    def test_error_logging(self):
        """测试ERROR级别日志记录"""
        self.logger.error("Error message")
        
        with open(self.log_file, 'r') as f:
            content = f.read()
            assert "ERROR" in content
            assert "Error message" in content
    
    def test_critical_logging(self):
        """测试CRITICAL级别日志记录"""
        self.logger.critical("Critical message")
        
        with open(self.log_file, 'r') as f:
            content = f.read()
            assert "CRITICAL" in content
            assert "Critical message" in content
    
    def test_error_with_exception_info(self):
        """测试带异常信息的错误日志"""
        try:
            raise ValueError("Test exception")
        except ValueError:
            self.logger.error("Error with exception", exc_info=True)
        
        with open(self.log_file, 'r') as f:
            content = f.read()
            assert "ERROR" in content
            assert "Error with exception" in content
            assert "ValueError" in content
            assert "Test exception" in content
    
    def test_exception_logging(self):
        """测试exception方法自动包含异常信息"""
        try:
            raise RuntimeError("Runtime error")
        except RuntimeError:
            self.logger.exception("Exception occurred")
        
        with open(self.log_file, 'r') as f:
            content = f.read()
            assert "ERROR" in content  # exception方法实际记录为ERROR级别
            assert "Exception occurred" in content
            assert "RuntimeError" in content
            assert "Runtime error" in content
    
    @patch('inspect.currentframe')
    def test_caller_info_extraction(self, mock_frame):
        """测试调用者信息提取"""
        # 模拟调用栈
        mock_caller_frame = MagicMock()
        mock_caller_frame.f_code.co_filename = "/test/caller.py"
        mock_caller_frame.f_lineno = 42
        
        mock_method_frame = MagicMock()
        mock_method_frame.f_back = mock_caller_frame
        
        mock_current_frame = MagicMock()
        mock_current_frame.f_back.f_back = mock_method_frame
        
        mock_frame.return_value = mock_current_frame
        
        self.logger.info("Test caller info")
        
        with open(self.log_file, 'r') as f:
            content = f.read()
            assert "/test/caller.py:42" in content


@pytest.mark.unit
class TestDynamicConfiguration:
    """动态配置测试"""
    
    def setup_method(self):
        """测试前准备"""
        # 使用 ~/.sage/test_tmp 而不是系统临时目录
        sage_test_dir = os.path.expanduser("~/.sage/test_tmp")
        os.makedirs(sage_test_dir, exist_ok=True)
        self.temp_dir = tempfile.mkdtemp(dir=sage_test_dir)
        self.logger = CustomLogger(
            outputs=[("console", "INFO")],
            name="DynamicLogger",
            log_base_folder=self.temp_dir
        )
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_output_configs(self):
        """测试获取输出配置"""
        configs = self.logger.get_output_configs()
        
        assert len(configs) == 1
        assert configs[0]['target'] == "console"
        assert configs[0]['level'] == "INFO"
        assert configs[0]['handler_active'] is True
    
    def test_add_output_relative_path(self):
        """测试添加相对路径输出"""
        self.logger.add_output("new.log", "DEBUG")
        
        configs = self.logger.get_output_configs()
        assert len(configs) == 2
        
        new_config = next(c for c in configs if c['target'] == "new.log")
        assert new_config['level'] == "DEBUG"
        assert new_config['handler_active'] is True
        
        expected_path = os.path.join(self.temp_dir, "new.log")
        assert new_config['resolved_path'] == expected_path
    
    def test_add_output_absolute_path(self):
        """测试添加绝对路径输出"""
        absolute_path = os.path.join(self.temp_dir, "absolute.log")
        self.logger.add_output(absolute_path, "ERROR")
        
        configs = self.logger.get_output_configs()
        new_config = next(c for c in configs if c['target'] == absolute_path)
        assert new_config['level'] == "ERROR"
        assert new_config['resolved_path'] == absolute_path
    
    def test_update_output_level_by_index(self):
        """测试通过索引更新输出级别"""
        self.logger.add_output("test.log", "INFO")
        
        # 更新第一个输出（console）的级别
        self.logger.update_output_level(0, "ERROR")
        
        configs = self.logger.get_output_configs()
        console_config = configs[0]
        assert console_config['level'] == "ERROR"
    
    def test_update_output_level_by_name(self):
        """测试通过名称更新输出级别"""
        self.logger.add_output("test.log", "INFO")
        
        # 通过目标名称更新级别
        self.logger.update_output_level("test.log", "WARNING")
        
        configs = self.logger.get_output_configs()
        test_config = next(c for c in configs if c['target'] == "test.log")
        assert test_config['level'] == "WARNING"
    
    def test_update_nonexistent_output(self):
        """测试更新不存在的输出"""
        with pytest.raises(ValueError, match="Output target not found"):
            self.logger.update_output_level("nonexistent", "DEBUG")
        
        with pytest.raises(ValueError, match="Output target not found"):
            self.logger.update_output_level(999, "DEBUG")
    
    def test_remove_output_by_index(self):
        """测试通过索引移除输出"""
        self.logger.add_output("remove_me.log", "DEBUG")
        
        initial_count = len(self.logger.output_configs)
        self.logger.remove_output(1)  # 移除刚添加的
        
        assert len(self.logger.output_configs) == initial_count - 1
        
        # 验证剩余的是console输出
        remaining_targets = [c['target'] for c in self.logger.output_configs]
        assert "remove_me.log" not in remaining_targets
        assert "console" in remaining_targets
    
    def test_remove_output_by_name(self):
        """测试通过名称移除输出"""
        self.logger.add_output("remove_me.log", "DEBUG")
        
        self.logger.remove_output("remove_me.log")
        
        remaining_targets = [c['target'] for c in self.logger.output_configs]
        assert "remove_me.log" not in remaining_targets
    
    def test_remove_nonexistent_output(self):
        """测试移除不存在的输出"""
        with pytest.raises(ValueError, match="Output target not found"):
            self.logger.remove_output("nonexistent")
        
        with pytest.raises(ValueError, match="Output target not found"):
            self.logger.remove_output(999)


@pytest.mark.unit
class TestGlobalConsoleDebug:
    """全局console debug控制测试"""
    
    def test_global_console_debug_enabled_by_default(self):
        """测试全局console debug默认启用"""
        assert CustomLogger.is_global_console_debug_enabled() is True
    
    def test_disable_global_console_debug(self):
        """测试禁用全局console debug"""
        CustomLogger.disable_global_console_debug()
        assert CustomLogger.is_global_console_debug_enabled() is False
        
        # 重新启用以免影响其他测试
        CustomLogger.enable_global_console_debug()
    
    def test_enable_global_console_debug(self):
        """测试启用全局console debug"""
        CustomLogger.disable_global_console_debug()
        CustomLogger.enable_global_console_debug()
        assert CustomLogger.is_global_console_debug_enabled() is True
    
    def test_console_handler_creation_when_disabled(self):
        """测试禁用时不创建console handler"""
        CustomLogger.disable_global_console_debug()
        
        try:
            logger = CustomLogger([("console", "INFO")])
            
            # 应该没有console handler被创建
            console_config = logger.output_configs[0]
            assert console_config['target'] == "console"
            assert console_config['handler'] is None
            
        finally:
            CustomLogger.enable_global_console_debug()
    
    def test_thread_safety_of_global_setting(self):
        """测试全局设置的线程安全性"""
        results = []
        
        def toggle_setting():
            for _ in range(100):
                CustomLogger.disable_global_console_debug()
                CustomLogger.enable_global_console_debug()
            results.append(CustomLogger.is_global_console_debug_enabled())
        
        threads = [threading.Thread(target=toggle_setting) for _ in range(5)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 所有线程应该得到一致的结果
        assert all(result is True for result in results)


@pytest.mark.unit
class TestUtilityMethods:
    """工具方法测试"""
    
    def test_get_available_levels(self):
        """测试获取可用日志级别"""
        levels = CustomLogger.get_available_levels()
        
        expected_levels = ['DEBUG', 'INFO', 'WARNING', 'WARN', 'ERROR', 'CRITICAL', 'FATAL']
        assert set(levels) == set(expected_levels)
    
    def test_print_current_configs(self):
        """测试打印当前配置"""
        with sage_temp_directory() as temp_dir:
            logger = CustomLogger(
                outputs=[
                    ("console", "INFO"),
                    ("app.log", "DEBUG"),
                    ("/tmp/error.log", "ERROR")
                ],
                name="PrintTestLogger",
                log_base_folder=temp_dir
            )
            
            # 捕获打印输出
            import sys
            import builtins
            
            # 使用内置的StringIO来避免导入冲突
            import importlib
            io_module = importlib.import_module('io')
            IOStringIO = io_module.StringIO
            
            old_stdout = sys.stdout
            captured_output = IOStringIO()
            sys.stdout = captured_output
            
            try:
                logger.print_current_configs()
                output = captured_output.getvalue()
                
                # 验证输出内容
                assert "PrintTestLogger" in output
                assert "console" in output
                assert "app.log" in output
                assert "/tmp/error.log" in output
                assert "INFO" in output
                assert "DEBUG" in output
                assert "ERROR" in output
                assert "ACTIVE" in output
                
            finally:
                sys.stdout = old_stdout


@pytest.mark.integration
class TestCustomLoggerIntegration:
    """CustomLogger集成测试"""
    
    def test_real_world_logging_scenario(self):
        """测试真实世界的日志记录场景"""
        with sage_temp_directory() as temp_dir:
            # 创建多层次日志配置
            logger = CustomLogger(
                outputs=[
                    ("console", "INFO"),
                    ("app.log", "DEBUG"),
                    ("error.log", "ERROR"),
                    (os.path.join(temp_dir, "system.log"), "WARNING")
                ],
                name="RealWorldLogger",
                log_base_folder=temp_dir
            )
            
            # 模拟应用启动过程
            logger.info("Application starting...")
            logger.debug("Loading configuration...")
            logger.info("Configuration loaded successfully")
            
            # 模拟警告情况
            logger.warning("Deprecated API usage detected")
            
            # 模拟错误情况
            try:
                raise ConnectionError("Database connection failed")
            except ConnectionError:
                logger.error("Failed to connect to database", exc_info=True)
            
            # 模拟异常情况
            try:
                raise ValueError("Invalid configuration value")
            except ValueError:
                logger.exception("Configuration validation failed")
            
            logger.critical("System is shutting down due to critical errors")
            
            # 验证日志文件内容
            app_log_path = os.path.join(temp_dir, "app.log")
            error_log_path = os.path.join(temp_dir, "error.log")
            system_log_path = os.path.join(temp_dir, "system.log")
            
            # app.log 应该包含所有级别的日志（DEBUG及以上）
            with open(app_log_path, 'r') as f:
                app_content = f.read()
                assert "Application starting..." in app_content
                assert "Loading configuration..." in app_content
                assert "Deprecated API usage" in app_content
                assert "Database connection failed" in app_content
                assert "Configuration validation failed" in app_content
                assert "System is shutting down" in app_content
            
            # error.log 应该只包含ERROR及以上级别的日志
            with open(error_log_path, 'r') as f:
                error_content = f.read()
                assert "Application starting..." not in error_content
                assert "Loading configuration..." not in error_content
                assert "Deprecated API usage" not in error_content
                assert "Database connection failed" in error_content
                assert "Configuration validation failed" in error_content
                assert "System is shutting down" in error_content
            
            # system.log 应该包含WARNING及以上级别的日志
            with open(system_log_path, 'r') as f:
                system_content = f.read()
                assert "Application starting..." not in system_content
                assert "Loading configuration..." not in system_content
                assert "Deprecated API usage" in system_content
                assert "Database connection failed" in system_content
                assert "System is shutting down" in system_content
    
    def test_dynamic_configuration_workflow(self):
        """测试动态配置工作流程"""
        with sage_temp_directory() as temp_dir:
            # 初始配置
            logger = CustomLogger(
                outputs=[("console", "INFO")],
                name="DynamicWorkflowLogger",
                log_base_folder=temp_dir
            )
            
            logger.info("Initial setup complete")
            
            # 运行时添加文件日志
            logger.add_output("runtime.log", "DEBUG")
            logger.debug("Runtime logging enabled")
            
            # 更新console日志级别
            logger.update_output_level("console", "ERROR")
            logger.info("This info message should not appear in console")
            logger.error("This error message should appear everywhere")
            
            # 添加临时调试日志
            debug_log = os.path.join(temp_dir, "debug.log")
            logger.add_output(debug_log, "DEBUG")
            logger.debug("Temporary debug information")
            
            # 移除临时调试日志
            logger.remove_output(debug_log)
            logger.debug("This debug should not go to debug.log anymore")
            
            # 验证文件内容
            runtime_log_path = os.path.join(temp_dir, "runtime.log")
            with open(runtime_log_path, 'r') as f:
                runtime_content = f.read()
                assert "Runtime logging enabled" in runtime_content
                assert "This error message should appear everywhere" in runtime_content
                assert "This debug should not go to debug.log anymore" in runtime_content
            
            # 验证临时调试文件存在且包含预期内容
            with open(debug_log, 'r') as f:
                debug_content = f.read()
                assert "Temporary debug information" in debug_content
                assert "This debug should not go to debug.log anymore" not in debug_content


@pytest.mark.unit
class TestErrorHandling:
    """错误处理测试"""
    
    def test_handler_creation_failure(self):
        """测试handler创建失败的处理"""
        # 使用安全的测试目录
        with sage_temp_directory() as temp_dir:
            invalid_path = os.path.join(temp_dir, "invalid", "nested", "path")
            with patch('os.makedirs', side_effect=OSError("Permission denied")):
                logger = CustomLogger(
                    outputs=[("test.log", "INFO")],
                    log_base_folder=invalid_path
                )
                
                # 应该能创建logger，但handler为None
                file_config = next(c for c in logger.output_configs if c['target'] == "test.log")
                assert file_config['handler'] is None
    
    def test_file_logging_with_invalid_directory(self):
        """测试无效目录的文件日志处理"""
        # 这里测试目录创建失败的情况
        with sage_temp_directory() as temp_dir:
            invalid_file_path = os.path.join(temp_dir, "invalid", "path", "test.log")
            with patch('logging.FileHandler', side_effect=OSError("Cannot create file")):
                logger = CustomLogger([(invalid_file_path, "INFO")])
                
                # logger应该能正常创建，但文件handler为None
                file_config = logger.output_configs[0]
                assert file_config['handler'] is None
    
    def test_logging_without_handlers(self):
        """测试没有有效handler时的日志记录"""
        with patch.object(CustomLogger, '_create_handler', return_value=None):
            logger = CustomLogger([("test.log", "INFO")])
            
            # 应该能调用日志方法而不出错
            logger.info("Test message")
            logger.error("Test error")


# 性能测试
@pytest.mark.slow
class TestCustomLoggerPerformance:
    """CustomLogger性能测试"""
    
    def test_logging_performance(self):
        """测试日志记录性能"""
        import time
        
        with sage_temp_directory() as temp_dir:
            logger = CustomLogger(
                outputs=[
                    ("console", "INFO"),
                    ("perf_test.log", "DEBUG")
                ],
                log_base_folder=temp_dir
            )
            
            # 测试大量日志记录的性能
            num_logs = 1000
            start_time = time.time()
            
            for i in range(num_logs):
                if i % 4 == 0:
                    logger.debug(f"Debug message {i}")
                elif i % 4 == 1:
                    logger.info(f"Info message {i}")
                elif i % 4 == 2:
                    logger.warning(f"Warning message {i}")
                else:
                    logger.error(f"Error message {i}")
            
            elapsed_time = time.time() - start_time
            
            # 性能断言
            assert elapsed_time < 5.0  # 1000条日志应在5秒内完成
            
            # 验证所有日志都被记录
            log_file = os.path.join(temp_dir, "perf_test.log")
            with open(log_file, 'r') as f:
                content = f.read()
                assert f"Debug message {num_logs-4}" in content
                assert f"Error message {num_logs-1}" in content
    
    def test_multiple_handlers_performance(self):
        """测试多handler性能"""
        import time
        
        with sage_temp_directory() as temp_dir:
            # 创建多个输出handler
            outputs = [("console", "INFO")]
            for i in range(10):
                outputs.append((f"log_{i}.log", "DEBUG"))
            
            logger = CustomLogger(outputs, log_base_folder=temp_dir)
            
            # 测试性能
            num_logs = 100
            start_time = time.time()
            
            for i in range(num_logs):
                logger.info(f"Multi-handler message {i}")
            
            elapsed_time = time.time() - start_time
            
            # 多handler的性能应该仍然可接受
            assert elapsed_time < 10.0  # 10个handler * 100条日志应在10秒内完成
            
            # 验证所有文件都包含日志
            for i in range(10):
                log_file = os.path.join(temp_dir, f"log_{i}.log")
                assert os.path.exists(log_file)
                with open(log_file, 'r') as f:
                    content = f.read()
                    assert "Multi-handler message" in content
