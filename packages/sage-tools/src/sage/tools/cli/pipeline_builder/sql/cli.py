"""SQL-based pipeline CLI commands for SAGE."""

from pathlib import Path
from typing import Optional

import typer
from rich import print
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from .store import SQLPipelineStore
from .parser import SQLPipelineDSLParser


app = typer.Typer(help="SQL-based pipeline definition and management")
console = Console()


@app.command("load")
def load_pipeline(
    sql_file: Path = typer.Argument(..., help="Path to SQL file containing pipeline definitions"),
    db_path: Optional[Path] = typer.Option(None, help="Path to SQLite database file"),
) -> None:
    """Load pipeline definitions from SQL file into database."""
    if not sql_file.exists():
        console.print(f"[red]Error: SQL file not found: {sql_file}[/red]")
        raise typer.Exit(1)
    
    try:
        # Read SQL content
        sql_content = sql_file.read_text(encoding='utf-8')
        
        # Parse SQL into pipeline definitions
        parser = SQLPipelineDSLParser()
        pipelines = parser.parse_statements(sql_content)
        
        if not pipelines:
            console.print("[yellow]Warning: No pipeline definitions found in SQL file[/yellow]")
            return
        
        # Store pipelines in database
        store = SQLPipelineStore(db_path=str(db_path) if db_path else None)
        
        for pipeline in pipelines:
            try:
                store.store_pipeline(pipeline)
                console.print(f"[green]✓[/green] Loaded pipeline: {pipeline.pipeline_id}")
            except Exception as e:
                console.print(f"[red]✗[/red] Failed to load pipeline {pipeline.pipeline_id}: {e}")
        
        console.print(f"\n[bold green]Successfully loaded {len(pipelines)} pipeline(s)[/bold green]")
        
    except Exception as e:
        console.print(f"[red]Error loading SQL file: {e}[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_pipelines(
    db_path: Optional[Path] = typer.Option(None, help="Path to SQLite database file"),
    json_format: bool = typer.Option(False, "--json", help="Output in JSON format"),
) -> None:
    """List all pipelines stored in database."""
    try:
        store = SQLPipelineStore(db_path=str(db_path) if db_path else None)
        pipelines = store.list_pipelines()
        
        if not pipelines:
            console.print("[yellow]No pipelines found in database[/yellow]")
            return
        
        if json_format:
            import json
            pipeline_data = [
                {
                    "pipeline_id": p.pipeline_id,
                    "name": p.name,
                    "description": p.description,
                    "mode": p.mode,
                    "operators": len(p.operators),
                    "edges": len(p.edges),
                }
                for p in pipelines
            ]
            print(json.dumps(pipeline_data, indent=2))
        else:
            table = Table(title="Available Pipelines")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="bright_white")
            table.add_column("Description", style="dim")
            table.add_column("Mode", style="green")
            table.add_column("Operators", justify="right", style="yellow")
            table.add_column("Edges", justify="right", style="yellow")
            
            for pipeline in pipelines:
                table.add_row(
                    pipeline.pipeline_id,
                    pipeline.name,
                    pipeline.description[:50] + "..." if len(pipeline.description) > 50 else pipeline.description,
                    pipeline.mode,
                    str(len(pipeline.operators)),
                    str(len(pipeline.edges)),
                )
            
            console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error listing pipelines: {e}[/red]")
        raise typer.Exit(1)


@app.command("show")
def show_pipeline(
    pipeline_id: str = typer.Argument(..., help="Pipeline ID to display"),
    db_path: Optional[Path] = typer.Option(None, help="Path to SQLite database file"),
    json_format: bool = typer.Option(False, "--json", help="Output in JSON format"),
) -> None:
    """Show detailed information about a specific pipeline."""
    try:
        store = SQLPipelineStore(db_path=str(db_path) if db_path else None)
        pipeline = store.load_pipeline(pipeline_id)
        
        if not pipeline:
            console.print(f"[red]Pipeline not found: {pipeline_id}[/red]")
            raise typer.Exit(1)
        
        if json_format:
            import json
            pipeline_data = {
                "pipeline_id": pipeline.pipeline_id,
                "name": pipeline.name,
                "description": pipeline.description,
                "mode": pipeline.mode,
                "operators": [
                    {
                        "operator_id": op.op_id,
                        "operator_type": op.op_type,
                        "position": op.position,
                        "config": op.config,
                    }
                    for op in pipeline.operators
                ],
                "edges": pipeline.edges,
            }
            print(json.dumps(pipeline_data, indent=2))
        else:
            console.print(f"\n[bold cyan]Pipeline: {pipeline.name}[/bold cyan]")
            console.print(f"ID: {pipeline.pipeline_id}")
            console.print(f"Description: {pipeline.description}")
            console.print(f"Mode: {pipeline.mode}")
            
            # Show operators
            console.print(f"\n[bold yellow]Operators ({len(pipeline.operators)}):[/bold yellow]")
            op_table = Table()
            op_table.add_column("Position", style="cyan")
            op_table.add_column("ID", style="bright_white")
            op_table.add_column("Type", style="green")
            op_table.add_column("Config", style="dim")
            
            for op in sorted(pipeline.operators, key=lambda x: x.position):
                config_str = str(op.config) if op.config else "{}"
                if len(config_str) > 40:
                    config_str = config_str[:37] + "..."
                op_table.add_row(
                    str(op.position),
                    op.op_id,
                    op.op_type,
                    config_str,
                )
            
            console.print(op_table)
            
            # Show edges
            if pipeline.edges:
                console.print(f"\n[bold yellow]Connections ({len(pipeline.edges)}):[/bold yellow]")
                for from_op, to_op in pipeline.edges:
                    console.print(f"  {from_op} → {to_op}")
    
    except Exception as e:
        console.print(f"[red]Error showing pipeline: {e}[/red]")
        raise typer.Exit(1)


