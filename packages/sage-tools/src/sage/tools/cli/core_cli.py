#!/usr/bin/env python3
"""
SAGE Core CLI - 统一命令行接口
所有SAGE核心功能的统一入口点
"""

import typer
# 导入各个子模块的app（直接导入，无需fallback）
from sage.tools.cli.commands.cluster import app as cluster_app
from sage.tools.cli.commands.config import app as config_app
from sage.tools.cli.commands.deploy import app as deploy_app
from sage.tools.cli.commands.extensions import app as extensions_app
from sage.tools.cli.commands.head import app as head_app
from sage.tools.cli.commands.job import app as job_app
from sage.tools.cli.commands.jobmanager import app as jobmanager_app
from sage.tools.cli.commands.worker import app as worker_app

app = typer.Typer(
    name="sage-core",
    help="SAGE Core unified command line interface",
    add_completion=False,
)

# 添加子命令
app.add_typer(jobmanager_app, name="jobmanager", help="JobManager operations")
app.add_typer(worker_app, name="worker", help="Worker node operations")
app.add_typer(head_app, name="head", help="Head node operations")
app.add_typer(cluster_app, name="cluster", help="Cluster management")
app.add_typer(job_app, name="job", help="Job operations")
app.add_typer(deploy_app, name="deploy", help="Deployment operations")
app.add_typer(extensions_app, name="extensions", help="Extensions management")
app.add_typer(config_app, name="config", help="Configuration management")


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
