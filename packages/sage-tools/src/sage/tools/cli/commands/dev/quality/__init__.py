"""
质量检查命令组

提供代码质量检查、架构检查、文档规范检查等功能。
"""

import typer
from rich.console import Console

app = typer.Typer(
    name="quality",
    help="🔍 质量检查 - 代码质量、架构合规、文档规范检查 (check, architecture, devnotes, readme)",
    no_args_is_help=True,
)

console = Console()


@app.command(name="check")
def check_all(
    all_files: bool = typer.Option(
        False,
        "--all-files",
        help="检查所有文件（默认只检查变更文件）",
    ),
    check_only: bool = typer.Option(
        False,
        "--check-only",
        help="只检查不修复（默认会自动修复）",
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
    examples: bool = typer.Option(
        True,
        "--examples/--no-examples",
        help="运行 examples 目录结构检查",
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

    包括：代码格式化、导入排序、Ruff 检查、类型检查、架构合规、文档规范等。

    默认行为：
    - 只检查变更的文件（使用 --all-files 检查所有文件）
    - 自动修复可修复的问题（使用 --check-only 只检查不修复）
    - 运行架构、dev-notes 和 examples 检查（使用 --no-* 跳过）

    示例：
        sage-dev quality check                # 检查变更文件，自动修复
        sage-dev quality check --all-files    # 检查所有文件
        sage-dev quality check --check-only   # 只检查不修复
        sage-dev quality check --readme       # 包含 README 检查
        sage-dev quality check --no-architecture  # 跳过架构检查
        sage-dev quality check --no-examples     # 跳过 examples 检查
    """
    from sage.tools.cli.commands.dev.main import quality

    # 调用主 quality 函数
    quality(
        fix=not check_only,
        check_only=check_only,
        all_files=all_files,
        hook=None,  # 运行所有 hooks
        architecture=architecture,
        devnotes=devnotes,
        examples=examples,
        readme=readme,
        include_submodules=False,
        submodules_only=False,
        warn_only=warn_only,
        project_root=".",
    )


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


@app.command(name="examples")
def check_examples(
    warn_only: bool = typer.Option(
        False,
        "--warn-only",
        help="只给警告，不中断运行",
    ),
):
    """
    📁 Examples 目录结构检查

    检查 examples/ 目录是否符合规范（只允许 apps/ 和 tutorials/ 两个顶层目录）。

    示例：
        sage-dev quality examples
    """
    if not _run_examples_check(warn_only=warn_only):
        if not warn_only:
            raise typer.Exit(1)


# 为了支持在 main.py 中调用，导出辅助函数
def _run_architecture_check(warn_only: bool = False, changed_only: bool = False) -> bool:
    """运行架构检查，返回是否通过"""
    try:
        from pathlib import Path

        from sage.tools.dev.tools.architecture_checker import ArchitectureChecker
        from sage.tools.dev.utils import find_project_root

        # 获取项目根目录
        root_dir = find_project_root()
        if root_dir is None:
            console.print("[red]错误: 无法找到项目根目录[/red]")
            return False

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
        from sage.tools.dev.utils import find_project_root

        # 获取项目根目录
        root_dir = find_project_root()
        if root_dir is None:
            console.print("[red]错误: 无法找到项目根目录[/red]")
            return False

        checker = DevNotesChecker(root_dir)
        result = checker.check_all()

        if not result["passed"]:
            console.print(f"[red]发现 {result['failed_count']} 个 dev-notes 问题[/red]")
            for issue in result["issues"][:10]:
                console.print(f"  [yellow]{issue['file']}: {issue['message']}[/yellow]")
            return False if not warn_only else True
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
        from sage.tools.dev.utils import find_project_root

        # 获取项目根目录
        root_dir = find_project_root()
        if root_dir is None:
            console.print("[red]错误: 无法找到项目根目录[/red]")
            return False

        checker = PackageREADMEChecker(root_dir)
        results = checker.check_all()

        # 检查是否有失败的包（分数低于阈值）
        failed_packages = [r for r in results if r.score < 80]

        if failed_packages:
            console.print(f"[red]发现 {len(failed_packages)} 个包的 README 需要改进[/red]")
            for pkg in failed_packages[:10]:
                console.print(f"  [yellow]{pkg.package_name}: score={pkg.score:.0f}%[/yellow]")
            return False if not warn_only else True
        else:
            console.print("[green]✓ README 检查通过[/green]")
            return True
    except Exception as e:
        console.print(f"[red]README 检查失败: {e}[/red]")
        import traceback

        traceback.print_exc()
        return False


def _run_examples_check(warn_only: bool = False) -> bool:
    """运行 examples 目录结构检查"""
    try:
        from pathlib import Path

        from sage.tools.dev.tools.examples_structure_checker import (
            ExamplesStructureChecker,
        )
        from sage.tools.dev.utils import find_project_root

        # 获取项目根目录
        root_dir = find_project_root()
        if root_dir is None:
            console.print("[red]错误: 无法找到项目根目录[/red]")
            return False

        examples_dir = Path(root_dir) / "examples"
        if not examples_dir.exists():
            console.print(f"[yellow]警告: examples 目录不存在: {examples_dir}[/yellow]")
            return True  # 如果目录不存在，不算失败

        checker = ExamplesStructureChecker(examples_dir)
        result = checker.check_structure()

        if result.passed:
            console.print("[green]✓ examples 目录结构检查通过[/green]")
            return True

        # 显示错误
        console.print(f"[red]发现 {len(result.violations)} 个结构问题[/red]")
        for violation in result.violations:
            console.print(f"  [yellow]{violation}[/yellow]")

        if result.unexpected_dirs:
            console.print("\n[yellow]不符合规范的目录:[/yellow]")
            for dir_name in result.unexpected_dirs:
                console.print(f"  • {dir_name}/")

        # 显示规范指南
        console.print(f"\n{checker.get_structure_guide()}")

        return False if not warn_only else True
    except Exception as e:
        console.print(f"[red]examples 检查失败: {e}[/red]")
        import traceback

        traceback.print_exc()
        return False


__all__ = ["app"]
