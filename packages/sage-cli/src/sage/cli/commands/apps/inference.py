#!/usr/bin/env python3
"""Unified Inference service management commands for SAGE.

This module manages the single OpenAI-compatible inference gateway runtime
provided by ``sagellm_gateway``.

Commands:
    - start: Start the unified inference server
    - stop: Stop the unified inference server
    - status: Check the status of the unified inference server
    - config: Manage configuration

Example:
    sage inference start
    sage inference stop
    sage inference status
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import psutil
import typer
from click.core import ParameterSource
from rich.console import Console
from rich.table import Table

from sage.cli.utils.runtime_helpers import load_structured_config, module_available
from sage.common.config import ensure_hf_mirror_configured
from sage.common.config.ports import SagePorts
from sage.common.config.user_paths import get_user_paths

console = Console()
app = typer.Typer(help="🔮 统一推理服务管理 - Gateway 统一入口")

# PID file location
USER_PATHS = get_user_paths()
INFERENCE_STATE_DIR = USER_PATHS.state_dir / "inference"
PID_FILE = INFERENCE_STATE_DIR / "inference_server.pid"
CONFIG_FILE = INFERENCE_STATE_DIR / "inference_server.json"
LOG_FILE = USER_PATHS.logs_dir / "inference_server.log"


# =============================================================================
# Helper Functions
# =============================================================================


def _is_port_in_use(port: int) -> bool:
    """Check if a port is in use.

    Note:
        This is a wrapper around sage.common.utils.system.network.is_port_occupied
    """
    from sage.common.utils.system.network import is_port_occupied

    return is_port_occupied("localhost", port)


def _get_running_pid() -> int | None:
    """Get the PID of the running server from PID file."""
    if not PID_FILE.exists():
        return None

    try:
        pid = int(PID_FILE.read_text().strip())
        # Check if process is still running
        if psutil.pid_exists(pid):
            try:
                proc = psutil.Process(pid)
                # Verify it's our process by checking command line
                cmdline = " ".join(proc.cmdline())
                if "sagellm_gateway" in cmdline:
                    return pid
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        # PID file exists but process is not running, clean up
        PID_FILE.unlink()
    except (ValueError, OSError):
        pass

    return None


def _save_pid(pid: int) -> None:
    """Save the server PID to file."""
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(pid))


def _save_config(config: dict[str, Any]) -> None:
    """Save the server configuration to file."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def _load_config() -> dict[str, Any] | None:
    """Load the server configuration from file."""
    if not CONFIG_FILE.exists():
        return None
    try:
        return json.loads(CONFIG_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _test_api_health(port: int, timeout: float = 2.0) -> dict[str, Any] | None:
    """Test the API health endpoint."""
    import urllib.error
    import urllib.request

    try:
        url = f"http://localhost:{port}/health"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except Exception:
        return None


# =============================================================================
# Start Command
# =============================================================================


@app.command("start")
def start_server(
    ctx: typer.Context,
    port: int = typer.Option(
        SagePorts.GATEWAY_DEFAULT,
        "--port",
        "-p",
        help=f"服务监听端口 (默认 {SagePorts.GATEWAY_DEFAULT})",
    ),
    host: str = typer.Option(
        "0.0.0.0",
        "--host",
        "-h",
        help="服务监听地址",
    ),
    background: bool = typer.Option(
        False,
        "--background",
        "-b",
        help="后台运行服务",
    ),
    config_file: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="配置文件路径 (YAML/JSON)",
    ),
    log_level: str = typer.Option(
        "info",
        "--log-level",
        help="日志级别 (debug, info, warning, error)",
    ),
):
    """启动统一推理服务。

    该服务提供 OpenAI 兼容的 API，同时支持 LLM 和 Embedding 请求。
    该命令启动 sagellm_gateway，并由 Control Plane 统一管理后端。

    示例：
        # 启动基本服务
        sage inference start

        # 后台运行
        sage inference start --background

        # 使用配置文件
        sage inference start --config inference-config.yaml

    说明：
        具体引擎由 gateway/control-plane 管理，通过 `sage llm engine` 操作。
    """
    console.print("[blue]🚀 启动统一推理服务...[/blue]")
    ensure_hf_mirror_configured()

    if not module_available("sagellm_gateway"):
        console.print("[red]❌ 缺少 sagellm_gateway 模块[/red]")
        console.print("   请安装: pip install isagellm-gateway")
        raise typer.Exit(1)

    # Check if already running
    existing_pid = _get_running_pid()
    if existing_pid:
        console.print(f"[yellow]⚠️ 服务已在运行中 (PID: {existing_pid})[/yellow]")
        console.print("   使用 'sage inference stop' 停止服务")
        raise typer.Exit(1)

    file_config: dict[str, Any] = {}

    # Load configuration from file if specified
    if config_file and config_file.exists():
        try:
            file_config = load_structured_config(config_file)
            console.print(f"[green]✓[/green] 加载配置文件: {config_file}")
        except Exception as e:
            console.print(f"[red]❌ 无法加载配置文件: {e}[/red]")
            raise typer.Exit(1)
    elif config_file and not config_file.exists():
        console.print(f"[red]❌ 配置文件不存在: {config_file}[/red]")
        raise typer.Exit(1)

    # Merge configuration (CLI args > file config > defaults)
    host_source = ctx.get_parameter_source("host")
    port_source = ctx.get_parameter_source("port")
    log_level_source = ctx.get_parameter_source("log_level")

    final_config: dict[str, str | int] = {
        "host": str(file_config.get("host", "0.0.0.0")),
        "port": int(file_config.get("port", SagePorts.GATEWAY_DEFAULT)),
        "log_level": str(file_config.get("log_level", "info")),
    }

    if host_source == ParameterSource.COMMANDLINE or not file_config:
        final_config["host"] = host
    if port_source == ParameterSource.COMMANDLINE or not file_config:
        final_config["port"] = port
    if log_level_source == ParameterSource.COMMANDLINE or not file_config:
        final_config["log_level"] = log_level

    # Check port availability with merged effective config
    effective_port = int(final_config["port"])
    if _is_port_in_use(effective_port):
        console.print(f"[red]❌ 端口 {effective_port} 已被占用[/red]")
        console.print("   请使用其他端口或停止占用该端口的服务")
        raise typer.Exit(1)

    # Build command to run the server (requires sagellm_gateway package)
    cmd: list[str] = [
        sys.executable,
        "-m",
        "sagellm_gateway",
        "--host",
        str(final_config["host"]),
        "--port",
        str(effective_port),
        "--log-level",
        str(final_config["log_level"]),
    ]

    console.print(f"[dim]命令: {' '.join(cmd[:6])}...[/dim]")

    try:
        if background:
            # Background mode
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            log_handle = open(LOG_FILE, "w")

            process = subprocess.Popen(
                cmd,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )

            _save_pid(process.pid)
            _save_config(final_config)

            console.print("[green]✅ 服务已在后台启动[/green]")
            console.print(f"   PID: {process.pid}")
            console.print(f"   端口: {final_config['port']}")
            console.print(f"   日志: {LOG_FILE}")
            console.print()
            console.print("[dim]API 端点:[/dim]")
            console.print(
                f"   Chat:      http://localhost:{final_config['port']}/v1/chat/completions"
            )
            console.print(f"   Completion: http://localhost:{final_config['port']}/v1/completions")
            console.print(f"   Embedding: http://localhost:{final_config['port']}/v1/embeddings")
            console.print(f"   Models:    http://localhost:{final_config['port']}/v1/models")
            console.print(f"   Health:    http://localhost:{final_config['port']}/health")
            console.print()
            console.print("[dim]使用 'sage inference status' 查看服务状态[/dim]")

        else:
            # Foreground mode
            console.print("[dim]按 Ctrl+C 停止服务[/dim]")
            console.print()

            _save_config(final_config)

            process = None
            try:
                # Run in foreground
                process = subprocess.Popen(cmd)
                _save_pid(process.pid)

                # Wait for process
                process.wait()

            except KeyboardInterrupt:
                console.print("\n[yellow]🛑 正在停止服务...[/yellow]")
                if process is not None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()

            finally:
                # Clean up PID file
                if PID_FILE.exists():
                    PID_FILE.unlink()

    except Exception as e:
        console.print(f"[red]❌ 启动失败: {e}[/red]")
        raise typer.Exit(1)


