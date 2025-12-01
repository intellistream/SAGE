#!/usr/bin/env python3
"""LLM service management commands for SAGE."""

from __future__ import annotations

import json
from typing import Any

import typer

from sage.common.config import ensure_hf_mirror_configured
from sage.common.model_registry import vllm_registry

try:  # Optional dependency: middleware is not required for every CLI install
    from sage.common.components.sage_llm import VLLMService
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
