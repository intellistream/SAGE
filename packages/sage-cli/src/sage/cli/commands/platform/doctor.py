#!/usr/bin/env python3
"""SAGE CLI Doctor Command — diagnose the local environment."""

import typer
from rich.console import Console

from sage.cli.utils.diagnostics import check_dependency_versions

console = Console()
app = typer.Typer(name="doctor", help="🔍 系统诊断")


@app.command()
def check():
    """诊断SAGE安装和配置"""
    console.rule("SAGE 系统诊断")

    # 检查Python版本
    import sys

    console.print(f"🐍 Python 版本: [bold]{sys.version.split()[0]}[/bold]")

    # 检查SAGE安装
    try:
        import sage.common

        console.print(f"✅ SAGE 安装: v{sage.common.__version__}")
    except ImportError as e:
        console.print(f"❌ SAGE 未安装: {e}")

    # 检查扩展 - 只检查实际存在的模块
    extensions = [("sage_db", "sage.middleware.components.sage_db")]

    for ext_name, ext_path in extensions:
        try:
            __import__(ext_path)
            console.print(f"✅ 扩展可用: {ext_name}")
        except ImportError:
            console.print(f"⚠️ 扩展缺失: {ext_name}")

    # 检查Ray
    try:
        import ray

        console.print(f"✅ Ray: v{ray.__version__}")
    except ImportError:
        console.print("❌ Ray 未安装")

    console.print("\n💡 如需安装扩展，运行: [bold]sage extensions install[/bold]")


@app.command()
def compat():
    """检查闭源依赖的兼容性。"""

    success = check_dependency_versions(console=console)
    if not success:
        raise typer.Exit(1)


# 为了向后兼容，也提供一个直接的doctor命令
@app.callback(invoke_without_command=True)
def doctor_callback(ctx: typer.Context):
    """诊断SAGE安装和配置"""
    if ctx.invoked_subcommand is None:
        check()