# =============================================================================
# Stop Command
# =============================================================================


@app.command("stop")
def stop_server(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="强制停止服务",
    ),
    port: int | None = typer.Option(
        None,
        "--port",
        "-p",
        help="指定端口（用于查找进程）",
    ),
):
    """停止统一推理服务。

    示例：
        sage inference stop          # 停止服务
        sage inference stop --force  # 强制停止
    """
    console.print("[blue]🛑 停止统一推理服务...[/blue]")

    pid = _get_running_pid()

    if not pid:
        # Try to find by port
        if port:
            for proc in psutil.process_iter(["pid", "cmdline"]):
                try:
                    cmdline = " ".join(proc.info.get("cmdline") or [])
                    if "sagellm_gateway" in cmdline and str(port) in cmdline:
                        pid = proc.pid
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

    if not pid:
        console.print("[yellow]⚠️ 未找到运行中的服务[/yellow]")
        # Clean up stale PID file
        if PID_FILE.exists():
            PID_FILE.unlink()
        raise typer.Exit(0)

    try:
        proc = psutil.Process(pid)
        console.print(f"[dim]找到进程 PID: {pid}[/dim]")

        if force:
            proc.kill()
            console.print("[green]✅ 服务已强制停止[/green]")
        else:
            proc.terminate()
            try:
                proc.wait(timeout=10)
                console.print("[green]✅ 服务已停止[/green]")
            except psutil.TimeoutExpired:
                console.print("[yellow]⚠️ 服务未响应，强制停止...[/yellow]")
                proc.kill()
                console.print("[green]✅ 服务已强制停止[/green]")

    except psutil.NoSuchProcess:
        console.print("[yellow]⚠️ 进程已不存在[/yellow]")
    except psutil.AccessDenied:
        console.print("[red]❌ 无权限停止进程，请使用 sudo[/red]")
        raise typer.Exit(1)
    finally:
        # Clean up PID file
        if PID_FILE.exists():
            PID_FILE.unlink()


