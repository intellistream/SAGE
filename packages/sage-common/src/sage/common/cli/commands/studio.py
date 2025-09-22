"""
SAGE CLI Studio Command

Studio前端管理命令，用于启动和管理SAGE Studio低代码编辑器。
"""

import typer
import subprocess
import os
import sys
import time
import requests
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from pathlib import Path

app = typer.Typer(name="studio", help="🎨 Studio - 低代码可视化管道编辑器")
console = Console()


def get_sage_root() -> Path:
    """获取SAGE项目根目录"""
    # 从当前文件位置推导SAGE根目录
    current_file = Path(__file__).resolve()
    # 当前文件在 packages/sage-common/src/sage/common/cli/commands/studio.py
    # 需要向上8级到达SAGE根目录 (/home/shuhao/SAGE)
    sage_root = current_file
    for _ in range(8):
        sage_root = sage_root.parent
SAGE_ROOT_MARKER = "pyproject.toml"  # 可根据实际情况修改为项目根目录下的标志文件

def get_sage_root() -> Path:
    """获取SAGE项目根目录（通过查找标志文件）"""
    current_file = Path(__file__).resolve()
    sage_root = current_file.parent
    while sage_root != sage_root.parent:
        marker = sage_root / SAGE_ROOT_MARKER
        if marker.exists():
            return sage_root
        sage_root = sage_root.parent
    raise FileNotFoundError(f"未找到SAGE项目根目录标志文件: {SAGE_ROOT_MARKER}")


def get_studio_dir() -> Path:
    """获取Studio目录"""
    sage_root = get_sage_root()
    return sage_root / "packages" / "sage-common" / "src" / "sage" / "common" / "frontend" / "studio"


def get_studio_script() -> Path:
    """获取Studio管理脚本路径"""
    sage_root = get_sage_root()
    return sage_root / "scripts" / "studio_manager.sh"


def run_studio_script(command: str) -> int:
    """运行Studio管理脚本"""
    script_path = get_studio_script()
    
    if not script_path.exists():
        console.print(f"[red]❌ Studio管理脚本不存在: {script_path}[/red]")
        return 1
    
    try:
        # 确保脚本有执行权限
        os.chmod(script_path, 0o755)
        
        # 执行脚本
        result = subprocess.run([str(script_path), command], 
                              capture_output=False, 
                              text=True)
        return result.returncode
    except Exception as e:
        console.print(f"[red]❌ 执行失败: {e}[/red]")
        return 1


