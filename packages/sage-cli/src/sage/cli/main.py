#!/usr/bin/env python3
"""
SAGE CLI - 统一命令行工具
Stream Analysis and Graph Engine
"""

import typer
from typing import Optional

# 导入子命令模块
from sage.cli.commands.job import app as job_app
from sage.cli.commands.deploy import app as deploy_app
from sage.cli.commands.jobmanager import app as jobmanager_app
from sage.cli.commands.worker import app as worker_app
from sage.cli.commands.head import app as head_app
from sage.cli.commands.cluster import app as cluster_app
from sage.cli.commands.extensions import app as extensions_app
from sage.cli.commands.version import app as version_app
from sage.cli.commands.config import app as config_app
from sage.cli.commands.doctor import app as doctor_app

# 创建主应用
app = typer.Typer(
    name="sage",
    help="🚀 SAGE - Stream Analysis and Graph Engine CLI",
    no_args_is_help=True
)

# 注册子命令
app.add_typer(version_app, name="version", help="📋 版本信息")
app.add_typer(config_app, name="config", help="⚙️ 配置管理")
app.add_typer(doctor_app, name="doctor", help="🔍 系统诊断")
app.add_typer(job_app, name="job", help="📋 作业管理 - 提交、监控、管理作业")
app.add_typer(deploy_app, name="deploy", help="🎯 系统部署 - 启动、停止、监控系统")
app.add_typer(jobmanager_app, name="jobmanager", help="🛠️ JobManager管理 - 启动、停止、重启JobManager")
app.add_typer(cluster_app, name="cluster", help="🏗️ 集群管理 - 统一管理Ray集群")
app.add_typer(head_app, name="head", help="🏠 Head节点管理 - 管理Ray集群的Head节点")
app.add_typer(worker_app, name="worker", help="👷 Worker节点管理 - 管理Ray集群的Worker节点")
app.add_typer(extensions_app, name="extensions", help="🧩 扩展管理 - 安装和管理C++扩展")

@app.callback()
def callback():
    """
    SAGE CLI - Stream Analysis and Graph Engine 命令行工具
    
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