#!/usr/bin/env python3
"""LLM service management commands for SAGE."""

from __future__ import annotations

import json
import os
import subprocess
import time
from typing import Any

import psutil
import typer

from sage.common.model_registry import vllm_registry

try:  # Optional dependency: middleware is not required for every CLI install
    from sage.common.components.sage_vllm import VLLMService
except Exception:  # pragma: no cover - handled gracefully at runtime
    VLLMService = None  # type: ignore

# Import config subcommands
from sage.cli.commands.platform.llm_config import app as config_app

app = typer.Typer(help="🤖 LLM 服务管理")
model_app = typer.Typer(help="📦 模型管理")

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


@model_app.command("download")
def download_model(
    model: str = typer.Option(..., "--model", "-m", help="要下载的模型名称"),
    revision: str | None = typer.Option(None, "--revision", help="模型 revision"),
    force: bool = typer.Option(False, "--force", "-f", help="强制重新下载"),
    no_progress: bool = typer.Option(False, "--no-progress", help="隐藏下载进度"),
):
    """下载模型到本地缓存。"""

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
    model: str = typer.Option("meta-llama/Llama-3.1-8B-Instruct", "--model", "-m", help="生成模型"),
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
        typer.echo("❌ 当前环境未安装 isage-middleware[vllm]，无法加载内置服务。")
        typer.echo("   请运行 `pip install isage-middleware[vllm]` 后重试。")
        raise typer.Exit(1)

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
        typer.echo("❌ 当前环境未安装 isage-middleware[vllm]，无法调用 fine-tune 接口。")
        raise typer.Exit(1)

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
# Legacy process-based controls (kept for backwards compatibility)
# ---------------------------------------------------------------------------
@app.command("start")
def start_llm_service(
    service: str = typer.Argument("vllm", help="要启动的服务类型 (默认: vllm)"),
    model: str = typer.Option("microsoft/DialoGPT-small", "--model", "-m", help="要加载的模型名称"),
    port: int = typer.Option(8000, "--port", "-p", help="服务监听端口"),
    auth_token: str = typer.Option("token-abc123", "--auth-token", "-t", help="API认证token"),
    gpu_memory_utilization: float = typer.Option(
        0.5, "--gpu-memory", help="GPU内存使用率 (0.1-1.0)"
    ),
    max_model_len: int = typer.Option(512, "--max-model-len", help="模型最大序列长度"),
    offline: bool = typer.Option(True, "--offline/--online", help="离线模式（不下载模型）"),
    background: bool = typer.Option(False, "--background", "-b", help="后台运行服务"),
):
    """启动旧版进程模式 vLLM 服务。"""

    typer.echo(
        "⚠️ 该命令采用旧的进程方式启动 vLLM。推荐使用 'sage llm run' 获取阻塞式内置服务体验。"
    )

    if service.lower() != "vllm":
        typer.echo(f"❌ 暂不支持的服务类型: {service}")
        typer.echo("💡 当前支持的服务类型: vllm")
        raise typer.Exit(1)

    if _is_service_running(port):
        typer.echo(f"⚠️ 端口 {port} 已被占用，服务可能已在运行")
        if not typer.confirm("是否继续启动？"):
            raise typer.Exit(0)

    # Try to resolve model from SAGE registry first
    try:
        model_path = vllm_registry.get_model_path(model)
        typer.echo(f"📦 使用 SAGE 缓存的模型: {model_path}")
        model_to_use = str(model_path)
    except Exception:
        # If not found in registry, use the model ID as-is
        typer.echo(f"⚠️ 模型未在 SAGE 缓存中找到，尝试使用模型ID: {model}")
        model_to_use = model

    cmd = [
        "vllm",
        "serve",
        model_to_use,
        "--dtype",
        "auto",
        "--api-key",
        auth_token,
        "--port",
        str(port),
        "--gpu-memory-utilization",
        str(gpu_memory_utilization),
        "--max-model-len",
        str(max_model_len),
        "--max-num-batched-tokens",
        "1024",
        "--max-num-seqs",
        "16",
        "--enforce-eager",
        "--disable-log-stats",
    ]

    if offline:
        env = os.environ.copy()
        env.update(
            {
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "HF_DATASETS_OFFLINE": "1",
            }
        )
    else:
        env = None

    typer.echo("🚀 启动 vLLM 服务 (进程模式)...")

    try:
        if background:
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            typer.echo(f"✅ vLLM 服务已在后台启动 (PID: {process.pid})")
            typer.echo(f"🌐 服务地址: http://localhost:{port}")
            typer.echo("📋 使用 'sage llm status' 查看服务状态")
        else:
            typer.echo("📝 按 Ctrl+C 停止服务")
            subprocess.run(cmd, env=env, check=True)

    except subprocess.CalledProcessError as exc:
        typer.echo(f"❌ 启动失败: {exc}")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        typer.echo("\n🛑 服务已停止")
        raise typer.Exit(0)


