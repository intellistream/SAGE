"""
SAGE Dev 命令模块

开发工具命令组，包括：
- quality: 质量检查
- project: 项目管理
- maintain: 维护工具
- package: 包管理
- resource: 资源管理
- github: GitHub 管理
"""

import typer
from rich.console import Console

# 创建主命令应用
app = typer.Typer(
    name="dev",
    help="""🛠️ 开发工具 - 质量检查、项目管理、维护工具、包管理等

    命令组：
    • quality   - 代码质量、架构合规、文档规范检查
    • project   - 项目状态、分析、测试、清理
    • maintain  - Submodule管理、Git hooks、诊断
    • package   - PyPI发布、版本管理、安装
    • resource  - 模型缓存、数据管理
    • github    - Issues、PR管理

    快速示例：
      sage dev quality check         # 运行所有质量检查
      sage dev project test          # 运行测试
      sage dev maintain doctor       # 健康检查
      sage dev package version bump  # 升级版本
    """,
)

console = Console()

# 注册新的命令组
try:
    from .quality import app as quality_app

    app.add_typer(quality_app, name="quality")
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 quality 命令组: {e}[/yellow]")

try:
    from .project import app as project_app

    app.add_typer(project_app, name="project")
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 project 命令组: {e}[/yellow]")

try:
    from .maintain import app as maintain_app

    app.add_typer(maintain_app, name="maintain")
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 maintain 命令组: {e}[/yellow]")

try:
    from .package import app as package_app

    app.add_typer(package_app, name="package")
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 package 命令组: {e}[/yellow]")

try:
    from .resource import app as resource_app

    app.add_typer(resource_app, name="resource")
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 resource 命令组: {e}[/yellow]")

try:
    from .github import app as github_app

    app.add_typer(github_app, name="github")
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 github 命令组: {e}[/yellow]")


# ============================================================================
# 主命令 Callback - 显示欢迎信息
# ============================================================================


@app.callback(invoke_without_command=True)
def dev_callback(ctx: typer.Context):
    """
    🛠️ SAGE 开发工具

    提供完整的开发工具集，包括质量检查、项目管理、维护工具等。
    """
    if ctx.invoked_subcommand is None:
        # 如果没有调用子命令，显示欢迎信息
        console.print("\n[bold blue]🛠️  SAGE 开发工具[/bold blue]\n")
        console.print("使用 [cyan]sage dev --help[/cyan] 查看所有可用命令\n")
        console.print("[bold]快速开始:[/bold]")
        console.print("  [green]sage dev quality check[/green]         # 运行所有质量检查")
        console.print("  [green]sage dev project test[/green]          # 运行测试")
        console.print("  [green]sage dev maintain doctor[/green]       # 健康检查")
        console.print("  [green]sage dev package version list[/green]  # 查看版本\n")
        console.print("[bold]命令组:[/bold]")
        console.print("  [cyan]quality[/cyan]   - 质量检查（架构、文档、代码格式）")
        console.print("  [cyan]project[/cyan]   - 项目管理（状态、分析、测试、清理）")
        console.print("  [cyan]maintain[/cyan]  - 维护工具（submodule、hooks、诊断）")
        console.print("  [cyan]package[/cyan]   - 包管理（PyPI发布、版本、安装）")
        console.print("  [cyan]resource[/cyan]  - 资源管理（模型缓存）")
        console.print("  [cyan]github[/cyan]    - GitHub管理（Issues、PR）\n")
        console.print("📚 详细文档: [link]https://github.com/intellistream/SAGE[/link]\n")


# ============================================================================
# 向后兼容别名
# ============================================================================

