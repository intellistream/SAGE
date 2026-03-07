"""
文档管理命令

提供文档构建、预览和管理功能
"""

import subprocess
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(
    name="docs",
    help="📚 文档管理 - 构建、预览、检查文档",
    no_args_is_help=True,
)

console = Console()


@app.command("build")
def build_docs(
    root: Path | None = typer.Option(
        None,
        "--root",
        "-r",
        help="项目根目录（默认：当前目录）",
    ),
    clean: bool = typer.Option(
        False,
        "--clean",
        "-c",
        help="清理旧的构建文件",
    ),
):
    """
    📖 构建文档

    构建 MkDocs 文档到 docs-public/site/
    """
    try:
        if root is None:
            root = Path.cwd()

        docs_dir = root / "docs-public"

        if not docs_dir.exists():
            console.print(f"[red]❌ 文档目录不存在: {docs_dir}[/red]")
            raise typer.Exit(1)

        console.print("\n[bold]📖 构建文档...[/bold]")
        console.print(f"文档目录: {docs_dir}\n")

        # 检查 mkdocs 是否可用
        try:
            subprocess.run(
                ["mkdocs", "--version"],
                check=True,
                capture_output=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print("[red]❌ mkdocs 未安装[/red]")
            console.print("\n安装命令:")
            console.print("  [cyan]pip install mkdocs mkdocs-material[/cyan]\n")
            raise typer.Exit(1)

        # 切换到文档目录
        import os

        original_dir = os.getcwd()
        os.chdir(docs_dir)

        try:
            # 清理旧文件
            if clean:
                console.print("[yellow]清理旧的构建文件...[/yellow]")
                site_dir = docs_dir / "site"
                if site_dir.exists():
                    import shutil

                    shutil.rmtree(site_dir)
                    console.print("[green]✓ 清理完成[/green]\n")

            # 检查是否有自定义构建脚本
            build_script = docs_dir / "build.sh"
            if build_script.exists():
                console.print("[cyan]使用自定义构建脚本...[/cyan]")
                result = subprocess.run(
                    ["bash", str(build_script)],
                    capture_output=False,
                )
                if result.returncode != 0:
                    console.print("[red]❌ 构建失败[/red]")
                    raise typer.Exit(1)
            else:
                console.print("[cyan]使用 mkdocs 构建...[/cyan]")
                result = subprocess.run(
                    ["mkdocs", "build"],
                    capture_output=False,
                )
                if result.returncode != 0:
                    console.print("[red]❌ 构建失败[/red]")
                    raise typer.Exit(1)

            console.print("\n[green]✅ 文档构建成功！[/green]")
            console.print(f"输出目录: {docs_dir / 'site'}")

        finally:
            os.chdir(original_dir)

    except Exception as e:
        console.print(f"[red]❌ 构建失败: {e}[/red]")
        raise typer.Exit(1)


@app.command("serve")
def serve_docs(
    root: Path | None = typer.Option(
        None,
        "--root",
        "-r",
        help="项目根目录（默认：当前目录）",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        "-p",
        help="服务端口",
    ),
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        "-h",
        help="服务地址",
    ),
):
    """
    🌐 启动文档服务器

    启动本地文档服务器，支持热重载
    """
    try:
        if root is None:
            root = Path.cwd()

        docs_dir = root / "docs-public"

        if not docs_dir.exists():
            console.print(f"[red]❌ 文档目录不存在: {docs_dir}[/red]")
            raise typer.Exit(1)

        console.print("\n[bold]🌐 启动文档服务器...[/bold]")
        console.print(f"文档目录: {docs_dir}")
        console.print(f"服务地址: http://{host}:{port}\n")

        # 检查 mkdocs 是否可用
        try:
            subprocess.run(
                ["mkdocs", "--version"],
                check=True,
                capture_output=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print("[red]❌ mkdocs 未安装[/red]")
            console.print("\n安装命令:")
            console.print("  [cyan]pip install mkdocs mkdocs-material[/cyan]\n")
            raise typer.Exit(1)

        # 切换到文档目录
        import os

        original_dir = os.getcwd()
        os.chdir(docs_dir)

        try:
            console.print("[cyan]启动服务器（Ctrl+C 停止）...[/cyan]\n")
            subprocess.run(
                ["mkdocs", "serve", "-a", f"{host}:{port}"],
                check=False,
            )
        except KeyboardInterrupt:
            console.print("\n[yellow]服务器已停止[/yellow]")
        finally:
            os.chdir(original_dir)

    except Exception as e:
        console.print(f"[red]❌ 启动失败: {e}[/red]")
        raise typer.Exit(1)


@app.command("check")
def check_docs(
    root: Path | None = typer.Option(
        None,
        "--root",
        "-r",
        help="项目根目录（默认：当前目录）",
    ),
):
    """
    ✅ 检查文档

    检查文档链接、格式等
    """
    try:
        if root is None:
            root = Path.cwd()

        docs_dir = root / "docs-public"

        if not docs_dir.exists():
            console.print(f"[red]❌ 文档目录不存在: {docs_dir}[/red]")
            raise typer.Exit(1)

        console.print("\n[bold]✅ 检查文档...[/bold]")
        console.print(f"文档目录: {docs_dir}\n")

        # 检查 mkdocs.yml
        mkdocs_config = docs_dir / "mkdocs.yml"
        if not mkdocs_config.exists():
            console.print("[red]❌ mkdocs.yml 不存在[/red]")
            raise typer.Exit(1)

        console.print("[green]✓ mkdocs.yml 存在[/green]")

        # 检查 docs_src
        docs_src = docs_dir / "docs_src"
        if not docs_src.exists():
            console.print("[red]❌ docs_src 目录不存在[/red]")
            raise typer.Exit(1)

        console.print("[green]✓ docs_src 目录存在[/green]")

        # 统计文档文件
        md_files = list(docs_src.rglob("*.md"))
        console.print(f"[green]✓ 找到 {len(md_files)} 个 Markdown 文件[/green]")

        # 检查 index.md
        index_file = docs_src / "index.md"
        if index_file.exists():
            console.print("[green]✓ index.md 存在[/green]")
        else:
            console.print("[yellow]⚠ index.md 不存在[/yellow]")

        console.print("\n[green]✅ 文档检查完成！[/green]")

    except Exception as e:
        console.print(f"[red]❌ 检查失败: {e}[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_commands():
    """
    📋 列出所有文档命令

    显示可用的文档管理命令
    """
    console.print("\n[bold]📚 文档管理命令[/bold]\n")

    commands = [
        ("build", "构建文档", "📖"),
        ("serve", "启动文档服务器", "🌐"),
        ("check", "检查文档", "✅"),
    ]

    for cmd, desc, icon in commands:
        console.print(f"{icon} [cyan]{cmd}[/cyan]")
        console.print(f"   {desc}")
        console.print()

    console.print("[dim]使用 sage-dev docs <command> --help 查看详细帮助[/dim]\n")


if __name__ == "__main__":
    app()
