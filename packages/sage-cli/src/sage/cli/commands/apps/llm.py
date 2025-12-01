#!/usr/bin/env python3
"""LLM service management commands for SAGE.

All LLM services should be managed through sageLLM (LLMAPIServer),
NOT by directly calling vLLM entrypoints.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from sage.common.config import ensure_hf_mirror_configured
from sage.common.config.ports import SagePorts
from sage.common.model_registry import fetch_recommended_models, vllm_registry

try:  # Optional dependency: middleware is not required for every CLI install
    from sage.common.components.sage_llm import VLLMService
except Exception:  # pragma: no cover - handled gracefully at runtime
    VLLMService = None  # type: ignore

try:
    from sage.common.components.sage_llm import LLMAPIServer, LLMServerConfig
except Exception:  # pragma: no cover
    LLMAPIServer = None  # type: ignore
    LLMServerConfig = None  # type: ignore

# Import config subcommands
from sage.cli.commands.platform.llm_config import app as config_app

console = Console()
app = typer.Typer(help="🤖 LLM 服务管理")
model_app = typer.Typer(help="📦 模型管理")

# PID file for tracking background service
SAGE_DIR = Path.home() / ".sage"
LLM_PID_FILE = SAGE_DIR / "llm_service.pid"
LLM_CONFIG_FILE = SAGE_DIR / "llm_service_config.json"
LOG_DIR = SAGE_DIR / "logs"


def _ensure_dirs():
    """Ensure required directories exist."""
    SAGE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _save_service_info(pid: int, config: dict):
    """Save service PID and config for later management."""
    _ensure_dirs()
    LLM_PID_FILE.write_text(str(pid))
    LLM_CONFIG_FILE.write_text(json.dumps(config, indent=2))


def _load_service_info() -> tuple[int | None, dict | None]:
    """Load saved service info."""
    pid = None
    config = None
    if LLM_PID_FILE.exists():
        try:
            pid = int(LLM_PID_FILE.read_text().strip())
        except (ValueError, OSError):
            pass
    if LLM_CONFIG_FILE.exists():
        try:
            config = json.loads(LLM_CONFIG_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return pid, config


def _clear_service_info():
    """Clear saved service info."""
    LLM_PID_FILE.unlink(missing_ok=True)
    LLM_CONFIG_FILE.unlink(missing_ok=True)


# Add subcommands
app.add_typer(config_app, name="config")
app.add_typer(model_app, name="model")


# ---------------------------------------------------------------------------
# Model management commands
# ---------------------------------------------------------------------------
@model_app.command("show")
def show_models(json_output: bool = typer.Option(False, "--json", help="以 JSON 格式输出")):
    """列出本地缓存的模型。"""

    infos = vllm_registry.list_models()
    if json_output:
        payload = [
            {
                "model_id": info.model_id,
                "revision": info.revision,
                "path": str(info.path),
                "size_bytes": info.size_bytes,
                "size_mb": round(info.size_mb, 2),
                "last_used": info.last_used_iso,
                "tags": info.tags,
            }
            for info in infos
        ]
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if not infos:
        typer.echo(
            "📭 本地尚未缓存任何 vLLM 模型。使用 'sage llm model download --model <name>' 开始下载。"
        )
        return

    header = f"{'模型ID':48} {'Revision':12} {'Size(MB)':>10} {'Last Used':>20}"
    typer.echo(header)
    typer.echo("-" * len(header))
    for info in infos:
        typer.echo(
            f"{info.model_id[:48]:48} {str(info.revision or '-'):12} {info.size_mb:>10.2f} {info.last_used_iso or '-':>20}"
        )


@model_app.command("list-remote")
def list_remote_models(
    json_output: bool = typer.Option(False, "--json", help="以 JSON 格式输出"),
    timeout: float = typer.Option(5.0, "--timeout", help="远程请求超时时间 (秒)"),
):
    """展示官方推荐的常用模型列表（自动从 GitHub 拉取）。"""

    models = fetch_recommended_models(timeout=timeout)
    if not models:
        typer.echo("⚠️ 未能获取推荐模型列表。请稍后重试或检查网络。")
        return

    if json_output:
        typer.echo(json.dumps(models, ensure_ascii=False, indent=2))
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("模型ID", overflow="fold")
    table.add_column("显存需求", justify="center")
    table.add_column("标签", justify="center")
    table.add_column("简介", overflow="fold")

    for item in models:
        tags = ", ".join(item.get("tags", [])) or "-"
        memory = item.get("min_gpu_memory_gb")
        memory_str = f"{memory} GB" if memory else "-"
        table.add_row(
            item.get("model_id", "-"),
            memory_str,
            tags,
            item.get("description", ""),
        )

    console.print(table)
    typer.echo(
        "💡 如需添加新的推荐模型，请更新 packages/sage-common/src/sage/common/model_registry/recommended_llm_models.json，"
        "或设置 SAGE_LLM_MODEL_INDEX_URL 指向自定义 JSON。"
    )


@model_app.command("download")
def download_model(
    model: str = typer.Option(..., "--model", "-m", help="要下载的模型名称"),
    revision: str | None = typer.Option(None, "--revision", help="模型 revision"),
    force: bool = typer.Option(False, "--force", "-f", help="强制重新下载"),
    no_progress: bool = typer.Option(False, "--no-progress", help="隐藏下载进度"),
):
    """下载模型到本地缓存。"""

    # Auto-configure HuggingFace mirror for China mainland users
    ensure_hf_mirror_configured()

    try:
        info = vllm_registry.download_model(
            model,
            revision=revision,
            force=force,
            progress=not no_progress,
        )
    except Exception as exc:  # pragma: no cover - huggingface errors
        typer.echo(f"❌ 下载失败: {exc}")
        raise typer.Exit(1)

    typer.echo("✅ 下载完成")
    typer.echo(f"📁 路径: {info.path}")
    typer.echo(f"📦 大小: {info.size_mb:.2f} MB")


@model_app.command("delete")
def delete_model(
    model: str = typer.Option(..., "--model", "-m", help="要删除的模型名称"),
    assume_yes: bool = typer.Option(False, "--yes", "-y", help="无需确认直接删除"),
):
    """删除本地缓存的模型。"""

    if not assume_yes and not typer.confirm(f"确认删除本地模型 '{model}'?"):
        raise typer.Exit(0)

    try:
        vllm_registry.delete_model(model)
    except Exception as exc:  # pragma: no cover - filesystem errors
        typer.echo(f"⚠️ 删除失败: {exc}")
        raise typer.Exit(1)

    typer.echo(f"🗑️ 已删除模型 {model}")


# ---------------------------------------------------------------------------
# Blocking service runner & fine-tune stub
# ---------------------------------------------------------------------------
@app.command("run")
def run_vllm_service(
    model: str = typer.Option("Qwen/Qwen2.5-1.5B-Instruct", "--model", "-m", help="生成模型"),
    embedding_model: str | None = typer.Option(
        None, "--embedding-model", help="嵌入模型（默认同生成模型）"
    ),
    auto_download: bool = typer.Option(
        True, "--auto-download/--no-auto-download", help="缺失时自动下载模型"
    ),
    temperature: float = typer.Option(0.7, "--temperature", help="采样温度"),
    top_p: float = typer.Option(0.95, "--top-p", help="Top-p 采样"),
    max_tokens: int = typer.Option(512, "--max-tokens", help="最大生成 token 数"),
):
    """以阻塞模式运行 vLLM 服务，并提供交互式体验。"""

    if VLLMService is None:  # pragma: no cover - dependency guard
        typer.echo("❌ 当前环境未安装 isage-common[vllm]，无法加载内置服务。")
        typer.echo("   请运行 `pip install isage-common[vllm]` 后重试。")
        raise typer.Exit(1)

    # Auto-configure HuggingFace mirror for China mainland users
    ensure_hf_mirror_configured()

    config_dict: dict[str, Any] = {
        "model_id": model,
        "embedding_model_id": embedding_model,
        "auto_download": auto_download,
        "sampling": {
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
        },
    }

    service = VLLMService(config_dict)

    try:
        service.setup()
        typer.echo("✅ vLLM 服务已加载完成。输入空行退出，或 Ctrl+C 结束。")
        while True:
            prompt = typer.prompt("💬 Prompt", default="")
            if not prompt.strip():
                break
            outputs = service.generate(prompt)
            if not outputs:
                typer.echo("⚠️ 未获得生成结果。")
                continue
            choice = outputs[0]["generations"][0]
            typer.echo(f"🧠 {choice['text'].strip()}")
    except KeyboardInterrupt:
        typer.echo("\n🛑 已中断。")
    except Exception as exc:
        typer.echo(f"❌ 运行失败: {exc}")
        raise typer.Exit(1)
    finally:
        try:
            service.cleanup()
        except Exception:  # pragma: no cover - cleanup best-effort
            pass


@app.command("fine-tune")
def fine_tune_stub(
    base_model: str = typer.Option(..., "--base-model", help="基础模型名称"),
    dataset_path: str = typer.Option(..., "--dataset", help="训练数据路径"),
    output_dir: str = typer.Option(..., "--output", help="输出目录"),
    auto_download: bool = typer.Option(
        True, "--auto-download/--no-auto-download", help="自动确保基础模型就绪"
    ),
):
    """提交 fine-tune 请求（当前为占位实现）。"""

    if VLLMService is None:  # pragma: no cover - dependency guard
        typer.echo("❌ 当前环境未安装 isage-common[vllm]，无法调用 fine-tune 接口。")
        raise typer.Exit(1)

    # Auto-configure HuggingFace mirror for China mainland users
    ensure_hf_mirror_configured()

    service = VLLMService({"model_id": base_model, "auto_download": auto_download})
    try:
        try:
            service.fine_tune(
                {
                    "base_model": base_model,
                    "dataset_path": dataset_path,
                    "output_dir": output_dir,
                }
            )
        except NotImplementedError as exc:
            typer.echo(f"ℹ️ {exc}")
        else:
            typer.echo("✅ fine-tune 请求已提交")
    finally:
        service.cleanup()


# ---------------------------------------------------------------------------
# Service lifecycle commands (via sageLLM LLMAPIServer)
# ---------------------------------------------------------------------------
@app.command("serve")
def serve_llm(
    model: str = typer.Option(
        "Qwen/Qwen2.5-0.5B-Instruct",
        "--model",
        "-m",
        help="LLM 模型名称",
    ),
    port: int = typer.Option(
        SagePorts.BENCHMARK_LLM,
        "--port",
        "-p",
        help=f"服务端口 (默认: {SagePorts.BENCHMARK_LLM})",
    ),
    host: str = typer.Option(
        "0.0.0.0",
        "--host",
        help="服务主机地址",
    ),
    gpu_memory: float = typer.Option(
        0.9,
        "--gpu-memory",
        help="GPU 内存使用率 (0.1-1.0)",
    ),
    max_model_len: int = typer.Option(
        4096,
        "--max-model-len",
        help="最大模型序列长度",
    ),
    tensor_parallel: int = typer.Option(
        1,
        "--tensor-parallel",
        "-tp",
        help="Tensor 并行 GPU 数量",
    ),
    background: bool = typer.Option(
        True,
        "--background/--foreground",
        help="后台运行（默认）或前台运行",
    ),
    with_embedding: bool = typer.Option(
        False,
        "--with-embedding",
        help="同时启动 Embedding 服务",
    ),
    embedding_model: str = typer.Option(
        "BAAI/bge-small-zh-v1.5",
        "--embedding-model",
        "-e",
        help="Embedding 模型名称",
    ),
    embedding_port: int = typer.Option(
        SagePorts.EMBEDDING_DEFAULT,
        "--embedding-port",
        help=f"Embedding 服务端口 (默认: {SagePorts.EMBEDDING_DEFAULT})",
    ),
):
    """启动 LLM 推理服务（通过 sageLLM）。

    使用 sageLLM 的 LLMAPIServer 启动 OpenAI 兼容的 LLM 服务。
    默认后台运行，可通过 'sage llm stop' 停止。

    示例:
        sage llm serve                           # 使用默认小模型启动
        sage llm serve -m Qwen/Qwen2.5-7B-Instruct  # 指定模型
        sage llm serve --with-embedding          # 同时启动 Embedding 服务
        sage llm serve --foreground              # 前台运行（阻塞）

    启动后可通过以下方式使用:

        from sage.common.components.sage_llm import UnifiedInferenceClient

        client = UnifiedInferenceClient.create_auto()
        response = client.chat([{"role": "user", "content": "Hello"}])
    """
    if LLMAPIServer is None:
        console.print("[red]❌ LLMAPIServer 不可用，请确保已安装 sage-common[/red]")
        raise typer.Exit(1)

    # Auto-configure HuggingFace mirror for China mainland users
    ensure_hf_mirror_configured()
    _ensure_dirs()

    # Check if service already running
    import psutil

    pid, _ = _load_service_info()
    if pid and psutil.pid_exists(pid):
        console.print(f"[yellow]⚠️  LLM 服务已在运行中 (PID: {pid})[/yellow]")
        console.print("使用 'sage llm stop' 停止现有服务，或 'sage llm status' 查看状态")
        raise typer.Exit(1)

    # Create server config
    config = LLMServerConfig(
        model=model,
        backend="vllm",
        host=host,
        port=port,
        gpu_memory_utilization=gpu_memory,
        max_model_len=max_model_len,
        tensor_parallel_size=tensor_parallel,
    )

    console.print("[blue]🚀 启动 LLM 服务 (sageLLM)[/blue]")
    console.print(f"   模型: {model}")
    console.print(f"   端口: {port}")
    console.print(f"   模式: {'后台' if background else '前台'}")

    server = LLMAPIServer(config)

    if background:
        log_file = LOG_DIR / f"llm_api_server_{port}.log"
        success = server.start(background=True, log_file=log_file)

        if success:
            # Save service info for management
            _save_service_info(
                server.pid,
                {
                    "model": model,
                    "port": port,
                    "host": host,
                    "log_file": str(log_file),
                },
            )

            console.print("\n[green]✅ LLM 服务已启动[/green]")
            console.print(f"   PID: {server.pid}")
            console.print(f"   API: http://localhost:{port}/v1")
            console.print(f"   日志: {log_file}")
            console.print("\n[dim]使用 'sage llm status' 查看状态[/dim]")
            console.print("[dim]使用 'sage llm stop' 停止服务[/dim]")
        else:
            console.print("[red]❌ LLM 服务启动失败[/red]")
            console.print(f"[dim]请检查日志: {LOG_DIR / f'llm_api_server_{port}.log'}[/dim]")
            raise typer.Exit(1)
    else:
        # Foreground mode - blocking
        console.print("\n[yellow]前台模式运行中，按 Ctrl+C 停止...[/yellow]")
        try:
            server.start(background=False)
        except KeyboardInterrupt:
            console.print("\n[yellow]收到中断信号，正在停止...[/yellow]")
            server.stop()

    # Optionally start Embedding service
    if with_embedding:
        console.print("\n[blue]🎯 启动 Embedding 服务[/blue]")
        console.print(f"   模型: {embedding_model}")
        console.print(f"   端口: {embedding_port}")

        import subprocess
        import sys

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
            )

        console.print(f"   [green]✓[/green] Embedding 服务已启动 (PID: {proc.pid})")
        console.print(f"   日志: {embedding_log}")


@app.command("stop")
def stop_llm(
    force: bool = typer.Option(False, "--force", "-f", help="强制停止"),
):
    """停止 LLM 推理服务。"""
    import psutil

    pid, config = _load_service_info()

    if not pid:
        console.print("[dim]没有运行中的 LLM 服务[/dim]")
        return

    if not psutil.pid_exists(pid):
        console.print(f"[dim]服务进程 (PID: {pid}) 已不存在，清理记录...[/dim]")
        _clear_service_info()
        return

    console.print(f"[blue]🛑 停止 LLM 服务 (PID: {pid})...[/blue]")

    try:
        proc = psutil.Process(pid)
        # Terminate children first
        children = proc.children(recursive=True)
        for child in children:
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass

        proc.terminate()
        try:
            proc.wait(timeout=10)
            console.print("[green]✅ LLM 服务已停止[/green]")
        except psutil.TimeoutExpired:
            if force:
                proc.kill()
                console.print("[yellow]⚠️  LLM 服务已强制停止[/yellow]")
            else:
                console.print("[yellow]⚠️  服务停止超时，使用 --force 强制停止[/yellow]")
                return

        _clear_service_info()
    except psutil.NoSuchProcess:
        console.print("[dim]服务进程已不存在[/dim]")
        _clear_service_info()
    except Exception as exc:
        console.print(f"[red]❌ 停止服务失败: {exc}[/red]")
        raise typer.Exit(1)


@app.command("status")
def status_llm():
    """查看 LLM 服务状态。"""
    import socket

    import psutil

    pid, config = _load_service_info()

    table = Table(title="LLM 服务状态", show_header=True, header_style="bold")
    table.add_column("属性")
    table.add_column("值")

    # Check process status
    process_running = False
    if pid and psutil.pid_exists(pid):
        try:
            proc = psutil.Process(pid)
            process_running = proc.is_running()
        except psutil.NoSuchProcess:
            pass

    # Check port status
    port = config.get("port", SagePorts.BENCHMARK_LLM) if config else SagePorts.BENCHMARK_LLM
    port_in_use = False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        port_in_use = sock.connect_ex(("localhost", port)) == 0

    # Determine overall status
    if process_running and port_in_use:
        status = "[green]运行中[/green]"
    elif port_in_use:
        status = "[yellow]端口被占用 (外部进程)[/yellow]"
    else:
        status = "[red]已停止[/red]"

    table.add_row("状态", status)
    table.add_row("PID", str(pid) if pid else "-")
    table.add_row("端口", str(port))

    if config:
        table.add_row("模型", config.get("model", "-"))
        table.add_row("日志", config.get("log_file", "-"))
        table.add_row("API 端点", f"http://localhost:{port}/v1")

    console.print(table)

    # Health check if running
    if port_in_use:
        try:
            import httpx

            resp = httpx.get(f"http://localhost:{port}/v1/models", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("data", [])
                if models:
                    console.print("\n[green]✓[/green] 健康检查通过")
                    console.print(f"  加载的模型: {models[0].get('id', 'unknown')}")
        except Exception as e:
            console.print(f"\n[yellow]⚠️  健康检查失败: {e}[/yellow]")


@app.command("logs")
def view_logs(
    follow: bool = typer.Option(False, "--follow", "-f", help="实时跟踪日志"),
    lines: int = typer.Option(50, "--lines", "-n", help="显示最后 N 行"),
):
    """查看 LLM 服务日志。"""
    import os

    _, config = _load_service_info()

    if config and config.get("log_file"):
        log_file = Path(config["log_file"])
    else:
        # Try default log file
        log_file = LOG_DIR / f"llm_api_server_{SagePorts.BENCHMARK_LLM}.log"

    if not log_file.exists():
        console.print(f"[yellow]日志文件不存在: {log_file}[/yellow]")
        return

    console.print(f"[blue]📄 日志文件: {log_file}[/blue]\n")

    if follow:
        import shlex

        os.system(f"tail -f {shlex.quote(str(log_file))}")
    else:
        try:
            content = log_file.read_text()
            log_lines = content.strip().split("\n")
            for line in log_lines[-lines:]:
                console.print(line)
        except Exception as e:
            console.print(f"[red]无法读取日志: {e}[/red]")
