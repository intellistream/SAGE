#!/usr/bin/env python3
"""
SAGE Core CLI - 统一命令行接口
所有SAGE核心功能的统一入口点
"""

import typer
from rich.console import Console
from rich.table import Table
import sys
from typing import Optional

app = typer.Typer(
    name="sage-core",
    help="SAGE Core unified command line interface",
    rich_markup_mode="rich"
)

console = Console()

@app.command()
def version():
    """显示版本信息"""
    console.print("[bold blue]SAGE Framework v0.1.0[/bold blue]")
    console.print("统一内核 (Core + Runtime + Utils + CLI)")

@app.command()
def info():
    """显示系统信息"""
    table = Table(title="SAGE System Information")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    
    table.add_row("Kernel", "✓ Active")
    table.add_row("Middleware", "✓ Active") 
    table.add_row("Apps", "✓ Active")
    table.add_row("CLI", "✓ Active")
    
    console.print(table)

# 尝试动态加载子命令，但不因缺失而失败
try:
    from sage.common.cli.commands.jobmanager import app as jobmanager_app
    app.add_typer(jobmanager_app, name="jobmanager", help="作业管理器控制")
except ImportError:
    pass

try:
    from sage.common.cli.commands.worker import app as worker_app
    app.add_typer(worker_app, name="worker", help="工作节点管理")
except ImportError:
    pass

try:
    from sage.common.cli.commands.head import app as head_app
    app.add_typer(head_app, name="head", help="头节点管理")
except ImportError:
    pass

try:
    from sage.common.cli.commands.cluster import app as cluster_app
    app.add_typer(cluster_app, name="cluster", help="集群管理")
except ImportError:
    pass

try:
    from sage.common.cli.commands.job import app as job_app
    app.add_typer(job_app, name="job", help="作业控制")
except ImportError:
    pass

try:
    from sage.common.cli.commands.deploy import app as deploy_app
    app.add_typer(deploy_app, name="deploy", help="部署管理")
except ImportError:
    pass

try:
    from sage.common.cli.commands.extensions import app as extensions_app
    app.add_typer(extensions_app, name="extensions", help="扩展管理")
except ImportError:
    pass

try:
    from sage.common.cli.commands.config import app as config_app
    app.add_typer(config_app, name="config", help="配置管理")
except ImportError:
    pass

if __name__ == "__main__":
    app()

import sys
import typer
from typing import Optional

app = typer.Typer(
    name="sage-core",
    help="SAGE Core unified command line interface",
    add_completion=False
)

# 导入各个子模块的app
try:
    from sage.common.cli.commands.jobmanager import app as jobmanager_app
    from sage.common.cli.commands.worker import app as worker_app
    from sage.common.cli.commands.head import app as head_app
    from sage.common.cli.commands.cluster import app as cluster_app
    from sage.common.cli.commands.job import app as job_app
    from sage.common.cli.commands.deploy import app as deploy_app
    from sage.common.cli.commands.extensions import app as extensions_app
    from sage.common.cli.commands.config import app as config_app
    
    # 添加子命令
    app.add_typer(jobmanager_app, name="jobmanager", help="JobManager operations")
    app.add_typer(worker_app, name="worker", help="Worker node operations")
    app.add_typer(head_app, name="head", help="Head node operations")
    app.add_typer(cluster_app, name="cluster", help="Cluster management")
    app.add_typer(job_app, name="job", help="Job operations")
    app.add_typer(deploy_app, name="deploy", help="Deployment operations")
    app.add_typer(extensions_app, name="extensions", help="Extensions management")
    app.add_typer(config_app, name="config", help="Configuration management")

except ImportError as e:
    print(f"⚠️ Warning: Some CLI modules not available: {e}")

@app.command()
def version():
    """Show version information"""
    from sage.kernel import __version__
    typer.echo(f"SAGE Core version: {__version__}")

@app.command()
def info():
    """Show system information"""
    typer.echo("🎯 SAGE Core - Unified CLI")
    typer.echo("=" * 40)
    typer.echo("Available commands:")
    typer.echo("  sage-core jobmanager  # JobManager operations")
    typer.echo("  sage-core worker      # Worker node operations") 
    typer.echo("  sage-core head        # Head node operations")
    typer.echo("  sage-core cluster     # Cluster management")
    typer.echo("  sage-core job         # Job operations")
    typer.echo("  sage-core deploy      # Deployment operations")
    typer.echo("  sage-core extensions  # Extensions management")
    typer.echo("  sage-core config      # Configuration management")
    typer.echo("")
    typer.echo("For detailed help on any command, use:")
    typer.echo("  sage-core <command> --help")

if __name__ == "__main__":
    app()
