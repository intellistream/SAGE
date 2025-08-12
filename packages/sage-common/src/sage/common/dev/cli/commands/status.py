"""
Status command implementation.
"""

import typer
from .common import console, get_toolkit, handle_command_error, VERBOSE_OPTION, PROJECT_ROOT_OPTION


app = typer.Typer(name="status", help="Show toolkit status and configuration")


@app.command()
def show(
    detailed: bool = typer.Option(False, "--detailed", help="Show detailed status"),
    project_root: str = PROJECT_ROOT_OPTION,
    verbose: bool = VERBOSE_OPTION
):
    """Show toolkit status and configuration"""
    try:
        toolkit = get_toolkit(project_root=project_root)
        
        if verbose:
            console.print("📊 Gathering status information...", style="blue")
        
        status = toolkit.get_status(detailed=detailed)
        
        console.print("🛠️ SAGE Development Toolkit Status", style="bold blue")
        console.print(f"📂 Project Root: {status.get('project_root')}")
        console.print(f"🔧 Toolkit Version: {status.get('version', 'Unknown')}")
        console.print(f"🐍 Python Version: {status.get('python_version')}")
        
        if detailed:
            console.print("\n📋 Detailed Configuration:", style="bold")
            config = status.get('config', {})
            for key, value in config.items():
                console.print(f"  • {key}: {value}")
        
        console.print("✅ Status check completed", style="green")
        
    except Exception as e:
        handle_command_error(e, "Status check", verbose)