@app.command("stop")
def stop_llm_service(
    port: int = typer.Option(8000, "--port", "-p", help="要停止的服务端口"),
    force: bool = typer.Option(False, "--force", "-f", help="强制停止服务"),
):
    """停止旧版进程模式的 vLLM 服务。"""

    processes = _find_llm_processes(port)
    if not processes:
        typer.echo(f"❌ 未找到运行在端口 {port} 的 vLLM 进程")
        raise typer.Exit(1)

    typer.echo(f"🔍 找到 {len(processes)} 个相关进程:")
    for proc in processes:
        try:
            typer.echo(f"  PID {proc.pid}: {' '.join(proc.cmdline())}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not force and not typer.confirm("确认停止这些进程？"):
        raise typer.Exit(0)

    stopped_count = 0
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
            stopped_count += 1
            typer.echo(f"✅ 已停止进程 {proc.pid}")
        except psutil.TimeoutExpired:
            proc.kill()
            stopped_count += 1
            typer.echo(f"🔥 强制终止进程 {proc.pid}")
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            typer.echo(f"⚠️ 无法停止进程 {proc.pid}: {exc}")

    if stopped_count > 0:
        typer.echo(f"✅ 成功停止 {stopped_count} 个进程")
    else:
        typer.echo("❌ 未能停止任何进程")


@app.command("status")
def llm_service_status(
    port: int = typer.Option(8000, "--port", "-p", help="要检查的服务端口"),
):
    """查看旧版进程模式 vLLM 服务状态。"""

    if not _is_service_running(port):
        typer.echo(f"❌ 端口 {port} 未被占用")
        typer.echo("ℹ️ 如果您使用的是 'sage llm run'，请在命令窗口中查看实时输出。")
        return

    processes = _find_llm_processes(port)

    typer.echo(f"🔍 LLM 服务状态 (端口 {port}):")
    typer.echo("📡 端口状态: ✅ 活跃")

    if processes:
        typer.echo(f"🔧 相关进程 ({len(processes)} 个):")
        for proc in processes:
            try:
                with proc.oneshot():
                    memory_info = proc.memory_info()
                    cpu_percent = proc.cpu_percent()
                    create_time = time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(proc.create_time())
                    )

                    typer.echo(f"  PID {proc.pid}:")
                    typer.echo(f"    命令: {' '.join(proc.cmdline()[:3])}...")
                    typer.echo(f"    内存: {memory_info.rss / 1024 / 1024:.1f} MB")
                    typer.echo(f"    CPU: {cpu_percent:.1f}%")
                    typer.echo(f"    启动时间: {create_time}")
                    typer.echo()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                typer.echo(f"  PID {proc.pid}: 无法获取详细信息")

    _test_api_endpoint(port)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _is_service_running(port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        result = sock.connect_ex(("localhost", port))
        return result == 0


def _find_llm_processes(port: int) -> list[psutil.Process]:
    processes: list[psutil.Process] = []

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline")
            if not cmdline:
                continue

            cmdline_str = " ".join(cmdline).lower()
            if any(keyword in cmdline_str for keyword in ["vllm", "ollama"]):
                processes.append(proc)
            elif str(port) in cmdline_str and any(
                keyword in cmdline_str for keyword in ["serve", "server", "api"]
            ):
                processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return processes


def _test_api_endpoint(port: int) -> None:
    import urllib.error
    import urllib.request

    try:
        for token in [None, "token-abc123"]:
            try:
                req = urllib.request.Request(f"http://localhost:{port}/v1/models")
                if token:
                    req.add_header("Authorization", f"Bearer {token}")

                with urllib.request.urlopen(req, timeout=3) as response:
                    data = json.loads(response.read().decode())
                    models = [item.get("id") for item in data.get("data", [])]

                    typer.echo("🌐 API状态: ✅ 可用")
                    if models:
                        typer.echo(f"📚 可用模型: {', '.join(models)}")
                    if token:
                        typer.echo(f"🔐 认证token: {token}")
                    return

            except urllib.error.HTTPError as exc:
                if exc.code == 401:
                    continue
                typer.echo(f"🌐 API状态: ❌ HTTP {exc.code}")
                return
            except Exception:
                continue

        typer.echo("🌐 API状态: ❌ 无法连接或需要认证")

    except Exception as exc:  # pragma: no cover - network errors
        typer.echo(f"🌐 API状态: ❌ 测试失败 ({exc})")
