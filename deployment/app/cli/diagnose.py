import typer
import subprocess

app = typer.Typer(help="诊断与维护相关命令。包括系统诊断、权限修复等。使用 --help 查看所有子命令。")

@app.command()
def diagnose():
    """系统诊断：检查依赖、端口、服务状态。"""
    typer.echo("正在进行系统诊断...")
    try:
        subprocess.run(["bash", "deployment/sage_deployment.sh", "health"], check=True)
    except subprocess.CalledProcessError:
        typer.echo("[错误] 系统诊断失败，请检查部署环境。", err=True)

@app.command()
def logs_collect(path: str = typer.Option(None, "--path", help="日志收集保存路径（暂未实现）")):
    """收集系统日志（暂未实现）。"""
    typer.echo("正在收集系统日志...")
    typer.echo("功能暂未实现，请手动收集 logs 目录下日志文件。", err=True)

@app.command()
def cleanup():
    """清理临时文件（暂未实现）。"""
    typer.echo("正在清理临时文件...")
    typer.echo("功能暂未实现，请手动清理 /tmp/sage 或 logs 目录。", err=True)

@app.command()
def report(path: str = typer.Option(None, "--path", help="报告保存路径（暂未实现）")):
    """生成系统报告（暂未实现）。"""
    typer.echo("正在生成系统报告...")
    typer.echo("功能暂未实现。", err=True)

@app.command()
def permissions_fix(confirm: bool = typer.Option(False, "--yes", help="无需确认，直接修复权限")):
    """修复系统权限。"""
    if not confirm:
        typer.confirm("确定要修复系统权限吗？", abort=True)
    typer.echo("正在修复系统权限...")
    try:
        subprocess.run(["bash", "deployment/sage_deployment.sh", "system-install"], check=True)
    except subprocess.CalledProcessError:
        typer.echo("[错误] 权限修复失败，请检查权限。", err=True)

@app.command()
def permissions_check():
    """检查权限状态（暂未实现）。"""
    typer.echo("正在检查权限状态...")
    typer.echo("功能暂未实现，请手动检查相关目录权限。", err=True)

@app.command()
def main():
    """诊断与维护主入口（占位）。"""
    typer.echo("请使用子命令或 --help 查看可用功能。")
