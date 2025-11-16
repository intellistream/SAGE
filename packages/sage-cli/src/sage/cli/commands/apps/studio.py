"""SAGE Studio CLI - Studio Web 界面管理命令"""

import typer
from rich.console import Console

# 导入StudioManager类 - 从新的sage-studio包导入
from sage.studio.studio_manager import StudioManager

console = Console()
app = typer.Typer(help="SAGE Studio - 图形化界面管理工具")

# 创建StudioManager实例
studio_manager = StudioManager()


@app.command()
def start(
    port: int | None = typer.Option(None, "--port", "-p", help="指定端口"),
    host: str = typer.Option("localhost", "--host", "-h", help="指定主机"),
    dev: bool = typer.Option(False, "--dev", help="开发模式"),
):
    """启动 SAGE Studio"""
    console.print("[blue]🚀 启动 SAGE Studio...[/blue]")

    try:
        # 先检查是否已经在运行
        running_pid = studio_manager.is_running()
        if running_pid:
            config = studio_manager.load_config()
            url = f"http://{config['host']}:{config['port']}"
            console.print(f"[green]✅ Studio 已经在运行中 (PID: {running_pid})[/green]")
            console.print(f"[blue]🌐 访问地址: {url}[/blue]")
            return

        success = studio_manager.start(port=port, host=host, dev=dev)
        if success:
            console.print("[green]✅ Studio 启动成功[/green]")
        else:
            console.print("[red]❌ Studio 启动失败[/red]")
    except Exception as e:
        console.print(f"[red]❌ 启动失败: {e}[/red]")


@app.command()
def stop():
    """停止 SAGE Studio"""
    console.print("[blue]🛑 停止 SAGE Studio...[/blue]")

    try:
        success = studio_manager.stop()
        if success:
            console.print("[green]✅ Studio 已停止[/green]")
        else:
            console.print("[yellow]ℹ️ Studio 未运行或停止失败[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ 停止失败: {e}[/red]")


@app.command()
def restart(
    port: int | None = typer.Option(None, "--port", "-p", help="指定端口"),
    host: str = typer.Option("localhost", "--host", "-h", help="指定主机"),
    dev: bool = typer.Option(False, "--dev", help="开发模式"),
):
    """重启 SAGE Studio"""
    console.print("[blue]🔄 重启 SAGE Studio...[/blue]")

    try:
        # 先停止
        studio_manager.stop()
        # 再启动
        success = studio_manager.start(port=port, host=host, dev=dev)
        if success:
            console.print("[green]✅ Studio 重启成功[/green]")
        else:
            console.print("[red]❌ Studio 重启失败[/red]")
    except Exception as e:
        console.print(f"[red]❌ 重启失败: {e}[/red]")


@app.command()
def status():
    """查看 SAGE Studio 状态"""
    console.print("[blue]📊 检查 SAGE Studio 状态...[/blue]")

    try:
        studio_manager.status()
    except Exception as e:
        console.print(f"[red]❌ 状态检查失败: {e}[/red]")


@app.command()
def logs(
    follow: bool = typer.Option(False, "--follow", "-f", help="跟踪日志"),
    backend: bool = typer.Option(False, "--backend", "-b", help="查看后端API日志"),
):
    """查看 SAGE Studio 日志"""
    console.print("[blue]📋 查看 Studio 日志...[/blue]")

    try:
        studio_manager.logs(follow=follow, backend=backend)
    except Exception as e:
        console.print(f"[red]❌ 查看日志失败: {e}[/red]")


@app.command()
def install():
    """安装 SAGE Studio 依赖"""
    console.print("[blue]📦 安装 SAGE Studio...[/blue]")

    try:
        success = studio_manager.install()
        if success:
            console.print("[green]✅ Studio 安装成功[/green]")
        else:
            console.print("[red]❌ Studio 安装失败[/red]")
    except Exception as e:
        console.print(f"[red]❌ 安装失败: {e}[/red]")


@app.command()
def build():
    """构建 SAGE Studio"""
    console.print("[blue]� 构建 SAGE Studio...[/blue]")

    try:
        success = studio_manager.build()
        if success:
            console.print("[green]✅ Studio 构建成功[/green]")
        else:
            console.print("[red]❌ Studio 构建失败[/red]")
    except Exception as e:
        console.print(f"[red]❌ 构建失败: {e}[/red]")


@app.command()
def open():
    """在浏览器中打开 Studio"""
    console.print("[blue]🌐 打开 Studio 界面...[/blue]")

    try:
        import webbrowser

        running_pid = studio_manager.is_running()
        if running_pid:
            config = studio_manager.load_config()
            url = f"http://{config['host']}:{config['port']}"
            webbrowser.open(url)
            console.print(f"[green]✅ 已在浏览器中打开: {url}[/green]")
        else:
            console.print("[yellow]⚠️ Studio 未运行，请先启动 Studio[/yellow]")
            console.print("使用命令: [bold]sage studio start[/bold]")
    except Exception as e:
        console.print(f"[red]❌ 打开失败: {e}[/red]")


@app.command()
def clean():
    """清理 Studio 缓存和临时文件"""
    console.print("[blue]🧹 清理 Studio 缓存...[/blue]")

    try:
        success = studio_manager.clean()
        if success:
            console.print("[green]✅ 清理完成[/green]")
        else:
            console.print("[red]❌ 清理失败[/red]")
    except Exception as e:
        console.print(f"[red]❌ 清理失败: {e}[/red]")


@app.command()
def npm(
    args: list[str] = typer.Argument(
        ...,
        metavar="ARGS...",
        help="传递给 npm 的参数，例如: install、run build、run lint",
    ),
):
    """在 Studio 前端目录中运行 npm 命令。"""
    joined = " ".join(args)
    console.print(f"[blue]执行 npm {joined}[/blue]")

    success = studio_manager.run_npm_command(args)
    if not success:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
