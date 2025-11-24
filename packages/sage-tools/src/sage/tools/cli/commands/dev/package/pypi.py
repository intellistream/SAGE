"""
PyPI 发布命令

使用 bytecode_compiler 提供的 PyPI 发布功能。
"""

from pathlib import Path

import typer
from rich.console import Console

from sage.tools.dev.core.bytecode_compiler import (
    BytecodeCompiler,
    compile_multiple_packages,
)

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
        console.print(
            f"[red]错误: 未找到 wheel 文件，请先构建: sage-dev package pypi build {package}[/red]"
        )
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
    ordered: bool = typer.Option(
        True,
        "--ordered/--no-ordered",
        help="按依赖顺序构建和上传",
    ),
):
    """
    📦 构建所有包

    批量构建所有 SAGE 包。

    示例：
        sage-dev package pypi build-all                    # 构建所有包
        sage-dev package pypi build-all -u --no-dry-run   # 构建并上传所有包
        sage-dev package pypi build-all -u --no-dry-run --ordered  # 按依赖顺序上传
    """
    console.print("\n[bold blue]📦 批量构建所有包[/bold blue]\n")

    project_root = Path.cwd()
    packages_dir = project_root / "packages"

    if not packages_dir.exists():
        console.print("[red]错误: 未找到 packages 目录[/red]")
        raise typer.Exit(1)

    # 获取所有包
    all_packages = [
        p for p in packages_dir.iterdir() if p.is_dir() and (p / "pyproject.toml").exists()
    ]

    # 如果需要按依赖顺序构建
    if ordered:
        from sage.tools.dev.tools.enhanced_package_manager import EnhancedPackageManager

        pkg_manager = EnhancedPackageManager(str(project_root))
        install_order = pkg_manager._get_full_install_order()

        # 按依赖顺序重新排列包
        package_paths = []
        for pkg_name in install_order:
            pkg_path = packages_dir / pkg_name
            if pkg_path.exists() and (pkg_path / "pyproject.toml").exists():
                package_paths.append(pkg_path)

        console.print("[cyan]📋 按依赖顺序构建:[/cyan]")
        for i, pkg_name in enumerate(install_order, 1):
            console.print(f"  {i}. {pkg_name}")
        console.print()
    else:
        package_paths = all_packages

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


