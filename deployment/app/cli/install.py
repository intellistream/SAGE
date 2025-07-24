import typer
import subprocess
import sys

app = typer.Typer(help="安装与环境管理相关命令。支持多种安装模式，详细参数请用 --help 查看。")

@app.command()
def install(
    minimal: bool = typer.Option(False, "--minimal", help="最小化安装（不使用Docker）"),
    docker: bool = typer.Option(False, "--docker", help="使用Docker进行安装"),
    dependencies: bool = typer.Option(False, "--dependencies", help="仅安装系统依赖")
):
    """交互式安装向导：可选最小化、Docker或依赖安装。"""
    script_path = "setup.sh"
    try:
        if minimal:
            typer.echo("执行最小化安装...")
            subprocess.run(["bash", script_path], input="1\n", text=True, check=True)
        elif docker:
            typer.echo("执行Docker安装...")
            subprocess.run(["bash", script_path], input="2\n", text=True, check=True)
        elif dependencies:
            typer.echo("仅安装系统依赖...")
            subprocess.run(["bash", script_path], input="1\n", text=True, check=True)
        else:
            typer.echo("启动交互式安装向导...")
            subprocess.run(["bash", script_path], check=True)
    except subprocess.CalledProcessError:
        typer.echo("[错误] 安装过程失败，请检查环境和依赖。", err=True)

@app.command()
def env_setup():
    """设置Conda环境。"""
    typer.echo("正在设置Conda环境...")
    try:
        subprocess.run(["bash", "setup.sh"], input="1\n", text=True, check=True)
    except subprocess.CalledProcessError:
        typer.echo("[错误] Conda环境设置失败。", err=True)

@app.command()
def env_activate():
    """激活SAGE环境。"""
    typer.echo("请在终端运行: conda activate sage")

@app.command()
def auth_huggingface():
    """配置HuggingFace认证。"""
    typer.echo("正在配置HuggingFace认证...")
    try:
        subprocess.run(["bash", "setup.sh"], input="6\n", text=True, check=True)
    except subprocess.CalledProcessError:
        typer.echo("[错误] HuggingFace认证失败。", err=True)

# ...可继续扩展其它安装相关命令...
