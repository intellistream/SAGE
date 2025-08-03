"""
SAGE Utils Module
================

通用工具包，提供配置管理、日志记录、队列管理等功能。
"""

from .config_loader import load_config
from .logging import get_logger, setup_logging

# 版本信息
__version__ = "1.0.0"
__author__ = "IntelliStream Team"

# 公开的API
__all__ = [
    "load_config",
    "get_logger", 
    "setup_logging",
]