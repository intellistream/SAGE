"""
sage-dev examples 命令组

用于测试和验证 examples/ 目录中的示例代码。

⚠️  注意：这些命令仅在开发环境中可用（需要访问源码仓库）。
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

console = Console()
app = typer.Typer(help="🔬 Examples 测试工具（需要开发环境）")


def _check_dev_environment() -> bool:
    """检查开发环境是否可用"""
    try:
        from sage.dev.impl.examples import ensure_development_environment

        return ensure_development_environment(raise_error=False)
    except ImportError:
        return False


def _show_setup_guide():
    """显示环境设置指南"""
    console.print(
        Panel(
            "[bold yellow]⚠️  Examples 测试工具需要开发环境[/bold yellow]\n\n"
            "这些工具需要访问 SAGE 源码仓库中的 examples/ 目录。\n\n"
            "[bold]设置方法：[/bold]\n"
            "1. 克隆 SAGE 仓库：\n"
            "   [cyan]git clone https://github.com/intellistream/SAGE[/cyan]\n"
            "   [cyan]cd SAGE[/cyan]\n\n"
            "2. 从源码安装 sage-tools：\n"
            "   [cyan]pip install -e packages/sage-tools[dev][/cyan]\n\n"
            "3. 或设置环境变量：\n"
            "   [cyan]export SAGE_ROOT=/path/to/SAGE[/cyan]\n\n"
            "[bold]了解更多：[/bold]\n"
            "  packages/sage-tools/src/sage/tools/dev/examples/README.md",
            title="环境设置指南",
            border_style="yellow",
        )
    )


@app.command(name="analyze")
def analyze_command(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细信息"),
):
    """分析 examples 目录结构

    扫描并分析所有示例文件，显示分类、依赖、运行时间等信息。

    示例：
        sage-dev examples analyze
        sage-dev examples analyze --verbose
    """
    # 检查环境
    if not _check_dev_environment():
        _show_setup_guide()
        raise typer.Exit(1)

    try:
        from sage.dev.impl.examples import ExampleAnalyzer

        console.print("🔍 [bold blue]分析 Examples 目录...[/bold blue]\n")

        analyzer = ExampleAnalyzer()
        examples = analyzer.discover_examples()

        console.print(f"📊 发现 [green]{len(examples)}[/green] 个示例文件\n")

        # 按类别统计
        categories = {}
        for example in examples:
            if example.category not in categories:
                categories[example.category] = []
            categories[example.category].append(example)

        # 显示类别摘要
        from rich.table import Table

        table = Table(title="Examples 分类统计")
        table.add_column("类别", style="cyan", no_wrap=True)
        table.add_column("数量", style="magenta", justify="right")
        table.add_column("快速", style="green", justify="right")
        table.add_column("中等", style="yellow", justify="right")
        table.add_column("慢速", style="red", justify="right")
        table.add_column("外部依赖", style="blue")

        for category in sorted(categories.keys()):
            cat_examples = categories[category]
            count = len(cat_examples)

            # 统计运行时间
            quick = sum(1 for e in cat_examples if e.estimated_runtime == "quick")
            medium = sum(1 for e in cat_examples if e.estimated_runtime == "medium")
            slow = sum(1 for e in cat_examples if e.estimated_runtime == "slow")

            # 收集依赖
            all_deps = set()
            for e in cat_examples:
                all_deps.update(e.dependencies)

            deps_str = ", ".join(sorted(all_deps)[:3])
            if len(all_deps) > 3:
                deps_str += f" +{len(all_deps) - 3}"

            table.add_row(
                category, str(count), str(quick), str(medium), str(slow), deps_str or "无"
            )

        console.print(table)

        # 详细信息
        if verbose:
            console.print("\n[bold]详细信息：[/bold]\n")
            for category in sorted(categories.keys()):
                console.print(f"[bold cyan]{category}[/bold cyan]:")
                for example in categories[category]:
                    deps = ", ".join(example.dependencies) if example.dependencies else "无"
                    tags = ", ".join(example.test_tags) if example.test_tags else "无"
                    console.print(
                        f"  • {Path(example.file_path).name} "
                        f"[dim]({example.estimated_runtime})[/dim]"
                    )
                    if verbose:
                        console.print(f"    依赖: {deps}")
                        console.print(f"    标记: {tags}")
                console.print()

        console.print("[green]✅ 分析完成！[/green]")

    except Exception as e:
        console.print(f"[red]❌ 分析失败: {e}[/red]")
        if verbose:
            import traceback

            traceback.print_exc()
        raise typer.Exit(1)


@app.command(name="test")
def test_command(
    category: list[str] | None = typer.Option(
        None, "--category", "-c", help="指定测试类别（可多次使用）"
    ),
    quick: bool = typer.Option(False, "--quick", "-q", help="只运行快速测试"),
    timeout: int | None = typer.Option(None, "--timeout", "-t", help="单个测试超时时间（秒）"),
    output: str | None = typer.Option(None, "--output", "-o", help="保存结果到JSON文件"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细输出"),
):
    """运行 examples 测试

    执行示例文件并验证其运行正常。

    示例：
        sage-dev examples test --quick              # 运行快速测试
        sage-dev examples test -c tutorials         # 测试 tutorials 类别
        sage-dev examples test -c rag -c memory     # 测试多个类别
        sage-dev examples test --timeout 120        # 设置超时
        sage-dev examples test -o results.json      # 保存结果
    """
    # 检查环境
    if not _check_dev_environment():
        _show_setup_guide()
        raise typer.Exit(1)

    try:
        from sage.dev.impl.examples import ExampleTestSuite

        console.print("🚀 [bold blue]运行 Examples 测试...[/bold blue]\n")

        # 创建测试套件
        suite = ExampleTestSuite()
        if timeout is not None:
            suite.runner.timeout = timeout

        # 显示配置
        console.print("[bold]测试配置：[/bold]")
        console.print(f"  类别: {', '.join(category) if category else '全部'}")
        console.print(f"  模式: {'快速测试' if quick else '完整测试'}")
        if timeout:
            console.print(f"  超时: {timeout}秒")
        console.print()

        # 运行测试
        stats = suite.run_all_tests(categories=category, quick_only=quick)

        # 保存结果
        if output:
            suite.save_results(output)

        # 根据结果设置退出码
        if stats["failed"] > 0 or stats["timeout"] > 0:
            console.print("\n[red]❌ 测试失败[/red]")
            raise typer.Exit(1)
        else:
            console.print("\n[green]✅ 测试通过！[/green]")

    except Exception as e:
        console.print(f"[red]❌ 测试失败: {e}[/red]")
        if verbose:
            import traceback

            traceback.print_exc()
        raise typer.Exit(1)


@app.command(name="check")
def check_command(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细信息"),
):
    """检查中间结果放置

    验证示例代码没有在项目根目录产生中间结果文件，
    所有输出应该在 .sage/ 目录下。

    示例：
        sage-dev examples check
        sage-dev examples check --verbose
    """
    # 检查环境
    if not _check_dev_environment():
        _show_setup_guide()
        raise typer.Exit(1)

    try:
        from sage_dev_tools.quality import IntermediateResultsChecker

        console.print("🔍 [bold blue]检查中间结果放置...[/bold blue]\n")

        # 获取项目根目录
        from sage.dev.impl.examples.utils import find_project_root

        project_root = find_project_root()
        if project_root is None:
            console.print("[red]❌ 无法找到项目根目录[/red]")
            raise typer.Exit(1)

        # 执行检查
        checker = IntermediateResultsChecker(str(project_root))
        passed = checker.print_check_result()

        if passed:
            console.print("\n[green]✅ 检查通过！项目根目录保持整洁。[/green]")
        else:
            console.print(
                "\n[yellow]⚠️  发现中间结果放置问题。请将所有输出移至 .sage/ 目录。[/yellow]"
            )
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]❌ 检查失败: {e}[/red]")
        if verbose:
            import traceback

            traceback.print_exc()
        raise typer.Exit(1)


@app.command(name="info")
def info_command():
    """显示开发环境信息

    检查并显示当前的开发环境状态。

    示例：
        sage-dev examples info
    """
    try:
        from sage.dev.impl.examples.utils import get_development_info

        console.print("🔍 [bold blue]开发环境信息[/bold blue]\n")

        info = get_development_info()

        from rich.table import Table

        table = Table(show_header=False, box=None)
        table.add_column("项目", style="cyan")
        table.add_column("状态", style="green")

        table.add_row("开发环境", "✅ 可用" if info["has_dev_env"] else "❌ 不可用")
        table.add_row("Examples 目录", info["examples_dir"] or "(未找到)")
        table.add_row("项目根目录", info["project_root"] or "(未找到)")
        table.add_row("SAGE_ROOT 环境变量", info["sage_root_env"] or "(未设置)")
        table.add_row("Git 仓库", "✅ 是" if info["in_git_repo"] else "❌ 否")

        console.print(table)

        if not info["has_dev_env"]:
            console.print()
            _show_setup_guide()

    except ImportError:
        console.print("[red]❌ 无法导入 Examples 测试工具[/red]")
        _show_setup_guide()
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
