#!/usr/bin/env python3
"""
SAGE CLI - 统一命令行工具
S    # 显示扩展信息面板
    console.print(Panel.fit(
        "[bold cyan]🧩 SAGE 扩展生态系统[/bold cyan]\n\n"
        "SAGE 提供丰富的扩展来满足不同使用场景的需求",
        title="扩展信息"
    ))
    
    # 创建扩展表格
    table = Table(title="可用扩展", show_header=True, header_style="bold magenta")
    table.add_column("扩展名称", style="cyan", width=15)
    table.add_column("类型", style="green", width=8) 
    table.add_column("描述", style="white", width=28)
    table.add_column("安装命令", style="yellow", width=30)s and Graph Engine
"""

import typer
from typing import Optional

# 导入核心子命令模块（这些都是核心功能，不依赖optional packages）
from sage.common.cli.commands.job import app as job_app
from sage.common.cli.commands.deploy import app as deploy_app
from sage.common.cli.commands.jobmanager import app as jobmanager_app
from sage.common.cli.commands.worker import app as worker_app
from sage.common.cli.commands.head import app as head_app
from sage.common.cli.commands.cluster import app as cluster_app
from sage.common.cli.commands.version import app as version_app
from sage.common.cli.commands.config import app as config_app
from sage.common.cli.commands.doctor import app as doctor_app
from sage.common.cli.commands.webui import app as webui_app
from sage.common.cli.commands.studio import app as studio_app

# 创建主应用
app = typer.Typer(
    name="sage",
    help="🚀 SAGE - Streaming-Augmented Generative Execution CLI",
    no_args_is_help=True
)

# 注册核心子命令
app.add_typer(version_app, name="version", help="📋 版本信息")
app.add_typer(config_app, name="config", help="⚙️ 配置管理")
app.add_typer(doctor_app, name="doctor", help="🔍 系统诊断")
app.add_typer(webui_app, name="web-ui", help="🌐 Web UI - Web管理界面和API文档")
app.add_typer(studio_app, name="studio", help="🎨 Studio - 低代码可视化管道编辑器")
app.add_typer(job_app, name="job", help="📋 作业管理 - 提交、监控、管理作业")
app.add_typer(deploy_app, name="deploy", help="🎯 系统部署 - 启动、停止、监控系统")
app.add_typer(jobmanager_app, name="jobmanager", help="🛠️ JobManager管理 - 启动、停止、重启JobManager")
app.add_typer(cluster_app, name="cluster", help="🏗️ 集群管理 - 统一管理Ray集群")
app.add_typer(head_app, name="head", help="🏠 Head节点管理 - 管理Ray集群的Head节点")
app.add_typer(worker_app, name="worker", help="👷 Worker节点管理 - 管理Ray集群的Worker节点")

@app.command("extensions")
def extensions_info():
    """🧩 显示可用扩展信息"""
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    
    console = Console()
    
    # 显示扩展信息面板
    console.print(Panel.fit(
        "[bold cyan]🧩 SAGE 扩展生态系统[/bold cyan]\n\n"
        "SAGE 提供丰富的扩展来满足不同使用场景的需求",
        title="扩展信息"
    ))
    
    # 创建扩展表格
    table = Table(title="可用扩展", show_header=True, header_style="bold magenta")
    table.add_column("扩展名称", style="cyan", width=15)
    table.add_column("类型", style="green", width=8) 
    table.add_column("描述", style="white", width=35)
    table.add_column("扩展标识", style="yellow", width=20)
    
        # 免费扩展
    table.add_row("frontend", "🆓 免费", "Web界面和仪表板", "pip install isage\[frontend\]")
    table.add_row("dev", "🆓 免费", "开发工具和调试功能", "pip install isage\[dev\]")
    table.add_row("full", "🆓 免费", "所有免费扩展的集合", "pip install isage\[full\]")
    
    # 商业扩展
    table.add_row("commercial", "💰 商业", "C++扩展和高性能组件", "pip install isage\[commercial\]")
    
    console.print(table)
    
    # 显示当前安装状态
    console.print("\n[bold green]当前安装状态:[/bold green]")
    
    # 检查frontend
    try:
        import fastapi
        import uvicorn
        console.print("✅ frontend - Web界面可用")
    except ImportError:
        console.print("❌ frontend - 未安装")
    
    # 检查dev (通过sage-dev命令检查)
    import shutil
    if shutil.which("sage-dev"):
        console.print("✅ dev - 开发工具可用")
    else:
        console.print("❌ dev - 未安装")
    
    # 检查commercial (检查是否有商业扩展的特定功能)
    try:
        import importlib
        importlib.import_module('sage.commercial')
        console.print("✅ commercial - 商业扩展可用")
    except ImportError:
        console.print("❌ commercial - 未安装")

# 移除的命令说明:
# - server-info: Web服务器信息应该通过 sage-server --help 获取
# - extensions管理: C++扩展管理需要商业授权，核心命令只显示扩展信息

@app.callback()
def callback():
    """
    SAGE CLI - Streaming-Augmented Generative Execution 命令行工具
    
    🚀 功能特性:
    • 作业管理: 提交、监控、管理流处理作业
    • 系统部署: 启动、停止、监控SAGE系统
    • 实时监控: 查看作业状态和系统健康
    
    📖 使用示例:
    sage job list                    # 列出所有作业
    sage deploy start               # 启动SAGE系统
    sage cluster status             # 查看集群状态
    sage extensions install         # 安装C++扩展
    
    🔗 更多信息: https://github.com/intellistream/SAGE
    """
    pass

if __name__ == "__main__":
    app()