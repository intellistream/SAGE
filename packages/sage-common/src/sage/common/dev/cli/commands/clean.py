"""
Clean command implementation.
"""

from typing import List

import typer

from .common import (PROJECT_ROOT_OPTION, VERBOSE_OPTION, console, get_toolkit,
                     handle_command_error)

app = typer.Typer(
    name="clean", help="🧹 Clean build artifacts and pip install intermediates"
)


@app.command()
def artifacts(
    categories: List[str] = typer.Option(
        ["all"], help="Categories to clean: all, pycache, build, dist, pip, vscode"
    ),
    dry_run: bool = typer.Option(
        True, "--dry-run", help="Preview what would be cleaned"
    ),
    recursive: bool = typer.Option(True, help="Clean recursively"),
    project_root: str = PROJECT_ROOT_OPTION,
    verbose: bool = VERBOSE_OPTION,
):
    """Clean build artifacts and temporary files"""
    try:
        toolkit = get_toolkit(project_root=project_root)

        if dry_run:
            console.print(
                "🔍 Preview mode - showing what would be cleaned", style="yellow"
            )
        else:
            console.print("🧹 Cleaning artifacts...", style="blue")

        result = toolkit.clean_artifacts(
            categories=categories, dry_run=dry_run, recursive=recursive, verbose=verbose
        )

        if dry_run:
            console.print(
                f"📋 Would clean {result.get('files_count', 0)} files", style="yellow"
            )
            console.print("💡 Use --no-dry-run to actually clean", style="blue")
        else:
            console.print(
                f"✅ Cleaned {result.get('files_count', 0)} files", style="green"
            )
            console.print(
                f"💾 Freed {result.get('space_freed', 0)} bytes", style="green"
            )

    except Exception as e:
        handle_command_error(e, "Clean", verbose)
