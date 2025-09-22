"""
SAGE CLI Web UI Command

Web管理界面命令，用于启动和管理SAGE Web UI服务。
"""

import typer
from typing import Optional
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(name="web-ui", help="🌐 Web UI - Web管理界面和API文档服务")
console = Console()


@app.command("start")
def start(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="服务器绑定地址"),
    port: int = typer.Option(8080, "--port", "-p", help="服务器端口"),
    reload: bool = typer.Option(False, "--reload", "-r", help="开启自动重载 (开发模式)")
):
    """启动 Web UI 服务"""
    
    console.print(Panel.fit(
        f"[bold cyan]🌐 启动 SAGE Web UI[/bold cyan]\n\n"
        f"地址: http://{host}:{port}\n"
        f"API文档: http://{host}:{port}/docs\n"
        f"健康检查: http://{host}:{port}/health",
        title="Web UI 服务"
    ))
    
    try:
        # 动态导入以避免硬依赖
        from sage.common.frontend.web_ui.app import start_server
        start_server(host=host, port=port, reload=reload)
    except ImportError as e:
        console.print(f"[red]❌ 无法启动 Web UI: {e}[/red]")
        console.print("[yellow]💡 请确保已安装 frontend 依赖: pip install isage[frontend][/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ 启动失败: {e}[/red]")
        raise typer.Exit(1)


@app.command("status")
def status():
    """检查 Web UI 服务状态"""
    import requests
    from requests.exceptions import RequestException
    
    console.print("[cyan]🔍 检查 Web UI 服务状态...[/cyan]")
    
    try:
        response = requests.get("http://127.0.0.1:8080/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            console.print(Panel.fit(
                f"[bold green]✅ Web UI 服务运行正常[/bold green]\n\n"
                f"服务: {data.get('service', 'Unknown')}\n"
                f"状态: {data.get('status', 'Unknown')}\n"
                f"时间: {data.get('timestamp', 'Unknown')}",
                title="服务状态"
            ))
        else:
            console.print(f"[yellow]⚠️ 服务响应异常: HTTP {response.status_code}[/yellow]")
    except RequestException:
        console.print("[red]❌ Web UI 服务未运行或无法连接[/red]")
        console.print("[yellow]💡 使用 'sage web-ui start' 启动服务[/yellow]")


@app.command("info")
def info():
    """显示 Web UI 信息"""
    
    console.print(Panel.fit(
        "[bold cyan]🌐 SAGE Web UI[/bold cyan]\n\n"
        "[bold]功能特性:[/bold]\n"
        "• API 文档和交互式测试界面\n"
        "• 系统健康检查和监控\n"
        "• Web 管理界面\n"
        "• 开发者工具和调试功能\n\n"
        "[bold]技术栈:[/bold]\n"
        "• Python + FastAPI\n"
        "• 自动生成的 OpenAPI 文档\n"
        "• 响应式 HTML 界面\n\n"
        "[bold]目标用户:[/bold]\n"
        "• 开发者和系统管理员\n"
        "• API 集成和调试",
        title="Web UI 信息"
    ))
    
    console.print("\n[bold green]常用命令:[/bold green]")
    console.print("  sage web-ui start              # 启动服务")
    console.print("  sage web-ui start --reload     # 开发模式启动") 
    console.print("  sage web-ui status             # 检查状态")
    console.print("  sage web-ui info               # 显示信息")


@app.callback()
def callback():
    """
    Web UI 命令 - SAGE Web管理界面和API文档服务
    
    🌐 Web UI 提供：
    • API 文档和交互式测试界面
    • 系统健康检查和监控 
    • Web 管理界面
    • 开发者工具
    
    📖 快速开始：
    sage web-ui start               # 启动服务 (http://localhost:8080)
    sage web-ui start --reload      # 开发模式
    sage web-ui status              # 检查状态
    """
    pass


if __name__ == "__main__":
    app()