# 导入原有命令（作为别名）
try:
    from .main import (
        analyze as _analyze_old,
        architecture as _architecture_old,
        clean as _clean_old,
        home as _home_old,
        quality as _quality_old,
        status as _status_old,
        test as _test_old,
    )

    # 命令别名映射
    DEPRECATED_COMMANDS = {
        "quality": "quality format",
        "analyze": "project analyze",
        "clean": "project clean",
        "status": "project status",
        "test": "project test",
        "home": "project home",
        "architecture": "project architecture",
        "check-all": "quality check",
        "check-architecture": "quality architecture",
        "check-devnotes": "quality devnotes",
        "check-readme": "quality readme",
        # 命令组别名
        "issues": "github issues",
        "pypi": "package pypi",
        "version": "package version",
        "models": "resource models",
    }

    def show_deprecation_warning(old_cmd: str, new_cmd: str):
        """显示弃用警告"""
        console.print(
            f"\n[yellow]⚠️  警告: 'sage dev {old_cmd}' 已弃用，"
            f"请使用 'sage dev {new_cmd}'[/yellow]"
        )
        console.print("[yellow]   旧命令将在 v1.0.0 版本后移除[/yellow]\n")

    # 注册别名命令
    @app.command(name="quality", hidden=True)
    def quality_alias(*args, **kwargs):
        """[已弃用] 使用 'sage dev quality format' 代替"""
        show_deprecation_warning("quality", "quality format")
        return _quality_old(*args, **kwargs)

    @app.command(name="analyze", hidden=True)
    def analyze_alias(*args, **kwargs):
        """[已弃用] 使用 'sage dev project analyze' 代替"""
        show_deprecation_warning("analyze", "project analyze")
        return _analyze_old(*args, **kwargs)

    @app.command(name="clean", hidden=True)
    def clean_alias(*args, **kwargs):
        """[已弃用] 使用 'sage dev project clean' 代替"""
        show_deprecation_warning("clean", "project clean")
        return _clean_old(*args, **kwargs)

    @app.command(name="status", hidden=True)
    def status_alias(*args, **kwargs):
        """[已弃用] 使用 'sage dev project status' 代替"""
        show_deprecation_warning("status", "project status")
        return _status_old(*args, **kwargs)

    @app.command(name="test", hidden=True)
    def test_alias(*args, **kwargs):
        """[已弃用] 使用 'sage dev project test' 代替"""
        show_deprecation_warning("test", "project test")
        return _test_old(*args, **kwargs)

    @app.command(name="home", hidden=True)
    def home_alias(*args, **kwargs):
        """[已弃用] 使用 'sage dev project home' 代替"""
        show_deprecation_warning("home", "project home")
        return _home_old(*args, **kwargs)

    @app.command(name="architecture", hidden=True)
    def architecture_alias(*args, **kwargs):
        """[已弃用] 使用 'sage dev project architecture' 代替"""
        show_deprecation_warning("architecture", "project architecture")
        return _architecture_old(*args, **kwargs)

    # check-* 别名
    @app.command(name="check-all", hidden=True)
    def check_all_alias(
        changed_only: bool = False,
        warn_only: bool = False,
    ):
        """[已弃用] 使用 'sage dev quality check' 代替"""
        show_deprecation_warning("check-all", "quality check")
        from .quality import check_all

        return check_all(
            changed_only=changed_only,
            fix=True,
            architecture=True,
            devnotes=True,
            readme=False,
            warn_only=warn_only,
        )

    @app.command(name="check-architecture", hidden=True)
    def check_architecture_alias(
        changed_only: bool = False,
        warn_only: bool = False,
    ):
        """[已弃用] 使用 'sage dev quality architecture' 代替"""
        show_deprecation_warning("check-architecture", "quality architecture")
        from .quality import check_architecture

        return check_architecture(
            changed_only=changed_only,
            warn_only=warn_only,
        )

    @app.command(name="check-devnotes", hidden=True)
    def check_devnotes_alias(warn_only: bool = False):
        """[已弃用] 使用 'sage dev quality devnotes' 代替"""
        show_deprecation_warning("check-devnotes", "quality devnotes")
        from .quality import check_devnotes

        return check_devnotes(warn_only=warn_only)

    @app.command(name="check-readme", hidden=True)
    def check_readme_alias(warn_only: bool = False):
        """[已弃用] 使用 'sage dev quality readme' 代替"""
        show_deprecation_warning("check-readme", "quality readme")
        from .quality import check_readme

        return check_readme(warn_only=warn_only)

except ImportError as e:
    console.print(f"[yellow]警告: 无法导入向后兼容别名: {e}[/yellow]")


__all__ = ["app"]
