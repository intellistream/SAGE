"""
日志系统模块
============

提供结构化日志和格式化输出功能。
支持多种输出格式和日志级别。
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Union, Dict, Any
from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install

__all__ = ["get_logger", "setup_logging", "LoggerManager"]


class LoggerManager:
    """日志管理器"""
    
    def __init__(self):
        self._loggers: Dict[str, logging.Logger] = {}
        self._configured = False
        self.console = Console()
        
        # 安装Rich的美化traceback
        install(show_locals=True)
    
    def setup(
        self,
        level: Union[str, int] = logging.INFO,
        format_string: Optional[str] = None,
        log_file: Optional[Union[str, Path]] = None,
        use_rich: bool = True,
        show_time: bool = True,
        show_level: bool = True,
        show_path: bool = False,
    ):
        """
        设置全局日志配置
        
        Args:
            level: 日志级别
            format_string: 日志格式字符串
            log_file: 日志文件路径
            use_rich: 是否使用Rich格式化
            show_time: 是否显示时间
            show_level: 是否显示级别
            show_path: 是否显示文件路径
        """
        # 清除已有的handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        # 设置级别
        if isinstance(level, str):
            level = getattr(logging, level.upper())
        root_logger.setLevel(level)
        
        handlers = []
        
        # 控制台处理器
        if use_rich:
            console_handler = RichHandler(
                console=self.console,
                show_time=show_time,
                show_level=show_level,
                show_path=show_path,
                rich_tracebacks=True,
                tracebacks_show_locals=True,
            )
        else:
            console_handler = logging.StreamHandler(sys.stdout)
            if format_string is None:
                format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            formatter = logging.Formatter(format_string)
            console_handler.setFormatter(formatter)
        
        console_handler.setLevel(level)
        handlers.append(console_handler)
        
        # 文件处理器
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_path, encoding='utf-8')
            file_handler.setLevel(level)
            
            if format_string is None:
                format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            file_formatter = logging.Formatter(format_string)
            file_handler.setFormatter(file_formatter)
            
            handlers.append(file_handler)
        
        # 添加处理器
        for handler in handlers:
            root_logger.addHandler(handler)
        
        self._configured = True
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        获取或创建logger
        
        Args:
            name: logger名称
            
        Returns:
            Logger实例
        """
        if name in self._loggers:
            return self._loggers[name]
        
        # 如果还没有配置过，使用默认配置
        if not self._configured:
            self.setup()
        
        logger = logging.getLogger(name)
        self._loggers[name] = logger
        
        return logger


# 全局日志管理器实例
_global_logger_manager = LoggerManager()


def setup_logging(
    level: Union[str, int] = logging.INFO,
    format_string: Optional[str] = None,
    log_file: Optional[Union[str, Path]] = None,
    use_rich: bool = True,
    show_time: bool = True,
    show_level: bool = True,
    show_path: bool = False,
):
    """
    设置全局日志配置 (便捷函数)
    
    Args:
        level: 日志级别
        format_string: 日志格式字符串
        log_file: 日志文件路径
        use_rich: 是否使用Rich格式化
        show_time: 是否显示时间
        show_level: 是否显示级别  
        show_path: 是否显示文件路径
    """
    _global_logger_manager.setup(
        level=level,
        format_string=format_string,
        log_file=log_file,
        use_rich=use_rich,
        show_time=show_time,
        show_level=show_level,
        show_path=show_path,
    )


def get_logger(name: str) -> logging.Logger:
    """
    获取logger (便捷函数)
    
    Args:
        name: logger名称，通常使用 __name__
        
    Returns:
        Logger实例
    """
    return _global_logger_manager.get_logger(name)
