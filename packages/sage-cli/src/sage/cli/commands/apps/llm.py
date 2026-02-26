#!/usr/bin/env python3
"""LLM service management commands for SAGE.

All LLM services should be managed through sageLLM (isagellm),
NOT by directly calling vLLM entrypoints.

MIGRATION NOTE (2026-01): This file now uses isagellm instead of sage.llm.
Recommended engine: sagellm (default). vllm engine is deprecated.
"""

from __future__ import annotations

import os
from importlib.metadata import PackageNotFoundError, version

import httpx
import typer
from rich.console import Console
from rich.table import Table

from sage.common.model_registry import fetch_recommended_models

# Import from isagellm (sageLLM inference engine)
try:
    from sagellm_control import ControlPlaneManager
    from sagellm_control.types import EngineInfo, EngineState
except ImportError:  # pragma: no cover
    ControlPlaneManager = None  # type: ignore
    EngineInfo = None  # type: ignore
    EngineState = None  # type: ignore

try:
    from sagellm_gateway import create_app as _gateway_create_app

    _SAGELLM_GATEWAY_AVAILABLE = True
except ImportError:  # pragma: no cover
    _gateway_create_app = None  # type: ignore
    _SAGELLM_GATEWAY_AVAILABLE = False

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

# Default LLM model — lightweight CPU-friendly default; override with --model
DEFAULT_LLM_MODEL: str = os.getenv("SAGELLM_DEFAULT_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")


def _check_sagellm_available() -> bool:
    """Check if isagellm components are available."""
    if ControlPlaneManager is None:
        console.print("[red]Error:[/red] isagellm not installed. Please run: pip install isagellm")
        return False
    return True


def _get_registry(engine: str):
    """Get the appropriate model registry based on engine selection.

    Args:
        engine: Engine type ('sagellm' is the only supported option)

    Returns:
        The appropriate registry module

    Raises:
        ValueError: If engine is 'vllm' (removed in v0.3.0)
    """
    if engine == "vllm":
        raise ValueError(
            "vllm engine has been removed in SAGE v0.3.0. "
            "Please use engine='sagellm' instead. "
            "See migration guide: docs-public/docs_src/dev-notes/migration/VLLM_TO_SAGELLM_MIGRATION.md"
        )
    from sage.common.model_registry import sagellm_registry as registry

    return registry


def _resolve_package_version(module_name: str, dist_names: list[str]) -> str:
    """Resolve package version from module attribute or distribution metadata."""
    try:
        module = __import__(module_name)
        module_version = getattr(module, "__version__", None)
        if isinstance(module_version, str) and module_version.strip():
            return module_version
    except Exception:
        pass

    for dist_name in dist_names:
        try:
            return version(dist_name)
        except PackageNotFoundError:
            continue

    return "unknown"


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
    engine: str = typer.Option(
        "sagellm",
        "--engine",
        "-e",
        help="推理引擎 (仅支持 sagellm)",
    ),
):
    """List available models.

    Uses sagellm registry for model management.
    """
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
        # List from selected registry
        registry = _get_registry(engine)
        models = registry.list_models()
        table = Table(title=f"Available Models ({engine})")
        table.add_column("Model ID", style="cyan")
        table.add_column("Size (MB)", style="green")
        table.add_column("Last Used", style="yellow")
        for model in models:
            size_mb = f"{model.size_mb:.1f}" if hasattr(model, "size_mb") else "N/A"
            last_used = model.last_used_iso if hasattr(model, "last_used_iso") else "N/A"
            table.add_row(model.model_id, size_mb, last_used)
        console.print(table)


@app.command("serve")
def serve(
    model: str | None = typer.Option(
        None, "--model", "-m", help=f"Model name or path (default: {DEFAULT_LLM_MODEL})"
    ),
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Server host"),
    port: int = typer.Option(8000, "--port", "-p", help="Server port"),
    mock: bool = typer.Option(False, "--mock", help="Run in mock mode (no GPU)"),
):
    """Start LLM server (via isagellm gateway).

    \b
    Examples:
        sage llm serve                                       # start with default model
        sage llm serve --model Qwen/Qwen2.5-0.5B-Instruct   # lightweight default
        sage llm serve --model Qwen/Qwen2.5-7B-Instruct     # larger model
        sage llm serve --model sshleifer/tiny-gpt2 --port 8888
    """
    if not _check_sagellm_available():
        raise typer.Exit(1)

    if not _SAGELLM_GATEWAY_AVAILABLE:
        console.print(
            "[red]Error:[/red] sagellm-gateway not available. "
            "Please run: pip install --upgrade isagellm"
        )
        raise typer.Exit(1)

    resolved_model = model or DEFAULT_LLM_MODEL
    console.print(f"[cyan]Starting LLM server for model:[/cyan] [bold]{resolved_model}[/bold]")
    console.print(f"  Host: {host}:{port}")
    console.print(f"  Mock mode: {mock}")
    if not model:
        console.print("  [dim](override with: sage llm serve --model <your-model>)[/dim]")

    # Pass model to the gateway via env var so sagellm engine picks it up.
    os.environ.setdefault("SAGELLM_ENGINE_MODEL", resolved_model)

    try:
        import uvicorn

        if mock:
            os.environ["SAGELLM_MOCK_MODE"] = "1"
        gateway_app = _gateway_create_app()
        uvicorn.run(gateway_app, host=host, port=port, log_level="info")
    except Exception as e:
        console.print(f"[red]Error starting server:[/red] {e}")
        raise typer.Exit(1)


@app.command("info")
def info():
    """Show isagellm installation info."""
    try:
        import sagellm  # noqa: F401

        sagellm_version = _resolve_package_version("sagellm", ["isagellm", "sagellm"])
        console.print(f"[green]✓[/green] isagellm version: {sagellm_version}")
    except ImportError:
        console.print("[red]✗[/red] isagellm not installed")
        return

    try:
        import sagellm_control  # noqa: F401

        control_version = _resolve_package_version(
            "sagellm_control", ["sagellm-control-plane", "sagellm_control"]
        )
        console.print(f"[green]✓[/green] sagellm-control-plane: {control_version}")
    except ImportError:
        console.print("[yellow]![/yellow] sagellm-control-plane not installed")

    try:
        import sagellm_gateway  # noqa: F401

        gateway_version = _resolve_package_version(
            "sagellm_gateway", ["sagellm-gateway", "sagellm_gateway"]
        )
        console.print(f"[green]✓[/green] sagellm-gateway: {gateway_version}")
    except ImportError:
        console.print("[yellow]![/yellow] sagellm-gateway not installed (optional)")


if __name__ == "__main__":
    app()
