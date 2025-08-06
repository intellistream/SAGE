"""
Package management commands for SAGE Development Toolkit.

Includes: package, compile, dependencies commands.
"""

import json
import tomli
from pathlib import Path
from typing import Optional, List

import typer
from rich.table import Table

from .common import (
    console, get_toolkit, handle_command_error, format_size,
    PROJECT_ROOT_OPTION, CONFIG_OPTION, ENVIRONMENT_OPTION, VERBOSE_OPTION
)
from ...core.bytecode_compiler import BytecodeCompiler, compile_multiple_packages

app = typer.Typer(name="package", help="Package management commands")


def _load_project_config(project_root: Path) -> dict:
    """加载项目配置文件"""
    config_path = project_root / "project_config.toml"
    if not config_path.exists():
        raise FileNotFoundError(f"项目配置文件不存在: {config_path}")
    
    with open(config_path, 'rb') as f:
        return tomli.load(f)


def _get_all_package_paths(project_root: Path) -> List[Path]:
    """从project_config.toml获取所有包的路径"""
    try:
        config = _load_project_config(project_root)
        packages = config.get('packages', {})
        
        package_paths = []
        for package_name, package_dir in packages.items():
            package_path = project_root / package_dir
            if package_path.exists() and package_path.is_dir():
                package_paths.append(package_path)
            else:
                console.print(f"⚠️  包路径不存在或不是目录: {package_path}", style="yellow")
        
        return package_paths
    except Exception as e:
        console.print(f"❌ 读取项目配置失败: {e}", style="red")
        return []


