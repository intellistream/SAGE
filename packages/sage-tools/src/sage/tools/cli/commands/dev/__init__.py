"""
sage-dev 命令模块

开发工具命令组，包括：
- quality: 质量检查
- project: 项目管理
- maintain: 维护工具
- package: 包管理
- resource: 资源管理
- examples: 示例测试
"""

import sys

import typer
from rich.console import Console
from rich.table import Table

# 创建主命令应用
app = typer.Typer(
    name="dev",
    no_args_is_help=True,
    add_completion=False,
    help="""🛠️ 开发工具 - 质量检查、项目管理、维护工具、包管理等

    命令组：
    • quality   - 代码质量、架构合规、文档规范检查
    • project   - 项目状态、分析、测试、清理
    • maintain  - Submodule管理、Git hooks、诊断
    • package   - 版本管理、安装 (PyPI发布已迁移至 wheelwright)
    • resource  - 模型缓存、数据管理
    • examples  - 示例代码测试和验证

    快速示例：
      sage-dev quality check         # 运行所有质量检查
      sage-dev project test          # 运行测试
      sage-dev maintain doctor       # 健康检查
      sage-dev package version bump  # 升级版本
    """,
)

console = Console()

# 注册新的命令组
try:
    from .quality import app as quality_app

    app.add_typer(
        quality_app,
        name="quality",
        help="🔍 质量检查 - 代码质量、架构合规、文档规范检查 (check, architecture, devnotes, readme, format, lint, fix)",
    )
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 quality 命令组: {e}[/yellow]")

try:
    from .project import app as project_app

    app.add_typer(
        project_app,
        name="project",
        help="📊 项目管理 - 状态、分析、测试、清理 (status, analyze, test, clean, home)",
    )
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 project 命令组: {e}[/yellow]")

try:
    from .maintain import app as maintain_app

    app.add_typer(
        maintain_app,
        name="maintain",
        help="🔧 维护工具 - Submodule、Hooks、诊断 (doctor, hooks, submodule)",
    )
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 maintain 命令组: {e}[/yellow]")

try:
    from .package import app as package_app

    app.add_typer(
        package_app,
        name="package",
        help="📦 包管理 - 版本管理、安装 (version, install)",
    )
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 package 命令组: {e}[/yellow]")

try:
    from .resource import app as resource_app

    app.add_typer(
        resource_app,
        name="resource",
        help="💾 资源管理 - 模型缓存、数据管理 (models)",
    )
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 resource 命令组: {e}[/yellow]")

# GitHub 命令组已移除 - 功能已迁移到其他工具
# try:
#     from .github import app as github_app
#     app.add_typer(
#         github_app,
#         name="github",
#         help="🐙 GitHub 管理 - Issues、PR 等 (issues)",
#     )
# except ImportError as e:
#     console.print(f"[yellow]警告: 无法导入 github 命令组: {e}[/yellow]")

try:
    from .examples import app as examples_app

    app.add_typer(
        examples_app,
        name="examples",
        help="🔬 Examples 测试 - 测试和验证示例代码（需要开发环境）(analyze, test, check, info)",
    )
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 examples 命令组: {e}[/yellow]")

try:
    from .maintenance import app as maintenance_app

    app.add_typer(
        maintenance_app,
        name="maintenance",
        help="🛠️ 维护工具 - Dev-notes 整理、元数据修复、Ruff 更新 (organize-devnotes, fix-metadata, update-ruff-ignore)",
    )
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 maintenance 命令组: {e}[/yellow]")

try:
    from .docs import app as docs_app

    app.add_typer(
        docs_app,
        name="docs",
        help="📚 文档管理 - 构建、预览、检查文档 (build, serve, check)",
    )
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 docs 命令组: {e}[/yellow]")


# ============================================================================
# 主命令 Callback - 显示欢迎信息和版本
# ============================================================================


def version_callback(value: bool):
    """显示版本信息"""
    if value:
        try:
            from sage.common._version import __version__

            console.print(f"SAGE Tools version {__version__}")
        except ImportError:
            console.print("SAGE Tools version unknown")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def dev_callback(
    ctx: typer.Context,
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="显示版本信息",
        callback=version_callback,
        is_eager=True,
    ),
):
    """
    🛠️ SAGE 开发工具

    提供完整的开发工具集，包括质量检查、项目管理、维护工具等。
    """
    if ctx.invoked_subcommand is None:
        # 如果没有调用子命令，显示欢迎信息
        console.print("\n[bold blue]🛠️  SAGE 开发工具[/bold blue]\n")
        console.print("使用 [cyan]sage-dev --help[/cyan] 查看所有可用命令\n")
        console.print("[bold]快速开始:[/bold]")
        console.print("  [green]sage-dev quality check[/green]         # 运行所有质量检查")
        console.print("  [green]sage-dev project test[/green]          # 运行测试")
        console.print("  [green]sage-dev maintain doctor[/green]       # 健康检查")
        console.print("  [green]sage-dev package version list[/green]  # 查看版本\n")
        console.print("[bold]命令组:[/bold]")
        console.print("  [cyan]quality[/cyan]   - 质量检查（架构、文档、代码格式）")
        console.print("  [cyan]project[/cyan]   - 项目管理（状态、分析、测试、清理）")
        console.print("  [cyan]maintain[/cyan]  - 维护工具（submodule、hooks、诊断）")
        console.print("  [cyan]package[/cyan]   - 包管理（版本、安装）")
        console.print("  [cyan]resource[/cyan]  - 资源管理（模型缓存）")
        console.print("  [cyan]github[/cyan]    - GitHub管理（Issues、PR）")
        console.print("  [cyan]examples[/cyan]  - Examples测试（需要开发环境）\n")
        console.print("📚 详细文档: [link]https://github.com/intellistream/SAGE[/link]\n")


# ============================================================================
# 智能命令建议 - 当用户输入错误命令时提示正确用法
# ============================================================================

# 常见的错误命令到正确命令的映射
COMMAND_SUGGESTIONS = {
    "check": ["quality check", "quality format", "quality lint"],
    "fix": ["quality fix", "quality format"],
    "format": ["quality format"],
    "lint": ["quality lint"],
    "test": ["project test"],
    "clean": ["project clean"],
    "status": ["project status"],
    "analyze": ["project analyze"],
    "doctor": ["maintain doctor"],
    "hooks": ["maintain hooks"],
    "issues": ["github issues"],
    "version": ["package version"],
    "models": ["resource models"],
    "install": ["package install"],
}


# 创建包装函数来提供更好的错误提示
def run_with_suggestions():
    """运行 app 并在命令不存在时提供建议"""

    try:
        app()
    except SystemExit as e:
        # 如果退出码是 2（通常表示命令行错误）且有参数
        if e.code == 2 and len(sys.argv) > 1:
            cmd = sys.argv[1]
            # 检查是否是未知命令（不是选项）
            if not cmd.startswith("-") and cmd in COMMAND_SUGGESTIONS:
                console.print(f"\n[yellow]💡 提示: 'sage-dev {cmd}' 命令已重组[/yellow]\n")
                console.print("[cyan]新的命令结构:[/cyan]\n")

                for suggestion in COMMAND_SUGGESTIONS[cmd]:
                    console.print(f"  [green]sage-dev {suggestion}[/green]")

                console.print("\n[dim]使用 [bold]sage-dev --help[/bold] 查看所有可用命令[/dim]\n")
        raise


__all__ = ["app", "run_with_suggestions"]
