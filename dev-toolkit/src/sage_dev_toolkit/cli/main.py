"""
Main CLI entry point for SAGE Development Toolkit.

This module provides the command-line interface using Typer framework
for intuitive and powerful command-line interactions.
"""

import sys
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..core.toolkit import SAGEDevToolkit
from ..core.exceptions import SAGEDevToolkitError

# 创建控制台对象用于富文本输出
console = Console()

# 全局变量存储toolkit实例
_toolkit: Optional[SAGEDevToolkit] = None

# 创建主应用
app = typer.Typer(
    name="sage-dev",
    help="🛠️ SAGE Development Toolkit - Unified development tools for SAGE project",
    no_args_is_help=True
)

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
            
            if phase_name == 'install' and 'installed_packages' in phase_data:
                details = f"{len(phase_data['installed_packages'])} packages"
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
    
    🛠️ Features:
    • Test execution with intelligent change detection
    • Comprehensive dependency analysis
    • Package management across SAGE ecosystem
    • Rich reporting with multiple output formats
    • Interactive and batch operation modes
    
    📖 Usage Examples:
    sage-dev test --mode diff           # Run tests on changed code
    sage-dev analyze --type circular    # Check for circular dependencies
    sage-dev package list               # List all SAGE packages
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

if __name__ == '__main__':
    main()
