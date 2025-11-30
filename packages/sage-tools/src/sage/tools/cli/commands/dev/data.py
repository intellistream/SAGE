"""
SAGE Data Management CLI Commands

Commands for managing and exploring SAGE datasets.
"""

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="data",
    help="Manage SAGE datasets",
    no_args_is_help=True,
)

console = Console()


@app.command("list")
def list_datasets(
    show_metadata: bool = typer.Option(
        False, "--metadata", "-m", help="Show metadata for each dataset"
    ),
    usage: str = typer.Option(None, "--usage", "-u", help="Filter by usage profile"),
):
    """
    List all available datasets.

    Examples:
        sage-dev data list
        sage-dev data list --metadata
        sage-dev data list --usage rag
    """
    try:
        from sage.data import DataManager

        manager = DataManager.get_instance()

        if usage:
            # List datasets for a specific usage
            try:
                profile = manager.get_by_usage(usage)
                console.print(f"\n[bold cyan]📦 Datasets in usage '{usage}':[/bold cyan]")
                console.print(f"Description: {profile.description}\n")

                datasets = profile.list_datasets()
                if not datasets:
                    console.print("[yellow]No datasets found[/yellow]")
                    return

                for ds_name in datasets:
                    console.print(f"  • {ds_name}")

            except ValueError as e:
                console.print(f"[red]Error: {e}[/red]")
                console.print(f"\nAvailable usages: {', '.join(manager.list_usages())}")
                raise typer.Exit(1)
        else:
            # List all sources
            sources = manager.list_sources()

            if not sources:
                console.print("[yellow]No datasets found[/yellow]")
                return

            console.print(f"\n[bold cyan]📦 Available Datasets ({len(sources)}):[/bold cyan]\n")

            if show_metadata:
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Name", style="cyan", width=15)
                table.add_column("Type", style="green", width=10)
                table.add_column("Size", style="yellow", width=10)
                table.add_column("Description", width=50)

                for source in sources:
                    metadata = manager.get_source_metadata(source)
                    table.add_row(
                        metadata.name,
                        metadata.type,
                        metadata.size,
                        (
                            metadata.description[:47] + "..."
                            if len(metadata.description) > 50
                            else metadata.description
                        ),
                    )

                console.print(table)
            else:
                for source in sources:
                    console.print(f"  • {source}")

            console.print("\n💡 Use [cyan]sage-dev data show <name>[/cyan] for details")
            console.print("💡 Use [cyan]sage-dev data list --metadata[/cyan] for full info\n")

    except ImportError as e:
        console.print(f"[red]Error importing sage.data: {e}[/red]")
        console.print("[yellow]Make sure sage-benchmark is installed[/yellow]")
        raise typer.Exit(1)


@app.command("show")
def show_dataset(
    name: str = typer.Argument(..., help="Dataset name"),
):
    """
    Show detailed information about a dataset.

    Examples:
        sage-dev data show qa_base
        sage-dev data show mmlu
    """
    try:
        from sage.data import DataManager

        manager = DataManager.get_instance()

        # Check if it's a valid source
        if name not in manager.list_sources():
            console.print(f"[red]Dataset '{name}' not found[/red]")
            console.print(f"\nAvailable datasets: {', '.join(manager.list_sources())}")
            raise typer.Exit(1)

        metadata = manager.get_source_metadata(name)

        console.print(f"\n[bold cyan]📦 Dataset: {metadata.name}[/bold cyan]\n")
        console.print(f"[bold]Description:[/bold] {metadata.description}")
        console.print(f"[bold]Type:[/bold] {metadata.type}")
        console.print(f"[bold]Format:[/bold] {metadata.format}")
        console.print(f"[bold]Size:[/bold] {metadata.size}")
        console.print(f"[bold]License:[/bold] {metadata.license}")
        console.print(f"[bold]Version:[/bold] {metadata.version}")
        console.print(f"[bold]Maintainer:[/bold] {metadata.maintainer}")

        if metadata.tags:
            console.print(f"[bold]Tags:[/bold] {', '.join(metadata.tags)}")

        # Show which usages include this dataset
        usages_with_dataset = []
        for usage_name in manager.list_usages():
            try:
                profile = manager.get_by_usage(usage_name)
                if name in [profile.datasets.get(k) for k in profile.datasets]:
                    usages_with_dataset.append(usage_name)
            except Exception:
                pass

        if usages_with_dataset:
            console.print(f"\n[bold]Used in:[/bold] {', '.join(usages_with_dataset)}")

        console.print()

    except ImportError as e:
        console.print(f"[red]Error importing sage.data: {e}[/red]")
        raise typer.Exit(1)


@app.command("usages")
def list_usages():
    """
    List all usage profiles.

    Examples:
        sage-dev data usages
    """
    try:
        from sage.data import DataManager

        manager = DataManager.get_instance()
        usages = manager.list_usages()

        if not usages:
            console.print("[yellow]No usage profiles found[/yellow]")
            return

        console.print(f"\n[bold cyan]🎯 Usage Profiles ({len(usages)}):[/bold cyan]\n")

        for usage_name in usages:
            try:
                profile = manager.get_by_usage(usage_name)
                console.print(f"[bold]{usage_name}[/bold]")
                console.print(f"  {profile.description}")
                console.print(f"  Datasets: {', '.join(profile.list_datasets())}")
                console.print()
            except Exception as e:
                console.print(f"[bold]{usage_name}[/bold]")
                console.print(f"  [red]Error loading: {e}[/red]\n")

    except ImportError as e:
        console.print(f"[red]Error importing sage.data: {e}[/red]")
        raise typer.Exit(1)


@app.command("structure")
def show_structure():
    """
    Show the complete data architecture structure.

    Examples:
        sage-dev data structure
    """
    try:
        from sage.data import DataManager

        manager = DataManager.get_instance()
        console.print()
        manager.print_structure()
        console.print()

    except ImportError as e:
        console.print(f"[red]Error importing sage.data: {e}[/red]")
        raise typer.Exit(1)


@app.command("test")
def test_dataset(
    name: str = typer.Argument(..., help="Dataset name or usage"),
    is_usage: bool = typer.Option(False, "--usage", "-u", help="Treat name as usage profile"),
):
    """
    Test loading a dataset.

    Examples:
        sage-dev data test qa_base
        sage-dev data test rag --usage
    """
    try:
        from sage.data import DataManager

        manager = DataManager.get_instance()

        console.print(f"\n[bold cyan]Testing dataset: {name}[/bold cyan]\n")

        if is_usage:
            profile = manager.get_by_usage(name)
            console.print(f"✓ Loaded usage profile: {name}")
            console.print(f"  Datasets: {profile.list_datasets()}")

            # Try loading first dataset
            if profile.list_datasets():
                first_ds = profile.list_datasets()[0]
                console.print(f"\n  Testing first dataset: {first_ds}")
                try:
                    loader = profile.load(first_ds)
                    console.print(f"  ✓ Loaded: {type(loader).__name__}")
                except Exception as e:
                    console.print(f"  ✗ Error: {e}")
        else:
            try:
                loader = manager.get_by_source(name)
                console.print(f"✓ Loaded dataset: {name}")
                console.print(f"  Loader type: {type(loader).__name__}")
                console.print(f"  Loader instance: {loader}")
            except Exception as e:
                console.print(f"✗ Error loading: {e}")
                raise typer.Exit(1)

        console.print("\n✓ Test passed!\n")

    except ImportError as e:
        console.print(f"[red]Error importing sage.data: {e}[/red]")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
