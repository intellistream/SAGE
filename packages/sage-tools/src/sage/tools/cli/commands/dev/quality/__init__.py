"""
质量检查命令组

提供代码质量检查、架构检查、文档规范检查等功能。
"""

import typer
from rich.console import Console

app = typer.Typer(
    name="quality",
    help="🔍 质量检查 - 代码质量、架构合规、文档规范检查",
    no_args_is_help=True,
)

console = Console()


@app.command(name="check")
def check_all(
    changed_only: bool = typer.Option(
        False,
        "--changed-only",
        help="只检查变更的文件",
    ),
    fix: bool = typer.Option(
        True,
        "--fix/--no-fix",
        help="自动修复问题",
    ),
    architecture: bool = typer.Option(
        True,
        "--architecture/--no-architecture",
        help="运行架构检查",
    ),
    devnotes: bool = typer.Option(
        True,
        "--devnotes/--no-devnotes",
        help="运行 dev-notes 检查",
    ),
    readme: bool = typer.Option(
        False,
        "--readme",
        help="运行 README 检查",
    ),
    warn_only: bool = typer.Option(
        False,
        "--warn-only",
        help="只给警告，不中断运行",
    ),
):
    """
    🔍 运行所有质量检查

    包括：架构合规性、dev-notes 规范、README 质量、代码格式等。

    示例：
        sage-dev quality check                # 运行所有检查
        sage-dev quality check --changed-only # 只检查变更文件
        sage-dev quality check --no-fix       # 只检查不修复
        sage-dev quality check --readme       # 包含 README 检查
    """
    console.print("\n[bold blue]🔍 运行质量检查[/bold blue]\n")

    failed_checks = []

    # 架构检查
    if architecture:
        console.print("[cyan]→ 架构合规性检查...[/cyan]")
        if not _run_architecture_check(changed_only=changed_only, warn_only=warn_only):
            failed_checks.append("architecture")

    # dev-notes 检查
    if devnotes:
        console.print("[cyan]→ dev-notes 规范检查...[/cyan]")
        if not _run_devnotes_check(warn_only=warn_only):
            failed_checks.append("devnotes")

    # README 检查
    if readme:
        console.print("[cyan]→ README 质量检查...[/cyan]")
        if not _run_readme_check(warn_only=warn_only):
            failed_checks.append("readme")

    # 总结
    console.print()
    if failed_checks:
        console.print(f"[bold red]✗ 检查失败: {', '.join(failed_checks)}[/bold red]")
        if not warn_only:
            raise typer.Exit(1)
    else:
        console.print("[bold green]✓ 所有检查通过[/bold green]")


@app.command(name="architecture")
def check_architecture(
    changed_only: bool = typer.Option(
        False,
        "--changed-only",
        help="只检查变更的文件",
    ),
    warn_only: bool = typer.Option(
        False,
        "--warn-only",
        help="只给警告，不中断运行",
    ),
):
    """
    🏗️ 架构合规性检查

    检查包之间的依赖关系是否符合分层架构定义。

    示例：
        sage-dev quality architecture                # 检查所有文件
        sage-dev quality architecture --changed-only # 只检查变更文件
    """
    if not _run_architecture_check(changed_only=changed_only, warn_only=warn_only):
        if not warn_only:
            raise typer.Exit(1)


@app.command(name="devnotes")
def check_devnotes(
    warn_only: bool = typer.Option(
        False,
        "--warn-only",
        help="只给警告，不中断运行",
    ),
):
    """
    📝 dev-notes 文档规范检查

    检查 dev-notes 文档是否符合规范（元数据、分类等）。

    示例：
        sage-dev quality devnotes
    """
    if not _run_devnotes_check(warn_only=warn_only):
        if not warn_only:
            raise typer.Exit(1)


@app.command(name="readme")
def check_readme(
    warn_only: bool = typer.Option(
        False,
        "--warn-only",
        help="只给警告，不中断运行",
    ),
):
    """
    📋 包 README 质量检查

    检查包的 README 文档是否完整、格式正确。

    示例：
        sage-dev quality readme
    """
    if not _run_readme_check(warn_only=warn_only):
        if not warn_only:
            raise typer.Exit(1)


