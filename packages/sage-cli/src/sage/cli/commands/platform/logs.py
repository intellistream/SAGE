"""Log management commands for SAGE platform."""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from sage.common.config.user_paths import get_user_paths

app = typer.Typer(help="Log management commands")
console = Console()


@app.command("clean")
def clean_logs(
    days: int = typer.Option(
        7,
        "--days",
        "-d",
        help="Delete logs older than this many days",
        min=1,
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be deleted without actually deleting",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt",
    ),
) -> None:
    """Clean old log files from .sage/logs directory.

    Args:
        days: Delete logs older than this many days (default: 7)
        dry_run: Show what would be deleted without actually deleting
        yes: Skip confirmation prompt

    Examples:
        sage logs clean --days 7          # Delete logs older than 7 days
        sage logs clean --days 30 --dry-run  # Preview deletion
        sage logs clean --days 1 --yes    # Delete logs older than 1 day without confirmation
    """
    user_paths = get_user_paths()
    logs_dir = user_paths.logs_dir

    if not logs_dir.exists():
        console.print(f"[yellow]Log directory does not exist: {logs_dir}[/yellow]")
        return

    # Calculate cutoff time
    cutoff_time = datetime.now() - timedelta(days=days)
    cutoff_timestamp = cutoff_time.timestamp()

    # Find old log files
    old_files = []
    total_size = 0

    for root, dirs, files in os.walk(logs_dir):
        for file in files:
            if file.endswith(".log") or file.endswith(".txt"):
                file_path = Path(root) / file
                try:
                    file_mtime = file_path.stat().st_mtime
                    if file_mtime < cutoff_timestamp:
                        file_size = file_path.stat().st_size
                        old_files.append((file_path, file_size))
                        total_size += file_size
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not access {file_path}: {e}[/yellow]")

    if not old_files:
        console.print(f"[green]✓ No log files older than {days} days found.[/green]")
        return

    # Display files to be deleted
    table = Table(title=f"Log Files Older Than {days} Days")
    table.add_column("File", style="cyan", no_wrap=False)
    table.add_column("Size", justify="right", style="yellow")
    table.add_column("Modified", style="magenta")

    for file_path, file_size in old_files:
        rel_path = file_path.relative_to(logs_dir)
        size_mb = file_size / (1024 * 1024)
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        table.add_row(str(rel_path), f"{size_mb:.2f} MB", mtime.strftime("%Y-%m-%d %H:%M"))

    console.print(table)
    console.print(
        f"\n[bold]Total:[/bold] {len(old_files)} files, {total_size / (1024 * 1024):.2f} MB"
    )

    if dry_run:
        console.print("\n[yellow]DRY RUN: No files were deleted.[/yellow]")
        return

    # Confirm deletion
    if not yes:
        console.print(
            f"\n[yellow]This will delete {len(old_files)} log files ({total_size / (1024 * 1024):.2f} MB).[/yellow]"
        )
        confirm = typer.confirm("Do you want to continue?", default=False)
        if not confirm:
            console.print("[yellow]Cancelled.[/yellow]")
            return

    # Delete files
    deleted_count = 0
    deleted_size = 0
    errors = []

    for file_path, file_size in old_files:
        try:
            file_path.unlink()
            deleted_count += 1
            deleted_size += file_size
        except Exception as e:
            errors.append((file_path, str(e)))

    # Report results
    if deleted_count > 0:
        console.print(
            f"\n[green]✓ Deleted {deleted_count} files ({deleted_size / (1024 * 1024):.2f} MB)[/green]"
        )

    if errors:
        console.print(f"\n[red]Failed to delete {len(errors)} files:[/red]")
        for file_path, error in errors:
            console.print(f"  [red]• {file_path.relative_to(logs_dir)}: {error}[/red]")


