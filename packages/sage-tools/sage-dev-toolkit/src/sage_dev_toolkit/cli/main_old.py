"""
Main CLI entry point for SAGE Development Toolkit.

This module provides the command-line interface using Typer framework
for intuitive and powerful command-line interactions.
"""

import sys
import typer
from .commands.common import console
from .commands import get_apps

# 创建主应用
app = typer.Typer(
    name="sage-dev",
    help="🛠️ SAGE Development Toolkit - Unified development tools for SAGE project",
    no_args_is_help=True
)

# 动态添加所有命令模块的命令
def _register_commands():
    """注册所有模块化命令"""
    apps = get_apps()
    
    # 直接从各个模块注册命令到主应用
    # Core commands
    core_app = apps['core']
    for command_name, command_func in core_app.registered_commands.items():
        app.registered_commands[command_name] = command_func
    
    # Package management commands  
    package_app = apps['package_mgmt']
    for command_name, command_func in package_app.registered_commands.items():
        app.registered_commands[command_name] = command_func
    
    # Maintenance commands
    maintenance_app = apps['maintenance']
    for command_name, command_func in maintenance_app.registered_commands.items():
        app.registered_commands[command_name] = command_func
        
    # Commercial commands
    commercial_app = apps['commercial']
    for command_name, command_func in commercial_app.registered_commands.items():
        app.registered_commands[command_name] = command_func
        
    # Development commands
    development_app = apps['development']
    for command_name, command_func in development_app.registered_commands.items():
        app.registered_commands[command_name] = command_func
        
    # Reporting commands
    reporting_app = apps['reporting']
    for command_name, command_func in reporting_app.registered_commands.items():
        app.registered_commands[command_name] = command_func
        
    # Home commands
    home_app = apps['home']
    for command_name, command_func in home_app.registered_commands.items():
        app.registered_commands[command_name] = command_func

# 注册所有命令
_register_commands()

def get_toolkit(
    project_root: Optional[str] = None,
    config_file: Optional[str] = None,
    environment: Optional[str] = None
) -> SAGEDevToolkit:
    """获取或创建toolkit实例"""
    global _toolkit
    
    if _toolkit is None:
        try:
            _toolkit = SAGEDevToolkit(
                project_root=project_root,
                config_file=config_file,
                environment=environment
            )
        except SAGEDevToolkitError as e:
            console.print(f"❌ Error initializing toolkit: {e}", style="red")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"❌ Unexpected error: {e}", style="red")
            raise typer.Exit(1)
    
    return _toolkit

