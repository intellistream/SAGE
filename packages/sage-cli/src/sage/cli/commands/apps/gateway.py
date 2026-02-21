#!/usr/bin/env python3
"""SAGE Gateway CLI - Unified API Gateway management commands.

The Gateway serves as the unified entry point for all SAGE services:
- OpenAI-compatible LLM/Embedding API endpoints
- Control Plane for engine management
- Session management and RAG capabilities
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from typing import TYPE_CHECKING, Any

import httpx
import typer
from rich.console import Console
from rich.table import Table

from sage.cli.utils.runtime_helpers import module_available
from sage.common.config import ensure_hf_mirror_configured
from sage.common.config.ports import SagePorts
from sage.common.config.user_paths import get_user_paths

if TYPE_CHECKING:
    pass

console = Console()
app = typer.Typer(help="🌐 Gateway - 统一 API 网关管理")

# State directory for Gateway
USER_PATHS = get_user_paths()
GATEWAY_DIR = USER_PATHS.state_dir / "gateway"
PID_FILE = GATEWAY_DIR / "gateway.pid"
LOG_FILE = USER_PATHS.logs_dir / "gateway.log"


def _ensure_dirs() -> None:
    """Ensure required directories exist."""
    GATEWAY_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def _get_gateway_pid() -> int | None:
    """Get the PID of the running Gateway process."""
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text().strip())
        # Check if process is still running
        os.kill(pid, 0)
        return pid
    except (ValueError, OSError):
        # Process not running, clean up stale PID file
        PID_FILE.unlink(missing_ok=True)
        return None


def _check_gateway_health(port: int, timeout: float = 2.0) -> bool:
    """Check if Gateway is healthy."""
    try:
        url = f"http://localhost:{port}/health"
        response = httpx.get(url, timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False


def _fetch_gateway_status(port: int, timeout: float = 5.0) -> dict[str, Any] | None:
    """Fetch Gateway status from the management API."""
    try:
        url = f"http://localhost:{port}/v1/management/status"
        response = httpx.get(url, timeout=timeout)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


def _fetch_registered_backends(port: int, timeout: float = 5.0) -> dict[str, Any] | None:
    """Fetch registered backends from the management API."""
    try:
        url = f"http://localhost:{port}/v1/management/backends"
        response = httpx.get(url, timeout=timeout)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


@app.command("start")
def start(
    port: int = typer.Option(
        SagePorts.GATEWAY_DEFAULT,
        "--port",
        "-p",
        help=f"Gateway 监听端口 (默认 {SagePorts.GATEWAY_DEFAULT})",
    ),
    host: str = typer.Option(
        "0.0.0.0",
        "--host",
        "-h",
        help="Gateway 监听地址",
    ),
    enable_control_plane: bool = typer.Option(
        True,
        "--control-plane/--no-control-plane",
        help="启用 Control Plane 引擎管理功能",
    ),
    background: bool = typer.Option(
        True,
        "--background/--foreground",
        "-b/-f",
        help="后台运行 (默认) 或前台运行",
    ),
    log_level: str = typer.Option(
        "info",
        "--log-level",
        help="日志级别 (debug, info, warning, error)",
    ),
):
    """启动 SAGE Gateway 服务。

    Gateway 是 SAGE 的统一 API 网关，提供：
    - OpenAI 兼容的 LLM/Embedding API 端点
    - Control Plane 引擎管理功能
    - 会话管理和 RAG 能力

    示例：
        sage gateway start                    # 后台启动 (端口 8889)
        sage gateway start -p 9000            # 指定端口
        sage gateway start --foreground       # 前台运行
        sage gateway start --no-control-plane # 禁用 Control Plane
    """
    _ensure_dirs()
    ensure_hf_mirror_configured()  # Set HF_ENDPOINT for China mirror if needed

    # Check if already running
    existing_pid = _get_gateway_pid()
    if existing_pid:
        if _check_gateway_health(port):
            console.print(f"[yellow]⚠️ Gateway 已在运行中 (PID: {existing_pid})[/yellow]")
            console.print(f"[blue]🌐 访问地址: http://localhost:{port}[/blue]")
            return
        else:
            console.print("[yellow]⚠️ 发现过期的 PID 文件，正在清理...[/yellow]")
            PID_FILE.unlink(missing_ok=True)

    # Check if port is available
    if not SagePorts.is_available(port):
        console.print(f"[red]❌ 端口 {port} 已被占用[/red]")
        console.print("请使用 --port 指定其他端口，或停止占用该端口的服务")
        raise typer.Exit(1)

    console.print(f"[blue]🚀 启动 SAGE Gateway (端口 {port})...[/blue]")

    if not module_available("sagellm_gateway"):
        console.print("[red]❌ 缺少 sagellm_gateway 模块[/red]")
        console.print("   请安装: pip install isagellm-gateway")
        raise typer.Exit(1)

    # Build command (requires isagellm-gateway package, module name is sagellm_gateway)
    cmd = [
        sys.executable,
        "-m",
        "sagellm_gateway",
        "--host",
        host,
        "--port",
        str(port),
        "--log-level",
        log_level,
    ]

    if enable_control_plane:
        cmd.append("--control-plane")

    if background:
        # Start in background
        with open(LOG_FILE, "a") as log_file:
            process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )

        # Save PID
        PID_FILE.write_text(str(process.pid))

        # Wait for startup
        console.print("[dim]等待 Gateway 启动...[/dim]")
        for _ in range(30):  # Wait up to 30 seconds
            time.sleep(1)
            if _check_gateway_health(port):
                console.print(f"[green]✅ Gateway 启动成功 (PID: {process.pid})[/green]")
                console.print(f"[blue]🌐 访问地址: http://localhost:{port}[/blue]")
                console.print(f"[dim]📝 日志文件: {LOG_FILE}[/dim]")
                if enable_control_plane:
                    console.print(
                        "[cyan]💡 Control Plane 已启用，可使用 'sage llm engine' 管理引擎[/cyan]"
                    )
                return

        console.print("[red]❌ Gateway 启动超时[/red]")
        console.print(f"[dim]查看日志: cat {LOG_FILE}[/dim]")
        raise typer.Exit(1)
    else:
        # Foreground mode
        console.print("[dim]前台运行模式，按 Ctrl+C 停止[/dim]")
        try:
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            console.print("\n[yellow]Gateway 已停止[/yellow]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]❌ Gateway 启动失败: {e}[/red]")
            raise typer.Exit(1)


@app.command("stop")
def stop(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="强制停止 (SIGKILL)",
    ),
):
    """停止 SAGE Gateway 服务。

    示例：
        sage gateway stop         # 优雅停止
        sage gateway stop --force # 强制停止
    """
    pid = _get_gateway_pid()
    if not pid:
        console.print("[yellow]Gateway 未运行[/yellow]")
        return

    console.print(f"[blue]🛑 停止 Gateway (PID: {pid})...[/blue]")

    try:
        if force:
            os.kill(pid, signal.SIGKILL)
        else:
            os.kill(pid, signal.SIGTERM)

        # Wait for process to exit
        for _ in range(10):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except OSError:
                # Process has exited
                break

        # Clean up PID file
        PID_FILE.unlink(missing_ok=True)
        console.print("[green]✅ Gateway 已停止[/green]")

    except OSError as e:
        console.print(f"[red]❌ 停止失败: {e}[/red]")
        raise typer.Exit(1)


@app.command("status")
def status(
    port: int = typer.Option(
        SagePorts.GATEWAY_DEFAULT,
        "--port",
        "-p",
        help=f"Gateway 端口 (默认 {SagePorts.GATEWAY_DEFAULT})",
    ),
    show_engines: bool = typer.Option(
        True,
        "--engines/--no-engines",
        help="显示已注册的引擎列表",
    ),
    show_backends: bool = typer.Option(
        True,
        "--backends/--no-backends",
        help="显示已注册的后端列表",
    ),
):
    """查看 SAGE Gateway 状态。

    显示 Gateway 运行状态、Control Plane 信息和已注册的引擎/后端。

    示例：
        sage gateway status              # 完整状态
        sage gateway status --no-engines # 不显示引擎列表
    """
    pid = _get_gateway_pid()

    # Basic status
    if pid and _check_gateway_health(port):
        console.print(f"[green]✅ Gateway 运行中 (PID: {pid})[/green]")
        console.print(f"[blue]🌐 地址: http://localhost:{port}[/blue]")
    else:
        console.print("[red]❌ Gateway 未运行[/red]")
        console.print("[dim]使用 'sage gateway start' 启动服务[/dim]")
        return

    # Fetch detailed status
    cluster_status = _fetch_gateway_status(port)
    if cluster_status:
        cp_status = cluster_status.get("control_plane", {})
        console.print("\n[bold]Control Plane 状态:[/bold]")
        console.print(f"  运行中: {cp_status.get('running', False)}")
        console.print(f"  调度策略: {cp_status.get('scheduling_policy', '-')}")
        console.print(f"  待处理请求: {cp_status.get('pending_requests', 0)}")
        console.print(f"  运行中请求: {cp_status.get('running_requests', 0)}")
        console.print(f"  注册实例: {cp_status.get('registered_instances', 0)}")

        # Show engines
        if show_engines:
            engines = cluster_status.get("engines", [])
            if engines:
                console.print(f"\n[bold]已注册引擎 ({len(engines)}):[/bold]")
                table = Table(show_header=True, header_style="bold")
                table.add_column("Engine ID", overflow="fold")
                table.add_column("模型", overflow="fold")
                table.add_column("类型", justify="center")
                table.add_column("状态", justify="center")
                table.add_column("端口", justify="center")

                for engine in engines:
                    engine_id = engine.get("engine_id") or engine.get("id") or "-"
                    model = engine.get("model_id") or engine.get("model") or "-"
                    kind = engine.get("engine_kind") or engine.get("runtime") or "llm"
                    state = engine.get("status") or engine.get("state") or "-"
                    engine_port = engine.get("port") or engine.get("listen_port") or "-"
                    table.add_row(
                        str(engine_id), str(model), str(kind), str(state), str(engine_port)
                    )

                console.print(table)
            else:
                console.print("\n[dim]暂无已注册的引擎[/dim]")

    # Show backends
    if show_backends:
        backends = _fetch_registered_backends(port)
        if backends:
            llm_backends = backends.get("llm_backends", [])
            embed_backends = backends.get("embedding_backends", [])

            if llm_backends or embed_backends:
                console.print("\n[bold]已发现后端:[/bold]")
                console.print(
                    f"  LLM: {backends.get('healthy_llm_backends', 0)}/{backends.get('total_llm_backends', 0)} 健康"
                )
                console.print(
                    f"  Embedding: {backends.get('healthy_embedding_backends', 0)}/{backends.get('total_embedding_backends', 0)} 健康"
                )


@app.command("logs")
def logs(
    follow: bool = typer.Option(
        False,
        "--follow",
        "-f",
        help="持续追踪日志输出",
    ),
    lines: int = typer.Option(
        50,
        "--lines",
        "-n",
        help="显示最后 N 行日志",
    ),
):
    """查看 SAGE Gateway 日志。

    示例：
        sage gateway logs           # 显示最后 50 行
        sage gateway logs -n 100    # 显示最后 100 行
        sage gateway logs -f        # 持续追踪日志
    """
    if not LOG_FILE.exists():
        console.print("[yellow]日志文件不存在[/yellow]")
        console.print(f"[dim]预期路径: {LOG_FILE}[/dim]")
        return

    if follow:
        console.print(f"[dim]追踪日志 (Ctrl+C 退出): {LOG_FILE}[/dim]")
        try:
            subprocess.run(["tail", "-f", str(LOG_FILE)], check=True)
        except KeyboardInterrupt:
            pass
        except subprocess.CalledProcessError:
            # Fallback for systems without tail -f
            console.print("[yellow]无法追踪日志，显示最后部分[/yellow]")
            console.print(LOG_FILE.read_text()[-10000:])
    else:
        try:
            result = subprocess.run(
                ["tail", "-n", str(lines), str(LOG_FILE)],
                capture_output=True,
                text=True,
            )
            console.print(result.stdout)
        except subprocess.CalledProcessError:
            # Fallback: read last N lines manually
            content = LOG_FILE.read_text()
            log_lines = content.splitlines()
            for line in log_lines[-lines:]:
                console.print(line)


@app.command("restart")
def restart(
    port: int = typer.Option(
        SagePorts.GATEWAY_DEFAULT,
        "--port",
        "-p",
        help=f"Gateway 端口 (默认 {SagePorts.GATEWAY_DEFAULT})",
    ),
    host: str = typer.Option(
        "0.0.0.0",
        "--host",
        "-h",
        help="Gateway 监听地址",
    ),
):
    """重启 SAGE Gateway 服务。

    等同于先执行 stop 再执行 start。

    示例：
        sage gateway restart
        sage gateway restart -p 9000
    """
    console.print("[blue]🔄 重启 Gateway...[/blue]")

    # Stop if running
    pid = _get_gateway_pid()
    if pid:
        stop(force=False)
        time.sleep(1)

    # Start again
    start(port=port, host=host, enable_control_plane=True, background=True, log_level="info")
