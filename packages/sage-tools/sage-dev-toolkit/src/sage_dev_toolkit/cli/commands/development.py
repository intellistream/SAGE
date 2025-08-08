"""
Development tools commands for SAGE Development Toolkit.

Includes: classes, setup-test, list-tests commands.
"""

import json
from typing import Optional

import typer
from rich.table import Table

from .common import (
    console, get_toolkit, handle_command_error,
    PROJECT_ROOT_OPTION, CONFIG_OPTION, ENVIRONMENT_OPTION, VERBOSE_OPTION
)

app = typer.Typer(name="development", help="Development and analysis tools")


@app.command("classes")
def classes_command(
    action: str = typer.Argument(help="Action: analyze, usage, diagram"),
    target: Optional[str] = typer.Option(None, help="Target class name or path"),
    output_format: str = typer.Option("mermaid", help="Diagram format: mermaid, dot"),
    project_root: Optional[str] = PROJECT_ROOT_OPTION
):
    """🏗️ Analyze class dependencies and relationships."""
    try:
        from ...tools.class_dependency_checker import ClassDependencyChecker
        
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
                
                for class_name, class_info in list(result['classes'].items())[:10]:
                    methods = len(class_info.get('methods', []))
                    bases = ', '.join(class_info.get('bases', []))
                    module = class_info.get('module', 'Unknown')
                    table.add_row(class_name, module, str(methods), bases[:50])
                
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
                
                for usage in result['usages'][:20]:
                    table.add_row(
                        usage.get('type', 'Unknown'),
                        usage.get('file', 'Unknown'),
                        str(usage.get('line', 0)),
                        usage.get('context', '')[:50]
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
        handle_command_error(e, "Class analysis", verbose=False)


@app.command("setup-test")
def setup_test_command(
    workers: Optional[int] = typer.Option(None, help="Number of parallel workers"),
    quick_test: bool = typer.Option(False, help="Run quick tests only"),
    discover_only: bool = typer.Option(False, help="Only discover test structure"),
    test_only: bool = typer.Option(False, help="Skip setup, only run tests"),
    project_root: Optional[str] = PROJECT_ROOT_OPTION,
    config: Optional[str] = CONFIG_OPTION,
    environment: Optional[str] = ENVIRONMENT_OPTION,
    verbose: bool = VERBOSE_OPTION
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
        
    except Exception as e:
        handle_command_error(e, "Setup and test", verbose)


@app.command("list-tests")
def list_tests_command(
    project_root: Optional[str] = PROJECT_ROOT_OPTION,
    config: Optional[str] = CONFIG_OPTION,
    environment: Optional[str] = ENVIRONMENT_OPTION,
    verbose: bool = VERBOSE_OPTION
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
                    console.print(f"  📄 {test_file}")
            else:
                # Show first 5 test files
                for test_file in test_files[:5]:
                    console.print(f"  📄 {test_file}")
                if len(test_files) > 5:
                    console.print(f"  ... and {len(test_files) - 5} more")
        
    except Exception as e:
        handle_command_error(e, "Test listing", verbose)
