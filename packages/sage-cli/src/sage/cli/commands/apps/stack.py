#!/usr/bin/env python3
"""Service stack management commands for SAGE.

Provides one-command startup for the complete sageLLM inference stack:
- LLM service (vLLM)
- Embedding service

Commands:
    - start: Start the complete inference stack (LLM + Embedding)
    - stop: Stop all stack services
    - status: Check status of all services

Example:
    sage apps stack start  # Start LLM + Embedding services
    sage apps stack status # Check running services
    sage apps stack stop   # Stop all services
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import psutil
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from sage.common.config.ports import SagePorts

console = Console()
app = typer.Typer(help="🚀 服务栈管理 - 一键启动 LLM + Embedding 服务")

# PID files location
SAGE_DIR = Path.home() / ".sage"
LLM_PID_FILE = SAGE_DIR / "llm_service.pid"
EMBEDDING_PID_FILE = SAGE_DIR / "embedding_service.pid"
LOG_DIR = SAGE_DIR / "logs"


def _ensure_dirs():
    """Ensure required directories exist."""
    SAGE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _is_port_in_use(port: int) -> bool:
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        result = sock.connect_ex(("localhost", port))
        return result == 0


def _wait_for_port(port: int, timeout: int = 60, service_name: str = "service") -> bool:
    """Wait for a port to become available."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if _is_port_in_use(port):
            return True
        console.print(f"  [dim]等待 {service_name} 启动中...[/dim]", end="\r")
        time.sleep(2)
    return False


def _get_pid_from_file(pid_file: Path) -> int | None:
    """Get PID from file if process is still running."""
    if not pid_file.exists():
        return None
    try:
        pid = int(pid_file.read_text().strip())
        if psutil.pid_exists(pid):
            return pid
    except (ValueError, OSError):
        pass
    return None


def _save_pid(pid_file: Path, pid: int):
    """Save PID to file."""
    pid_file.write_text(str(pid))


def _stop_service(pid_file: Path, service_name: str) -> bool:
    """Stop a service by PID file."""
    pid = _get_pid_from_file(pid_file)
    if not pid:
        return False

    try:
        proc = psutil.Process(pid)
        # Terminate child processes first
        children = proc.children(recursive=True)
        for child in children:
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass

        proc.terminate()
        proc.wait(timeout=10)
        pid_file.unlink(missing_ok=True)
        console.print(f"  [green]✓[/green] {service_name} 已停止 (PID: {pid})")
        return True
    except psutil.NoSuchProcess:
        pid_file.unlink(missing_ok=True)
        return False
    except psutil.TimeoutExpired:
        # Force kill
        try:
            os.kill(pid, signal.SIGKILL)
            pid_file.unlink(missing_ok=True)
            console.print(f"  [yellow]⚠[/yellow] {service_name} 已强制停止 (PID: {pid})")
            return True
        except OSError:
            return False


