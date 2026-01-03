"""
包管理命令组

提供 PyPI 发布、版本管理、安装管理等功能。
"""

import typer
from rich.console import Console

app = typer.Typer(
    name="package",
    help="📦 包管理 - PyPI 发布、版本管理、安装",
    no_args_is_help=True,
)

console = Console()

# 仅保留 version 命令组；原 pypi 命令已移至独立仓库
try:
    from ..package_version import app as version_app

    app.add_typer(version_app, name="version")
except ImportError as e:
    console.print(f"[yellow]警告: 无法导入 version 命令: {e}[/yellow]")


@app.command(name="install")
def install_packages(
    mode: str = typer.Option(
        "dev",
        "--mode",
        "-m",
        help="安装模式: dev (开发模式), deps (只安装依赖)",
    ),
    packages: str = typer.Option(
        None,
        "--packages",
        "-p",
        help="指定包名，逗号分隔",
    ),
    editable: bool = typer.Option(
        True,
        "--editable/--no-editable",
        help="可编辑模式安装",
    ),
):
    """
    📥 安装包

    安装 SAGE 包及其依赖。

    示例：
        sage-dev package install                    # 开发模式安装所有包
        sage-dev package install -m deps            # 只安装依赖
        sage-dev package install -p sage-libs       # 安装特定包
    """
    import subprocess
    import sys
    from pathlib import Path

    project_root = Path.cwd()
    packages_dir = project_root / "packages"

    if not packages_dir.exists():
        console.print("[red]错误: 未找到 packages 目录[/red]")
        raise typer.Exit(1)

    # 确定要安装的包
    if packages:
        pkg_list = [p.strip() for p in packages.split(",")]
    else:
        # 获取所有包
        pkg_list = [
            p.name for p in packages_dir.iterdir() if p.is_dir() and (p / "pyproject.toml").exists()
        ]

    console.print(f"\n[bold blue]📥 安装模式: {mode}[/bold blue]")
    console.print(f"[cyan]包列表: {', '.join(pkg_list)}[/cyan]\n")

    for pkg_name in pkg_list:
        pkg_path = packages_dir / pkg_name

        if not pkg_path.exists():
            console.print(f"[yellow]跳过不存在的包: {pkg_name}[/yellow]")
            continue

        console.print(f"[cyan]→ 安装 {pkg_name}...[/cyan]")

        try:
            cmd = [sys.executable, "-m", "pip", "install"]

            if mode == "dev" and editable:
                cmd.append("-e")

            cmd.append(str(pkg_path))

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                console.print(f"[green]✓ {pkg_name} 安装成功[/green]")
            else:
                console.print(f"[red]✗ {pkg_name} 安装失败[/red]")
                console.print(result.stderr)

        except Exception as e:
            console.print(f"[red]✗ {pkg_name} 安装出错: {e}[/red]")

    console.print("\n[bold green]✓ 安装完成[/bold green]")


__all__ = ["app"]
