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
    print("🚀 SAGE - Stream Analysis and Graph Engine")
    print("Version: 0.1.2")
    print("Author: IntelliStream")
    print("Repository: https://github.com/intellistream/SAGE")
    print("")
    print("💡 Tip: Use 'sage-core' for unified core commands:")
    print("   sage-core jobmanager  # instead of sage-jobmanager")
    print("   sage-core worker      # instead of sage-worker")
    print("   sage-core cluster     # instead of sage-cluster")

# 为了向后兼容，也提供一个直接的version命令
@app.callback(invoke_without_command=True)
def version_callback(ctx: typer.Context):
    """显示版本信息"""
    if ctx.invoked_subcommand is None:
        show()