@app.command("start")
def start_stack(
    llm_model: str = typer.Option(
        "Qwen/Qwen2.5-0.5B-Instruct",
        "--llm-model",
        "-l",
        help="LLM 模型名称",
    ),
    embedding_model: str = typer.Option(
        "BAAI/bge-small-zh-v1.5",
        "--embedding-model",
        "-e",
        help="Embedding 模型名称",
    ),
    llm_port: int = typer.Option(
        SagePorts.BENCHMARK_LLM,
        "--llm-port",
        help=f"LLM 服务端口 (默认: {SagePorts.BENCHMARK_LLM})",
    ),
    embedding_port: int = typer.Option(
        SagePorts.EMBEDDING_DEFAULT,
        "--embedding-port",
        help=f"Embedding 服务端口 (默认: {SagePorts.EMBEDDING_DEFAULT})",
    ),
    gpu_memory: float = typer.Option(
        0.5,
        "--gpu-memory",
        help="vLLM GPU 内存使用率 (0.1-1.0)",
    ),
    skip_llm: bool = typer.Option(
        False,
        "--skip-llm",
        help="跳过 LLM 服务启动（如果已手动启动）",
    ),
    skip_embedding: bool = typer.Option(
        False,
        "--skip-embedding",
        help="跳过 Embedding 服务启动",
    ),
    wait: bool = typer.Option(
        True,
        "--wait/--no-wait",
        help="等待服务完全启动",
    ),
):
    """一键启动完整推理服务栈（LLM + Embedding）。

    该命令会启动：
    1. vLLM 服务 - 用于 chat/generate 请求
    2. Embedding 服务 - 用于文本向量化

    启动后可通过 UnifiedInferenceClient 统一访问：

    \b
    from sage.common.components.sage_llm import UnifiedInferenceClient

    client = UnifiedInferenceClient.create_with_control_plane(
        llm_base_url="http://localhost:8901/v1",
        embedding_base_url="http://localhost:8090/v1",
    )

    # LLM
    response = client.chat([{"role": "user", "content": "Hello"}])

    # Embedding
    vectors = client.embed(["text1", "text2"])

    示例：
        # 使用默认模型启动
        sage apps stack start

        # 指定模型
        sage apps stack start -l Qwen/Qwen2.5-7B-Instruct -e BAAI/bge-m3

        # 只启动 Embedding（LLM 已手动启动）
        sage apps stack start --skip-llm

    """
    _ensure_dirs()

    console.print(
        Panel.fit(
            "[bold blue]🚀 SAGE 推理服务栈[/bold blue]\n"
            f"LLM: {llm_model} @ :{llm_port}\n"
            f"Embedding: {embedding_model} @ :{embedding_port}",
            title="启动配置",
        )
    )

    services_started = []

    # 1. Start LLM service (vLLM)
    if not skip_llm:
        if _is_port_in_use(llm_port):
            console.print(f"[yellow]⚠[/yellow] LLM 端口 {llm_port} 已被占用，跳过启动")
        else:
            console.print("\n[blue]1/2[/blue] 启动 LLM 服务 (vLLM)...")

            llm_log = LOG_DIR / "vllm.log"
            llm_cmd = [
                sys.executable,
                "-m",
                "vllm.entrypoints.openai.api_server",
                "--model",
                llm_model,
                "--port",
                str(llm_port),
                "--gpu-memory-utilization",
                str(gpu_memory),
                "--max-model-len",
                "4096",
                "--enforce-eager",
                "--disable-log-stats",
                "--trust-remote-code",
            ]

            with open(llm_log, "w") as log_file:
                proc = subprocess.Popen(
                    llm_cmd,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    env={**os.environ, "TOKENIZERS_PARALLELISM": "false"},
                )

            _save_pid(LLM_PID_FILE, proc.pid)
            console.print(f"  [green]✓[/green] vLLM 进程已启动 (PID: {proc.pid})")
            console.print(f"  [dim]日志: {llm_log}[/dim]")

            if wait:
                console.print(f"  等待 vLLM 服务就绪 (端口 {llm_port})...")
                if _wait_for_port(llm_port, timeout=120, service_name="vLLM"):
                    console.print("  [green]✓[/green] vLLM 服务已就绪")
                    services_started.append(("LLM (vLLM)", llm_port))
                else:
                    console.print(f"  [yellow]⚠[/yellow] vLLM 启动超时，请检查日志: {llm_log}")
            else:
                services_started.append(("LLM (vLLM)", llm_port))
    else:
        console.print("[dim]跳过 LLM 服务启动[/dim]")

    # 2. Start Embedding service
    if not skip_embedding:
        if _is_port_in_use(embedding_port):
            console.print(f"[yellow]⚠[/yellow] Embedding 端口 {embedding_port} 已被占用，跳过启动")
        else:
            console.print("\n[blue]2/2[/blue] 启动 Embedding 服务...")

            embedding_log = LOG_DIR / "embedding.log"
            embedding_cmd = [
                sys.executable,
                "-m",
                "sage.common.components.sage_embedding.embedding_server",
                "--model",
                embedding_model,
                "--port",
                str(embedding_port),
            ]

            with open(embedding_log, "w") as log_file:
                proc = subprocess.Popen(
                    embedding_cmd,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    env={**os.environ, "TOKENIZERS_PARALLELISM": "false"},
                )

            _save_pid(EMBEDDING_PID_FILE, proc.pid)
            console.print(f"  [green]✓[/green] Embedding 进程已启动 (PID: {proc.pid})")
            console.print(f"  [dim]日志: {embedding_log}[/dim]")

            if wait:
                console.print(f"  等待 Embedding 服务就绪 (端口 {embedding_port})...")
                if _wait_for_port(embedding_port, timeout=60, service_name="Embedding"):
                    console.print("  [green]✓[/green] Embedding 服务已就绪")
                    services_started.append(("Embedding", embedding_port))
                else:
                    console.print(
                        f"  [yellow]⚠[/yellow] Embedding 启动超时，请检查日志: {embedding_log}"
                    )
            else:
                services_started.append(("Embedding", embedding_port))
    else:
        console.print("[dim]跳过 Embedding 服务启动[/dim]")

    # Summary
    if services_started:
        console.print("\n" + "=" * 50)
        console.print("[bold green]✅ 服务栈启动完成[/bold green]\n")

        table = Table(show_header=True, header_style="bold")
        table.add_column("服务")
        table.add_column("端口")
        table.add_column("API 端点")

        for svc_name, svc_port in services_started:
            table.add_row(svc_name, str(svc_port), f"http://localhost:{svc_port}/v1")

        console.print(table)

        console.print("\n[bold]使用示例:[/bold]")
        example_code = f"""
[dim]from sage.common.components.sage_llm import UnifiedInferenceClient

client = UnifiedInferenceClient.create_with_control_plane(
    llm_base_url="http://localhost:{llm_port}/v1",
    embedding_base_url="http://localhost:{embedding_port}/v1",
)

# Chat
response = client.chat([{{"role": "user", "content": "Hello"}}])
print(response)

# Embedding
vectors = client.embed(["Hello world"])
print(f"Embedding dim: {{len(vectors[0])}}")
[/dim]"""
        console.print(example_code)

        console.print("\n[dim]使用 'sage apps stack status' 查看状态[/dim]")
        console.print("[dim]使用 'sage apps stack stop' 停止服务[/dim]")
    else:
        console.print("\n[yellow]⚠ 没有新服务被启动[/yellow]")