@app.command(name="publish-sage")
def publish_sage_meta_package(
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--no-dry-run",
        help="预演模式（不实际上传）",
    ),
    skip_deps: bool = typer.Option(
        False,
        "--skip-deps",
        help="跳过依赖包，仅构建和上传 sage 元包",
    ),
    repository: str = typer.Option(
        "pypi",
        "--repository",
        "-r",
        help="上传目标仓库 (pypi 或 testpypi)",
    ),
    skip_cpp_packages: bool = typer.Option(
        True,
        "--skip-cpp/--include-cpp",
        help="跳过包含 C++ 扩展的包（推荐），使用源码发布",
    ),
):
    """
    🚀 发布 SAGE 元包及其所有依赖

    按正确的依赖顺序构建并上传所有包到 PyPI 或 TestPyPI。
    这是发布完整 SAGE 的推荐方式。

    依赖顺序：
        1. sage-common (基础包，无依赖)
        2. sage-kernel (依赖 sage-common)
        3. sage-libs (依赖 sage-common)
        4. sage-middleware (依赖 sage-common, sage-kernel)
        5. sage-platform (依赖 sage-common, sage-kernel, sage-middleware)
        6. sage-cli (依赖核心包)
        7. sage-apps (依赖核心包)
        8. sage-benchmark (依赖核心包)
        9. sage-studio (依赖所有包)
        10. sage-tools (开发工具)
        11. sage (元包，依赖所有包)

    示例：
        # 预演模式（默认）
        sage-dev package pypi publish-sage

        # 上传到 TestPyPI（测试环境）
        sage-dev package pypi publish-sage --no-dry-run -r testpypi

        # 上传到 PyPI（正式环境）
        sage-dev package pypi publish-sage --no-dry-run -r pypi

        # 仅上传元包
        sage-dev package pypi publish-sage --no-dry-run --skip-deps
    """
    repo_name = "TestPyPI" if repository == "testpypi" else "PyPI"
    console.print(f"\n[bold blue]🚀 发布 SAGE 到 {repo_name}[/bold blue]\n")

    project_root = Path.cwd()
    packages_dir = project_root / "packages"

    if not packages_dir.exists():
        console.print("[red]错误: 未找到 packages 目录[/red]")
        raise typer.Exit(1)

    # 导入包管理器以获取依赖顺序
    from sage.tools.dev.tools.enhanced_package_manager import EnhancedPackageManager

    pkg_manager = EnhancedPackageManager(str(project_root))

    if skip_deps:
        # 仅发布 sage 元包
        package_order = ["sage"]
        console.print("[yellow]⚠️  跳过依赖包，仅发布 sage 元包[/yellow]\n")
    else:
        # 获取完整依赖顺序
        package_order = pkg_manager._get_full_install_order()
        console.print(f"[cyan]📋 将按依赖顺序处理 {len(package_order)} 个包[/cyan]\n")

    # 过滤出实际存在的包
    package_paths = []
    skipped_cpp_packages = []
    cpp_packages = ["sage-middleware"]  # 包含 C++ 扩展的包列表

    for pkg_name in package_order:
        pkg_path = packages_dir / pkg_name
        if pkg_path.exists() and (pkg_path / "pyproject.toml").exists():
            # 检查是否应该跳过 C++ 包
            if skip_cpp_packages and pkg_name in cpp_packages:
                skipped_cpp_packages.append(pkg_name)
                console.print(f"[yellow]⏭️  跳过 C++ 扩展包: {pkg_name} (使用源码发布)[/yellow]")
                continue
            package_paths.append(pkg_path)
        else:
            console.print(f"[yellow]⚠️  跳过不存在的包: {pkg_name}[/yellow]")

    if skipped_cpp_packages:
        console.print(
            f"\n[blue]ℹ️  跳过了 {len(skipped_cpp_packages)} 个 C++ 扩展包，这些包将使用源码发布[/blue]"
        )
        console.print(f"[dim]   跳过的包: {', '.join(skipped_cpp_packages)}[/dim]\n")

    console.print(f"\n[cyan]总计 {len(package_paths)} 个包需要处理[/cyan]\n")

    if dry_run:
        console.print("[yellow]🔍 预演模式：将显示构建过程，但不会实际上传[/yellow]\n")
    else:
        console.print(f"[bold red]⚠️  实际上传模式：将构建并上传到 {repo_name}！[/bold red]\n")

        # 确认提示
        import time

        console.print("[bold]5秒后开始上传，按 Ctrl+C 可取消...[/bold]")
        try:
            for i in range(5, 0, -1):
                console.print(f"  {i}...", style="dim")
                time.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]已取消[/yellow]")
            raise typer.Exit(0)

    console.print("\n" + "=" * 70)
    console.print("[bold]开始构建和上传流程[/bold]")
    console.print("=" * 70 + "\n")

    results = {}
    failed_packages = []

    for i, package_path in enumerate(package_paths, 1):
        package_name = package_path.name
        console.print(f"\n[bold cyan]📦 [{i}/{len(package_paths)}] {package_name}[/bold cyan]")
        console.print("-" * 70)

        try:
            # 创建编译器
            compiler = BytecodeCompiler(package_path)

            # 编译包
            console.print("[dim]→ 编译中...[/dim]")
            compiler.compile_package()

            # 构建 wheel
            console.print("[dim]→ 构建 wheel...[/dim]")
            wheel_path = compiler.build_wheel(upload=False, dry_run=True)

            # 上传到 PyPI
            if dry_run:
                console.print("[yellow]→ 预演模式：跳过上传[/yellow]")
                results[package_name] = True
            else:
                console.print(f"[dim]→ 上传到 {repo_name}...[/dim]")
                # 获取 dist 目录
                dist_dir = wheel_path.parent
                upload_success = compiler._upload_to_pypi(repository=repository, dist_dir=dist_dir)
                results[package_name] = upload_success

                if not upload_success:
                    failed_packages.append(package_name)
                    console.print("[bold red]❌ 失败[/bold red]")
                    # 询问是否继续
                    if i < len(package_paths):
                        console.print("\n[yellow]继续处理剩余包 (按 Ctrl+C 取消)...[/yellow]")
                        try:
                            time.sleep(2)
                        except KeyboardInterrupt:
                            console.print("\n[yellow]已取消剩余包的处理[/yellow]")
                            break
                else:
                    console.print("[bold green]✅ 成功[/bold green]")

        except KeyboardInterrupt:
            console.print(f"\n[yellow]已取消: {package_name}[/yellow]")
            break
        except Exception as e:
            console.print("[bold red]❌ 处理失败[/bold red]")
            console.print(f"[red]错误: {str(e)[:200]}[/red]")
            results[package_name] = False
            failed_packages.append(package_name)

    # 显示最终结果
    console.print("\n" + "=" * 70)
    console.print("[bold]📊 发布结果汇总[/bold]")
    console.print("=" * 70 + "\n")

    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)

    console.print("[bold]包处理状态:[/bold]")
    for pkg_name, success in results.items():
        status = "[green]✅[/green]" if success else "[red]❌[/red]"
        console.print(f"  {status} {pkg_name}")

    console.print(f"\n[bold]总计: {success_count}/{total_count} 成功[/bold]")

    if failed_packages:
        console.print(f"\n[bold red]失败的包 ({len(failed_packages)}):[/bold red]")
        for pkg in failed_packages:
            console.print(f"  • {pkg}")

    if dry_run:
        console.print("\n[yellow]ℹ️  这是预演模式。使用 --no-dry-run 进行实际上传。[/yellow]")

    if success_count == total_count:
        console.print("\n[bold green]🎉 所有包都已成功处理！[/bold green]")
    elif success_count > 0:
        console.print("\n[bold yellow]⚠️  部分包处理成功[/bold yellow]")
        raise typer.Exit(1)
    else:
        console.print("\n[bold red]❌ 所有包都处理失败[/bold red]")
        raise typer.Exit(1)


__all__ = ["app"]
