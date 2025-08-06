"""
Core commands for SAGE Development Toolkit.

Includes: test, analyze, status, version commands.
"""

from typing import Optional

import typer
from rich.table import Table
from rich.panel import Panel

from .common import (
    console, get_toolkit, handle_command_error,
    PROJECT_ROOT_OPTION, CONFIG_OPTION, ENVIRONMENT_OPTION, VERBOSE_OPTION
)

app = typer.Typer(name="core", help="Core SAGE development commands")


@app.command("test")
def test_command(
    mode: str = typer.Option("diff", help="Test execution mode: all, diff, package"),
    package: Optional[str] = typer.Option(None, help="Package name for package mode"),
    workers: Optional[int] = typer.Option(None, help="Number of parallel workers"),
    timeout: Optional[int] = typer.Option(None, help="Test timeout in seconds"),
    quick: bool = typer.Option(False, help="Run quick tests only"),
    project_root: Optional[str] = PROJECT_ROOT_OPTION,
    config: Optional[str] = CONFIG_OPTION,
    environment: Optional[str] = ENVIRONMENT_OPTION,
    verbose: bool = VERBOSE_OPTION
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
            
    except Exception as e:
        handle_command_error(e, "Test execution", verbose)


@app.command("analyze")
def analyze_command(
    analysis_type: str = typer.Option("summary", help="Analysis type: full, summary, circular"),
    project_root: Optional[str] = PROJECT_ROOT_OPTION,
    config: Optional[str] = CONFIG_OPTION,
    environment: Optional[str] = ENVIRONMENT_OPTION,
    verbose: bool = VERBOSE_OPTION
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
                for i, dep in enumerate(circular_deps[:5]):
                    console.print(f"  {i+1}. {dep}")
                if len(circular_deps) > 5:
                    console.print(f"  ... and {len(circular_deps) - 5} more")
            else:
                console.print("✅ No circular dependencies found", style="green")
        else:
            console.print("✅ Dependency analysis completed", style="green")
            console.print(f"⏱️ Analysis time: {results.get('execution_time', 0):.2f}s")
            
    except Exception as e:
        handle_command_error(e, "Dependency analysis", verbose)


@app.command("status")
def status_command(
    project_root: Optional[str] = PROJECT_ROOT_OPTION,
    config: Optional[str] = CONFIG_OPTION,
    environment: Optional[str] = ENVIRONMENT_OPTION
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
            
    except Exception as e:
        handle_command_error(e, "Status check", verbose=False)


@app.command("version")
def version_command():
    """Show version information."""
    console.print("🛠️ SAGE Development Toolkit", style="bold green")
    console.print("Version: 1.0.0")
    console.print("Author: IntelliStream Team")
    console.print("Repository: https://github.com/intellistream/SAGE")
