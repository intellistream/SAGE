#!/usr/bin/env python3
"""
开发模式检查工具

提供装饰器和函数来检查命令是否在开发环境（源码安装）中运行
"""

from collections.abc import Callable
from functools import wraps
from pathlib import Path

import typer
from rich.console import Console

console = Console()


def is_source_installation() -> bool:
    """
    检查是否在源码安装模式下运行

    通过查找 packages 目录来判断是否在开发环境中

    Returns:
        bool: True 如果在源码目录中，False 否则
    """
    # 从当前工作目录开始向上查找
    current_dir = Path.cwd()

    # 最多向上查找 5 层
    for _ in range(5):
        packages_dir = current_dir / "packages"
        if packages_dir.exists() and packages_dir.is_dir():
            # 额外检查是否包含 SAGE 的子包
            sage_packages = [
                "sage",
                "sage-common",
                "sage-kernel",
                "sage-tools",
                "sage-middleware",
                "sage-libs",
            ]
            # 至少找到 3 个包才认为是有效的源码目录
            found_count = sum(1 for pkg in sage_packages if (packages_dir / pkg).exists())
            if found_count >= 3:
                return True

        # 到达根目录
        if current_dir.parent == current_dir:
            break
        current_dir = current_dir.parent

    return False


def get_project_root() -> Path:
    """
    获取项目根目录（包含 packages 目录的目录）

    Returns:
        Path: 项目根目录路径

    Raises:
        FileNotFoundError: 如果未找到项目根目录
    """
    current_dir = Path.cwd()

    for _ in range(5):
        packages_dir = current_dir / "packages"
        if packages_dir.exists() and packages_dir.is_dir():
            return current_dir

        if current_dir.parent == current_dir:
            break
        current_dir = current_dir.parent

    raise FileNotFoundError("未找到 SAGE 项目根目录")


def require_source_code(func: Callable) -> Callable:
    """
    装饰器：要求命令在源码模式下运行

    如果不在源码模式下，显示友好的错误提示并退出

    Usage:
        @app.command()
        @require_source_code
        def my_dev_command():
            ...
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_source_installation():
            console.print("\n[red]❌ 此命令仅在开发模式（源码安装）下可用[/red]\n")

            console.print("[yellow]💡 从源码安装 SAGE：[/yellow]")
            console.print("   [cyan]# 1. 克隆仓库[/cyan]")
            console.print("   git clone https://github.com/intellistream/SAGE.git")
            console.print("   cd SAGE")
            console.print()
            console.print("   [cyan]# 2. 安装为可编辑模式（开发模式）[/cyan]")
            console.print("   pip install -e .")
            console.print()
            console.print("   [cyan]# 或使用快速启动脚本[/cyan]")
            console.print("   ./quickstart.sh")
            console.print()
            console.print("[dim]更多信息请访问: https://github.com/intellistream/SAGE[/dim]")

            raise typer.Exit(1)

        return func(*args, **kwargs)

    return wrapper


def show_dev_mode_info():
    """显示开发模式的信息提示"""
    if is_source_installation():
        console.print("[green]✓[/green] 开发模式已启用")
        try:
            project_root = get_project_root()
            console.print(f"[dim]项目路径: {project_root}[/dim]")
        except FileNotFoundError:
            pass
    else:
        console.print("[yellow]ℹ[/yellow] 当前为标准安装模式")
        console.print("[dim]部分开发命令不可用，从源码安装以启用开发模式[/dim]")
