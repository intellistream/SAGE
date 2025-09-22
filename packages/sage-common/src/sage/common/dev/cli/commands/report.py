"""
Report command implementation.
"""

import typer
from .common import console, get_toolkit, handle_command_error, VERBOSE_OPTION, PROJECT_ROOT_OPTION


app = typer.Typer(name="report", help="Generate comprehensive development report")


@app.command()
def generate(
    output_format: str = typer.Option("markdown", help="Output format: markdown, json, html"),
    output_file: str = typer.Option(None, help="Output file path"),
    include_tests: bool = typer.Option(True, help="Include test results"),
    include_dependencies: bool = typer.Option(True, help="Include dependency analysis"),
    include_coverage: bool = typer.Option(False, help="Include code coverage"),
    project_root: str = PROJECT_ROOT_OPTION,
    verbose: bool = VERBOSE_OPTION
):
    """Generate comprehensive development report"""
    try:
        toolkit = get_toolkit(project_root=project_root)
        
        if verbose:
            console.print("📊 Generating comprehensive report...", style="blue")
        
        report = toolkit.generate_report(
            output_format=output_format,
            include_tests=include_tests,
            include_dependencies=include_dependencies,
            include_coverage=include_coverage,
            verbose=verbose
        )
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            console.print(f"📄 Report saved to: {output_file}", style="green")
        else:
            console.print(report)
        
        console.print("✅ Report generation completed", style="green")
        
    except Exception as e:
        handle_command_error(e, "Report generation", verbose)
