"""
GitHub 管理命令组

提供 Issues 管理、PR 管理等功能。
"""

import typer
from rich.console import Console

app = typer.Typer(
    name="github",
    help="🐙 GitHub 管理 - Issues、PR 等",
    no_args_is_help=True,
)

console = Console()

# 导入 issues 命令
try:
    from sage.tools.dev.issues.cli import app as issues_app

    app.add_typer(issues_app, name="issues")

except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 issues 命令: {e}[/yellow]")

    # 创建占位命令
    @app.command(name="issues")
    def issues_placeholder():
        """Issues 管理（待迁移）"""
        console.print("[yellow]Issues 管理功能正在迁移中...[/yellow]")
        console.print("[cyan]请临时使用: sage dev issues[/cyan]")


__all__ = ["app"]