@app.command("compile")
def compile_pipeline(
    pipeline_id: str = typer.Argument(..., help="Pipeline ID to compile"),
    output_dir: Path = typer.Option(Path("./output"), help="Output directory for generated files"),
    db_path: Optional[Path] = typer.Option(None, help="Path to SQLite database file"),
    format_type: str = typer.Option("both", "--format", help="Output format: yaml, python, or both"),
) -> None:
    """Compile pipeline definition to YAML config and Python runner."""
    if format_type not in ["yaml", "python", "both"]:
        console.print(f"[red]Error: Invalid format '{format_type}'. Use yaml, python, or both[/red]")
        raise typer.Exit(1)
    
    try:
        store = SQLPipelineStore(db_path=str(db_path) if db_path else None)
        pipeline = store.load_pipeline(pipeline_id)
        
        if not pipeline:
            console.print(f"[red]Pipeline not found: {pipeline_id}[/red]")
            raise typer.Exit(1)
        
        # Compile pipeline
        from .store import SQLPipelineCompiler
        compiler = SQLPipelineCompiler()
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        generated_files = []
        
        if format_type in ["yaml", "both"]:
            # Generate YAML config
            yaml_config = compiler.compile_to_yaml(pipeline)
            yaml_file = output_dir / f"{pipeline_id}.yaml"
            yaml_file.write_text(yaml_config, encoding='utf-8')
            generated_files.append(yaml_file)
            
            console.print(f"[green]✓[/green] Generated YAML config: {yaml_file}")
        
        if format_type in ["python", "both"]:
            # Generate Python runner
            python_code = compiler.compile_to_python(pipeline)
            python_file = output_dir / f"{pipeline_id}_runner.py"
            python_file.write_text(python_code, encoding='utf-8')
            generated_files.append(python_file)
            
            console.print(f"[green]✓[/green] Generated Python runner: {python_file}")
        
        console.print(f"\n[bold green]Successfully compiled pipeline: {pipeline_id}[/bold green]")
        
        # Show preview of generated files
        console.print("\n[bold yellow]File previews:[/bold yellow]")
        for file_path in generated_files:
            console.print(f"\n[cyan]{file_path.name}:[/cyan]")
            content = file_path.read_text(encoding='utf-8')
            
            # Determine syntax highlighting
            if file_path.suffix == '.yaml':
                syntax = Syntax(content[:500], "yaml", theme="monokai", line_numbers=True)
            elif file_path.suffix == '.py':
                syntax = Syntax(content[:500], "python", theme="monokai", line_numbers=True)
            else:
                syntax = Syntax(content[:500], "text", theme="monokai", line_numbers=True)
            
            console.print(syntax)
            if len(content) > 500:
                console.print("[dim]... (truncated)[/dim]")
    
    except Exception as e:
        console.print(f"[red]Error compiling pipeline: {e}[/red]")
        raise typer.Exit(1)


@app.command("delete")
def delete_pipeline(
    pipeline_id: str = typer.Argument(..., help="Pipeline ID to delete"),
    db_path: Optional[Path] = typer.Option(None, help="Path to SQLite database file"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
) -> None:
    """Delete a pipeline from the database."""
    try:
        store = SQLPipelineStore(db_path=str(db_path) if db_path else None)
        
        # Check if pipeline exists
        pipeline = store.load_pipeline(pipeline_id)
        if not pipeline:
            console.print(f"[red]Pipeline not found: {pipeline_id}[/red]")
            raise typer.Exit(1)
        
        # Confirm deletion
        if not force:
            console.print(f"Pipeline: [cyan]{pipeline.name}[/cyan] ({pipeline_id})")
            console.print(f"Description: {pipeline.description}")
            console.print(f"Operators: {len(pipeline.operators)}")
            
            confirm = typer.confirm("\nAre you sure you want to delete this pipeline?")
            if not confirm:
                console.print("Deletion cancelled.")
                return
        
        # Delete pipeline
        store.delete_pipeline(pipeline_id)
        console.print(f"[green]✓[/green] Deleted pipeline: {pipeline_id}")
    
    except Exception as e:
        console.print(f"[red]Error deleting pipeline: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()


__all__ = ["app"]