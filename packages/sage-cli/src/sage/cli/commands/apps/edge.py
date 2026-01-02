#!/usr/bin/env python3
"""SAGE Edge CLI - Aggregator shell commands."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from typing import Any

import httpx
import typer
from rich.console import Console

from sage.common.config.ports import SagePorts
from sage.common.config.user_paths import get_user_paths

console = Console()
app = typer.Typer(help="🪄 Edge - Aggregator shell (mounts LLM gateway)")

_paths = get_user_paths()
EDGE_STATE_DIR = _paths.state_dir / "edge"
PID_FILE = EDGE_STATE_DIR / "edge.pid"
LOG_FILE = _paths.get_log_file("edge")


def _ensure_dirs() -> None:
    EDGE_STATE_DIR.mkdir(parents=True, exist_ok=True)
    _paths.logs_dir.mkdir(parents=True, exist_ok=True)


def _get_edge_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
        return pid
    except (ValueError, OSError):
        PID_FILE.unlink(missing_ok=True)
        return None


def _check_edge_health(port: int, timeout: float = 2.0) -> bool:
    try:
        url = f"http://localhost:{port}/healthz"
        response = httpx.get(url, timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False


def _fetch_edge_ready(port: int, timeout: float = 2.0) -> dict[str, Any] | None:
    try:
        url = f"http://localhost:{port}/readyz"
        response = httpx.get(url, timeout=timeout)
        if response.status_code == 200:
            return response.json()
    except Exception:
        return None


@app.command("start")
def start(
    port: int = typer.Option(
        SagePorts.EDGE_DEFAULT,
        "--port",
        "-p",
        help=f"Edge listen port (default {SagePorts.EDGE_DEFAULT})",
    ),
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Edge listen address"),
    llm_prefix: str | None = typer.Option(
        None,
        "--llm-prefix",
        help="Optional mount prefix for the LLM gateway (default: /)",
    ),
    mount_llm: bool = typer.Option(
        True,
        "--mount-llm/--no-mount-llm",
        help="Mount the LLM gateway application",
    ),
    background: bool = typer.Option(
        True,
        "--background/--foreground",
        "-b/-f",
        help="Run in background (default) or foreground",
    ),
    log_level: str = typer.Option("info", "--log-level", help="Log level for uvicorn"),
):
    """Start the edge aggregator shell."""
    _ensure_dirs()

    existing_pid = _get_edge_pid()
    if existing_pid:
        if _check_edge_health(port):
            console.print(f"[yellow]⚠️ Edge 已在运行中 (PID: {existing_pid})[/yellow]")
            console.print(f"[blue]🌐 访问地址: http://localhost:{port}[/blue]")
            return
        console.print("[yellow]⚠️ 发现过期的 PID 文件，正在清理...[/yellow]")
        PID_FILE.unlink(missing_ok=True)

    if not SagePorts.is_available(port):
        console.print(f"[red]❌ 端口 {port} 已被占用[/red]")
        console.print("请使用 --port 指定其他端口，或停止占用该端口的服务")
        raise typer.Exit(1)

    console.print(f"[blue]🚀 启动 SAGE Edge (端口 {port})...[/blue]")

    cmd = [
        sys.executable,
        "-m",
        "sage.edge.server",
        "--host",
        host,
        "--port",
        str(port),
        "--log-level",
        log_level,
    ]

    if llm_prefix:
        cmd += ["--llm-prefix", llm_prefix]
    if not mount_llm:
        cmd.append("--no-llm")

    if background:
        with open(LOG_FILE, "a") as log_file:
            process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )

        PID_FILE.write_text(str(process.pid))

        console.print("[dim]等待 Edge 启动...[/dim]")
        for _ in range(30):
            time.sleep(1)
            if _check_edge_health(port):
                console.print(f"[green]✅ Edge 启动成功 (PID: {process.pid})[/green]")
                console.print(f"[blue]🌐 访问地址: http://localhost:{port}[/blue]")
                console.print(f"[dim]📝 日志文件: {LOG_FILE}[/dim]")
                return

        console.print("[red]❌ Edge 启动超时[/red]")
        console.print(f"[dim]查看日志: cat {LOG_FILE}[/dim]")
        raise typer.Exit(1)

    console.print("[dim]前台运行模式，按 Ctrl+C 停止[/dim]")
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        console.print("\n[yellow]Edge 已停止[/yellow]")
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]❌ Edge 启动失败: {exc}[/red]")
        raise typer.Exit(1)


@app.command("stop")
def stop(
    force: bool = typer.Option(False, "--force", "-f", help="强制停止 (SIGKILL)"),
):
    """Stop the edge aggregator shell."""
    pid = _get_edge_pid()
    if not pid:
        console.print("[yellow]Edge 未运行[/yellow]")
        return

    console.print(f"[blue]🛑 停止 Edge (PID: {pid})...[/blue]")

    try:
        os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)
        for _ in range(10):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except OSError:
                break
        PID_FILE.unlink(missing_ok=True)
        console.print("[green]✅ Edge 已停止[/green]")
    except OSError as exc:
        console.print(f"[red]❌ 停止失败: {exc}[/red]")
        PID_FILE.unlink(missing_ok=True)


@app.command("status")
def status(port: int = typer.Option(SagePorts.EDGE_DEFAULT, "--port", "-p")):
    """Show edge process and health status."""
    pid = _get_edge_pid()
    is_healthy = _check_edge_health(port)
    ready_payload = _fetch_edge_ready(port)

    if pid:
        console.print(f"[green]✅ Edge 进程运行中 (PID: {pid})[/green]")
    else:
        console.print("[yellow]Edge 进程未运行[/yellow]")

    if is_healthy:
        console.print(f"[green]🌐 健康检查通过: http://localhost:{port}/healthz[/green]")
    else:
        console.print(f"[red]⚠️ 健康检查失败: http://localhost:{port}/healthz[/red]")

    if ready_payload:
        console.print(f"[dim]readyz: {ready_payload}[/dim]")


__all__ = ["app"]
