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
from sage.cli.jobmanager_controller import app as jobmanager_app
from sage.cli.worker_manager import app as worker_app
from sage.cli.head_manager import app as head_app
from sage.cli.cluster_manager import app as cluster_app

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
app.add_typer(cluster_app, name="cluster", help="🏗️ 集群管理 - 统一管理Ray集群")
app.add_typer(head_app, name="head", help="🏠 Head节点管理 - 管理Ray集群的Head节点")
app.add_typer(worker_app, name="worker", help="👥 Worker管理 - 管理Ray集群的Worker节点")

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
    from .config_manager import get_config_manager
    
    try:
        config_manager = get_config_manager()
        config = config_manager.load_config()
        
        print("📋 Current SAGE Configuration:")
        print("=" * 50)
        
        import yaml
        print(yaml.dump(config, default_flow_style=False, allow_unicode=True))
        
    except FileNotFoundError:
        print("❌ Config file not found. Creating default config...")
        config_manager = get_config_manager()
        config_manager.create_default_config()
        print("✅ Default config created at ~/.sage/config.yaml")
        print("💡 Please edit the config file to match your environment")
    except Exception as e:
        print(f"❌ Failed to load config: {e}")

@app.command("init")
def init_config():
    """初始化SAGE配置文件"""
    from .config_manager import get_config_manager
    
    try:
        config_manager = get_config_manager()
        
        if config_manager.config_path.exists():
            print(f"⚠️  Configuration file already exists: {config_manager.config_path}")
            confirm = typer.confirm("Do you want to overwrite it?")
            if not confirm:
                print("❌ Configuration initialization cancelled")
                return
        
        config_manager.create_default_config()
        print(f"✅ Configuration file created: {config_manager.config_path}")
        print("💡 Please edit the config file to match your environment")
        
        # 显示配置模板位置
        from pathlib import Path
        template_path = Path(__file__).parent.parent.parent / "config" / "cluster_config_template.yaml"
        if template_path.exists():
            print(f"📋 Reference template: {template_path}")
        
    except Exception as e:
        print(f"❌ Failed to initialize config: {e}")
        raise typer.Exit(1)

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