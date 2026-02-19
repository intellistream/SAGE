#!/usr/bin/env python3
"""Configuration management commands for SAGE."""

import typer

# Import the configuration subcommands
from .env import app as env_app
from .llm_config import app as llm_config_app

app = typer.Typer(name="config", help="⚙️ 配置管理")

# Add config-related subcommands
app.add_typer(llm_config_app, name="llm", help="🤖 LLM 服务配置管理")
app.add_typer(env_app, name="env", help="🌱 环境变量与 .env 文件管理")


@app.command("show")
def config_info():
    """显示配置信息"""
    from ...management.config_manager import get_config_manager

    try:
        config_manager = get_config_manager()
        config = config_manager.load_config()

        print("📋 SAGE 配置信息:")
        print(f"配置文件: {config_manager.config_path}")
        print(f"数据目录: {config.get('data_dir', '未设置')}")
        print(f"日志级别: {config.get('log_level', '未设置')}")
        print(f"工作目录: {config.get('work_dir', '未设置')}")

        if "ray" in config or "runtime" in config:
            runtime_config = config.get("runtime", config.get("ray", {}))
            print(f"运行时地址: {runtime_config.get('address', '未设置')}")
            print(f"运行时端口: {runtime_config.get('port', '未设置')}")

    except Exception as e:
        print(f"❌ 读取配置失败: {e}")
        print("💡 运行 'sage config init' 创建配置文件")


@app.command("init")
def init_config(force: bool = typer.Option(False, "--force", "-f", help="强制覆盖现有配置")):
    """初始化SAGE配置文件"""
    from ...management.config_manager import get_config_manager

    try:
        config_manager = get_config_manager()

        if config_manager.config_path.exists():
            if not force:
                print(f"配置文件已存在: {config_manager.config_path}")
                print("使用 --force 选项覆盖现有配置")
                return

        config_manager.create_default_config()
        print(f"✅ 配置文件已创建: {config_manager.config_path}")

    except Exception as e:
        print(f"❌ 初始化配置失败: {e}")


# 为了向后兼容，也提供一个直接的config命令
@app.callback(invoke_without_command=True)
def config_callback(ctx: typer.Context):
    """显示配置信息"""
    if ctx.invoked_subcommand is None:
        config_info()
