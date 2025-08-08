"""
Base command class for standardized command structure.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import typer
from .common import console, get_toolkit, handle_command_error


class BaseCommand(ABC):
    """基础命令类，提供统一的命令结构"""
    
    def __init__(self, name: str, help: str):
        self.name = name
        self.help = help
        self.app = typer.Typer(name=name, help=help)
        self._register_commands()
    
    @abstractmethod
    def _register_commands(self):
        """注册命令到 typer app，子类必须实现"""
        pass
    
    def create_standard_options(self):
        """创建标准选项"""
        return {
            'project_root': typer.Option(None, help="Project root directory"),
            'config': typer.Option(None, help="Configuration file path"),
            'environment': typer.Option(None, help="Environment (development/production/ci)"),
            'verbose': typer.Option(False, "-v", "--verbose", help="Enable verbose output")
        }
    
    def execute_with_toolkit(self, func, *args, **kwargs):
        """使用toolkit执行函数，统一错误处理"""
        try:
            project_root = kwargs.pop('project_root', None)
            config = kwargs.pop('config', None) 
            environment = kwargs.pop('environment', None)
            verbose = kwargs.pop('verbose', False)
            
            toolkit = get_toolkit(project_root, config, environment)
            
            if verbose:
                console.print(f"🔧 Executing {self.name} command...", style="blue")
            
            return func(toolkit, *args, **kwargs)
            
        except Exception as e:
            handle_command_error(e, f"{self.name} command", verbose)
    
    def show_success(self, message: str):
        """显示成功信息"""
        console.print(f"✅ {message}", style="green")
    
    def show_info(self, message: str):
        """显示信息"""
        console.print(f"ℹ️  {message}", style="blue")
    
    def show_warning(self, message: str):
        """显示警告"""
        console.print(f"⚠️  {message}", style="yellow")
    
    def show_error(self, message: str):
        """显示错误"""
        console.print(f"❌ {message}", style="red")
