"""
Reporting commands for SAGE Development Toolkit.

Includes: report command.
"""

from typing import Optional

import typer
from rich.table import Table

from .common import (
    console, get_toolkit, handle_command_error,
    PROJECT_ROOT_OPTION, CONFIG_OPTION, ENVIRONMENT_OPTION, VERBOSE_OPTION
)

app = typer.Typer(name="reporting", help="Report generation commands")


@app.command("report")
def report_command(
    output_format: str = typer.Option("both", help="Output format: json, markdown, both"),
    project_root: Optional[str] = PROJECT_ROOT_OPTION,
    config: Optional[str] = CONFIG_OPTION,
    environment: Optional[str] = ENVIRONMENT_OPTION,
    verbose: bool = VERBOSE_OPTION
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
            
    except Exception as e:
        handle_command_error(e, "Report generation", verbose)
