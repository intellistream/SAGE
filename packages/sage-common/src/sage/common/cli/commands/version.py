#!/usr/bin/env python3
"""
SAGE CLI Version Command
显示版本信息
"""

import typer

app = typer.Typer(name="version", help="📋 版本信息")

def _load_version():
    """从项目根目录动态加载版本信息"""
    from pathlib import Path
    
    # 计算到项目根目录的路径 (common包位于: packages/sage-common/src/sage/common/cli/commands/)
    current_file = Path(__file__).resolve()
    root_dir = current_file.parent.parent.parent.parent.parent.parent  # 向上6层到项目根目录
    version_file = root_dir / "_version.py"
    
    if version_file.exists():
        version_globals = {}
        try:
            with open(version_file, 'r', encoding='utf-8') as f:
                exec(f.read(), version_globals)
            return {
                'version': version_globals.get('__version__', '0.1.4'),
                'author': version_globals.get('__author__', 'SAGE Team'),
                'project_name': version_globals.get('__project_name__', 'SAGE'),
                'project_full_name': version_globals.get('__project_full_name__', 'Streaming-Augmented Generative Execution'),
                'repository': version_globals.get('__repository__', 'https://github.com/intellistream/SAGE')
            }
        except Exception:
            pass
    
    # 默认值（找不到_version.py时使用）
    return {
        'version': '0.1.4',
        'author': 'SAGE Team',
        'project_name': 'SAGE',
        'project_full_name': 'Streaming-Augmented Generative Execution',
        'repository': 'https://github.com/intellistream/SAGE'
    }

@app.command()
def show():
    """显示版本信息"""
    info = _load_version()
    print(f"🚀 {info['project_name']} - {info['project_full_name']}")
    print(f"Version: {info['version']}")
    print(f"Author: {info['author']}")
    print(f"Repository: {info['repository']}")
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
