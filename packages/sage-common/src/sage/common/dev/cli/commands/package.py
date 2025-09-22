"""
Package management commands.
"""

import typer
from typing import Optional
from .common import console, get_toolkit, handle_command_error, VERBOSE_OPTION, PROJECT_ROOT_OPTION


app = typer.Typer(name="package", help="SAGE package management commands")


@app.command("manage")
def manage_package(
    action: str = typer.Argument(help="Action: list, install, uninstall, status, build"),
    package_name: Optional[str] = typer.Argument(None, help="Package name"),
    dev: bool = typer.Option(False, help="Install in development mode"),
    force: bool = typer.Option(False, help="Force operation"),
    project_root: str = PROJECT_ROOT_OPTION,
    verbose: bool = VERBOSE_OPTION
):
    """Manage SAGE packages"""
    try:
        toolkit = get_toolkit(project_root=project_root)
        
        if verbose:
            console.print(f"📦 Package management: {action}", style="blue")
        
        result = toolkit.manage_packages(
            action=action,
            package_name=package_name,
            dev=dev,
            force=force
        )
        
        if action == 'list':
            packages = result.get('packages', [])
            from rich.table import Table
            
            table = Table(title=f"SAGE Packages ({len(packages)} found)")
            table.add_column("Package", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Version", style="yellow")
            
            for pkg in packages:
                status = "✅ Installed" if pkg.get('installed') else "❌ Not Installed"
                version = pkg.get('version', 'Unknown')
                table.add_row(pkg.get('name', 'Unknown'), status, version)
            
            console.print(table)
        else:
            console.print(f"✅ Package {action} completed successfully", style="green")
        
    except Exception as e:
        handle_command_error(e, "Package management", verbose)


@app.command("dependencies")
def dependencies(
    action: str = typer.Argument(help="Action: analyze, report, health"),
    output_format: str = typer.Option("json", help="Output format: json, markdown, summary"),
    project_root: str = PROJECT_ROOT_OPTION,
    verbose: bool = VERBOSE_OPTION
):
    """📊 Analyze package dependencies"""
    try:
        toolkit = get_toolkit(project_root=project_root)
        
        if verbose:
            console.print(f"📊 Dependency analysis: {action}", style="blue")
        
        result = toolkit.analyze_dependencies(action=action, output_format=output_format)
        
        if output_format == "summary":
            console.print("📊 Dependency Analysis Summary", style="bold blue")
            console.print(f"Total packages: {result.get('total_packages', 0)}")
            console.print(f"Issues found: {len(result.get('issues', []))}")
        else:
            console.print(result)
        
        console.print("✅ Dependency analysis completed", style="green")
        
    except Exception as e:
        handle_command_error(e, "Dependency analysis", verbose)


@app.command("fix-imports")
def fix_imports(
    package_name: Optional[str] = typer.Argument(None, help="Package to fix"),
    dry_run: bool = typer.Option(True, "--dry-run", help="Preview changes"),
    project_root: str = PROJECT_ROOT_OPTION,
    verbose: bool = VERBOSE_OPTION
):
    """Fix import paths in SAGE packages"""
    try:
        toolkit = get_toolkit(project_root=project_root)
        
        if verbose:
            console.print(f"🔧 Fixing imports for: {package_name or 'all packages'}", style="blue")
        
        result = toolkit.fix_imports(
            package_name=package_name,
            dry_run=dry_run,
            verbose=verbose
        )
        
        if dry_run:
            console.print(f"🔍 Would fix {result.get('changes_count', 0)} import issues", style="yellow")
            console.print("💡 Use --no-dry-run to apply changes", style="blue")
        else:
            console.print(f"✅ Fixed {result.get('changes_count', 0)} import issues", style="green")
        
    except Exception as e:
        handle_command_error(e, "Import fixing", verbose)