# =============================================================================
# Status Command
# =============================================================================


@app.command("status")
def server_status(
    port: int = typer.Option(
        SagePorts.GATEWAY_DEFAULT,
        "--port",
        "-p",
        help=f"服务端口 (默认 {SagePorts.GATEWAY_DEFAULT})",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="以 JSON 格式输出",
    ),
):
    """查看统一推理服务状态。

    示例：
        sage inference status          # 查看状态
        sage inference status --json   # JSON 格式输出
    """
    pid = _get_running_pid()
    config = _load_config()
    port_to_check = config.get("port", port) if config else port

    # Gather status information
    status_info: dict[str, Any] = {
        "running": False,
        "pid": None,
        "port": port_to_check,
        "health": None,
        "uptime": None,
        "config": config,
    }

    if pid:
        try:
            proc = psutil.Process(pid)
            status_info["running"] = proc.is_running()
            status_info["pid"] = pid
            status_info["uptime"] = time.time() - proc.create_time()
            status_info["memory_mb"] = proc.memory_info().rss / 1024 / 1024
            status_info["cpu_percent"] = proc.cpu_percent()
        except psutil.NoSuchProcess:
            pass

    # Check health endpoint
    if _is_port_in_use(port_to_check):
        health = _test_api_health(port_to_check)
        status_info["health"] = health
        if not status_info["running"]:
            status_info["running"] = health is not None

    if json_output:
        console.print_json(json.dumps(status_info, indent=2, default=str))
        return

    # Pretty print status
    console.print()
    console.print("[bold]🔮 统一推理服务状态[/bold]")
    console.print()

    if status_info["running"]:
        console.print("[green]● 运行中[/green]")
        console.print(f"   PID: {status_info.get('pid', 'N/A')}")
        console.print(f"   端口: {status_info['port']}")

        if status_info.get("uptime"):
            uptime_hours = status_info["uptime"] / 3600
            console.print(f"   运行时间: {uptime_hours:.2f} 小时")

        if status_info.get("memory_mb"):
            console.print(f"   内存使用: {status_info['memory_mb']:.1f} MB")

        # Health status
        health = status_info.get("health")
        if health:
            console.print()
            console.print("[bold]健康状态:[/bold]")
            console.print(f"   状态: {health.get('status', 'unknown')}")
            backends = health.get("backends", {})
            if backends:
                llm_status = "✅" if backends.get("llm", {}).get("healthy") else "❌"
                embed_status = "✅" if backends.get("embedding", {}).get("healthy") else "❌"
                console.print(f"   LLM 后端: {llm_status}")
                console.print(f"   Embedding 后端: {embed_status}")

        # Configuration
        if config:
            console.print()
            console.print("[bold]配置:[/bold]")

        console.print()
        console.print("[dim]API 端点:[/dim]")
        console.print(f"   http://localhost:{status_info['port']}/v1/chat/completions")
        console.print(f"   http://localhost:{status_info['port']}/v1/embeddings")
        console.print(f"   http://localhost:{status_info['port']}/v1/models")

    else:
        console.print("[red]● 未运行[/red]")
        console.print()
        console.print("[dim]使用 'sage inference start' 启动服务[/dim]")


