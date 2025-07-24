import typer
import yaml
from pathlib import Path

app = typer.Typer(help="配置与信息相关命令。支持配置展示、修改、版本查询等。详细参数请用 --help 查看。")

CONFIG_PATH = Path.home() / ".sage" / "config.yaml"

@app.command()
def show():
    """显示当前配置。"""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            typer.echo("当前配置:")
            typer.echo(yaml.dump(config, allow_unicode=True))
        except Exception as e:
            typer.echo(f"[错误] 读取配置失败: {e}", err=True)
    else:
        typer.echo(f"未找到配置文件: {CONFIG_PATH}", err=True)

@app.command()
def set(key: str = typer.Argument(..., help="配置项名"), value: str = typer.Argument(..., help="配置项值")):
    """设置配置项。支持简单的一级key。"""
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}
        config[key] = value
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, allow_unicode=True)
        typer.echo(f"已设置 {key} = {value}")
    except Exception as e:
        typer.echo(f"[错误] 设置配置失败: {e}", err=True)

@app.command()
def version():
    """显示SAGE版本信息。"""
    try:
        import pkg_resources
        version = pkg_resources.get_distribution("sage").version
        typer.echo(f"SAGE 版本: {version}")
    except Exception:
        typer.echo("无法获取版本信息", err=True)

@app.command()
def help():
    """显示帮助信息。"""
    typer.echo("使用 sage config show/set/version/help 查看和管理配置信息。")

@app.command()
def main():
    """配置与信息主入口（占位）。"""
    typer.echo("请使用子命令或 --help 查看可用功能。")
