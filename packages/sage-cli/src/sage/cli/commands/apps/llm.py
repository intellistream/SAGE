#!/usr/bin/env python3
"""LLM service management commands for SAGE.

All LLM services should be managed through sageLLM (isagellm),
NOT by directly calling vLLM entrypoints.

MIGRATION NOTE (2026-01): This file now uses isagellm instead of sage.llm.
"""

from __future__ import annotations

import httpx
import typer
from rich.console import Console
from rich.table import Table

from sage.common.model_registry import fetch_recommended_models, vllm_registry

# Import from isagellm (sageLLM inference engine)
try:
    from sagellm_control import ControlPlaneManager
    from sagellm_control.types import EngineInfo, EngineState
except ImportError:  # pragma: no cover
    ControlPlaneManager = None  # type: ignore
    EngineInfo = None  # type: ignore
    EngineState = None  # type: ignore

try:
    from sagellm_gateway import GatewayConfig, GatewayServer
except ImportError:  # pragma: no cover
    GatewayServer = None  # type: ignore
    GatewayConfig = None  # type: ignore

# Import config subcommands
from sage.cli.commands.platform.llm_config import app as config_app

app = typer.Typer(
    name="llm",
    help="LLM service management (powered by isagellm)",
    no_args_is_help=True,
)
console = Console()

# Add config subcommand group
app.add_typer(config_app, name="config")


def _check_sagellm_available() -> bool:
    """Check if isagellm components are available."""
    if ControlPlaneManager is None:
        console.print("[red]Error:[/red] isagellm not installed. Please run: pip install isagellm")
        return False
    return True


@app.command("status")
def status(
    host: str = typer.Option("localhost", "--host", "-h", help="Server host"),
    port: int = typer.Option(8000, "--port", "-p", help="Server port"),
):
    """Check LLM server status."""
    url = f"http://{host}:{port}/health"
    try:
        resp = httpx.get(url, timeout=5.0)
        if resp.status_code == 200:
            console.print(f"[green]✓[/green] Server at {host}:{port} is healthy")
            data = resp.json()
            if data:
                console.print(f"  Status: {data}")
        else:
            console.print(f"[yellow]![/yellow] Server returned: {resp.status_code}")
    except httpx.ConnectError:
        console.print(f"[red]✗[/red] Cannot connect to {host}:{port}")
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")


@app.command("list-models")
def list_models(
    recommended: bool = typer.Option(False, "--recommended", "-r", help="Show recommended models"),
):
    """List available models."""
    if recommended:
        models = fetch_recommended_models()
        table = Table(title="Recommended Models")
        table.add_column("Name", style="cyan")
        table.add_column("Size", style="green")
        table.add_column("Description")
        for model in models:
            table.add_row(model.get("name", ""), model.get("size", ""), model.get("desc", ""))
        console.print(table)
    else:
        # List from vllm registry
        models = vllm_registry.list_models()
        table = Table(title="Available Models")
        table.add_column("Model ID", style="cyan")
        table.add_column("Type", style="green")
        for model in models:
            table.add_row(model.model_id, model.model_type)
        console.print(table)


@app.command("serve")
def serve(
    model: str = typer.Argument(..., help="Model name or path"),
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Server host"),
    port: int = typer.Option(8000, "--port", "-p", help="Server port"),
    mock: bool = typer.Option(False, "--mock", help="Run in mock mode (no GPU)"),
):
    """Start LLM server (via isagellm gateway)."""
    if not _check_sagellm_available():
        raise typer.Exit(1)

    if GatewayServer is None:
        console.print(
            "[red]Error:[/red] isagellm[gateway] not installed. "
            "Please run: pip install 'isagellm[gateway]'"
        )
        raise typer.Exit(1)

    console.print(f"[cyan]Starting LLM server for model:[/cyan] {model}")
    console.print(f"  Host: {host}:{port}")
    console.print(f"  Mock mode: {mock}")

    try:
        config = GatewayConfig(
            host=host,
            port=port,
            mock_mode=mock,
        )
        server = GatewayServer(config)
        server.run()
    except Exception as e:
        console.print(f"[red]Error starting server:[/red] {e}")
        raise typer.Exit(1)


@app.command("info")
def info():
    """Show isagellm installation info."""
    try:
        import sagellm

        console.print(f"[green]✓[/green] isagellm version: {sagellm.__version__}")
    except ImportError:
        console.print("[red]✗[/red] isagellm not installed")
        return

    try:
        import sagellm_control

        console.print(f"[green]✓[/green] sagellm-control-plane: {sagellm_control.__version__}")
    except ImportError:
        console.print("[yellow]![/yellow] sagellm-control-plane not installed")

    try:
        import sagellm_gateway

        console.print(f"[green]✓[/green] sagellm-gateway: {sagellm_gateway.__version__}")
    except ImportError:
        console.print("[yellow]![/yellow] sagellm-gateway not installed (optional)")


if __name__ == "__main__":
    app()
