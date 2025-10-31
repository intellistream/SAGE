"""
资源管理命令组

提供模型缓存、数据管理等功能。
"""

import typer
from rich.console import Console

app = typer.Typer(
    name="resource",
    help="💾 资源管理 - 模型缓存、数据管理",
    no_args_is_help=True,
)

console = Console()

# 导入现有的 models 命令组
try:
    from sage.tools.cli.commands.dev.models import app as models_app

    app.add_typer(models_app, name="models")
except ImportError:
    console.print("[yellow]警告: 无法导入 models 命令[/yellow]")


__all__ = ["app"]
