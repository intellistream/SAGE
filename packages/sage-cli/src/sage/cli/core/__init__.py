#!/usr/bin/env python3
"""
SAGE CLI Core Module
====================

提供CLI命令的通用功能和共有逻辑

Components:
-----------
- base: 基础CLI命令类和装饰器
- output: 统一的输出格式化和显示
- ssh: SSH连接和远程命令执行
- config: 配置文件管理和验证
- exceptions: 自定义异常类
- utils: 通用工具函数
- validation: 输入验证和数据校验
"""

from .base import BaseCommand, CLIException, cli_command, require_connection
from .output import OutputFormatter, format_table, print_status, Colors
from .ssh import SSHManager, RemoteExecutor
from .config import ConfigValidator, load_and_validate_config
from .exceptions import *
from .utils import *
from .validation import *

__all__ = [
    # Base
    'BaseCommand', 'CLIException', 'cli_command', 'require_connection',
    
    # Output
    'OutputFormatter', 'format_table', 'print_status', 'Colors',
    
    # SSH
    'SSHManager', 'RemoteExecutor',
    
    # Config
    'ConfigValidator', 'load_and_validate_config',
    
    # Utils
    'find_project_root', 'ensure_directory', 'run_subprocess',
    
    # Validation
    'validate_host', 'validate_port', 'validate_path'
]