@app.command("stop")
def stop_stack(
    force: bool = typer.Option(False, "--force", "-f", help="强制停止所有进程"),
):
    """停止所有服务栈中的服务。"""
    console.print("[blue]🛑 停止服务栈...[/blue]\n")

    stopped_any = False

    # Stop LLM service
    console.print("[bold]LLM 服务:[/bold]")
    if _stop_service(LLM_PID_FILE, "vLLM"):
        stopped_any = True
    else:
        # Try to find and kill vllm processes
        if force:
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    cmdline = proc.info.get("cmdline") or []
                    if any("vllm" in str(c) for c in cmdline):
                        proc.terminate()
                        console.print(f"  [yellow]⚠[/yellow] 终止 vLLM 进程 (PID: {proc.pid})")
                        stopped_any = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        else:
            console.print("  [dim]无运行中的 LLM 服务[/dim]")

    # Stop Embedding service
    console.print("\n[bold]Embedding 服务:[/bold]")
    if _stop_service(EMBEDDING_PID_FILE, "Embedding"):
        stopped_any = True
    else:
        # Try to find and kill embedding processes
        if force:
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    cmdline = proc.info.get("cmdline") or []
                    if any("embedding_server" in str(c) for c in cmdline):
                        proc.terminate()
                        console.print(f"  [yellow]⚠[/yellow] 终止 Embedding 进程 (PID: {proc.pid})")
                        stopped_any = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        else:
            console.print("  [dim]无运行中的 Embedding 服务[/dim]")

    if stopped_any:
        console.print("\n[green]✅ 服务已停止[/green]")
    else:
        console.print("\n[dim]没有需要停止的服务[/dim]")


