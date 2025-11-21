"""Environment management commands for the SAGE CLI."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from sage.cli.utils import env as env_utils

console = Console()
app = typer.Typer(name="env", help="🌱 环境变量与 .env 文件管理")


def _render_status(status: dict) -> None:
    """Pretty print environment status information."""

    project_root: Path = Path(str(status["project_root"]))  # type: ignore[arg-type]
    console.print(f"📁 项目根目录: [cyan]{project_root}[/cyan]")
    console.print(f"python-dotenv 可用: {'✅' if status['dotenv_available'] else '⚠️'}")
    console.print(
        f".env 存在: {'✅' if status['env_file_exists'] else '❌'} ({status['env_file']})"
    )
    console.print(
        f".env.template 存在: {'✅' if status['env_template_exists'] else '❌'} ({status['env_template']})"
    )

    table = Table(title="API Key 状态", show_edge=False, show_header=True)
    table.add_column("环境变量")
    table.add_column("已设置")
    table.add_column("长度")

    for key, info in status["api_keys"].items():
        icon = "✅" if info["set"] else "❌"
        length = str(info["length"]) if info["set"] else "-"
        table.add_row(key, icon, length)

    console.print(table)


def _open_env_file(env_path: Path) -> None:
    """Attempt to open the provided ``.env`` file in a suitable editor."""

    for editor in ("code", "nano", "vim"):
        if shutil.which(editor):
            console.print(f"💡 使用 {editor} 打开 {env_path}")
            try:
                subprocess.run([editor, str(env_path)], check=False)
            except OSError as exc:
                console.print(f"⚠️ 无法启动 {editor}: {exc}")
            return

    console.print(f"💡 请手动编辑文件: [cyan]{env_path}[/cyan]")


def _copy_template(project_root: Path, *, overwrite: bool = False) -> Path | None:
    env_template = project_root / ".env.template"
    env_file = project_root / ".env"

    if not env_template.exists():
        return None

    if env_file.exists() and not overwrite:
        return env_file

    shutil.copy(env_template, env_file)
    return env_file


def run_setup_interactive(open_editor: bool = True, overwrite: bool = False) -> dict:
    """Shared implementation used by the CLI and legacy script wrapper."""

    status = env_utils.check_environment_status()
    project_root: Path = Path(str(status["project_root"]))  # type: ignore[arg-type]

    console.print("🔧 [bold]SAGE 环境配置向导[/bold]")
    console.rule()
    _render_status(status)

    if not status["env_file_exists"]:
        if status["env_template_exists"]:
            console.print("\n📋 检测到 .env.template，可以复制生成新的 .env 文件。")
            if typer.confirm("是否立即创建 .env?", default=True):
                env_path = _copy_template(project_root, overwrite=overwrite) or (
                    project_root / ".env"
                )
                console.print(f"✅ 已创建 .env: [green]{env_path}[/green]")
                if open_editor:
                    _open_env_file(env_path)
            else:
                console.print("💡 可以稍后手动复制 .env.template → .env")
        else:
            console.print("❌ 未找到 .env 或 .env.template，请手动创建并填写 API Keys。")
    elif open_editor and typer.confirm("是否编辑现有的 .env 文件?", default=False):
        _open_env_file(Path(status["env_file"]))  # type: ignore[arg-type]

    console.print("\n🔍 当前环境变量状态:")
    status = env_utils.check_environment_status()
    _render_status(status)

    return status


@app.command()
def load(
    env_file: Path | None = typer.Option(None, "--env-file", "-f", help="显式指定 .env 文件位置"),
    override: bool = typer.Option(False, "--override", help="覆盖已存在的环境变量"),
):
    """加载 .env 文件并将变量导入当前环境。"""

    try:
        loaded, path = env_utils.load_environment_file(env_file, override=override)
    except RuntimeError as exc:
        console.print(f"⚠️ {exc}")
        raise typer.Exit(1) from exc

    if not loaded:
        resolved = path or env_file or (env_utils.find_project_root() / ".env")
        console.print(f"ℹ️ 未找到 .env 文件: [cyan]{resolved}[/cyan]")
        raise typer.Exit(1)

    console.print(f"✅ 已加载环境变量: [green]{path}[/green]")


@app.command()
def check():
    """检查当前环境变量配置。"""

    status = env_utils.check_environment_status()
    _render_status(status)


@app.command()
def setup(
    overwrite: bool = typer.Option(False, "--overwrite", help="如果已经存在 .env ，重新覆盖"),
    no_open: bool = typer.Option(False, "--no-open", help="创建/检测完成后不自动打开编辑器"),
):
    """运行交互式环境配置向导。"""

    run_setup_interactive(open_editor=not no_open, overwrite=overwrite)


__all__ = ["app", "run_setup_interactive"]
