"""
CLI Commands package for SAGE Development Toolkit.

This package contains modular command implementations organized by functionality.
Each command file corresponds to a CLI subcommand.
"""

from pathlib import Path
import importlib


def get_apps():
    """自动发现并返回所有命令应用"""
    commands = {}
    commands_dir = Path(__file__).parent
    
    # 自动发现所有命令文件
    command_files = []
    for file_path in commands_dir.glob("*.py"):
        if file_path.name.startswith("_"):  # 跳过私有文件
            continue
        if file_path.stem in ["__init__", "common"]:  # 跳过特殊文件
            continue
        command_files.append(file_path.stem)
    
    # 动态导入命令模块
    for command_name in sorted(command_files):
        try:
            module = importlib.import_module(f".{command_name}", package=__name__)
            
            if hasattr(module, 'app'):
                commands[command_name] = module.app
            elif hasattr(module, 'command') and hasattr(module.command, 'app'):
                commands[command_name] = module.command.app
                
        except ImportError:
            # 静默跳过无法导入的模块
            continue
    
    return commands


__all__ = [
    'get_apps'
]
