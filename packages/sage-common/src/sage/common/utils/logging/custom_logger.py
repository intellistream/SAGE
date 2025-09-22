import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Union, Optional, Tuple
import threading
import inspect
from .custom_formatter import CustomFormatter  # 假设有一个自定义格式化器





class CustomLogger:
    """
    简化的自定义Logger类
    支持多种输出目标配置：
    - "console": 控制台输出
    - 相对路径: 相对于log_base_folder的路径
    - 绝对路径: 完整路径的文件输出
    """
    # 全局console debug开关
    _global_console_debug_enabled: bool = True
    _lock = threading.Lock()
    
    # 日志级别映射
    _LEVEL_MAPPING = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'WARN': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
        'FATAL': logging.CRITICAL,
    }

    def __init__(self,
                 outputs: List[Tuple[str, Union[str, int]]] = [("console", "INFO")],
                 name: str = None,
                 log_base_folder: str = None):
        """
        初始化自定义Logger
        
        Args:
            outputs: 输出配置列表，每个元素为 (output_target, level) 元组
                    - output_target 可以是:
                      - "console": 控制台输出
                      - 相对路径: 相对于log_base_folder的路径，如 "app.log", "logs/error.log"
                      - 绝对路径: 完整路径，如 "/tmp/app.log"
                    - level 可以是字符串("DEBUG", "INFO"等) 或数字
            name: logger名称，默认使用 "Logger"
            log_base_folder: 日志基础文件夹，用于解析相对路径。如果为None，则不支持相对路径
        
        Examples:
            # JobManager示例 - 必须提供log_base_folder才能使用相对路径
            logger = CustomLogger([
                ("console", "INFO"),
                ("jobmanager.log", "DEBUG"),           # 相对路径
                ("error.log", "ERROR"),               # 相对路径
            ], name="JobManager", log_base_folder="/tmp/sage/logs")
            
            # 仅使用绝对路径示例 - 无需log_base_folder
            logger = CustomLogger([
                ("console", "INFO"),
                ("/tmp/app.log", "DEBUG"),             # 绝对路径
                ("/var/log/error.log", "ERROR")        # 绝对路径
            ], name="MyApp")
            
            # 混合路径示例 - 需要log_base_folder支持相对路径
            logger = CustomLogger([
                ("console", "INFO"),
                ("app.log", "DEBUG"),                 # 相对于log_base_folder
                ("/var/log/system.log", "ERROR")      # 绝对路径
            ], name="MyApp", log_base_folder="./logs")
        """
        self.name = name or "Logger"
        self.log_base_folder = log_base_folder
        
        # 如果提供了log_base_folder，确保其存在
        if self.log_base_folder:
            Path(self.log_base_folder).mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(self.name)

        # 解析输出配置 - 需要在早期返回之前初始化
        self.output_configs = []

        # 清除已有handlers以确保重新配置
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
            
        enabled_levels = []
        
        for output_target, level in outputs:
            level_int = self._extract_log_level(level)
            self.output_configs.append({
                'target': output_target,
                'level': level_int,
                'level_str': logging.getLevelName(level_int),
                'handler': None,
                'resolved_path': self._resolve_path(output_target)
            })
            enabled_levels.append(level_int)

        # 设置logger的最低级别
        min_level = min(enabled_levels) if enabled_levels else logging.INFO
        self.logger.setLevel(min_level)

        # 创建统一的自定义格式化器
        formatter = CustomFormatter()

        # 为每个输出目标创建handler
        for config in self.output_configs:
            handler = self._create_handler(config, formatter)
            if handler:
                handler.setLevel(config['level'])
                self.logger.addHandler(handler)
                config['handler'] = handler

        # 不传播到父logger
        self.logger.propagate = False

    def _resolve_path(self, output_target: str) -> str:
        """
        解析输出路径
        
        Args:
            output_target: 输出目标
            
        Returns:
            str: 解析后的路径
            
        Raises:
            ValueError: 当使用相对路径但未设置log_base_folder时
        """
        if output_target == "console":
            return "console"
        
        # 检查是否为绝对路径
        if os.path.isabs(output_target):
            return output_target
        else:
            # 相对路径需要log_base_folder支持
            if not self.log_base_folder:
                raise ValueError(
                    f"Cannot use relative path '{output_target}' without log_base_folder. "
                    f"Please provide log_base_folder in __init__ or use absolute path."
                )
            return os.path.join(self.log_base_folder, output_target)

    def _extract_log_level(self, level_setting: Union[str, int]) -> int:
        """
        从级别设置中提取日志级别
        
        Args:
            level_setting: 级别设置
        
        Returns:
            int: 对应的日志级别数值
        """
        if isinstance(level_setting, str):
            level_str = level_setting.upper()
            if level_str not in self._LEVEL_MAPPING:
                raise ValueError(f"Invalid log level: {level_setting}. "
                               f"Valid levels are: {list(self._LEVEL_MAPPING.keys())}")
            return self._LEVEL_MAPPING[level_str]
        elif isinstance(level_setting, int):
            return level_setting
        else:
            raise TypeError(f"level_setting must be str or int, got {type(level_setting)}")

    def _create_handler(self, config: dict, formatter: CustomFormatter) -> Optional[logging.Handler]:
        """
        根据输出配置创建对应的handler
        
        Args:
            config: 输出配置字典
            formatter: 格式化器
            
        Returns:
            logging.Handler: 创建的handler，如果创建失败返回None
        """
        try:
            if config['target'] == "console":
                # 控制台输出
                if not self._global_console_debug_enabled:
                    return None
                handler = logging.StreamHandler()
                handler.setFormatter(formatter)
                return handler
            else:
                # 文件输出
                file_path = config['resolved_path']
                log_dir = os.path.dirname(file_path)
                if log_dir:  # 如果有目录路径
                    os.makedirs(log_dir, exist_ok=True)
                handler = logging.FileHandler(file_path, encoding='utf-8')
                handler.setFormatter(formatter)
                return handler
                
        except Exception as e:
            print(f"Failed to create handler for {config['target']}: {e}")
            return None

    def get_output_configs(self) -> List[dict]:
        """获取当前输出配置"""
        return [
            {
                'target': config['target'],
                'resolved_path': config['resolved_path'],
                'level': config['level_str'],  # Return string level for public API consistency
                'level_str': config['level_str'],
                'level_num': config['level'],
                'handler_active': config['handler'] is not None
            }
            for config in self.output_configs
        ]

    def print_current_configs(self):
        """打印当前输出配置"""
        configs = self.get_output_configs()
        print(f"\n=== Logger '{self.name}' Output Configurations ===")
        if self.log_base_folder:
            print(f"Log base folder: {self.log_base_folder}")
        else:
            print("Log base folder: Not set (relative paths not supported)")
        for i, config in enumerate(configs, 1):
            status = "ACTIVE" if config['handler_active'] else "INACTIVE"
            print(f"{i}. Target: {config['target']}")
            if config['target'] != "console":
                print(f"   Resolved Path: {config['resolved_path']}")
            print(f"   Level: {config['level']} ({config['level_num']}) - {status}")
        print(f"Logger minimum level: {logging.getLevelName(self.logger.level)} ({self.logger.level})")
        print("=" * 60)

    def update_output_level(self, target_index_or_name: Union[int, str], new_level: Union[str, int]):
        """
        动态更新指定输出的级别
        
        Args:
            target_index_or_name: 目标索引(0开始)或目标名称
            new_level: 新的日志级别
        """
        # 查找目标配置
        target_config = None
        if isinstance(target_index_or_name, int):
            if 0 <= target_index_or_name < len(self.output_configs):
                target_config = self.output_configs[target_index_or_name]
        else:
            for config in self.output_configs:
                if config['target'] == target_index_or_name:
                    target_config = config
                    break
        
        if not target_config:
            raise ValueError(f"Output target not found: {target_index_or_name}")
        
        # 更新级别
        new_level_int = self._extract_log_level(new_level)
        target_config['level'] = new_level_int
        target_config['level_str'] = logging.getLevelName(new_level_int)
        
        # 更新handler级别
        if target_config['handler']:
            target_config['handler'].setLevel(new_level_int)
        
        # 更新logger的最低级别
        enabled_levels = [config['level'] for config in self.output_configs if config['handler']]
        min_level = min(enabled_levels) if enabled_levels else logging.INFO
        self.logger.setLevel(min_level)
        
        print(f"Updated {target_config['target']} level to {target_config['level_str']}")

    def add_output(self, output_target: str, level: Union[str, int]):
        """
        动态添加新的输出目标
        
        Args:
            output_target: 输出目标
            level: 日志级别
        """
        level_int = self._extract_log_level(level)
        
        # 创建新配置
        new_config = {
            'target': output_target,
            'level': level_int,
            'level_str': logging.getLevelName(level_int),
            'handler': None,
            'resolved_path': self._resolve_path(output_target)
        }
        
        # 创建handler
        formatter = CustomFormatter()
        handler = self._create_handler(new_config, formatter)
        if handler:
            handler.setLevel(level_int)
            self.logger.addHandler(handler)
            new_config['handler'] = handler
            
        self.output_configs.append(new_config)
        
        # 更新logger最低级别
        enabled_levels = [config['level'] for config in self.output_configs if config['handler']]
        min_level = min(enabled_levels) if enabled_levels else logging.INFO
        self.logger.setLevel(min_level)
        
        print(f"Added output: {output_target} -> {new_config['resolved_path']} with level {new_config['level_str']}")

    def remove_output(self, target_index_or_name: Union[int, str]):
        """
        移除指定的输出目标
        
        Args:
            target_index_or_name: 目标索引或名称
        """
        # 查找并移除配置
        target_config = None
        target_index = None
        
        if isinstance(target_index_or_name, int):
            if 0 <= target_index_or_name < len(self.output_configs):
                target_index = target_index_or_name
                target_config = self.output_configs[target_index]
        else:
            for i, config in enumerate(self.output_configs):
                if config['target'] == target_index_or_name:
                    target_index = i
                    target_config = config
                    break
        
        if not target_config:
            raise ValueError(f"Output target not found: {target_index_or_name}")
        
        # 移除handler
        if target_config['handler']:
            self.logger.removeHandler(target_config['handler'])
        
        # 移除配置
        self.output_configs.pop(target_index)
        
        # 更新logger最低级别
        enabled_levels = [config['level'] for config in self.output_configs if config['handler']]
        min_level = min(enabled_levels) if enabled_levels else logging.INFO
        self.logger.setLevel(min_level)
        
        print(f"Removed output: {target_config['target']}")

    def _log_with_caller_info(self, level: int, message: str, exc_info: bool = False):
        """
        使用调用者信息记录日志，而不是CustomLogger的信息
        """
        # 获取调用栈，跳过当前方法和调用的debug/info/等方法
        frame = inspect.currentframe()
        try:
            # 跳过 _log_with_caller_info -> debug/info/warning/error -> 实际调用位置
            caller_frame = frame.f_back.f_back
            if caller_frame:
                pathname = caller_frame.f_code.co_filename
                lineno = caller_frame.f_lineno
                # 如果 exc_info=True，就取当前异常信息元组；否则为 None
                err = sys.exc_info() if exc_info else None
                # 创建一个临时的LogRecord，手动设置调用者信息
                record = self.logger.makeRecord(
                    name=self.logger.name,
                    level=level,
                    fn=pathname,
                    lno=lineno,
                    msg=message,
                    args=(),
                    exc_info=err
                )

                # 直接调用handlers处理记录
                self.logger.handle(record)
            else:
                # 回退到普通logging
                self.logger.log(level, message, exc_info=exc_info)
        finally:
            del frame

    def debug(self, message: str):
        """Debug级别日志"""
        self._log_with_caller_info(logging.DEBUG, message)

    def info(self, message: str):
        """Info级别日志"""
        self._log_with_caller_info(logging.INFO, message)

    def warning(self, message: str):
        """Warning级别日志"""
        self._log_with_caller_info(logging.WARNING, message)

    def error(self, message: str, exc_info: bool = False):
        """Error级别日志"""
        self._log_with_caller_info(logging.ERROR, message, exc_info)

    def critical(self, message: str):
        """Critical级别日志"""
        self._log_with_caller_info(logging.CRITICAL, message)

    def exception(self, message: str):
        """异常级别日志，自动包含异常信息"""
        self.error(message, exc_info=True)

    @classmethod
    def get_available_levels(cls) -> list:
        """获取所有可用的日志级别"""
        return list(cls._LEVEL_MAPPING.keys())

    @classmethod
    def disable_global_console_debug(cls):
        """全局禁用所有console debug输出"""
        with cls._lock:
            cls._global_console_debug_enabled = False

    @classmethod
    def enable_global_console_debug(cls):
        """全局启用所有console debug输出"""
        with cls._lock:
            cls._global_console_debug_enabled = True

    @classmethod
    def is_global_console_debug_enabled(cls) -> bool:
        """检查全局console debug是否启用"""
        return cls._global_console_debug_enabled