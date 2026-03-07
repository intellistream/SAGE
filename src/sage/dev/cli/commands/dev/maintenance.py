"""
SAGE 维护工具 CLI 命令

提供各种项目维护相关的命令

Author: SAGE Team
Date: 2025-10-27
"""

from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(
    name="maintenance",
    help="🔧 项目维护工具",
    no_args_is_help=True,
)

console = Console()


@app.command("organize-devnotes")
def organize_devnotes(
    root: Path | None = typer.Option(
        None,
        "--root",
        "-r",
        help="项目根目录（默认：当前目录）",
    ),
    verbose: bool = typer.Option(
        True,
        "--verbose/--quiet",
        "-v/-q",
        help="详细输出",
    ),
):
    """
    📊 整理 dev-notes 文档

    分析文档内容、建议分类、检查元数据、生成整理建议
    """
    try:
        from sage_dev_tools.docs import DevNotesOrganizer

        if root is None:
            root = Path.cwd()

        console.print("\n[bold]📊 分析 dev-notes 文档...[/bold]")
        console.print(f"项目根目录: {root}\n")

        organizer = DevNotesOrganizer(root)
        results = organizer.analyze_all()
        report = organizer.generate_report(results, verbose=verbose)

        console.print("\n[green]✅ 分析完成！[/green]")
        console.print(
            f"共分析 {report['total']} 个文件，"
            f"发现 {len(report['root_files'])} 个需要整理的根目录文件"
        )

    except Exception as e:
        console.print(f"[red]❌ 执行失败: {e}[/red]")
        raise typer.Exit(1)


@app.command("fix-metadata")
def fix_metadata(
    root: Path | None = typer.Option(
        None,
        "--root",
        "-r",
        help="项目根目录（默认：当前目录）",
    ),
    scan: bool = typer.Option(
        False,
        "--scan",
        "-s",
        help="扫描并修复所有缺失元数据的文件",
    ),
):
    """
    📝 修复 dev-notes 文档元数据

    为缺少元数据（Date、Author、Summary）的文档添加元数据
    """
    try:
        from sage_dev_tools.docs import MetadataFixer

        if root is None:
            root = Path.cwd()

        console.print("\n[bold]📝 修复文档元数据...[/bold]")
        console.print(f"项目根目录: {root}\n")

        fixer = MetadataFixer(root)

        if scan:
            console.print("[yellow]⚠️  扫描模式：将使用默认元数据[/yellow]")
            console.print("[yellow]⚠️  请在修复后手动更新实际的日期和摘要[/yellow]\n")
            stats = fixer.scan_and_fix()
        else:
            stats = fixer.fix_all()

        console.print("\n[green]✅ 修复完成！[/green]")
        console.print(
            f"成功: {stats['success']}, 跳过: {stats['skipped']}, 失败: {stats['failed']}"
        )

    except Exception as e:
        console.print(f"[red]❌ 执行失败: {e}[/red]")
        raise typer.Exit(1)


@app.command("update-ruff-ignore")
def update_ruff_ignore(
    root: Path | None = typer.Option(
        None,
        "--root",
        "-r",
        help="项目根目录（默认：当前目录）",
    ),
    rules: str | None = typer.Option(
        None,
        "--rules",
        help="要添加的规则，逗号分隔（如：B904,C901）",
    ),
    preset: str | None = typer.Option(
        None,
        "--preset",
        help="使用预设规则集（如：b904-c901）",
    ),
):
    """
    🔧 更新 Ruff ignore 规则

    批量更新所有 pyproject.toml 文件中的 ruff.lint.ignore 规则
    """
    try:
        from sage_dev_tools.quality import RuffIgnoreUpdater

        if root is None:
            root = Path.cwd()

        console.print("\n[bold]🔧 更新 Ruff ignore 规则...[/bold]")
        console.print(f"项目根目录: {root}\n")

        updater = RuffIgnoreUpdater(root)

        if preset == "b904-c901":
            console.print("[cyan]使用预设: B904 + C901[/cyan]\n")
            stats = updater.add_b904_c901()
        elif rules:
            rules_list = [r.strip() for r in rules.split(",")]
            console.print(f"[cyan]添加规则: {', '.join(rules_list)}[/cyan]\n")
            stats = updater.update_all(rules_list)
        else:
            console.print("[yellow]请指定 --rules 或 --preset[/yellow]")
            console.print("\n示例:")
            console.print("  sage-dev maintenance update-ruff-ignore --preset b904-c901")
            console.print("  sage-dev maintenance update-ruff-ignore --rules B904,C901")
            raise typer.Exit(1)

        console.print("\n[green]✅ 更新完成！[/green]")
        console.print(
            f"更新: {stats['updated']}, 跳过: {stats['skipped']}, 失败: {stats['failed']}"
        )

    except Exception as e:
        console.print(f"[red]❌ 执行失败: {e}[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_tools():
    """
    📋 列出所有维护工具

    显示可用的维护工具及其说明
    """
    console.print("\n[bold]🔧 SAGE 维护工具[/bold]\n")

    tools = [
        ("organize-devnotes", "整理 dev-notes 文档", "📊"),
        ("fix-metadata", "修复文档元数据", "📝"),
        ("update-ruff-ignore", "更新 Ruff ignore 规则", "🔧"),
    ]

    for cmd, desc, icon in tools:
        console.print(f"{icon} [cyan]{cmd}[/cyan]")
        console.print(f"   {desc}")
        console.print()

    console.print("[dim]使用 sage-dev maintenance <command> --help 查看详细帮助[/dim]\n")


if __name__ == "__main__":
    app()
