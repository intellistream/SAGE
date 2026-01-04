#!/usr/bin/env python3
"""
SAGE CLI 主入口

统一的命令行接口，包括：
- Platform: 集群管理、作业调度
- Apps: LLM、Chat、Embedding、Pipeline、Studio

注意：Dev 开发工具命令由 sage-tools 包提供，不在此包中
"""

import logging
import os

# Suppress noisy INFO logs during CLI startup unless SAGE_CLI_VERBOSE is set
# This must be done BEFORE importing any sage modules
if not os.environ.get("SAGE_CLI_VERBOSE"):
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    # Also suppress specific noisy loggers
    for logger_name in [
        "sage.platform",
        "sage.middleware",
        "sage.kernel",
        "sage.common",
        "faiss",
        "httpx",
        "httpcore",
    ]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

import typer
from rich.console import Console

# 创建主应用
app = typer.Typer(
    name="sage",
    help="""🚀 SAGE - Streaming Applied to GEneral data stream

    命令分类：
    • Platform  - 集群管理和作业调度
    • Apps      - 应用层服务（LLM、Chat等）

    快速示例：
      sage cluster start              # 启动集群
      sage llm serve                  # 启动LLM服务
      sage job submit task.py         # 提交作业

    开发工具：
      开发命令请使用 sage-dev (由 sage-tools 包提供)
      sage-dev quality check          # 运行质量检查
      sage-dev project test           # 运行测试
    """,
    no_args_is_help=True,
)

console = Console()


# ============================================================================
# Version Callback
# ============================================================================


def version_callback(value: bool):
    """Show version information"""
    if value:
        try:
            from sage.common._version import __version__

            typer.echo(f"SAGE version {__version__}")
        except ImportError:
            typer.echo("SAGE version unknown")
        raise typer.Exit()


# ============================================================================
# Platform Commands - 平台管理命令
# ============================================================================

# 导入 Platform 命令组
try:
    from .commands.platform import (
        cluster_app,
        config_app,
        docs_app,
        doctor_app,
        extensions_app,
        head_app,
        job_app,
        jobmanager_app,
        version_app,
        worker_app,
    )

    if version_app:
        app.add_typer(version_app, name="version", help="📋 版本信息")
    if cluster_app:
        app.add_typer(
            cluster_app,
            name="cluster",
            help="🌐 Cluster - 集群管理和状态监控 (start, stop, status, restart, logs)",
        )
    if head_app:
        app.add_typer(
            head_app,
            name="head",
            help="🎯 Head - 集群头节点管理 (start, stop, status, restart, logs)",
        )
    if worker_app:
        app.add_typer(
            worker_app,
            name="worker",
            help="🔧 Worker - 工作节点管理 (start, stop, status, restart, logs, add, remove)",
        )
    if job_app:
        app.add_typer(
            job_app,
            name="job",
            help="📋 作业管理 - 提交、监控、管理作业 (submit, list, status, stop, logs, attach)",
        )
    if jobmanager_app:
        app.add_typer(
            jobmanager_app,
            name="jobmanager",
            help="⚡ JobManager - 作业管理器服务 (start, stop, status, restart)",
        )
    if config_app:
        app.add_typer(config_app, name="config", help="⚙️ 配置管理 (show, set, reset)")
    if doctor_app:
        app.add_typer(doctor_app, name="doctor", help="🔍 系统诊断")
    if extensions_app:
        app.add_typer(
            extensions_app,
            name="extensions",
            help="🧩 扩展管理 - 安装和管理C++扩展 (list, install, uninstall, status)",
        )
    if docs_app:
        app.add_typer(
            docs_app,
            name="docs",
            help="📚 文档管理 - 预览、构建和部署文档 (serve, build, install-deps, info)",
        )
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 platform 命令组: {e}[/yellow]")


# ============================================================================
# Apps Commands - 应用层命令
# ============================================================================

try:
    from .commands.apps import (
        chat_app,
        edge_app,
        embedding_app,
        gateway_app,
        inference_app,
        llm_app,
        pipeline_app,
        studio_app,
    )

    if llm_app:
        app.add_typer(
            llm_app,
            name="llm",
            help="🤖 LLM服务管理 - 启动、停止、配置LLM服务 (serve, start, stop, status, models)",
        )
    if chat_app:
        app.add_typer(
            chat_app, name="chat", help="🧭 编程助手 - 基于 SageVDB 的文档问答 (interactive mode)"
        )
    if embedding_app:
        app.add_typer(
            embedding_app,
            name="embedding",
            help="🎯 Embedding 管理 - 管理和测试 embedding 方法 (list, test, benchmark)",
        )
    if pipeline_app:
        app.add_typer(
            pipeline_app,
            name="pipeline",
            help="🧱 Pipeline Builder - 大模型辅助的配置生成 (build, validate, template)",
        )
    if studio_app:
        app.add_typer(
            studio_app,
            name="studio",
            help="🎨 Studio - 低代码可视化管道编辑器 (start, stop, status)",
        )
    if inference_app:
        app.add_typer(
            inference_app,
            name="inference",
            help="🔮 统一推理服务 - LLM 和 Embedding 混合调度 (start, stop, status, config)",
        )
    if gateway_app:
        app.add_typer(
            gateway_app,
            name="gateway",
            help="🌐 API Gateway - 统一推理网关服务 (start, stop, status, logs, restart)",
        )
    if edge_app:
        app.add_typer(
            edge_app,
            name="edge",
            help="🪄 Edge - L6 聚合器 (mount LLM gateway at / or custom prefix)",
        )
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 apps 命令组: {e}[/yellow]")


# ============================================================================
# Dev Commands - 已独立为 sage-dev 命令
# ============================================================================

# 注意: 开发命令已经从 sage-cli 中移除，现在由 sage-tools 包通过 sage-dev 命令提供
# 如需使用开发工具，请使用: sage-dev --help


# ============================================================================
# Main Callback
# ============================================================================


@app.callback()
def main(
    version: bool | None = typer.Option(
        None, "--version", "-v", help="显示版本信息", callback=version_callback
    ),
):
    """
    🚀 SAGE - Streaming-Augmented Generative Execution

    统一的AI研究和流式计算平台命令行工具

    💡 使用示例:

    Platform Commands:
      sage cluster start             # 启动集群
      sage cluster status            # 查看集群状态
      sage config show               # 显示配置
      sage doctor                    # 系统诊断

        Application Commands:
            sage llm run                   # 启动阻塞式 LLM 服务
      sage chat                      # 启动聊天助手
      sage pipeline build            # 构建 pipeline
      sage studio start              # 启动可视化编辑器

    🏗️  架构说明:
      - Platform Commands: 平台管理 (cluster, config, doctor, etc.)
      - Application Commands: 应用功能 (llm, chat, pipeline, studio)

    📝 开发工具:
      开发命令请使用独立的 sage-dev 命令（由 sage-tools 包提供）
      安装: pip install sage-tools
      使用: sage-dev quality check, sage-dev project test 等

    📚 文档: https://intellistream.github.io/SAGE
    """
    pass


if __name__ == "__main__":
    app()
