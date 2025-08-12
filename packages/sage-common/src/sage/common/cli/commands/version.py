#!/usr/bin/env python3
"""
SAGE CLI Version Command
显示版本信息
"""

import typer

app = typer.Typer(name="version", help="📋 版本信息")

@app.command()
def show():
    """显示版本信息"""
    print("🚀 SAGE - Streaming-Augmented Generative Execution")
    print("Version: 0.1.0")
    print("Author: IntelliStream")
    print("Repository: https://github.com/intellistream/SAGE")
    print("")
    print("💡 Tips:")
    print("   sage job list         # 查看作业列表")
    print("   sage deploy start     # 启动SAGE系统")
    print("   sage extensions       # 查看可用扩展")
    print("   sage-dev --help       # 开发工具")
    print("   sage-server start     # 启动Web界面")

# 为了向后兼容，也提供一个直接的version命令
@app.callback(invoke_without_command=True)
def version_callback(ctx: typer.Context):
    """显示版本信息"""
    if ctx.invoked_subcommand is None:
        show()
