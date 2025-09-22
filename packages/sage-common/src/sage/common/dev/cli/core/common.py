"""
Common utilities and imports for CLI commands.
"""

import sys
import time
import traceback
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ...core.toolkit import SAGEDevToolkit
from ...core.exceptions import SAGEDevToolkitError

# 创建控制台对象用于富文本输出
console = Console()

# 全局变量存储toolkit实例
_toolkit: Optional[SAGEDevToolkit] = None


def get_toolkit(
    project_root: Optional[str] = None,
    config_file: Optional[str] = None,
    environment: Optional[str] = None
) -> SAGEDevToolkit:
    """获取或创建toolkit实例"""
    global _toolkit
    
    if _toolkit is None:
        try:
            _toolkit = SAGEDevToolkit(
                project_root=project_root,
                config_file=config_file,
                environment=environment
            )
        except SAGEDevToolkitError as e:
            console.print(f"❌ Error initializing toolkit: {e}", style="red")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"❌ Unexpected error: {e}", style="red")
            raise typer.Exit(1)
    
    return _toolkit


def handle_command_error(e: Exception, operation: str, verbose: bool = False):
    """统一处理命令错误"""
    if isinstance(e, SAGEDevToolkitError):
        console.print(f"❌ {operation} failed: {e}", style="red")
    else:
        console.print(f"❌ {operation} failed: {e}", style="red")
        if verbose:
            console.print(traceback.format_exc(), style="dim red")
    raise typer.Exit(1)


def format_size(size):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


# 公共命令选项
PROJECT_ROOT_OPTION = typer.Option(None, help="Project root directory")
CONFIG_OPTION = typer.Option(None, help="Configuration file path")
ENVIRONMENT_OPTION = typer.Option(None, help="Environment (development/production/ci)")
VERBOSE_OPTION = typer.Option(False, "-v", "--verbose", help="Enable verbose output")