@app.command("list")
def list_logs(
    days: Optional[int] = typer.Option(
        None,
        "--days",
        "-d",
        help="Only list logs from the last N days",
    ),
    sort_by_size: bool = typer.Option(
        False,
        "--sort-size",
        "-s",
        help="Sort by file size instead of modification time",
    ),
) -> None:
    """List all log files in .sage/logs directory.

    Args:
        days: Only list logs from the last N days
        sort_by_size: Sort by file size instead of modification time

    Examples:
        sage logs list                # List all logs
        sage logs list --days 7       # List logs from last 7 days
        sage logs list --sort-size    # Sort by size
    """
    user_paths = get_user_paths()
    logs_dir = user_paths.logs_dir

    if not logs_dir.exists():
        console.print(f"[yellow]Log directory does not exist: {logs_dir}[/yellow]")
        return

    # Find log files
    log_files = []
    cutoff_time = None
    if days is not None:
        cutoff_time = (datetime.now() - timedelta(days=days)).timestamp()

    for root, dirs, files in os.walk(logs_dir):
        for file in files:
            if file.endswith(".log") or file.endswith(".txt"):
                file_path = Path(root) / file
                try:
                    file_stat = file_path.stat()
                    if cutoff_time is None or file_stat.st_mtime >= cutoff_time:
                        log_files.append((file_path, file_stat))
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not access {file_path}: {e}[/yellow]")

    if not log_files:
        if days is not None:
            console.print(f"[yellow]No log files found in the last {days} days.[/yellow]")
        else:
            console.print("[yellow]No log files found.[/yellow]")
        return

    # Sort files
    if sort_by_size:
        log_files.sort(key=lambda x: x[1].st_size, reverse=True)
    else:
        log_files.sort(key=lambda x: x[1].st_mtime, reverse=True)

    # Display files
    title = "Log Files"
    if days is not None:
        title += f" (Last {days} Days)"

    table = Table(title=title)
    table.add_column("File", style="cyan", no_wrap=False)
    table.add_column("Size", justify="right", style="yellow")
    table.add_column("Modified", style="magenta")

    total_size = 0
    for file_path, file_stat in log_files:
        rel_path = file_path.relative_to(logs_dir)
        size_mb = file_stat.st_size / (1024 * 1024)
        mtime = datetime.fromtimestamp(file_stat.st_mtime)
        table.add_row(
            str(rel_path),
            f"{size_mb:.2f} MB" if size_mb > 0.01 else f"{file_stat.st_size / 1024:.2f} KB",
            mtime.strftime("%Y-%m-%d %H:%M"),
        )
        total_size += file_stat.st_size

    console.print(table)
    console.print(
        f"\n[bold]Total:[/bold] {len(log_files)} files, {total_size / (1024 * 1024):.2f} MB"
    )


@app.command("info")
def log_info() -> None:
    """Show log directory information and disk usage."""
    user_paths = get_user_paths()
    logs_dir = user_paths.logs_dir

    console.print("\n[bold cyan]Log Directory Information[/bold cyan]")
    console.print(f"Location: {logs_dir}")

    if not logs_dir.exists():
        console.print("[yellow]Directory does not exist.[/yellow]")
        return

    # Count files and calculate size
    log_count = 0
    total_size = 0

    for root, dirs, files in os.walk(logs_dir):
        for file in files:
            if file.endswith(".log") or file.endswith(".txt"):
                log_count += 1
                file_path = Path(root) / file
                try:
                    total_size += file_path.stat().st_size
                except Exception:
                    pass

    console.print(f"Log files: {log_count}")
    console.print(f"Total size: {total_size / (1024 * 1024):.2f} MB")

    # Show disk usage
    try:
        disk_usage = shutil.disk_usage(logs_dir)
        console.print("\n[bold]Disk Usage:[/bold]")
        console.print(f"  Total: {disk_usage.total / (1024**3):.2f} GB")
        console.print(f"  Used: {disk_usage.used / (1024**3):.2f} GB")
        console.print(f"  Free: {disk_usage.free / (1024**3):.2f} GB")
        console.print(f"  Usage: {disk_usage.used / disk_usage.total * 100:.1f}%")
    except Exception as e:
        console.print(f"[yellow]Could not get disk usage: {e}[/yellow]")


if __name__ == "__main__":
    app()
