"""
Version command implementation.
"""

import typer
from .common import console


app = typer.Typer(name="version", help="Show version information")


@app.command()
def show():
    """Show version information"""
    try:
        from ...core.toolkit import SAGEDevToolkit
        
        version_info = SAGEDevToolkit.get_version_info()
        
        console.print("📦 SAGE Development Toolkit", style="bold blue")
        console.print(f"Version: {version_info.get('version', 'Unknown')}")
        console.print(f"Build: {version_info.get('build', 'Unknown')}")
        console.print(f"Python: {version_info.get('python_version', 'Unknown')}")
        
    except Exception as e:
        console.print(f"❌ Failed to get version info: {e}", style="red")
        raise typer.Exit(1)