# =============================================================================
# Config Command
# =============================================================================


@app.command("config")
def show_config(
    output: str = typer.Option(
        "table",
        "--output",
        "-o",
        help="输出格式 (table, json, yaml)",
    ),
):
    """显示当前配置。

    示例：
        sage inference config              # 表格格式
        sage inference config --output json   # JSON 格式
    """
    config = _load_config()

    if not config:
        console.print("[yellow]⚠️ 暂无保存的配置[/yellow]")
        console.print("[dim]使用 'sage inference start' 首次启动后会生成配置[/dim]")
        return

    if output == "json":
        console.print_json(json.dumps(config, indent=2))
    elif output == "yaml":
        try:
            import yaml  # type: ignore[import-untyped]

            console.print(yaml.dump(config, default_flow_style=False))
        except ImportError:
            console.print("[red]需要安装 PyYAML: pip install pyyaml[/red]")
    else:
        # Table format
        table = Table(title="统一推理服务配置")
        table.add_column("配置项", style="cyan")
        table.add_column("值", style="green")

        table.add_row("服务地址", f"{config.get('host', 'N/A')}:{config.get('port', 'N/A')}")
        table.add_row("日志级别", config.get("log_level", "info"))

        console.print(table)


# =============================================================================
# Logs Command
# =============================================================================


@app.command("logs")
def show_logs(
    follow: bool = typer.Option(
        False,
        "--follow",
        "-f",
        help="持续输出日志",
    ),
    lines: int = typer.Option(
        50,
        "--lines",
        "-n",
        help="显示最后 N 行",
    ),
):
    """查看服务日志。

    示例：
        sage inference logs           # 显示最后 50 行
        sage inference logs -n 100    # 显示最后 100 行
        sage inference logs -f        # 持续输出
    """
    if not LOG_FILE.exists():
        console.print("[yellow]⚠️ 日志文件不存在[/yellow]")
        console.print(f"[dim]预期路径: {LOG_FILE}[/dim]")
        return

    if follow:
        # Follow mode - like tail -f
        console.print(f"[dim]跟踪日志文件: {LOG_FILE}[/dim]")
        console.print("[dim]按 Ctrl+C 退出[/dim]")
        console.print()

        try:
            import subprocess

            subprocess.run(["tail", "-f", str(LOG_FILE)])
        except KeyboardInterrupt:
            pass
    else:
        # Show last N lines
        try:
            with open(LOG_FILE) as f:
                all_lines = f.readlines()
                last_lines = all_lines[-lines:]
                for line in last_lines:
                    console.print(line.rstrip())
        except Exception as e:
            console.print(f"[red]❌ 无法读取日志: {e}[/red]")


if __name__ == "__main__":
    app()