@app.command("status")
def status_stack():
    """查看服务栈状态。"""
    console.print("[blue]📊 服务栈状态[/blue]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("服务")
    table.add_column("状态")
    table.add_column("PID")
    table.add_column("端口")
    table.add_column("API 端点")

    # Check LLM service
    llm_pid = _get_pid_from_file(LLM_PID_FILE)
    llm_port = SagePorts.BENCHMARK_LLM
    llm_running = llm_pid is not None or _is_port_in_use(llm_port)

    if llm_running:
        table.add_row(
            "LLM (vLLM)",
            "[green]运行中[/green]",
            str(llm_pid or "外部"),
            str(llm_port),
            f"http://localhost:{llm_port}/v1",
        )
    else:
        table.add_row("LLM (vLLM)", "[red]已停止[/red]", "-", str(llm_port), "-")

    # Check Embedding service
    emb_pid = _get_pid_from_file(EMBEDDING_PID_FILE)
    emb_port = SagePorts.EMBEDDING_DEFAULT
    emb_running = emb_pid is not None or _is_port_in_use(emb_port)

    if emb_running:
        table.add_row(
            "Embedding",
            "[green]运行中[/green]",
            str(emb_pid or "外部"),
            str(emb_port),
            f"http://localhost:{emb_port}/v1",
        )
    else:
        table.add_row("Embedding", "[red]已停止[/red]", "-", str(emb_port), "-")

    console.print(table)

    # Quick test if services are responding
    if llm_running or emb_running:
        console.print("\n[bold]快速测试:[/bold]")

        if llm_running:
            try:
                import httpx

                resp = httpx.get(f"http://localhost:{llm_port}/v1/models", timeout=5)
                if resp.status_code == 200:
                    models = resp.json().get("data", [])
                    if models:
                        console.print(f"  [green]✓[/green] LLM: {models[0].get('id', 'unknown')}")
                else:
                    console.print(f"  [yellow]⚠[/yellow] LLM: 响应异常 ({resp.status_code})")
            except Exception as e:
                console.print(f"  [red]✗[/red] LLM: 连接失败 ({e})")

        if emb_running:
            try:
                import httpx

                resp = httpx.get(f"http://localhost:{emb_port}/v1/models", timeout=5)
                if resp.status_code == 200:
                    models = resp.json().get("data", [])
                    if models:
                        console.print(
                            f"  [green]✓[/green] Embedding: {models[0].get('id', 'unknown')}"
                        )
                else:
                    console.print(f"  [yellow]⚠[/yellow] Embedding: 响应异常 ({resp.status_code})")
            except Exception as e:
                console.print(f"  [red]✗[/red] Embedding: 连接失败 ({e})")


@app.command("logs")
def view_logs(
    service: str = typer.Argument("all", help="服务名称 (llm/embedding/all)"),
    follow: bool = typer.Option(False, "--follow", "-f", help="实时跟踪日志"),
    lines: int = typer.Option(50, "--lines", "-n", help="显示最后 N 行"),
):
    """查看服务日志。"""
    log_files = []

    if service in ("all", "llm"):
        llm_log = LOG_DIR / "vllm.log"
        if llm_log.exists():
            log_files.append(("LLM", llm_log))

    if service in ("all", "embedding"):
        emb_log = LOG_DIR / "embedding.log"
        if emb_log.exists():
            log_files.append(("Embedding", emb_log))

    if not log_files:
        console.print("[yellow]没有找到日志文件[/yellow]")
        raise typer.Exit(0)

    if follow:
        # Use tail -f for live following
        import shlex

        files = " ".join(shlex.quote(str(f[1])) for f in log_files)
        os.system(f"tail -f {files}")
    else:
        for name, log_file in log_files:
            console.print(f"\n[bold blue]{'=' * 20} {name} {'=' * 20}[/bold blue]")
            try:
                content = log_file.read_text()
                log_lines = content.strip().split("\n")
                for line in log_lines[-lines:]:
                    console.print(line)
            except Exception as e:
                console.print(f"[red]无法读取日志: {e}[/red]")


if __name__ == "__main__":
    app()
