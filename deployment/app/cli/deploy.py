import typer
import subprocess

app = typer.Typer(help="系统部署与管理相关命令。支持启动、停止、重启、健康检查等。详细参数请用 --help 查看。")

@app.command()
def start(
    ray_only: bool = typer.Option(False, "--ray-only", help="仅启动Ray集群"),
    daemon_only: bool = typer.Option(False, "--daemon-only", help="仅启动JobManager守护进程")
):
    """启动SAGE系统（可选仅启动Ray或Daemon）。"""
    script_path = "deployment/sage_deployment.sh"
    try:
        if ray_only:
            typer.echo("仅启动Ray集群...")
            subprocess.run(["bash", script_path, "start-ray"], check=True)
        elif daemon_only:
            typer.echo("仅启动JobManager守护进程...")
            subprocess.run(["bash", script_path, "start-daemon"], check=True)
        else:
            typer.echo("启动SAGE系统（Ray+Daemon）...")
            subprocess.run(["bash", script_path, "start"], check=True)
    except subprocess.CalledProcessError:
        typer.echo("[错误] 启动失败，请检查系统环境。", err=True)

@app.command()
def stop():
    """停止SAGE系统。"""
    typer.echo("正在停止SAGE系统...")
    try:
        subprocess.run(["bash", "deployment/sage_deployment.sh", "stop"], check=True)
    except subprocess.CalledProcessError:
        typer.echo("[错误] 停止失败。", err=True)

@app.command()
def restart():
    """重启SAGE系统。"""
    typer.echo("正在重启SAGE系统...")
    try:
        subprocess.run(["bash", "deployment/sage_deployment.sh", "restart"], check=True)
    except subprocess.CalledProcessError:
        typer.echo("[错误] 重启失败。", err=True)

@app.command()
def status():
    """显示系统状态。"""
    typer.echo("查询SAGE系统状态...")
    try:
        subprocess.run(["bash", "deployment/sage_deployment.sh", "status"], check=True)
    except subprocess.CalledProcessError:
        typer.echo("[错误] 状态查询失败。", err=True)

@app.command()
def health():
    """健康检查。"""
    typer.echo("正在进行健康检查...")
    try:
        subprocess.run(["bash", "deployment/sage_deployment.sh", "health"], check=True)
    except subprocess.CalledProcessError:
        typer.echo("[错误] 健康检查失败。", err=True)

@app.command()
def monitor(refresh: int = typer.Option(5, "--refresh", help="刷新间隔（秒）")):
    """实时监控系统。可指定刷新间隔。"""
    typer.echo(f"实时监控SAGE系统，每{refresh}秒刷新...")
    try:
        subprocess.run(["bash", "deployment/sage_deployment.sh", "monitor", str(refresh)], check=True)
    except subprocess.CalledProcessError:
        typer.echo("[错误] 监控失败。", err=True)

@app.command()
def main():
    """系统部署与管理主入口（占位）。"""
    typer.echo("请使用子命令或 --help 查看可用功能。")
