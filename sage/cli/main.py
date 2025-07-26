#!/usr/bin/env python3
"""
SAGE CLI - 统一命令行工具
Stream Analysis and Graph Engine
"""

import typer
from typing import Optional

# 导入子命令模块
from sage.cli.job import app as job_app
from sage.cli.deploy import app as deploy_app
from sage.cli.jobmanager import app as jobmanager_app

# 创建主应用
app = typer.Typer(
    name="sage",
    help="🚀 SAGE - Stream Analysis and Graph Engine CLI",
    no_args_is_help=True
)

# 注册子命令
app.add_typer(job_app, name="job", help="📋 作业管理 - 提交、监控、管理作业")
app.add_typer(deploy_app, name="deploy", help="🎯 系统部署 - 启动、停止、监控系统")
app.add_typer(jobmanager_app, name="jobmanager", help="🛠️ JobManager管理 - 启动、停止、重启JobManager")

@app.command("version")
def version():
    """显示版本信息"""
    print("🚀 SAGE - Stream Analysis and Graph Engine")
    print("Version: 0.1.1")
    print("Author: IntelliStream")
    print("Repository: https://github.com/intellistream/SAGE")

@app.command("config")
def config_info():
    """显示配置信息"""
    from pathlib import Path
    import yaml
    
    config_path = Path.home() / ".sage" / "config.yaml"
    
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
            print("📋 Current SAGE Configuration:")
            print(yaml.dump(config, default_flow_style=False))
        except Exception as e:
            print(f"❌ Failed to load config: {e}")
    else:
        print("ℹ️  No configuration file found at ~/.sage/config.yaml")
        print("   Using default settings")

@app.callback()
def main(
    version: Optional[bool] = typer.Option(None, "--version", "-v", help="显示版本信息")
):
    """
    SAGE CLI - Stream Analysis and Graph Engine 命令行工具
    
    🚀 功能特性:
    • 作业管理: 提交、监控、管理流处理作业
    • 系统部署: 启动、停止、监控SAGE系统
    • 实时监控: 查看作业状态和系统健康
    
    📖 使用示例:
    sage job list                    # 列出所有作业
    sage job show 1                  # 显示作业1的详情
    sage job run script.py           # 运行Python脚本
    sage deploy start               # 启动SAGE系统
    sage deploy status              # 查看系统状态
    
    💡 提示: 使用 'sage <command> --help' 查看具体命令帮助
    """
    if version:
        print("SAGE CLI v0.1.1")
        raise typer.Exit()

if __name__ == "__main__":
    app()
