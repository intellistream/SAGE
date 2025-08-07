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
from sage.cli.extensions import app as extensions_app

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
app.add_typer(worker_app, name="worker", help="👷 Worker节点管理 - 管理Ray集群的Worker节点")
app.add_typer(extensions_app, name="extensions", help="🧩 扩展管理 - 安装和管理C++扩展")

@app.command("version")
def version():
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

@app.command("config")
def config_info():
    """显示配置信息"""
    from .config_manager import get_config_manager
    
    try:
        config_manager = get_config_manager()
        config = config_manager.load_config()
        
        print("📋 SAGE 配置信息:")
        print(f"配置文件: {config_manager.config_path}")
        print(f"数据目录: {config.get('data_dir', '未设置')}")
        print(f"日志级别: {config.get('log_level', '未设置')}")
        print(f"工作目录: {config.get('work_dir', '未设置')}")
        
        if 'ray' in config:
            ray_config = config['ray']
            print(f"Ray地址: {ray_config.get('address', '未设置')}")
            print(f"Ray端口: {ray_config.get('port', '未设置')}")
        
    except Exception as e:
        print(f"❌ 读取配置失败: {e}")
        print("💡 运行 'sage init' 创建配置文件")

@app.command("init")
def init_config(
    force: bool = typer.Option(False, "--force", "-f", help="强制覆盖现有配置")
):
    """初始化SAGE配置文件"""
    from .config_manager import get_config_manager
    
    try:
        config_manager = get_config_manager()
        
        if config_manager.config_path.exists():
            if not force:
                print(f"配置文件已存在: {config_manager.config_path}")
                print("使用 --force 选项覆盖现有配置")
                return
            else:
                print("🔄 覆盖现有配置文件...")
        
        # 创建默认配置
        default_config = {
            "log_level": "INFO",
            "data_dir": "~/sage_data",
            "work_dir": "~/sage_work",
            "ray": {
                "address": "auto",
                "port": 10001
            }
        }
        
        config_manager.save_config(default_config)
        print(f"✅ 配置文件已创建: {config_manager.config_path}")
        print("🔧 你可以编辑配置文件来自定义设置")
        
    except Exception as e:
        print(f"❌ 初始化配置失败: {e}")

@app.command("doctor")
def doctor():
    """诊断SAGE安装和配置"""
    print("🔍 SAGE 系统诊断")
    print("=" * 40)
    
    # 检查Python版本
    import sys
    print(f"Python版本: {sys.version.split()[0]}")
    
    # 检查SAGE安装
    try:
        import sage
        print(f"✅ SAGE安装: v{sage.__version__}")
    except ImportError:
        print("❌ SAGE未安装")
    
    # 检查扩展
    extensions = ["sage_ext", "sage_ext.sage_queue", "sage_ext.sage_db"]
    for ext in extensions:
        try:
            __import__(ext)
            print(f"✅ {ext}")
        except ImportError:
            print(f"⚠️ {ext} 不可用")
    
    # 检查Ray
    try:
        import ray
        print(f"✅ Ray: v{ray.__version__}")
    except ImportError:
        print("❌ Ray未安装")
    
    print("\n💡 如需安装扩展，运行: sage extensions install")

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