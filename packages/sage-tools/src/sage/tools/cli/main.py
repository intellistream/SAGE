#!/usr/bin/env python3
"""
SAGE CLI - 统一命令行工具
Streaming-Augmented Generative Execution - AI Research and Graph Engine
"""

from typing import Optional

import typer
from sage.tools.cli.commands.chat import app as chat_app
from sage.tools.cli.commands.cluster import app as cluster_app
from sage.tools.cli.commands.config import app as config_app
from sage.tools.cli.commands.dev import app as dev_app  # 新增dev命令
from sage.tools.cli.commands.doctor import app as doctor_app
from sage.tools.cli.commands.embedding import app as embedding_app  # 新增embedding命令
from sage.tools.cli.commands.enterprise import app as enterprise_app
from sage.tools.cli.commands.extensions import app as extensions_app
from sage.tools.cli.commands.head import app as head_app
from sage.tools.cli.commands.job import app as job_app
from sage.tools.cli.commands.jobmanager import app as jobmanager_app
from sage.tools.cli.commands.license import app as license_app
from sage.tools.cli.commands.llm import app as llm_app  # 新增LLM命令
from sage.tools.cli.commands.pipeline import app as pipeline_app
from sage.tools.cli.commands.studio import app as studio_app
from sage.tools.cli.commands.test_extensions import app as test_extensions_app
from sage.tools.cli.commands.version import app as version_app
from sage.tools.cli.commands.worker import app as worker_app


def version_callback(value: bool):
    """Show version information"""
    if value:
        try:
            from sage.common._version import __version__

            typer.echo(f"SAGE version {__version__}")
        except ImportError:
            typer.echo("SAGE version unknown")
        raise typer.Exit()


# 创建主应用
app = typer.Typer(
    name="sage",
    help="🚀 SAGE - Streaming-Augmented Generative Execution CLI",
    no_args_is_help=True,
)

# 注册核心子命令
app.add_typer(version_app, name="version", help="📋 版本信息")
app.add_typer(config_app, name="config", help="⚙️ 配置管理")
app.add_typer(enterprise_app, name="enterprise", help="🏢 企业版功能管理")
app.add_typer(license_app, name="license", help="🛡️ 许可证管理 - 客户与厂商工具")
app.add_typer(llm_app, name="llm", help="🤖 LLM服务管理 - 启动、停止、配置LLM服务")
app.add_typer(doctor_app, name="doctor", help="🔍 系统诊断")
app.add_typer(chat_app, name="chat", help="🧭 编程助手 - 基于 SageDB 的文档问答")
app.add_typer(
    pipeline_app, name="pipeline", help="🧱 Pipeline Builder - 大模型辅助的配置生成"
)
app.add_typer(embedding_app, name="embedding", help="🎯 Embedding 管理 - 管理和测试 embedding 方法")

# 开发工具命令
app.add_typer(dev_app, name="dev", help="🛠️ 开发工具 - 项目开发和管理")

# 扩展和界面命令
app.add_typer(extensions_app, name="extensions", help="🧩 扩展管理 - 安装和管理C++扩展")
app.add_typer(test_extensions_app, name="test", help="🧪 测试 - 扩展和功能测试")
app.add_typer(studio_app, name="studio", help="🎨 Studio - 低代码可视化管道编辑器")

# 作业和集群管理命令
app.add_typer(job_app, name="job", help="📋 作业管理 - 提交、监控、管理作业")
app.add_typer(jobmanager_app, name="jobmanager", help="⚡ JobManager - 作业管理器服务")
app.add_typer(worker_app, name="worker", help="🔧 Worker - 工作节点管理")
app.add_typer(cluster_app, name="cluster", help="🌐 Cluster - 集群管理和状态监控")
app.add_typer(head_app, name="head", help="🎯 Head - 集群头节点管理")


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", help="显示版本信息", callback=version_callback
    ),
):
    """
    🚀 SAGE - Streaming-Augmented Generative Execution

    统一的AI研究和流式计算平台命令行工具

    💡 使用示例:
    sage dev status                 # 查看开发环境状态
    sage studio start               # 启动可视化界面
    sage job list                   # 列出所有作业
    sage jobmanager start          # 启动作业管理器服务
    sage cluster status            # 查看集群状态

    🔗 更多信息: https://github.com/intellistream/SAGE
    """
    if version:
        from sage.common._version import __version__

        typer.echo(f"SAGE CLI version {__version__}")
        raise typer.Exit()


if __name__ == "__main__":
    app()
