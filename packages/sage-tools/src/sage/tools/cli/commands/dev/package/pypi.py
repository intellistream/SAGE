"""
PyPI 发布命令

使用 bytecode_compiler 提供的 PyPI 发布功能。
"""

from pathlib import Path

import typer
from rich.console import Console

from sage.tools.dev.core.bytecode_compiler import BytecodeCompiler, compile_multiple_packages

console = Console()
app = typer.Typer(
    name="pypi",
    help="🚀 PyPI 发布管理",
    no_args_is_help=True,
)


@app.command(name="build")
def build_package(
    package: str = typer.Argument(
        ...,
        help="包名 (如 sage-common, sage-kernel)",
    ),
    upload: bool = typer.Option(
        False,
        "--upload",
        "-u",
        help="构建后上传到 PyPI",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--no-dry-run",
        help="预演模式（不实际上传）",
    ),
):
    """
    📦 构建 wheel 包

    构建指定包的 wheel 文件，可选上传到 PyPI。

    示例：
        sage-dev package pypi build sage-common              # 构建但不上传
        sage-dev package pypi build sage-common -u --no-dry-run  # 构建并上传
    """
    console.print(f"\n[bold blue]📦 构建包: {package}[/bold blue]\n")

    # 查找包路径
    project_root = Path.cwd()
    packages_dir = project_root / "packages"
    package_path = packages_dir / package

    if not package_path.exists():
        console.print(f"[red]错误: 包不存在: {package_path}[/red]")
        raise typer.Exit(1)

    if not (package_path / "pyproject.toml").exists():
        console.print(f"[red]错误: 包缺少 pyproject.toml: {package}[/red]")
        raise typer.Exit(1)

    try:
        # 使用 BytecodeCompiler 构建
        compiler = BytecodeCompiler(package_path)

        # 编译包
        console.print("[cyan]→ 编译包...[/cyan]")
        compiler.compile_package()

        # 构建 wheel
        console.print("[cyan]→ 构建 wheel...[/cyan]")
        wheel_path = compiler.build_wheel(upload=upload, dry_run=dry_run)

        console.print(f"\n[bold green]✓ 构建成功: {wheel_path}[/bold green]")

        if upload:
            if dry_run:
                console.print("[yellow]ℹ️  预演模式，未实际上传[/yellow]")
            else:
                console.print("[green]✓ 已上传到 PyPI[/green]")

    except Exception as e:
        console.print(f"\n[red]✗ 构建失败: {e}[/red]")
        raise typer.Exit(1)


@app.command(name="upload")
def upload_package(
    package: str = typer.Argument(
        ...,
        help="包名 (如 sage-common, sage-kernel)",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--no-dry-run",
        help="预演模式（不实际上传）",
    ),
):
    """
    🚀 上传包到 PyPI

    上传已构建的 wheel 文件到 PyPI。

    示例：
        sage-dev package pypi upload sage-common              # 预演模式
        sage-dev package pypi upload sage-common --no-dry-run # 实际上传
    """
    console.print(f"\n[bold blue]🚀 上传包: {package}[/bold blue]\n")

    # 查找包路径
    project_root = Path.cwd()
    packages_dir = project_root / "packages"
    package_path = packages_dir / package

    if not package_path.exists():
        console.print(f"[red]错误: 包不存在: {package_path}[/red]")
        raise typer.Exit(1)

    dist_dir = package_path / "dist"
    if not dist_dir.exists() or not list(dist_dir.glob("*.whl")):
        console.print(f"[red]错误: 未找到 wheel 文件，请先构建: sage-dev package pypi build {package}[/red]")
        raise typer.Exit(1)

    try:
        compiler = BytecodeCompiler(package_path)

        if dry_run:
            console.print("[yellow]ℹ️  预演模式，显示将要上传的文件:[/yellow]")
            for wheel in dist_dir.glob("*.whl"):
                console.print(f"  📦 {wheel.name}")
        else:
            console.print("[cyan]→ 上传到 PyPI...[/cyan]")
            success = compiler._upload_to_pypi()

            if success:
                console.print("\n[bold green]✓ 上传成功[/bold green]")
            else:
                console.print("\n[red]✗ 上传失败[/red]")
                raise typer.Exit(1)

    except Exception as e:
        console.print(f"\n[red]✗ 上传失败: {e}[/red]")
        raise typer.Exit(1)


@app.command(name="build-all")
def build_all_packages(
    upload: bool = typer.Option(
        False,
        "--upload",
        "-u",
        help="构建后上传到 PyPI",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--no-dry-run",
        help="预演模式（不实际上传）",
    ),
):
    """
    📦 构建所有包

    批量构建所有 SAGE 包。

    示例：
        sage-dev package pypi build-all                    # 构建所有包
        sage-dev package pypi build-all -u --no-dry-run   # 构建并上传所有包
    """
    console.print("\n[bold blue]📦 批量构建所有包[/bold blue]\n")

    project_root = Path.cwd()
    packages_dir = project_root / "packages"

    if not packages_dir.exists():
        console.print("[red]错误: 未找到 packages 目录[/red]")
        raise typer.Exit(1)

    # 获取所有包
    package_paths = [
        p for p in packages_dir.iterdir() if p.is_dir() and (p / "pyproject.toml").exists()
    ]

    console.print(f"[cyan]找到 {len(package_paths)} 个包[/cyan]\n")

    try:
        results = compile_multiple_packages(
            package_paths=package_paths,
            build_wheels=True,
            upload=upload,
            dry_run=dry_run,
        )

        # 显示结果
        console.print("\n[bold]构建结果:[/bold]")
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        for package_name, success in results.items():
            status = "[green]✓[/green]" if success else "[red]✗[/red]"
            console.print(f"  {status} {package_name}")

        console.print(f"\n[bold]总计: {success_count}/{total_count} 成功[/bold]")

        if success_count < total_count:
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"\n[red]✗ 批量构建失败: {e}[/red]")
        raise typer.Exit(1)


__all__ = ["app"]