@app.command("test")
def test_command(
    mode: str = typer.Option("diff", help="Test execution mode: all, diff, package"),
    package: Optional[str] = typer.Option(None, help="Package name for package mode"),
    workers: Optional[int] = typer.Option(None, help="Number of parallel workers"),
    timeout: Optional[int] = typer.Option(None, help="Test timeout in seconds"),
    quick: bool = typer.Option(False, help="Run quick tests only"),
    project_root: Optional[str] = typer.Option(None, help="Project root directory"),
    config: Optional[str] = typer.Option(None, help="Configuration file path"),
    environment: Optional[str] = typer.Option(None, help="Environment (development/production/ci)"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable verbose output")
):
    """Run tests with various modes and options."""
    
    if mode not in ["all", "diff", "package"]:
        console.print("❌ Invalid mode. Choose from: all, diff, package", style="red")
        raise typer.Exit(1)
    
    try:
        toolkit = get_toolkit(project_root, config, environment)
        
        kwargs = {}
        if package:
            kwargs['package'] = package
        if workers:
            kwargs['workers'] = workers
        if timeout:
            kwargs['timeout'] = timeout
        if quick:
            kwargs['quick'] = quick
            
        if verbose:
            console.print(f"🧪 Running tests in '{mode}' mode...")
            
        results = toolkit.run_tests(mode, **kwargs)
        
        # Display summary
        if 'summary' in results:
            summary = results['summary']
            
            table = Table(title="Test Results")
            table.add_column("Metric", style="cyan")
            table.add_column("Count", style="green")
            
            table.add_row("Total", str(summary.get('total', 0)))
            table.add_row("Passed", str(summary.get('passed', 0)))
            table.add_row("Failed", str(summary.get('failed', 0)))
            table.add_row("Duration", f"{results.get('execution_time', 0):.2f}s")
            
            console.print(table)
        else:
            console.print("✅ Tests completed successfully", style="green")
            
    except SAGEDevToolkitError as e:
        console.print(f"❌ Test execution failed: {e}", style="red")
        raise typer.Exit(1)

@app.command("analyze")
def analyze_command(
    analysis_type: str = typer.Option("summary", help="Analysis type: full, summary, circular"),
    project_root: Optional[str] = typer.Option(None, help="Project root directory"),
    config: Optional[str] = typer.Option(None, help="Configuration file path"),
    environment: Optional[str] = typer.Option(None, help="Environment (development/production/ci)"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable verbose output")
):
    """Analyze project dependencies."""
    
    if analysis_type not in ["full", "summary", "circular"]:
        console.print("❌ Invalid analysis type. Choose from: full, summary, circular", style="red")
        raise typer.Exit(1)
    
    try:
        toolkit = get_toolkit(project_root, config, environment)
        
        if verbose:
            console.print(f"🔍 Running dependency analysis: {analysis_type}")
            
        results = toolkit.analyze_dependencies(analysis_type)
        
        # Display summary
        if analysis_type == 'circular':
            circular_deps = results.get('circular_dependencies', [])
            if circular_deps:
                console.print("⚠️ Circular dependencies found:", style="yellow")
                for i, dep in enumerate(circular_deps[:5]):  # Show first 5
                    console.print(f"  {i+1}. {' -> '.join(dep)}")
                if len(circular_deps) > 5:
                    console.print(f"  ... and {len(circular_deps) - 5} more")
            else:
                console.print("✅ No circular dependencies found", style="green")
        else:
            console.print("✅ Dependency analysis completed", style="green")
            console.print(f"⏱️ Analysis time: {results.get('execution_time', 0):.2f}s")
            
    except SAGEDevToolkitError as e:
        console.print(f"❌ Dependency analysis failed: {e}", style="red")
        raise typer.Exit(1)

@app.command("package")
def package_command(
    action: str = typer.Argument(help="Package action: list, install, uninstall, status, build"),
    package_name: Optional[str] = typer.Argument(None, help="Package name"),
    dev: bool = typer.Option(False, help="Install in development mode"),
    force: bool = typer.Option(False, help="Force operation"),
    project_root: Optional[str] = typer.Option(None, help="Project root directory"),
    config: Optional[str] = typer.Option(None, help="Configuration file path"),
    environment: Optional[str] = typer.Option(None, help="Environment (development/production/ci)"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable verbose output")
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
            
    except SAGEDevToolkitError as e:
        console.print(f"❌ Package management failed: {e}", style="red")
        raise typer.Exit(1)

@app.command("report")
def report_command(
    output_format: str = typer.Option("both", help="Output format: json, markdown, both"),
    project_root: Optional[str] = typer.Option(None, help="Project root directory"),
    config: Optional[str] = typer.Option(None, help="Configuration file path"),
    environment: Optional[str] = typer.Option(None, help="Environment (development/production/ci)"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable verbose output")
):
    """Generate comprehensive development report."""
    
    if output_format not in ["json", "markdown", "both"]:
        console.print("❌ Invalid format. Choose from: json, markdown, both", style="red")
        raise typer.Exit(1)
    
    try:
        toolkit = get_toolkit(project_root, config, environment)
        
        if verbose:
            console.print("📊 Generating comprehensive report...")
            
        results = toolkit.generate_comprehensive_report()
        
        # Display summary
        sections = results.get('sections', {})
        
        table = Table(title="Report Summary")
        table.add_column("Section", style="cyan")
        table.add_column("Status", style="green")
        
        for section_name, section_data in sections.items():
            status = section_data.get('status', 'unknown')
            icon = "✅" if status == "success" else "❌" if status == "error" else "⚠️"
            section_title = section_name.replace('_', ' ').title()
            table.add_row(section_title, f"{icon} {status.title()}")
        
        console.print(table)
        
        execution_time = results.get('metadata', {}).get('execution_time', 0)
        console.print(f"⏱️ Report generation time: {execution_time:.2f}s", style="yellow")
            
    except SAGEDevToolkitError as e:
        console.print(f"❌ Report generation failed: {e}", style="red")
        raise typer.Exit(1)

@app.command("status")
def status_command(
    project_root: Optional[str] = typer.Option(None, help="Project root directory"),
    config: Optional[str] = typer.Option(None, help="Configuration file path"),
    environment: Optional[str] = typer.Option(None, help="Environment (development/production/ci)")
):
    """Show toolkit status and configuration."""
    
    try:
        toolkit = get_toolkit(project_root, config, environment)
        
        # Basic info panel
        info_text = f"""
📁 Project root: {toolkit.config.project_root}
🌍 Environment: {toolkit.config.environment}
📦 Packages dir: {toolkit.config.packages_dir}
📜 Scripts dir: {toolkit.config.scripts_dir}
📊 Output dir: {toolkit.config.output_dir}
        """
        
        console.print(Panel(info_text.strip(), title="🔧 SAGE Development Toolkit Status", expand=False))
        
        # Tools status
        status_info = toolkit.get_tool_status()
        loaded_tools = status_info['loaded_tools']
        available_tools = status_info['available_tools']
        
        table = Table(title=f"Tools Status ({len(loaded_tools)}/{len(available_tools)} loaded)")
        table.add_column("Tool", style="cyan")
        table.add_column("Status", style="green")
        
        for tool in available_tools:
            status = "✅ Loaded" if tool in loaded_tools else "❌ Not Loaded"
            table.add_row(tool, status)
        
        console.print(table)
        
        # Configuration validation
        errors = toolkit.validate_configuration()
        if errors:
            console.print("⚠️ Configuration Issues:", style="yellow")
            for error in errors:
                console.print(f"  • {error}", style="red")
        else:
            console.print("✅ Configuration is valid", style="green")
            
    except SAGEDevToolkitError as e:
        console.print(f"❌ Status check failed: {e}", style="red")
        raise typer.Exit(1)

@app.command("version")
def version_command():
    """Show version information."""
    console.print("🛠️ SAGE Development Toolkit", style="bold green")
    console.print("Version: 1.0.0")
    console.print("Author: IntelliStream Team")
    console.print("Repository: https://github.com/intellistream/SAGE")

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
    project_root: Optional[str] = typer.Option(None, help="Project root directory"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable verbose output")
):
    """🔧 Compile Python packages to bytecode (.pyc files) to hide source code."""
    
    try:
        # 显示SAGE home信息（如果需要）
        if show_sage_info:
            from ..core.bytecode_compiler import _get_sage_home_info
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
                from ..core.bytecode_compiler import _create_sage_home_symlink
                _create_sage_home_symlink()
            
            try:
                compiler = BytecodeCompiler(package_path)
                compiled_path = compiler.compile_package(output_path, use_sage_home)
                
                if build_wheel:
                    success = compiler.build_wheel(upload=upload, dry_run=dry_run)
                    if not success:
                        console.print("❌ Wheel构建失败", style="red")
                        raise typer.Exit(1)
                
                console.print(f"✅ 编译完成: {compiled_path}", style="green")
                
                if force_cleanup:
                    compiler.cleanup_temp_dir()
                
            except SAGEDevToolkitError as e:
                console.print(f"❌ 编译失败: {e}", style="red")
                raise typer.Exit(1)
        
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
        console.print(f"❌ 命令执行失败: {e}", style="red")
        if verbose:
            import traceback
            console.print(traceback.format_exc(), style="dim red")
        raise typer.Exit(1)

@app.command("fix-imports")
def fix_imports_command(
    dry_run: bool = typer.Option(False, help="Show what would be fixed without making changes"),
    project_root: Optional[str] = typer.Option(None, help="Project root directory"),
    config: Optional[str] = typer.Option(None, help="Configuration file path"),
    environment: Optional[str] = typer.Option(None, help="Environment (development/production/ci)"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable verbose output")
):
    """Fix import paths in SAGE packages."""
    try:
        toolkit = get_toolkit(project_root, config, environment)
        
        if verbose:
            console.print("🔧 Fixing import paths in SAGE packages...")
            
        results = toolkit.fix_import_paths(dry_run=dry_run)
        
        # Display results
        if dry_run:
            console.print("🔍 Dry run - showing what would be fixed:", style="yellow")
        else:
            console.print("✅ Import path fixing completed", style="green")
        
        console.print(f"📁 Files checked: {results.get('total_files_checked', 0)}")
        console.print(f"🔧 Fixes applied: {len(results.get('fixes_applied', []))}")
        console.print(f"❌ Fixes failed: {len(results.get('fixes_failed', []))}")
        
        if results.get('fixes_applied'):
            table = Table(title="Applied Fixes")
            table.add_column("File", style="cyan")
            table.add_column("Changes", style="green")
            
            for fix in results['fixes_applied'][:10]:  # Show first 10
                changes = len(fix.get('changes', []))
                table.add_row(fix['file'], str(changes))
            
            console.print(table)
            
            if len(results['fixes_applied']) > 10:
                console.print(f"... and {len(results['fixes_applied']) - 10} more files")
        
    except SAGEDevToolkitError as e:
        console.print(f"❌ Import fixing failed: {e}", style="red")
        raise typer.Exit(1)

@app.command("update-vscode")
def update_vscode_command(
    mode: str = typer.Option("enhanced", help="Update mode: basic (pyproject.toml only) or enhanced (all packages)"),
    project_root: Optional[str] = typer.Option(None, help="Project root directory"),
    config: Optional[str] = typer.Option(None, help="Configuration file path"),
    environment: Optional[str] = typer.Option(None, help="Environment (development/production/ci)"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable verbose output")
):
    """Update VS Code Python path configurations."""
    try:
        toolkit = get_toolkit(project_root, config, environment)
        
        if verbose:
            console.print(f"🔧 Updating VS Code paths in {mode} mode...")
            
        results = toolkit.update_vscode_paths(mode=mode)
        
        # Display results
        console.print("✅ VS Code paths updated successfully", style="green")
        console.print(f"📁 Settings file: {results.get('settings_file', 'Unknown')}")
        console.print(f"🔗 Paths added: {results.get('paths_added', 0)}")
        
        if verbose and results.get('paths'):
            table = Table(title="Added Paths")
            table.add_column("Path", style="cyan")
            
            for path in results['paths'][:15]:  # Show first 15
                table.add_row(path)
            
            console.print(table)
            
            if len(results['paths']) > 15:
                console.print(f"... and {len(results['paths']) - 15} more paths")
        
    except SAGEDevToolkitError as e:
        console.print(f"❌ VS Code update failed: {e}", style="red")
        raise typer.Exit(1)

@app.command("setup-test")
def setup_test_command(
    workers: Optional[int] = typer.Option(None, help="Number of parallel workers"),
    quick_test: bool = typer.Option(False, help="Run quick tests only"),
    discover_only: bool = typer.Option(False, help="Only discover test structure"),
    test_only: bool = typer.Option(False, help="Skip setup, only run tests"),
    project_root: Optional[str] = typer.Option(None, help="Project root directory"),
    config: Optional[str] = typer.Option(None, help="Configuration file path"),
    environment: Optional[str] = typer.Option(None, help="Environment (development/production/ci)"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable verbose output")
):
    """Run one-click setup and test cycle."""
    try:
        toolkit = get_toolkit(project_root, config, environment)
        
        console.print("🚀 Starting one-click setup and test cycle...", style="bold blue")
        
        kwargs = {}
        if workers:
            kwargs['workers'] = workers
        if quick_test:
            kwargs['quick_test'] = quick_test
        if discover_only:
            kwargs['discover_only'] = discover_only
        if test_only:
            kwargs['test_only'] = test_only
            
        results = toolkit.one_click_setup_and_test(**kwargs)
        
        # Display results
        if results['status'] == 'success':
            console.print("✅ Setup and test cycle completed successfully", style="green")
        else:
            console.print("❌ Setup and test cycle failed", style="red")
        
        console.print(f"⏱️ Total execution time: {results.get('total_execution_time', 0):.2f}s")
        
        # Show phase results
        phases = results.get('phases', {})
        
        table = Table(title="Phase Results")
        table.add_column("Phase", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="yellow")
        
        for phase_name, phase_data in phases.items():
            status = phase_data.get('status', 'unknown')
            icon = "✅" if status == 'success' else "❌"
            details = ""
            
            if phase_name == 'install' and 'installed_components' in phase_data:
                method = phase_data.get('method', 'unknown')
                details = f"{len(phase_data['installed_components'])} components ({method})"
            elif phase_name == 'test' and 'stdout' in phase_data:
                details = "Check logs for details"
            
            table.add_row(phase_name.title(), f"{icon} {status.title()}", details)
        
        console.print(table)
        
    except SAGEDevToolkitError as e:
        console.print(f"❌ Setup and test failed: {e}", style="red")
        raise typer.Exit(1)

@app.command("list-tests")
def list_tests_command(
    project_root: Optional[str] = typer.Option(None, help="Project root directory"),
    config: Optional[str] = typer.Option(None, help="Configuration file path"),
    environment: Optional[str] = typer.Option(None, help="Environment (development/production/ci)"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable verbose output")
):
    """List all available tests in the project."""
    try:
        toolkit = get_toolkit(project_root, config, environment)
        
        results = toolkit.list_available_tests()
        
        test_structure = results.get('test_structure', {})
        
        console.print(f"📋 Found {results.get('total_test_files', 0)} test files in {results.get('total_packages', 0)} packages", style="bold")
        
        for package_name, test_files in test_structure.items():
            console.print(f"\n📦 {package_name} ({len(test_files)} tests)", style="cyan")
            
            if verbose:
                for test_file in test_files:
                    console.print(f"  • {test_file}")
            else:
                # Show first 5 test files
                for test_file in test_files[:5]:
                    console.print(f"  • {test_file}")
                if len(test_files) > 5:
                    console.print(f"  ... and {len(test_files) - 5} more")
        
    except SAGEDevToolkitError as e:
        console.print(f"❌ Test listing failed: {e}", style="red")
        raise typer.Exit(1)

@app.callback()
def callback():
    """
    SAGE Development Toolkit - Unified development tools for SAGE project
    
    🛠️ Core Features:
    • Test execution with intelligent change detection
    • Comprehensive dependency analysis  
    • Package management across SAGE ecosystem
    • Bytecode compilation for source code protection
    • Build artifacts cleanup and management
    • Rich reporting with multiple output formats
    • Interactive and batch operation modes
    
    📖 Common Usage Examples:
    sage-dev test --mode diff           # Run tests on changed code
    sage-dev analyze --type circular    # Check for circular dependencies
    sage-dev package list               # List all SAGE packages
    sage-dev compile packages/sage-apps # Compile package to ~/.sage/dist with symlink
    sage-dev compile packages/sage-apps --no-create-symlink  # Compile without symlink
    sage-dev compile packages/sage-apps --output /tmp/build  # Compile to custom directory
    sage-dev compile packages/sage-apps --build --upload --no-dry-run  # Compile and upload
    sage-dev compile --info             # Show SAGE home directory information
    sage-dev clean --dry-run            # Preview build artifacts cleanup
    sage-dev clean --categories pycache # Clean Python cache files
    sage-dev report                     # Generate comprehensive report
    
    🔗 More info: https://github.com/intellistream/SAGE/tree/main/dev-toolkit
    """
    pass

def main():
    """Main entry point for the CLI."""
    app()

@app.command("commercial")
def commercial_command(
    action: str = typer.Argument(help="Action: list, install, build, status"),
    package: Optional[str] = typer.Option(None, help="Package name for install/build actions"),
    dev_mode: bool = typer.Option(True, help="Install in development mode"),
    project_root: Optional[str] = typer.Option(None, help="Project root directory")
):
    """🏢 Manage commercial SAGE packages."""
    try:
        from ..tools.commercial_package_manager import CommercialPackageManager
        
        toolkit = get_toolkit(project_root=project_root)
        manager = CommercialPackageManager(str(toolkit.config.project_root))
        
        if action == "list":
            with console.status("🔍 Listing commercial packages..."):
                result = manager.list_commercial_packages()
            
            table = Table(title="Commercial SAGE Packages")
            table.add_column("Package", style="cyan")
            table.add_column("Description", style="white")
            table.add_column("Status", style="green")
            table.add_column("Components", style="yellow")
            
            for pkg in result['packages']:
                status = "✅ Available" if pkg['exists'] else "❌ Missing"
                components = ", ".join(pkg['components'])
                table.add_row(pkg['name'], pkg['description'], status, components)
            
            console.print(table)
            console.print(f"\n📊 Total packages: {result['total_packages']}")
        
        elif action == "install":
            if not package:
                console.print("❌ Package name required for install action", style="red")
                raise typer.Exit(1)
            
            with console.status(f"📦 Installing {package}..."):
                result = manager.install_commercial_package(package, dev_mode)
            
            if result['status'] == 'success':
                console.print(f"✅ Successfully installed {package}", style="green")
            else:
                console.print(f"❌ Failed to install {package}: {result.get('stderr', 'Unknown error')}", style="red")
        
        elif action == "build":
            with console.status("🔨 Building commercial extensions..."):
                result = manager.build_commercial_extensions(package)
            
            if package:
                if result['status'] == 'success':
                    console.print(f"✅ Successfully built {package}", style="green")
                else:
                    console.print(f"❌ Failed to build {package}: {result.get('error', 'Unknown error')}", style="red")
            else:
                success_count = sum(1 for r in result['results'].values() if r['status'] == 'success')
                total_count = len(result['results'])
                console.print(f"✅ Built {success_count}/{total_count} packages successfully", style="green")
        
        elif action == "status":
            with console.status("📊 Checking commercial package status..."):
                result = manager.check_commercial_status()
            
            table = Table(title="Commercial Package Status")
            table.add_column("Package", style="cyan")
            table.add_column("Available", style="white")
            table.add_column("Installed", style="green")
            table.add_column("Components Built", style="yellow")
            
            for name, status in result['packages'].items():
                available = "✅" if status['exists'] else "❌"
                installed = "✅" if status['installed'] else "❌"
                built = "✅" if status['components_built'] else "❌"
                table.add_row(name, available, installed, built)
            
            console.print(table)
            console.print(f"\n📊 Summary: {result['summary']['available']}/{result['summary']['total']} available, "
                         f"{result['summary']['installed']}/{result['summary']['total']} installed")
        
        else:
            console.print(f"❌ Unknown action: {action}", style="red")
            console.print("Available actions: list, install, build, status")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"❌ Commercial package management failed: {e}", style="red")
        raise typer.Exit(1)

@app.command("dependencies")
def dependencies_command(
    action: str = typer.Argument(help="Action: analyze, report, health"),
    output_format: str = typer.Option("json", help="Output format: json, markdown, summary"),
    project_root: Optional[str] = typer.Option(None, help="Project root directory")
):
    """📊 Analyze project dependencies."""
    try:
        from ..tools.dependency_analyzer import DependencyAnalyzer
        
        toolkit = get_toolkit(project_root=project_root)
        analyzer = DependencyAnalyzer(str(toolkit.config.project_root))
        
        if action == "analyze":
            with console.status("🔍 Analyzing dependencies..."):
                result = analyzer.analyze_all_dependencies()
            
            if output_format == "json":
                import json
                console.print(json.dumps(result, indent=2, default=str))
            else:
                # Show summary table
                table = Table(title="Dependency Analysis Summary")
                table.add_column("Package", style="cyan")
                table.add_column("Dependencies", style="white")
                table.add_column("Dev Dependencies", style="yellow")
                table.add_column("Optional Dependencies", style="green")
                
                for name, info in result['packages'].items():
                    table.add_row(
                        name,
                        str(len(info['dependencies'])),
                        str(len(info['dev_dependencies'])),
                        str(len(info['optional_dependencies']))
                    )
                
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
                import json
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
        console.print(f"❌ Dependency analysis failed: {e}", style="red")
        raise typer.Exit(1)

@app.command("classes")
def classes_command(
    action: str = typer.Argument(help="Action: analyze, usage, diagram"),
    target: Optional[str] = typer.Option(None, help="Target class name or path"),
    output_format: str = typer.Option("mermaid", help="Diagram format: mermaid, dot"),
    project_root: Optional[str] = typer.Option(None, help="Project root directory")
):
    """🏗️ Analyze class dependencies and relationships."""
    try:
        from ..tools.class_dependency_checker import ClassDependencyChecker
        
        toolkit = get_toolkit(project_root=project_root)
        checker = ClassDependencyChecker(str(toolkit.config.project_root))
        
        if action == "analyze":
            target_paths = [target] if target else None
            
            with console.status("🔍 Analyzing class dependencies..."):
                result = checker.analyze_class_dependencies(target_paths)
            
            # Show summary
            console.print(f"📊 Analysis Results:")
            console.print(f"  • Total classes: {result['summary']['total_classes']}")
            console.print(f"  • Total files: {result['summary']['total_files']}")
            console.print(f"  • Inheritance chains: {len(result['summary']['inheritance_chains'])}")
            console.print(f"  • Circular imports: {len(result['summary']['circular_imports'])}")
            console.print(f"  • Unused classes: {len(result['summary']['unused_classes'])}")
            
            # Show top classes
            if result['classes']:
                table = Table(title="Classes Found")
                table.add_column("Class", style="cyan")
                table.add_column("Module", style="white")
                table.add_column("Methods", style="yellow")
                table.add_column("Bases", style="green")
                
                for class_name, class_info in list(result['classes'].items())[:10]:  # Show top 10
                    bases = ", ".join(class_info['bases']) if class_info['bases'] else "None"
                    table.add_row(
                        class_name.split('.')[-1],
                        class_info['module'],
                        str(len(class_info['methods'])),
                        bases
                    )
                
                console.print(table)
        
        elif action == "usage":
            if not target:
                console.print("❌ Class name required for usage analysis", style="red")
                raise typer.Exit(1)
            
            with console.status(f"🔍 Checking usage of class {target}..."):
                result = checker.check_class_usage(target)
            
            console.print(f"🔍 Usage Analysis for '{target}':")
            console.print(f"  • Total usages: {result['summary']['total_usages']}")
            console.print(f"  • Files with usage: {result['summary']['files_with_usage']}")
            
            if result['usages']:
                table = Table(title="Usage Details")
                table.add_column("Type", style="cyan")
                table.add_column("File", style="white")
                table.add_column("Line", style="yellow")
                table.add_column("Context", style="green")
                
                for usage in result['usages'][:20]:  # Show top 20
                    file_name = Path(usage['file']).name
                    table.add_row(
                        usage['type'],
                        file_name,
                        str(usage['line']),
                        usage['context']
                    )
                
                console.print(table)
        
        elif action == "diagram":
            with console.status(f"🎨 Generating class diagram in {output_format} format..."):
                result = checker.generate_class_diagram(output_format)
            
            console.print(f"🎨 Class Diagram ({output_format.upper()}):")
            console.print(result)
        
        else:
            console.print(f"❌ Unknown action: {action}", style="red")
            console.print("Available actions: analyze, usage, diagram")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"❌ Class analysis failed: {e}", style="red")
        raise typer.Exit(1)

@app.command("clean")
def clean_command(
    categories: Optional[str] = typer.Option(None, help="Categories to clean (comma-separated): egg_info,dist,build,pycache,coverage,pytest,mypy,temp,logs,all"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be cleaned without actually deleting"),
    force: bool = typer.Option(False, "--force", "-f", help="Force cleanup without confirmation"),
    older_than_days: Optional[int] = typer.Option(None, "--older-than-days", help="Only clean files older than specified days"),
    create_script: bool = typer.Option(False, "--create-script", help="Generate cleanup script"),
    update_gitignore: bool = typer.Option(False, "--update-gitignore", help="Update .gitignore with build artifact rules"),
    project_root: Optional[str] = typer.Option(None, help="Project root directory"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable verbose output")
):
    """🧹 Clean build artifacts and pip install intermediates."""
    try:
        from ..tools.build_artifacts_manager import BuildArtifactsManager
        
        toolkit = get_toolkit(project_root=project_root)
        manager = BuildArtifactsManager(str(toolkit.config.project_root))
        
        # 处理类别参数
        category_list = None
        if categories:
            if categories.lower() == "all":
                category_list = None  # None means all categories
            else:
                category_list = [cat.strip() for cat in categories.split(",")]
                # 验证类别
                valid_categories = set(manager.DEFAULT_PATTERNS.keys())
                invalid_categories = set(category_list) - valid_categories
                if invalid_categories:
                    console.print(f"❌ Invalid categories: {', '.join(invalid_categories)}", style="red")
                    console.print(f"Valid categories: {', '.join(valid_categories)}")
                    raise typer.Exit(1)
        
        # 更新gitignore
        if update_gitignore:
            with console.status("📝 Updating .gitignore..."):
                gitignore_result = manager.setup_gitignore_rules()
            
            console.print("📝 .gitignore Update Results:", style="cyan")
            console.print(f"  📄 File: {gitignore_result['gitignore_path']}")
            console.print(f"  ➕ Rules added: {gitignore_result['rules_added']}")
            if gitignore_result['new_rules']:
                console.print("  📋 New rules:", style="yellow")
                for rule in gitignore_result['new_rules'][:5]:
                    console.print(f"    • {rule}")
                if len(gitignore_result['new_rules']) > 5:
                    console.print(f"    ... and {len(gitignore_result['new_rules']) - 5} more")
        
        # 创建清理脚本
        if create_script:
            with console.status("📜 Creating cleanup script..."):
                script_path = manager.create_cleanup_script()
            
            console.print(f"📜 Cleanup script created: {script_path}", style="green")
            console.print("   Run with: bash scripts/cleanup_build_artifacts.sh")
            return
        
        # 扫描构建产物
        with console.status("🔍 Scanning build artifacts..."):
            artifacts = manager.scan_artifacts()
            summary = manager.get_artifacts_summary(artifacts)
        
        # 显示扫描结果
        console.print("🔍 Build Artifacts Scan Results:", style="cyan")
        
        # 创建汇总表格
        table = Table(title="Build Artifacts Summary")
        table.add_column("Category", style="cyan")
        table.add_column("Count", style="yellow")
        table.add_column("Size", style="green")
        table.add_column("Sample Paths", style="white")
        
        total_count = 0
        total_size = 0
        
        for category, info in summary.items():
            if info['count'] > 0:
                total_count += info['count']
                total_size += info['total_size']
                
                # 只有在详细模式或该类别将被清理时才显示路径样本
                sample_paths = ""
                if verbose or (category_list is None or category in (category_list or [])):
                    sample_paths = "\n".join(info['paths'][:3])
                    if len(info['paths']) > 3:
                        sample_paths += f"\n... +{len(info['paths']) - 3} more"
                
                table.add_row(
                    category.replace('_', ' ').title(),
                    str(info['count']),
                    info['size_formatted'],
                    sample_paths
                )
        
        console.print(table)
        console.print(f"\n📊 Total: {total_count} items ({manager._format_size(total_size)})")
        
        # 应用时间过滤提示
        if older_than_days:
            console.print(f"⏰ Filtering: Only items older than {older_than_days} days", style="yellow")
        
        # 如果没有找到任何构建产物
        if total_count == 0:
            console.print("✨ No build artifacts found to clean!", style="green")
            return
        
        # 执行清理
        if not dry_run:
            # 确认操作（除非强制模式）
            if not force:
                action_desc = f"clean {category_list if category_list else 'all'} categories"
                if older_than_days:
                    action_desc += f" (older than {older_than_days} days)"
                
                confirm = typer.confirm(f"🗑️ Proceed to {action_desc}?")
                if not confirm:
                    console.print("❌ Operation cancelled.", style="yellow")
                    return
        
        # 执行清理
        action_desc = "preview" if dry_run else "clean"
        with console.status(f"🧹 Starting {action_desc} operation..."):
            results = manager.clean_artifacts(
                categories=category_list,
                dry_run=dry_run,
                force=force,
                older_than_days=older_than_days
            )
        
        # 显示结果
        mode_text = "Preview" if dry_run else "Cleanup"
        console.print(f"🧹 {mode_text} Results:", style="green")
        
        if results['total_files_removed'] > 0 or results['total_dirs_removed'] > 0:
            console.print(f"  📄 Files: {results['total_files_removed']}")
            console.print(f"  📁 Directories: {results['total_dirs_removed']}")
            console.print(f"  💾 Space freed: {manager._format_size(results['total_size_freed'])}")
            
            if verbose and results['cleaned_categories']:
                detail_table = Table(title="Detailed Results")
                detail_table.add_column("Category", style="cyan")
                detail_table.add_column("Files", style="yellow")
                detail_table.add_column("Dirs", style="yellow") 
                detail_table.add_column("Size", style="green")
                
                for category, stats in results['cleaned_categories'].items():
                    detail_table.add_row(
                        category.replace('_', ' ').title(),
                        str(stats['files_removed']),
                        str(stats['dirs_removed']),
                        manager._format_size(stats['size_freed'])
                    )
                
                console.print(detail_table)
        
        # 显示错误
        if results['errors']:
            console.print(f"\n⚠️ Errors occurred:", style="yellow")
            for error in results['errors'][:5]:  # Show first 5 errors
                console.print(f"  ❌ {error}", style="red")
            if len(results['errors']) > 5:
                console.print(f"  ... and {len(results['errors']) - 5} more errors")
        
        # 提供额外建议
        if not dry_run and results['total_files_removed'] > 0:
            console.print("\n💡 Tips:", style="blue")
            console.print("  • Use --dry-run to preview before cleaning")
            console.print("  • Use --update-gitignore to prevent future artifacts")
            console.print("  • Use --create-script to generate automated cleanup")
        
    except Exception as e:
        console.print(f"❌ Build artifacts cleanup failed: {e}", style="red")
        raise typer.Exit(1)

@app.command("home")
def home_command(
    action: str = typer.Argument(help="Action: setup, status, clean, logs"),
    project_root: Optional[str] = typer.Option(None, help="Project root directory"),
    force: bool = typer.Option(False, "--force", "-f", help="Force operation without confirmation"),
    days: int = typer.Option(7, "--days", "-d", help="Clean logs older than specified days"),
    log_type: Optional[str] = typer.Option(None, "--type", "-t", help="Log type filter: test, jobmanager, toolkit, all")
):
    """🏠 Manage SAGE home directory (~/.sage/) and logs."""
    import os
    
    try:
        # 使用直接路径而不是get_toolkit避免循环导入
        if project_root:
            project_path = Path(project_root).resolve()
        else:
            # 从当前目录开始向上查找项目根目录
            current = Path.cwd()
            while current != current.parent:
                if (current / "pyproject.toml").exists() or (current / "setup.py").exists():
                    project_path = current
                    break
                current = current.parent
            else:
                project_path = Path.cwd()
        
        project_name = project_path.name
        
        # 实际的SAGE家目录在用户目录下
        real_sage_home = Path.home() / ".sage"
        # 项目中的软链接
        project_sage_link = project_path / ".sage"
        
        if action == "setup":
            with console.status("🏗️ Setting up SAGE home directory..."):
                # 1. 创建用户家目录下的.sage目录
                real_sage_home.mkdir(exist_ok=True)
                
                # 2. 创建子目录
                for subdir in ["logs", "reports", "coverage", "temp", "cache"]:
                    (real_sage_home / subdir).mkdir(exist_ok=True)
                
                # 3. 如果项目中已有.sage，先检查和处理
                if project_sage_link.exists():
                    if project_sage_link.is_symlink():
                        # 如果已经是软链接，检查是否指向正确位置
                        if project_sage_link.resolve() != real_sage_home:
                            project_sage_link.unlink()
                            project_sage_link.symlink_to(real_sage_home)
                    else:
                        # 如果是实际目录，需要备份并创建软链接
                        backup_path = project_path / f".sage_backup_{project_name}"
                        if backup_path.exists():
                            import shutil
                            shutil.rmtree(backup_path)
                        project_sage_link.rename(backup_path)
                        project_sage_link.symlink_to(real_sage_home)
                        console.print(f"⚠️ Moved existing .sage to {backup_path.name}", style="yellow")
                else:
                    # 4. 创建软链接
                    project_sage_link.symlink_to(real_sage_home)
                
                success = real_sage_home.exists() and project_sage_link.is_symlink()
            
            console.print("🏠 SAGE Home Directory Setup Complete!", style="green")
            console.print(f"📁 Real SAGE home: {real_sage_home}")
            console.print(f"🔗 Project symlink: {project_sage_link}")
            
            status_icon = "✅" if success else "❌"
            console.print(f"\n🔗 Setup result:")
            console.print(f"  {status_icon} ~/.sage/ -> Real home directory")
            console.print(f"  {status_icon} .sage/ -> Symlink to ~/.sage/")
        
        elif action == "status":
            with console.status("📊 Checking SAGE home status..."):
                pass
            
            console.print("📊 SAGE Home Status:", style="cyan")
            console.print(f"📁 Real SAGE home: {real_sage_home}")
            console.print(f"🔗 Project symlink: {project_sage_link}")
            
            # Check real directory status
            if real_sage_home.exists():
                if real_sage_home.is_dir():
                    console.print("✅ ~/.sage directory exists")
                    
                    # Check subdirectories
                    subdirs = ["logs", "reports", "coverage", "temp", "cache"]
                    missing_dirs = [d for d in subdirs if not (real_sage_home / d).exists()]
                    if missing_dirs:
                        console.print(f"⚠️ Missing subdirectories: {', '.join(missing_dirs)}")
                    else:
                        console.print("✅ All subdirectories present")
                else:
                    console.print("❌ ~/.sage exists but is not a directory")
            else:
                console.print("❌ ~/.sage directory does not exist")
            
            # Check symlink status
            if project_sage_link.exists():
                if project_sage_link.is_symlink():
                    target = project_sage_link.resolve()
                    if target == real_sage_home:
                        console.print("✅ Project .sage symlink is correct")
                    else:
                        console.print(f"⚠️ Project .sage points to wrong location: {target}")
                else:
                    console.print("⚠️ Project .sage exists but is not a symlink")
            else:
                console.print("❌ Project .sage symlink does not exist")
        
        elif action == "clean":
            _clean_logs(real_sage_home, force, days, log_type)
        
        elif action == "logs":
            _show_logs_info(real_sage_home)
        
        else:
            console.print(f"❌ Unknown action: {action}", style="red")
            console.print("Available actions: setup, status, clean, logs")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"❌ SAGE home management failed: {e}", style="red")
        raise typer.Exit(1)


def _clean_logs(sage_home: Path, force: bool, days: int, log_type: Optional[str] = None):
    """Clean logs from SAGE home directory."""
    import time
    import shutil
    from datetime import datetime, timedelta
    
    logs_dir = sage_home / "logs"
    if not logs_dir.exists():
        console.print("📁 No logs directory found.", style="yellow")
        return
    
    # Calculate cutoff time
    cutoff_time = time.time() - (days * 24 * 3600)
    cutoff_date = datetime.fromtimestamp(cutoff_time)
    
    console.print(f"🗂️ Scanning logs directory: {logs_dir}")
    console.print(f"📅 Cleaning logs older than {days} days (before {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')})")
    
    # Collect files to clean
    files_to_clean = []
    total_size = 0
    
    for item in logs_dir.rglob("*"):
        if item.is_file():
            # Check file age
            file_mtime = item.stat().st_mtime
            if file_mtime < cutoff_time:
                # Apply log type filter if specified
                if log_type and log_type != "all":
                    if log_type == "test" and not any(pattern in item.name for pattern in ["test_", "_test", "packages_"]):
                        continue
                    elif log_type == "jobmanager" and "jobmanager" not in str(item.parent):
                        continue
                    elif log_type == "toolkit" and "sage_dev_toolkit" not in item.name:
                        continue
                
                file_size = item.stat().st_size
                files_to_clean.append((item, file_size))
                total_size += file_size
    
    # Also collect empty directories
    dirs_to_clean = []
    for item in logs_dir.rglob("*"):
        if item.is_dir() and not any(item.iterdir()):  # Empty directory
            dir_mtime = item.stat().st_mtime
            if dir_mtime < cutoff_time:
                dirs_to_clean.append(item)
    
    if not files_to_clean and not dirs_to_clean:
        console.print("✨ No old log files to clean.", style="green")
        return
    
    # Format size
    def format_size(size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    # Show summary
    console.print(f"🧹 Found {len(files_to_clean)} old log files ({format_size(total_size)}) and {len(dirs_to_clean)} empty directories")
    
    # Show files to be cleaned if not too many
    if len(files_to_clean) <= 10:
        for file_path, size in files_to_clean:
            rel_path = file_path.relative_to(logs_dir)
            age_days = (time.time() - file_path.stat().st_mtime) / (24 * 3600)
            console.print(f"  📄 {rel_path} ({format_size(size)}, {age_days:.1f} days old)")
    else:
        console.print(f"  📄 {len(files_to_clean)} files total...")
    
    # Ask for confirmation unless force is specified
    if not force:
        confirm = typer.confirm(f"🗑️ Delete {len(files_to_clean)} files and {len(dirs_to_clean)} directories?")
        if not confirm:
            console.print("❌ Operation cancelled.", style="yellow")
            return
    
    # Clean files
    cleaned_files = 0
    cleaned_size = 0
    failed_files = []
    
    with console.status("🧹 Cleaning log files..."):
        for file_path, size in files_to_clean:
            try:
                file_path.unlink()
                cleaned_files += 1
                cleaned_size += size
            except Exception as e:
                failed_files.append((file_path, str(e)))
        
        # Clean empty directories
        for dir_path in dirs_to_clean:
            try:
                dir_path.rmdir()
            except Exception as e:
                failed_files.append((dir_path, str(e)))
    
    # Report results
    console.print(f"✅ Cleaned {cleaned_files} log files ({format_size(cleaned_size)})", style="green")
    
    if failed_files:
        console.print(f"⚠️ Failed to clean {len(failed_files)} items:", style="yellow")
        for path, error in failed_files[:5]:  # Show first 5 failures
            console.print(f"  ❌ {path.name}: {error}")
        if len(failed_files) > 5:
            console.print(f"  ... and {len(failed_files) - 5} more")


def _show_logs_info(sage_home: Path):
    """Show information about logs in SAGE home directory."""
    from datetime import datetime
    import time
    
    logs_dir = sage_home / "logs"
    if not logs_dir.exists():
        console.print("📁 No logs directory found.", style="yellow")
        return
    
    console.print("📊 SAGE Logs Information", style="cyan")
    console.print(f"📁 Logs directory: {logs_dir}")
    
    # Categorize log files
    categories = {
        'test': {'files': [], 'size': 0},
        'jobmanager': {'files': [], 'size': 0},
        'toolkit': {'files': [], 'size': 0},
        'other': {'files': [], 'size': 0}
    }
    
    total_files = 0
    total_size = 0
    oldest_file = None
    newest_file = None
    
    def format_size(size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    # Scan all files
    for item in logs_dir.rglob("*"):
        if item.is_file():
            file_size = item.stat().st_size
            file_mtime = item.stat().st_mtime
            
            total_files += 1
            total_size += file_size
            
            # Track oldest and newest
            if oldest_file is None or file_mtime < oldest_file[1]:
                oldest_file = (item, file_mtime)
            if newest_file is None or file_mtime > newest_file[1]:
                newest_file = (item, file_mtime)
            
            # Categorize
            if any(pattern in item.name for pattern in ["test_", "_test", "packages_"]):
                categories['test']['files'].append(item)
                categories['test']['size'] += file_size
            elif "jobmanager" in str(item.parent) or "jobmanager" in item.name:
                categories['jobmanager']['files'].append(item)
                categories['jobmanager']['size'] += file_size
            elif "sage_dev_toolkit" in item.name:
                categories['toolkit']['files'].append(item)
                categories['toolkit']['size'] += file_size
            else:
                categories['other']['files'].append(item)
                categories['other']['size'] += file_size
    
    # Show summary
    console.print(f"\n📈 Summary:")
    console.print(f"  📄 Total files: {total_files}")
    console.print(f"  💾 Total size: {format_size(total_size)}")
    
    if oldest_file and newest_file:
        oldest_date = datetime.fromtimestamp(oldest_file[1])
        newest_date = datetime.fromtimestamp(newest_file[1])
        age_days = (newest_file[1] - oldest_file[1]) / (24 * 3600)
        console.print(f"  📅 Date range: {oldest_date.strftime('%Y-%m-%d')} to {newest_date.strftime('%Y-%m-%d')} ({age_days:.1f} days)")
    
    # Show categories
    console.print(f"\n📊 By Category:")
    for category, data in categories.items():
        if data['files']:
            icon = {"test": "🧪", "jobmanager": "📋", "toolkit": "🔧", "other": "📄"}[category]
            console.print(f"  {icon} {category.title()}: {len(data['files'])} files ({format_size(data['size'])})")
    
    # Show recent files (last 5)
    recent_files = sorted(
        [item for item in logs_dir.rglob("*") if item.is_file()],
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )[:5]
    
    if recent_files:
        console.print(f"\n🕐 Recent files:")
        for item in recent_files:
            rel_path = item.relative_to(logs_dir)
            file_time = datetime.fromtimestamp(item.stat().st_mtime)
            file_size = format_size(item.stat().st_size)
            console.print(f"  📄 {rel_path} ({file_size}, {file_time.strftime('%Y-%m-%d %H:%M')})")


if __name__ == '__main__':
    def main():
        """Main entry point for the CLI."""
        try:
            app()
        except KeyboardInterrupt:
            console.print("\n👋 Goodbye!", style="yellow")
            sys.exit(0)
        except Exception as e:
            console.print(f"❌ Unexpected error: {e}", style="red")
            sys.exit(1)
    
    main()