#!/usr/bin/env python3
"""LLM service management commands for SAGE."""

import os
import subprocess
import time

import psutil
import typer

# Import config subcommands
from .llm_config import app as config_app

app = typer.Typer(help="🤖 LLM 服务管理")

# Add config subcommand
app.add_typer(config_app, name="config")


@app.command("start")
def start_llm_service(
    service: str = typer.Argument("vllm", help="要启动的服务类型 (默认: vllm)"),
    model: str = typer.Option(
        "microsoft/DialoGPT-small", "--model", "-m", help="要加载的模型名称"
    ),
    port: int = typer.Option(8000, "--port", "-p", help="服务监听端口"),
    auth_token: str = typer.Option(
        "token-abc123", "--auth-token", "-t", help="API认证token"
    ),
    gpu_memory_utilization: float = typer.Option(
        0.5, "--gpu-memory", help="GPU内存使用率 (0.1-1.0)"
    ),
    max_model_len: int = typer.Option(512, "--max-model-len", help="模型最大序列长度"),
    offline: bool = typer.Option(
        True, "--offline/--online", help="离线模式（不下载模型）"
    ),
    background: bool = typer.Option(False, "--background", "-b", help="后台运行服务"),
):
    """启动LLM服务"""

    if service.lower() != "vllm":
        typer.echo(f"❌ 暂不支持的服务类型: {service}")
        typer.echo("💡 当前支持的服务类型: vllm")
        raise typer.Exit(1)

    # Check if service is already running
    if _is_service_running(port):
        typer.echo(f"⚠️ 端口 {port} 已被占用，服务可能已在运行")
        if not typer.confirm("是否继续启动？"):
            raise typer.Exit(0)

    # Build vllm command
    cmd = [
        "vllm",
        "serve",
        model,
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
        # Set environment variables for offline mode
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

    typer.echo("🚀 启动vLLM服务...")
    typer.echo(f"   模型: {model}")
    typer.echo(f"   端口: {port}")
    typer.echo(f"   认证: {auth_token}")
    typer.echo(f"   GPU内存: {gpu_memory_utilization}")
    typer.echo(f"   离线模式: {offline}")

    try:
        if background:
            # Run in background
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            typer.echo(f"✅ vLLM服务已在后台启动 (PID: {process.pid})")
            typer.echo(f"🌐 服务地址: http://localhost:{port}")
            typer.echo("📋 使用 'sage llm status' 查看服务状态")
        else:
            # Run in foreground
            typer.echo("📝 按 Ctrl+C 停止服务")
            subprocess.run(cmd, env=env, check=True)

    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ 启动失败: {e}")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        typer.echo("\\n🛑 服务已停止")
        raise typer.Exit(0)


@app.command("stop")
def stop_llm_service(
    port: int = typer.Option(8000, "--port", "-p", help="要停止的服务端口"),
    force: bool = typer.Option(False, "--force", "-f", help="强制停止服务"),
):
    """停止LLM服务"""

    processes = _find_llm_processes(port)
    if not processes:
        typer.echo(f"❌ 未找到运行在端口 {port} 的LLM服务")
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
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            typer.echo(f"⚠️ 无法停止进程 {proc.pid}: {e}")

    if stopped_count > 0:
        typer.echo(f"✅ 成功停止 {stopped_count} 个进程")
    else:
        typer.echo("❌ 未能停止任何进程")


@app.command("status")
def llm_service_status(
    port: int = typer.Option(8000, "--port", "-p", help="要检查的服务端口"),
):
    """查看LLM服务状态"""

    # Check if port is in use
    if not _is_service_running(port):
        typer.echo(f"❌ 端口 {port} 未被占用")
        return

    # Find related processes
    processes = _find_llm_processes(port)

    typer.echo(f"🔍 LLM服务状态 (端口 {port}):")
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

    # Test API endpoint
    _test_api_endpoint(port)


def _is_service_running(port: int) -> bool:
    """检查指定端口是否被占用"""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        result = sock.connect_ex(("localhost", port))
        return result == 0


def _find_llm_processes(port: int) -> list:
    """查找与LLM服务相关的进程"""
    processes = []

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = proc.info["cmdline"]
            if not cmdline:
                continue

            cmdline_str = " ".join(cmdline).lower()

            # Look for vllm, ollama, or processes using the specific port
            if any(keyword in cmdline_str for keyword in ["vllm", "ollama"]):
                processes.append(proc)
            elif str(port) in cmdline_str and any(
                keyword in cmdline_str for keyword in ["serve", "server", "api"]
            ):
                processes.append(proc)

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return processes


def _test_api_endpoint(port: int):
    """测试API端点可用性"""
    import json
    import urllib.request

    try:
        # Test with common auth tokens
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

            except urllib.error.HTTPError as e:
                if e.code == 401:
                    continue  # Try next token
                else:
                    typer.echo(f"🌐 API状态: ❌ HTTP {e.code}")
                    return
            except Exception:
                continue

        typer.echo("🌐 API状态: ❌ 无法连接或需要认证")

    except Exception as e:
        typer.echo(f"🌐 API状态: ❌ 测试失败 ({e})")