@app.command(name="format")
def format_code(
    check_only: bool = typer.Option(
        False,
        "--check-only",
        help="只检查不修复",
    ),
    all_files: bool = typer.Option(
        False,
        "--all-files",
        help="检查所有文件",
    ),
):
    """
    🎨 代码格式化

    使用 black, isort 等工具格式化代码。

    示例：
        sage-dev quality format              # 格式化变更的文件
        sage-dev quality format --all-files  # 格式化所有文件
        sage-dev quality format --check-only # 只检查不修复
    """
    # 调用原 quality 命令，只运行格式化
    import sys

    from sage.tools.cli.commands.dev.main import quality

    sys.argv = ["sage", "dev", "quality"]
    if check_only:
        sys.argv.append("--check-only")
    if all_files:
        sys.argv.append("--all-files")
    sys.argv.extend(["--no-architecture", "--no-devnotes", "--hook", "black"])

    quality(
        fix=not check_only,
        check_only=check_only,
        all_files=all_files,
        hook="black",
        architecture=False,
        devnotes=False,
        readme=False,
        include_submodules=False,
        submodules_only=False,
        warn_only=False,
    )


@app.command(name="lint")
def lint_code(
    all_files: bool = typer.Option(
        False,
        "--all-files",
        help="检查所有文件",
    ),
):
    """
    🔬 代码检查

    使用 ruff, mypy 等工具检查代码质量。

    示例：
        sage-dev quality lint              # 检查变更的文件
        sage-dev quality lint --all-files  # 检查所有文件
    """
    from sage.tools.cli.commands.dev.main import quality

    quality(
        fix=False,
        check_only=True,
        all_files=all_files,
        hook="ruff",
        architecture=False,
        devnotes=False,
        readme=False,
        include_submodules=False,
        submodules_only=False,
        warn_only=False,
    )


@app.command(name="fix")
def fix_issues(
    all_files: bool = typer.Option(
        False,
        "--all-files",
        help="修复所有文件",
    ),
):
    """
    🔧 自动修复问题

    自动修复可修复的代码质量问题。

    示例：
        sage-dev quality fix              # 修复变更的文件
        sage-dev quality fix --all-files  # 修复所有文件
    """
    from sage.tools.cli.commands.dev.main import quality

    quality(
        fix=True,
        check_only=False,
        all_files=all_files,
        hook=None,
        architecture=False,
        devnotes=False,
        readme=False,
        include_submodules=False,
        submodules_only=False,
        warn_only=False,
    )


# 为了支持在 main.py 中调用，导出辅助函数
def _run_architecture_check(changed_only: bool = False, warn_only: bool = False) -> bool:
    """运行架构检查，返回是否通过"""
    try:
        from pathlib import Path

        from sage.tools.dev.tools.architecture_checker import ArchitectureChecker

        # 获取项目根目录
        root_dir = Path(__file__).parent.parent.parent.parent.parent.parent.parent
        checker = ArchitectureChecker(root_dir)
        result = checker.check_all()

        if changed_only:
            # TODO: 过滤只显示变更文件的违规
            pass

        if not result.passed:
            console.print(f"[red]发现 {len(result.violations)} 个架构违规[/red]")
            for v in result.violations[:10]:  # 只显示前10个
                console.print(f"  [yellow]{v}[/yellow]")
            return False
        else:
            console.print("[green]✓ 架构检查通过[/green]")
            return True
    except Exception as e:
        console.print(f"[red]架构检查失败: {e}[/red]")
        import traceback

        traceback.print_exc()
        return False


def _run_devnotes_check(warn_only: bool = False) -> bool:
    """运行 dev-notes 检查，返回是否通过"""
    try:
        from pathlib import Path

        from sage.tools.dev.tools.devnotes_checker import DevNotesChecker

        # 获取项目根目录
        root_dir = Path(__file__).parent.parent.parent.parent.parent.parent.parent
        checker = DevNotesChecker(root_dir)
        issues = checker.check_all()

        if issues:
            console.print(f"[red]发现 {len(issues)} 个 dev-notes 问题[/red]")
            for issue in issues[:10]:
                console.print(f"  [yellow]{issue}[/yellow]")
            return False
        else:
            console.print("[green]✓ dev-notes 检查通过[/green]")
            return True
    except Exception as e:
        console.print(f"[red]dev-notes 检查失败: {e}[/red]")
        import traceback

        traceback.print_exc()
        return False


def _run_readme_check(warn_only: bool = False) -> bool:
    """运行 README 检查，返回是否通过"""
    try:
        from pathlib import Path

        from sage.tools.dev.tools.package_readme_checker import PackageREADMEChecker

        # 获取项目根目录
        root_dir = Path(__file__).parent.parent.parent.parent.parent.parent.parent
        checker = PackageREADMEChecker(root_dir)
        issues = checker.check_all()

        if issues:
            console.print(f"[red]发现 {len(issues)} 个 README 问题[/red]")
            for issue in issues[:10]:
                console.print(f"  [yellow]{issue}[/yellow]")
            return False
        else:
            console.print("[green]✓ README 检查通过[/green]")
            return True
    except Exception as e:
        console.print(f"[red]README 检查失败: {e}[/red]")
        import traceback

        traceback.print_exc()
        return False


__all__ = ["app"]
