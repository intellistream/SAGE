"""
Command registry for managing CLI commands.
"""

from typing import Dict, List
import typer
from pathlib import Path
import importlib


class CommandRegistry:
    """命令注册器，负责自动发现和注册命令"""
    
    def __init__(self):
        self.commands: Dict[str, typer.Typer] = {}
        self.command_modules: Dict[str, any] = {}
    
    def discover_commands(self, commands_path: Path) -> Dict[str, typer.Typer]:
        """自动发现命令模块"""
        command_files = []
        
        # 查找所有 Python 文件作为潜在命令
        for file_path in commands_path.glob("*.py"):
            if file_path.name.startswith("_"):  # 跳过私有文件
                continue
            if file_path.stem == "__init__":  # 跳过 __init__.py
                continue
                
            command_files.append(file_path.stem)
        
        # 动态导入命令模块
        for command_name in command_files:
            try:
                module = importlib.import_module(f"sage.common.dev.cli.commands.{command_name}")
                
                # 查找 app 对象或命令类
                if hasattr(module, 'app'):
                    self.commands[command_name] = module.app
                    self.command_modules[command_name] = module
                elif hasattr(module, 'command'):
                    self.commands[command_name] = module.command.app
                    self.command_modules[command_name] = module
                    
            except ImportError as e:
                # 静默跳过无法导入的模块
                continue
        
        return self.commands
    
    def get_command(self, name: str) -> typer.Typer:
        """获取指定命令"""
        return self.commands.get(name)
    
    def list_commands(self) -> List[str]:
        """列出所有可用命令"""
        return list(self.commands.keys())
    
    def register_command(self, name: str, app: typer.Typer):
        """手动注册命令"""
        self.commands[name] = app
