"""
Analyze command implementation.
"""

import typer
from .common import console, get_toolkit, handle_command_error, VERBOSE_OPTION, PROJECT_ROOT_OPTION


app = typer.Typer(name="analyze", help="Analyze project dependencies and structure")


@app.command()
def dependencies(
    analysis_type: str = typer.Option("all", help="Analysis type: all, circular, missing, conflicts"),
    output_format: str = typer.Option("summary", help="Output format: summary, json, markdown"),
    project_root: str = PROJECT_ROOT_OPTION,
    verbose: bool = VERBOSE_OPTION
):
    """Analyze project dependencies"""
    try:
        toolkit = get_toolkit(project_root=project_root)
        
        if verbose:
            console.print("🔍 Analyzing dependencies...", style="blue")
        
        result = toolkit.analyze_dependencies(
            analysis_type=analysis_type,
            output_format=output_format
        )
        
        console.print("✅ Dependency analysis completed", style="green")
        
        if output_format == "summary":
            console.print(f"📊 Found {result.get('total_packages', 0)} packages")
            if result.get('issues'):
                console.print(f"⚠️  Found {len(result['issues'])} issues", style="yellow")
        
    except Exception as e:
        handle_command_error(e, "Dependency analysis", verbose)


@app.command()
def classes(
    package_name: str = typer.Argument(None, help="Package to analyze"),
    show_relationships: bool = typer.Option(True, help="Show class relationships"),
    output_format: str = typer.Option("tree", help="Output format: tree, graph, json"),
    project_root: str = PROJECT_ROOT_OPTION,
    verbose: bool = VERBOSE_OPTION
):
    """🏗️ Analyze class dependencies and relationships"""
    try:
        toolkit = get_toolkit(project_root=project_root)
        
        if verbose:
            console.print("🏗️ Analyzing class structure...", style="blue")
        
        result = toolkit.analyze_classes(
            package_name=package_name,
            show_relationships=show_relationships,
            output_format=output_format
        )
        
        console.print("✅ Class analysis completed", style="green")
        
    except Exception as e:
        handle_command_error(e, "Class analysis", verbose)