@app.command("start")
def start(
    dev: bool = typer.Option(False, "--dev", "-d", help="开发模式启动"),
    background: bool = typer.Option(True, "--background", "-b", help="后台运行")
):
    """启动 Studio 服务"""
    
    console.print(Panel.fit(
        "[bold cyan]🎨 启动 SAGE Studio[/bold cyan]\n\n"
        "Studio 是 SAGE 的低代码可视化管道编辑器\n"
        "功能包括：操作符编辑、管道设计、作业管理",
        title="Studio 服务"
    ))
    
    # 检查依赖
    studio_dir = get_studio_dir()
    if not studio_dir.exists():
        console.print(f"[red]❌ Studio目录不存在: {studio_dir}[/red]")
        raise typer.Exit(1)
    
    # 检查Node.js
    try:
        result = subprocess.run(["node", "--version"], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            console.print("[red]❌ Node.js 未安装，请先安装 Node.js 18+[/red]")
            raise typer.Exit(1)
        console.print(f"[green]✅ Node.js 版本: {result.stdout.strip()}[/green]")
    except FileNotFoundError:
        console.print("[red]❌ Node.js 未安装，请先安装 Node.js 18+[/red]")
        raise typer.Exit(1)
    
    # 运行启动脚本
    exit_code = run_studio_script("start")
    if exit_code == 0:
        console.print("\n[bold green]🎉 Studio 启动成功！[/bold green]")
        console.print("📱 访问地址: http://localhost:4200")
        console.print("💡 使用 'sage studio status' 检查状态")
    else:
        raise typer.Exit(exit_code)


@app.command("stop")
def stop():
    """停止 Studio 服务"""
    console.print("[cyan]🛑 停止 Studio 服务...[/cyan]")
    
    exit_code = run_studio_script("stop")
    if exit_code == 0:
        console.print("[green]✅ Studio 已停止[/green]")
    else:
        raise typer.Exit(exit_code)


@app.command("restart")
def restart():
    """重启 Studio 服务"""
    console.print("[cyan]🔄 重启 Studio 服务...[/cyan]")
    
    exit_code = run_studio_script("restart")
    if exit_code == 0:
        console.print("[green]✅ Studio 重启成功[/green]")
        console.print("📱 访问地址: http://localhost:4200")
    else:
        raise typer.Exit(exit_code)


@app.command("status")
def status():
    """检查 Studio 服务状态"""
    console.print("[cyan]🔍 检查 Studio 服务状态...[/cyan]")
    
    # 使用脚本检查状态
    exit_code = run_studio_script("status")
    
    # 同时检查HTTP连通性
    try:
        response = requests.get("http://localhost:4200", timeout=3)
        if response.status_code == 200:
            console.print("[green]✅ HTTP服务响应正常[/green]")
        else:
            console.print(f"[yellow]⚠️ HTTP响应异常: {response.status_code}[/yellow]")
    except requests.RequestException:
        console.print("[red]❌ HTTP服务无法连接[/red]")
    
    return exit_code


@app.command("logs")
def logs(
    lines: int = typer.Option(50, "--lines", "-n", help="显示的日志行数"),
    follow: bool = typer.Option(False, "--follow", "-f", help="实时跟踪日志")
):
    """查看 Studio 运行日志"""
    if follow:
        console.print("[cyan]📜 实时跟踪 Studio 日志 (Ctrl+C 退出)...[/cyan]")
        try:
            log_file = "/tmp/sage-studio.log"
            if os.path.exists(log_file):
                subprocess.run(["tail", "-f", log_file])
            else:
                console.print("[yellow]⚠️ 日志文件不存在[/yellow]")
        except KeyboardInterrupt:
            console.print("\n[cyan]📜 日志跟踪已停止[/cyan]")
    else:
        exit_code = run_studio_script("logs")


@app.command("install")
def install():
    """安装 Studio 依赖"""
    console.print("[cyan]📦 安装 Studio 依赖...[/cyan]")
    
    exit_code = run_studio_script("install")
    if exit_code == 0:
        console.print("[green]✅ 依赖安装完成[/green]")
    else:
        raise typer.Exit(exit_code)


@app.command("info")
def info():
    """显示 Studio 信息"""
    
    # 获取路径信息
    studio_dir = get_studio_dir()
    script_path = get_studio_script()
    
    console.print(Panel.fit(
        "[bold cyan]🎨 SAGE Studio[/bold cyan]\n\n"
        "[bold]功能特性:[/bold]\n"
        "• 可视化管道编辑器 - 拖拽式设计\n"
        "• 操作符编辑器 - 代码编辑和管理\n"
        "• 作业监控 - 实时状态和性能\n"
        "• 低代码开发 - 简化流处理开发\n\n"
        "[bold]技术栈:[/bold]\n"
        "• Angular 16 + TypeScript\n"
        "• ng-zorro-antd UI组件\n"
        "• D3.js 可视化图形\n"
        "• Monaco Editor 代码编辑\n\n"
        "[bold]目标用户:[/bold]\n"
        "• 业务分析师和数据工程师\n"
        "• 需要可视化开发的用户",
        title="Studio 信息"
    ))
    
    # 显示路径信息
    path_table = Table(title="路径信息", show_header=True)
    path_table.add_column("项目", style="cyan")
    path_table.add_column("路径", style="white")
    path_table.add_column("状态", style="green")
    
    path_table.add_row(
        "Studio目录", 
        str(studio_dir),
        "✅ 存在" if studio_dir.exists() else "❌ 不存在"
    )
    path_table.add_row(
        "管理脚本",
        str(script_path),
        "✅ 存在" if script_path.exists() else "❌ 不存在"
    )
    
    console.print(path_table)
    
    console.print("\n[bold green]常用命令:[/bold green]")
    console.print("  sage studio start              # 启动服务")
    console.print("  sage studio start --dev        # 开发模式启动")
    console.print("  sage studio status             # 检查状态")
    console.print("  sage studio logs --follow      # 实时查看日志")
    console.print("  sage studio restart            # 重启服务")
    console.print("  sage studio stop               # 停止服务")


@app.command("open")
def open_browser():
    """在浏览器中打开 Studio"""
    console.print("[cyan]🌐 在浏览器中打开 Studio...[/cyan]")
    
    # 检查服务是否运行
    try:
        response = requests.get("http://localhost:4200", timeout=3)
        if response.status_code == 200:
            # 尝试在浏览器中打开
            import webbrowser
            webbrowser.open("http://localhost:4200")
            console.print("[green]✅ 已在浏览器中打开 Studio[/green]")
        else:
            console.print("[red]❌ Studio 服务未运行，请先启动服务[/red]")
            console.print("💡 使用 'sage studio start' 启动服务")
    except requests.RequestException:
        console.print("[red]❌ Studio 服务未运行，请先启动服务[/red]")
        console.print("💡 使用 'sage studio start' 启动服务")


@app.callback()
def callback():
    """
    Studio 命令 - SAGE 低代码可视化管道编辑器
    
    🎨 Studio 提供：
    • 可视化管道编辑器
    • 操作符代码编辑
    • 作业状态监控
    • 低代码开发体验
    
    📖 快速开始：
    sage studio start               # 启动服务 (http://localhost:4200)
    sage studio open                # 在浏览器中打开
    sage studio status              # 检查状态
    """
    pass


if __name__ == "__main__":
    app()
