#!/usr/bin/env python3
"""
Demo: Using SAGE Examples Testing Tools

This script demonstrates how to use the Examples testing framework
and handles the development environment requirement gracefully.
"""

from rich.console import Console

console = Console()


def check_environment():
    """检查并报告开发环境状态"""
    console.print("\n[bold blue]🔍 Checking Development Environment[/bold blue]\n")

    try:
        from sage.tools.dev.examples.utils import (
            find_examples_directory,
            find_project_root,
            get_development_info,
        )

        info = get_development_info()

        console.print("Development Environment Info:")
        console.print(f"  Has Dev Environment: {'✅ Yes' if info['has_dev_env'] else '❌ No'}")
        console.print(f"  Examples Directory: {info['examples_dir'] or '(not found)'}")
        console.print(f"  Project Root: {info['project_root'] or '(not found)'}")
        console.print(f"  SAGE_ROOT env: {info['sage_root_env'] or '(not set)'}")
        console.print(f"  In Git Repo: {'✅ Yes' if info['in_git_repo'] else '❌ No'}")

        return info["has_dev_env"]

    except ImportError as e:
        console.print(f"[red]❌ Failed to import tools: {e}[/red]")
        return False


def demo_analysis():
    """演示示例分析功能"""
    console.print("\n[bold blue]📊 Examples Analysis Demo[/bold blue]\n")

    try:
        from sage.tools.dev.examples import ExampleAnalyzer

        analyzer = ExampleAnalyzer()
        examples = analyzer.discover_examples()

        console.print(f"Found [green]{len(examples)}[/green] examples\n")

        # 按类别统计
        categories = {}
        for example in examples:
            if example.category not in categories:
                categories[example.category] = []
            categories[example.category].append(example)

        console.print("[bold]Examples by Category:[/bold]")
        for category, cat_examples in sorted(categories.items()):
            console.print(f"  • {category}: {len(cat_examples)} files")

        # 显示一些示例细节
        if examples:
            console.print("\n[bold]Sample Example Details:[/bold]")
            sample = examples[0]
            console.print(f"  File: {sample.file_path}")
            console.print(f"  Category: {sample.category}")
            console.print(f"  Runtime: {sample.estimated_runtime}")
            console.print(f"  Dependencies: {', '.join(sample.dependencies) or 'none'}")
            console.print(f"  Test tags: {', '.join(sample.test_tags) or 'none'}")

        return True

    except RuntimeError as e:
        console.print(f"[yellow]⚠️  {e}[/yellow]")
        return False
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        import traceback

        traceback.print_exc()
        return False


def demo_quick_test():
    """演示快速测试"""
    console.print("\n[bold blue]🧪 Quick Test Demo[/bold blue]\n")

    try:
        from sage.tools.dev.examples import ExampleTestSuite

        suite = ExampleTestSuite()

        console.print("Running quick tests on tutorials category...\n")

        stats = suite.run_all_tests(categories=["tutorials"], quick_only=True)

        console.print("\n[bold]Test Results:[/bold]")
        console.print(f"  Total: {stats['total']}")
        console.print(f"  [green]Passed: {stats['passed']}[/green]")
        console.print(f"  [red]Failed: {stats['failed']}[/red]")
        console.print(f"  [yellow]Skipped: {stats['skipped']}[/yellow]")
        console.print(f"  [orange]Timeout: {stats['timeout']}[/orange]")

        if stats["total"] > 0:
            pass_rate = stats["passed"] / stats["total"] * 100
            console.print(f"\n  Pass Rate: [bold]{pass_rate:.1f}%[/bold]")

        return True

    except RuntimeError as e:
        console.print(f"[yellow]⚠️  {e}[/yellow]")
        return False
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        import traceback

        traceback.print_exc()
        return False


def show_setup_guide():
    """显示设置指南"""
    console.print("\n[bold yellow]📚 Setup Guide[/bold yellow]\n")
    console.print("To use Examples testing tools, you need a development environment:\n")
    console.print("[bold]Option 1: Clone Repository[/bold]")
    console.print("  git clone https://github.com/intellistream/SAGE")
    console.print("  cd SAGE")
    console.print("  pip install -e packages/sage-tools[dev]")
    console.print("\n[bold]Option 2: Set SAGE_ROOT[/bold]")
    console.print("  export SAGE_ROOT=/path/to/your/SAGE")
    console.print("\n[bold]Then you can use:[/bold]")
    console.print("  sage-dev examples analyze")
    console.print("  sage-dev examples test --quick")
    console.print("  python this_demo.py")
    console.print()


def main():
    """主函数"""
    console.print("[bold cyan]=" * 60 + "[/bold cyan]")
    console.print("[bold cyan]SAGE Examples Testing Tools - Demo[/bold cyan]")
    console.print("[bold cyan]=" * 60 + "[/bold cyan]")

    # 检查环境
    has_dev_env = check_environment()

    if not has_dev_env:
        console.print("\n[yellow]⚠️  Development environment not available[/yellow]")
        show_setup_guide()
        console.print("[blue]ℹ️  This is expected if you installed via PyPI[/blue]")
        console.print("[blue]ℹ️  Examples testing is only for SAGE developers[/blue]")
        return

    console.print("\n[green]✅ Development environment is ready![/green]")

    # 运行演示
    console.print("\n" + "=" * 60)

    # 1. 分析示例
    if demo_analysis():
        console.print("\n[green]✅ Analysis completed[/green]")

    # 2. 运行快速测试（可选，注释掉以加快演示）
    # Uncomment to run actual tests:
    # console.print("\n" + "=" * 60)
    # if demo_quick_test():
    #     console.print("\n[green]✅ Tests completed[/green]")

    console.print("\n" + "=" * 60)
    console.print("\n[bold green]🎉 Demo completed successfully![/bold green]\n")
    console.print("For more information:")
    console.print("  sage-dev examples --help")
    console.print("  See: packages/sage-tools/src/sage/tools/dev/examples/README.md")
    console.print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Demo interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Unexpected error: {e}[/red]")
        import traceback

        traceback.print_exc()
