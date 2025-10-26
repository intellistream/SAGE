#!/usr/bin/env python3
"""
SAGE Tools CLI - 开发工具命令行
Development Tools for SAGE Platform
"""

import typer


def version_callback(value: bool):
    """Show version information"""
    if value:
        try:
            from sage.common._version import __version__

            typer.echo(f"SAGE Tools version {__version__}")
        except ImportError:
            typer.echo("SAGE Tools version unknown")
        raise typer.Exit()


# 创建主应用 - 仅用于 sage 命令（已被 sage-cli 替代）
# 保留用于向后兼容，但主要功能已移至 sage-cli
app = typer.Typer(
    name="sage",
    help="⚠️  注意: 此命令已被 sage-cli 替代，请使用 sage 命令（来自 sage-cli 包）",
    no_args_is_help=True,
)


# 仅注册 dev 命令（主要功能）
try:
    from sage.tools.cli.commands.dev import app as dev_app  # noqa: E402

    app.add_typer(
        dev_app,
        name="dev",
        help="🛠️ 开发工具 - 质量检查、项目管理、维护工具、包管理等",
        rich_help_panel="开发工具",
    )
except ImportError as e:
    print(f"Warning: Failed to import dev commands: {e}")


# 可选：finetune 命令
try:
    from sage.tools.finetune import app as finetune_app  # noqa: E402

    app.add_typer(finetune_app, name="finetune", help="🎓 模型微调 - 多场景大模型微调工具")
except ImportError:
    pass  # finetune 是可选的


@app.callback()
def main(
    version: bool | None = typer.Option(
        None, "--version", "-v", help="显示版本信息", callback=version_callback
    ),
):
    """
    �️ SAGE Tools - 开发工具命令行

    ⚠️  注意: sage 生产命令已移至 sage-cli 包
    请使用 sage 命令（来自 sage-cli）访问平台和应用功能

    此包提供:
    - sage-dev: 开发工具命令（推荐使用）
    - sage dev: 开发工具（通过此入口点，仅用于兼容）

    💡 推荐使用:
      sage-dev quality check         # 运行代码质量检查
      sage-dev project test          # 运行项目测试
      sage-dev maintain doctor       # 健康检查

    📦 生产命令请使用 sage-cli:
      pip install sage-cli
      sage cluster start             # 启动集群
      sage llm serve                 # 启动LLM服务
    """
    pass
    • quality   - 质量检查（架构、文档、代码格式）
    • project   - 项目管理（状态、分析、测试、清理）
    • maintain  - 维护工具（submodule、hooks、诊断）
    • package   - 包管理（PyPI发布、版本、安装）
    • resource  - 资源管理（模型缓存）
    • github    - GitHub管理（Issues、PR）

    📚 查看详细命令: sage dev --help

    🔗 更多信息: https://github.com/intellistream/SAGE
    """
    if version:
        from sage.common._version import __version__

        typer.echo(f"SAGE CLI version {__version__}")
        raise typer.Exit()


if __name__ == "__main__":
    app()
