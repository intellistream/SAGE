import typer
import subprocess

app = typer.Typer(help="CLI工具管理相关命令。支持安装、卸载、检查、更新等。详细参数请用 --help 查看。")

@app.command()
def install():
    """安装CLI工具（如sage-jm）。"""
    typer.echo("正在安装CLI工具...")
    try:
        subprocess.run(["bash", "deployment/scripts/cli_manager.sh", "setup_cli_tools"], check=True)
    except subprocess.CalledProcessError:
        typer.echo("[错误] CLI工具安装失败。", err=True)

@app.command()
def uninstall():
    """卸载CLI工具。"""
    typer.echo("正在卸载CLI工具...")
    try:
        subprocess.run(["bash", "deployment/scripts/cli_manager.sh", "uninstall_cli_tools"], check=True)
    except subprocess.CalledProcessError:
        typer.echo("[错误] CLI工具卸载失败。", err=True)

@app.command()
def check():
    """检查CLI工具状态。"""
    typer.echo("正在检查CLI工具状态...")
    try:
        subprocess.run(["bash", "deployment/scripts/cli_manager.sh", "check_cli_tools"], check=True)
    except subprocess.CalledProcessError:
        typer.echo("[错误] CLI工具状态检查失败。", err=True)

@app.command()
def update():
    """更新CLI工具。"""
    typer.echo("正在更新CLI工具...")
    try:
        subprocess.run(["bash", "deployment/scripts/cli_manager.sh", "reinstall_cli_tools"], check=True)
    except subprocess.CalledProcessError:
        typer.echo("[错误] CLI工具更新失败。", err=True)

@app.command()
def info():
    """显示CLI工具信息。"""
    try:
        subprocess.run(["bash", "deployment/scripts/cli_manager.sh", "get_cli_info"], check=True)
    except subprocess.CalledProcessError:
        typer.echo("[错误] 获取CLI工具信息失败。", err=True)

@app.command()
def main():
    """CLI工具管理主入口（占位）。"""
    typer.echo("请使用子命令或 --help 查看可用功能。")