@app.command("manage-package")
def package_command(
    action: str = typer.Argument(help="Package action: list, install, uninstall, status, build"),
    package_name: Optional[str] = typer.Argument(None, help="Package name"),
    dev: bool = typer.Option(False, help="Install in development mode"),
    force: bool = typer.Option(False, help="Force operation"),
    project_root: Optional[str] = PROJECT_ROOT_OPTION,
    config: Optional[str] = CONFIG_OPTION,
    environment: Optional[str] = ENVIRONMENT_OPTION,
    verbose: bool = VERBOSE_OPTION
):
    """Manage SAGE packages."""
    
    valid_actions = ['list', 'install', 'uninstall', 'status', 'build']
    if action not in valid_actions:
        console.print(f"❌ Invalid action. Choose from: {', '.join(valid_actions)}", style="red")
        raise typer.Exit(1)
    
    try:
        toolkit = get_toolkit(project_root, config, environment)
        
        kwargs = {}
        if dev:
            kwargs['dev'] = dev
        if force:
            kwargs['force'] = force
            
        if verbose:
            console.print(f"📦 Package management: {action}")
            
        results = toolkit.manage_packages(action, package_name, **kwargs)
        
        # Display results based on action
        if action == 'list':
            packages = results.get('packages', [])
            
            table = Table(title=f"SAGE Packages ({len(packages)} found)")
            table.add_column("Package", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Version", style="yellow")
            
            for pkg in packages:
                status = "✅ Installed" if pkg.get('installed') else "❌ Not Installed"
                version = pkg.get('version', 'Unknown')
                table.add_row(pkg.get('name', 'Unknown'), status, version)
            
            console.print(table)
            
        elif action == 'status':
            console.print("📦 Package Status:", style="bold")
            for key, value in results.items():
                console.print(f"  • {key}: {value}")
        else:
            console.print(f"✅ Package {action} completed successfully", style="green")
            
    except Exception as e:
        handle_command_error(e, "Package management", verbose)


@app.command("compile")
def compile_command(
    package_path: Optional[str] = typer.Argument(None, help="Path to the package to compile (single package or comma-separated list)"),
    output_dir: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory for compiled packages (overrides --use-sage-home)"),
    build_wheel: bool = typer.Option(False, "--build", "-b", help="Build wheel package after compilation"),
    upload: bool = typer.Option(False, "--upload", "-u", help="Upload to PyPI after building"),
    dry_run: bool = typer.Option(True, "--dry-run", help="Dry run mode (default: true, use --no-dry-run to disable)"),
    force_cleanup: bool = typer.Option(False, "--force-cleanup", help="Force cleanup of temporary directories"),
    batch_mode: bool = typer.Option(False, "--batch", help="Batch mode for multiple packages"),
    use_sage_home: bool = typer.Option(True, "--use-sage-home", help="Use ~/.sage/dist as output directory (default: true)"),
    create_symlink: bool = typer.Option(True, "--create-symlink", help="Create symlink .sage -> ~/.sage in current directory (default: true)"),
    show_sage_info: bool = typer.Option(False, "--info", help="Show SAGE home directory information"),
    project_root: Optional[str] = PROJECT_ROOT_OPTION,
    verbose: bool = VERBOSE_OPTION
):
    """🔧 Compile Python packages to bytecode (.pyc files) to hide source code."""
    
    try:
        # 显示SAGE home信息（如果需要）
        if show_sage_info:
            from ...core.bytecode_compiler import _get_sage_home_info
            _get_sage_home_info()
            if not package_path or package_path.strip() == "":
                # 只显示信息，不执行其他操作
                return
        
        # 检查是否提供了package_path
        if not package_path or package_path.strip() == "":
            console.print("❌ 必须提供包路径参数", style="red")
            console.print("💡 使用 --info 可以只显示SAGE home信息", style="yellow")
            raise typer.Exit(1)
        
        # 解析包路径
        if "," in package_path:
            # 多个包路径
            package_paths = [Path(p.strip()) for p in package_path.split(",")]
            batch_mode = True
        else:
            # 单个包路径
            package_paths = [Path(package_path)]
        
        # 验证包路径
        valid_paths = []
        for path in package_paths:
            if not path.is_absolute():
                # 如果是相对路径，尝试相对于项目根目录或当前目录
                if project_root:
                    abs_path = Path(project_root) / path
                else:
                    abs_path = Path.cwd() / path
            else:
                abs_path = path
            
            if not abs_path.exists():
                console.print(f"❌ 包路径不存在: {abs_path}", style="red")
                continue
            
            if not abs_path.is_dir():
                console.print(f"❌ 路径不是目录: {abs_path}", style="red")
                continue
            
            valid_paths.append(abs_path)
        
        if not valid_paths:
            console.print("❌ 没有有效的包路径", style="red")
            raise typer.Exit(1)
        
        # 设置输出目录
        output_path = Path(output_dir) if output_dir else None
        
        # 如果指定了output_dir，则不使用sage_home
        if output_dir:
            use_sage_home = False
            console.print(f"📁 使用指定输出目录: {output_path}", style="blue")
        
        if len(valid_paths) == 1 and not batch_mode:
            # 单包模式
            package_path = valid_paths[0]
            console.print(f"🎯 编译单个包: {package_path.name}", style="bold cyan")
            
            # 创建软链接（如果需要）
            if use_sage_home and create_symlink:
                from ...core.bytecode_compiler import _create_sage_home_symlink
                _create_sage_home_symlink()
            
            try:
                compiler = BytecodeCompiler(package_path)
                compiled_path = compiler.compile_package(output_path, use_sage_home)
                
                if build_wheel:
                    wheel_path = compiler.build_wheel(compiled_path, upload, dry_run)
                    console.print(f"🎡 轮子构建完成: {wheel_path}")
                
                console.print(f"✅ 编译完成: {compiled_path}", style="green")
                
                if force_cleanup:
                    compiler.cleanup()
                
            except Exception as e:
                handle_command_error(e, "编译", verbose)
        
        else:
            # 批量模式
            console.print(f"🎯 批量编译 {len(valid_paths)} 个包", style="bold cyan")
            
            results = compile_multiple_packages(
                package_paths=valid_paths,
                output_dir=output_path,
                build_wheels=build_wheel,
                upload=upload,
                dry_run=dry_run,
                use_sage_home=use_sage_home,
                create_symlink=create_symlink
            )
            
            failed_packages = [name for name, success in results.items() if not success]
            if failed_packages:
                console.print(f"❌ 以下包编译失败: {', '.join(failed_packages)}", style="red")
                raise typer.Exit(1)
        
        # 显示使用提示
        if dry_run and (build_wheel or upload):
            console.print("\n💡 提示: 当前为预演模式，要实际执行请使用 --no-dry-run", style="yellow")
        
        if upload and not build_wheel:
            console.print("\n💡 提示: 要上传到PyPI需要同时使用 --build 和 --upload", style="yellow")
        
        if use_sage_home:
            sage_home = Path.home() / ".sage" / "dist"
            console.print(f"\n📂 编译产物保存在: {sage_home}", style="blue")
            
            symlink_path = Path.cwd() / ".sage"
            if symlink_path.exists() and symlink_path.is_symlink():
                console.print(f"🔗 可通过软链接访问: {symlink_path}", style="blue")
        
    except Exception as e:
        handle_command_error(e, "命令执行", verbose)


@app.command("dependencies")
def dependencies_command(
    action: str = typer.Argument(help="Action: analyze, report, health"),
    output_format: str = typer.Option("json", help="Output format: json, markdown, summary"),
    project_root: Optional[str] = PROJECT_ROOT_OPTION
):
    """📊 Analyze project dependencies."""
    try:
        from ...tools.dependency_analyzer import DependencyAnalyzer
        
        toolkit = get_toolkit(project_root=project_root)
        analyzer = DependencyAnalyzer(str(toolkit.config.project_root))
        
        if action == "analyze":
            with console.status("🔍 Analyzing dependencies..."):
                result = analyzer.analyze_all_dependencies()
            
            if output_format == "json":
                console.print(json.dumps(result, indent=2, default=str))
            else:
                # Show summary table
                table = Table(title="Dependency Analysis Summary")
                table.add_column("Package", style="cyan")
                table.add_column("Dependencies", style="white")
                table.add_column("Dev Dependencies", style="yellow")
                table.add_column("Optional Dependencies", style="green")
                
                for name, info in result['packages'].items():
                    deps = len(info.get('dependencies', []))
                    dev_deps = len(info.get('dev_dependencies', []))
                    opt_deps = len(info.get('optional_dependencies', []))
                    table.add_row(name, str(deps), str(dev_deps), str(opt_deps))
                
                console.print(table)
                console.print(f"\n📊 Total packages: {result['summary']['total_packages']}")
                console.print(f"📊 Unique dependencies: {result['summary']['total_unique_dependencies']}")
        
        elif action == "report":
            with console.status("📋 Generating dependency report..."):
                result = analyzer.generate_dependency_report(output_format)
            
            if output_format == "markdown":
                console.print(result)
            elif output_format == "summary":
                console.print("📊 Dependency Report Summary")
                console.print(f"Total packages: {result['total_packages']}")
                console.print(f"Total dependencies: {result['total_dependencies']}")
                console.print(f"Conflicts: {result['conflicts']}")
                console.print(f"Circular dependencies: {result['circular_dependencies']}")
            else:
                console.print(json.dumps(result, indent=2, default=str))
        
        elif action == "health":
            with console.status("🏥 Checking dependency health..."):
                result = analyzer.check_dependency_health()
            
            # Display health score
            score = result['health_score']
            grade = result['grade']
            
            if score >= 90:
                score_style = "green"
            elif score >= 70:
                score_style = "yellow"
            else:
                score_style = "red"
            
            console.print(f"🏥 Dependency Health Score: {score}/100 (Grade: {grade})", style=score_style)
            
            if result['issues']:
                console.print("\n⚠️ Issues Found:", style="yellow")
                for issue in result['issues']:
                    console.print(f"  • {issue}")
            
            if result['recommendations']:
                console.print("\n💡 Recommendations:", style="blue")
                for rec in result['recommendations']:
                    console.print(f"  • {rec}")
        
        else:
            console.print(f"❌ Unknown action: {action}", style="red")
            console.print("Available actions: analyze, report, health")
            raise typer.Exit(1)
            
    except Exception as e:
        handle_command_error(e, "Dependency analysis", verbose=False)
