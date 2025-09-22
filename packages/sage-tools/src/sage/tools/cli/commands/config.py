#!/usr/bin/env python3
"""
from sage.common.utils.logging.custom_logger import CustomLogger
SAGE CLI Config Command
配置管理相关命令
"""

import typer

app = typer.Typer(name="config", help="⚙️ 配置管理")


@app.command("show")
def config_info():
    """显示配置信息"""
    from ..config_manager import get_config_manager

    try:
        config_manager = get_config_manager()
        config = config_manager.load_config()

        self.logger.info("📋 SAGE 配置信息:")
        self.logger.info(f"配置文件: {config_manager.config_path}")
        self.logger.info(f"数据目录: {config.get('data_dir', '未设置')}")
        self.logger.info(f"日志级别: {config.get('log_level', '未设置')}")
        self.logger.info(f"工作目录: {config.get('work_dir', '未设置')}")

        if "ray" in config:
            ray_config = config["ray"]
            self.logger.info(f"Ray地址: {ray_config.get('address', '未设置')}")
            self.logger.info(f"Ray端口: {ray_config.get('port', '未设置')}")

    except Exception as e:
        self.logger.info(f"❌ 读取配置失败: {e}")
        self.logger.info("💡 运行 'sage config init' 创建配置文件")


@app.command("init")
def init_config(
    force: bool = typer.Option(False, "--force", "-f", help="强制覆盖现有配置")
):
    """初始化SAGE配置文件"""
    from ..config_manager import get_config_manager

    try:
        config_manager = get_config_manager()

        if config_manager.config_path.exists():
            if not force:
                self.logger.info(f"配置文件已存在: {config_manager.config_path}")
                self.logger.info("使用 --force 选项覆盖现有配置")
                return
            else:
                self.logger.info("🔄 覆盖现有配置文件...")

        # 创建默认配置
        # default_config = {
        #     "log_level": "INFO",
        #     "data_dir": "~/sage_data",
        #     "work_dir": "~/sage_work",
        #     "ray": {
        #         "address": "auto",
        #         "port": 10001
        #     }
        # }
        config_manager.create_default_config()
        # config_manager.save_config(default_config)
        self.logger.info(f"✅ 配置文件已创建: {config_manager.config_path}")
        self.logger.info("🔧 你可以编辑配置文件来自定义设置")

    except Exception as e:
        self.logger.info(f"❌ 初始化配置失败: {e}")


# 为了向后兼容，也提供一个直接的config命令
@app.callback(invoke_without_command=True)
def config_callback(ctx: typer.Context):
    """显示配置信息"""
    if ctx.invoked_subcommand is None:
        config_info()
