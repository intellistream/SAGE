"""
Commercial package management commands for SAGE Development Toolkit.

Includes: commercial command.
"""

from typing import Optional

import typer
from rich.table import Table

from .common import (
    console, get_toolkit, handle_command_error,
    PROJECT_ROOT_OPTION
)

app = typer.Typer(name="commercial", help="Commercial SAGE package management")


@app.command("manage-commercial")
def commercial_command(
    action: str = typer.Argument(help="Action: list, install, build, status"),
    package: Optional[str] = typer.Option(None, help="Package name for install/build actions"),
    dev_mode: bool = typer.Option(True, help="Install in development mode"),
    project_root: Optional[str] = PROJECT_ROOT_OPTION
):
    """🏢 Manage commercial SAGE packages."""
    try:
        from ...tools.commercial_package_manager import CommercialPackageManager
        
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
                    console.print(f"❌ Failed to build {package}: {result.get('stderr', 'Unknown error')}", style="red")
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
        handle_command_error(e, "Commercial package management", verbose=False)
