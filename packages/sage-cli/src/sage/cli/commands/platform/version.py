#!/usr/bin/env python3
"""
SAGE CLI Version Command
显示版本信息
"""

import typer

app = typer.Typer(name="version", help="📋 版本信息")


def _load_version():
    """加载版本信息"""
    try:
        # 尝试从本地包的版本文件加载
        from sage.common._version import __version__

        return __version__
    except ImportError:
        # 如果本地版本文件不存在，尝试从项目根目录加载（开发环境）
        try:
            from sage.common.config import find_sage_project_root

            root_dir = find_sage_project_root()
            version_file = root_dir / "_version.py"

            if version_file.exists():
                version_globals = {}
                with open(version_file, encoding="utf-8") as f:
                    exec(f.read(), version_globals)
                return version_globals.get("__version__", "0.1.3")
        except Exception:
            pass

    # 最后的默认值
    return "0.1.3"


@app.command()
def show():
    """显示版本信息"""
    version = _load_version()
    print("🚀 SAGE - Streaming-Augmented Generative Execution")
    print(f"Version: {version}")
    print("Author: IntelliStream")
    print("Repository: https://github.com/intellistream/SAGE")
    print("")
    print("💡 Tips:")
    print("   sage job list         # 查看作业列表")
    print("   sage studio start     # 启动Studio可视化编辑器")
    print("   sage extensions       # 查看可用扩展")
    print("   sage-dev --help       # 开发工具")
    print("   sage jobmanager start # 启动作业管理器服务")


# 为了向后兼容，也提供一个直接的version命令
@app.callback(invoke_without_command=True)
def version_callback(ctx: typer.Context):
    """显示版本信息"""
    if ctx.invoked_subcommand is None:
        show()
