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

# 导入现有的 issues 命令
try:
    # issues 命令在 sage.tools.cli.commands.dev.main 中定义
    # 需要重新导入或移动
    from sage.tools.dev.utils.issues_manager import IssuesManager

    issues_app = typer.Typer(
        name="issues",
        help="📋 Issues 管理",
        no_args_is_help=True,
    )

    @issues_app.command(name="status")
    def issues_status():
        """查看 Issues 状态"""
        manager = IssuesManager()
        manager.show_status()

    @issues_app.command(name="download")
    def issues_download():
        """下载 Issues"""
        manager = IssuesManager()
        manager.download()

    @issues_app.command(name="stats")
    def issues_stats():
        """Issues 统计"""
        manager = IssuesManager()
        manager.show_stats()

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
