"""
SAGE 文档命令

提供文档预览、构建和部署功能
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(help="📚 文档管理 - 预览、构建和部署文档")
console = Console()


def find_docs_dir() -> Optional[Path]:
    """查找文档目录"""
    # 从当前目录向上查找
    current = Path.cwd()

    # 检查常见位置
    candidates = [
        current / "docs-public",
        current.parent / "docs-public",
        current.parent.parent / "docs-public",
    ]

    # 如果在 SAGE 项目中
    for candidate in candidates:
        if candidate.exists() and (candidate / "mkdocs.yml").exists():
            return candidate

    return None


def check_mkdocs_installed() -> bool:
    """检查 mkdocs 是否安装"""
    try:
        subprocess.run(["mkdocs", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


@app.command("serve")
def serve(
    port: int = typer.Option(8000, "--port", "-p", help="服务端口"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="绑定地址"),
    dev_addr: Optional[str] = typer.Option(None, "--dev-addr", help="开发服务器地址 (host:port)"),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="自动打开浏览器"),
):
    """
    🚀 启动文档预览服务器

    示例：
      sage docs serve                    # 默认 127.0.0.1:8000
      sage docs serve --port 8080        # 指定端口
      sage docs serve --host 0.0.0.0     # 监听所有网卡
      sage docs serve --dev-addr 0.0.0.0:8080
    """
    # 检查 mkdocs
    if not check_mkdocs_installed():
        console.print(
            Panel(
                "[red]❌ MkDocs 未安装[/red]\n\n"
                "请先安装 MkDocs：\n"
                "  [cyan]pip install mkdocs-material[/cyan]",
                title="错误",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    # 查找文档目录
    docs_dir = find_docs_dir()
    if not docs_dir:
        console.print(
            Panel(
                "[red]❌ 未找到文档目录[/red]\n\n请确保在 SAGE 项目目录中运行此命令",
                title="错误",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    console.print(f"[green]📚 文档目录:[/green] {docs_dir}")

    # 构建命令
    cmd = ["mkdocs", "serve"]

    if dev_addr:
        cmd.extend(["--dev-addr", dev_addr])
    else:
        cmd.extend(["--dev-addr", f"{host}:{port}"])

    if not open_browser:
        cmd.append("--no-livereload")

    # 显示信息
    addr = dev_addr or f"{host}:{port}"
    console.print(
        Panel(
            f"[green]🚀 启动文档服务器...[/green]\n\n"
            f"地址: [cyan]http://{addr}[/cyan]\n"
            f"目录: [dim]{docs_dir}[/dim]\n\n"
            f"[yellow]💡 提示:[/yellow]\n"
            f"  • 文档会自动重载\n"
            f"  • 按 Ctrl+C 停止服务器",
            title="文档预览",
            border_style="green",
        )
    )

    # 启动服务器
    try:
        subprocess.run(cmd, cwd=docs_dir)
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 文档服务器已停止[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ 启动失败: {e}[/red]")
        raise typer.Exit(1)


@app.command("build")
def build(
    strict: bool = typer.Option(False, "--strict", help="严格模式 (有警告则失败)"),
    clean: bool = typer.Option(True, "--clean/--no-clean", help="构建前清理"),
    output_dir: Optional[str] = typer.Option(None, "--output", "-o", help="输出目录"),
):
    """
    🔨 构建静态文档站点

    示例：
      sage docs build                # 构建到默认目录
      sage docs build --strict       # 严格模式
      sage docs build -o ./site      # 指定输出目录
    """
    # 检查 mkdocs
    if not check_mkdocs_installed():
        console.print("[red]❌ MkDocs 未安装，请先安装: pip install mkdocs-material[/red]")
        raise typer.Exit(1)

    # 查找文档目录
    docs_dir = find_docs_dir()
    if not docs_dir:
        console.print("[red]❌ 未找到文档目录[/red]")
        raise typer.Exit(1)

    console.print(f"[green]📚 文档目录:[/green] {docs_dir}")

    # 构建命令
    cmd = ["mkdocs", "build"]

    if strict:
        cmd.append("--strict")

    if clean:
        cmd.append("--clean")

    if output_dir:
        cmd.extend(["--site-dir", output_dir])

    console.print(Panel("[green]🔨 开始构建文档...[/green]", title="构建", border_style="green"))

    # 执行构建
    try:
        subprocess.run(cmd, cwd=docs_dir, check=True)

        output = output_dir or "site"
        console.print(
            Panel(
                f"[green]✅ 构建成功！[/green]\n\n输出目录: [cyan]{docs_dir / output}[/cyan]",
                title="完成",
                border_style="green",
            )
        )
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ 构建失败: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ 构建失败: {e}[/red]")
        raise typer.Exit(1)


@app.command("install-deps")
def install_deps():
    """
    📦 安装文档依赖

    安装 MkDocs 和所需插件
    """
    console.print(Panel("[green]📦 安装文档依赖...[/green]", title="安装", border_style="green"))

    packages = [
        "mkdocs>=1.6.0",
        "mkdocs-material>=9.5.0",
    ]

    try:
        cmd = [sys.executable, "-m", "pip", "install"] + packages
        subprocess.run(cmd, check=True)

        console.print(
            Panel(
                "[green]✅ 依赖安装完成！[/green]\n\n"
                "现在可以使用：\n"
                "  [cyan]sage docs serve[/cyan]  - 预览文档\n"
                "  [cyan]sage docs build[/cyan]  - 构建文档",
                title="完成",
                border_style="green",
            )
        )
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ 安装失败: {e}[/red]")
        raise typer.Exit(1)


@app.command("info")
def info():
    """
    ℹ️  显示文档信息

    显示文档目录、配置等信息
    """
    docs_dir = find_docs_dir()

    if not docs_dir:
        console.print("[red]❌ 未找到文档目录[/red]")
        raise typer.Exit(1)

    # 读取配置
    config_file = docs_dir / "mkdocs.yml"
    mkdocs_installed = check_mkdocs_installed()

    info_text = f"""
[cyan]文档目录:[/cyan] {docs_dir}
[cyan]配置文件:[/cyan] {config_file}
[cyan]MkDocs:[/cyan] {"✅ 已安装" if mkdocs_installed else "❌ 未安装"}

[yellow]快速命令:[/yellow]
  sage docs serve        - 启动预览服务器
  sage docs build        - 构建静态站点
  sage docs install-deps - 安装依赖
"""

    console.print(Panel(info_text, title="📚 文档信息", border_style="blue"))


if __name__ == "__main__":
    app()
