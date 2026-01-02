#!/usr/bin/env python3
"""LLM service management commands for SAGE.

All LLM services should be managed through sageLLM (LLMAPIServer),
NOT by directly calling vLLM entrypoints.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import typer
import yaml
from rich.console import Console
from rich.table import Table

from sage.common.config import ensure_hf_mirror_configured
from sage.common.config.ports import SagePorts
from sage.common.model_registry import fetch_recommended_models, vllm_registry
from sage.llm.presets import (
    EnginePreset,
    get_builtin_preset,
    list_builtin_presets,
    load_preset_file,
)

try:  # Optional dependency: middleware is not required for every CLI install
    from sage.llm import VLLMService
except Exception:  # pragma: no cover - handled gracefully at runtime
    VLLMService = None  # type: ignore

try:
    from sage.llm import (
        LLMAPIServer,
        LLMLauncher,
        LLMServerConfig,
    )
except Exception:  # pragma: no cover
    LLMAPIServer = None  # type: ignore
    LLMLauncher = None  # type: ignore
    LLMServerConfig = None  # type: ignore

try:
    from sage.llm import (
        BackendInstanceConfig,
        UnifiedAPIServer,
        UnifiedServerConfig,
    )
except Exception:  # pragma: no cover
    UnifiedAPIServer = None  # type: ignore
    UnifiedServerConfig = None  # type: ignore
    BackendInstanceConfig = None  # type: ignore

# Import config subcommands
from sage.cli.commands.platform.llm_config import app as config_app

console = Console()
app = typer.Typer(help="🤖 LLM 服务管理")
model_app = typer.Typer(help="📦 模型管理")
engine_app = typer.Typer(help="⚙️ 引擎管理")
preset_app = typer.Typer(help="🎛️ 预设编排")

# PID file for tracking background service
SAGE_DIR = Path.home() / ".sage"
LOG_DIR = SAGE_DIR / "logs"


def _ensure_dirs():
    """Ensure required directories exist."""
    SAGE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_api_base(api_base: str | None, port: int | None) -> str:
    """Return the control plane base URL (including /v1)."""
    if api_base:
        return api_base.rstrip("/")
    target_port = port or SagePorts.GATEWAY_DEFAULT
    return f"http://localhost:{target_port}/v1"


def _print_management_api_hint(api_base: str) -> None:
    """Provide guidance when the management API cannot be reached."""

    parsed = urlparse(api_base)
    host = parsed.hostname or "localhost"
    port = parsed.port or SagePorts.GATEWAY_DEFAULT

    console.print(
        "[yellow]💡 控制平面管理 API 未运行或不可达。[/yellow]",
    )
    console.print(
        "   请先启动 Unified API Server（gateway），例如运行 [cyan]sage llm serve[/cyan]",
    )
    console.print(
        f"   默认管理地址: http://{host}:{port}/v1，可用 --api-port 或 --api-base 自行覆盖。",
    )


def _extract_error_detail(resp: httpx.Response) -> str:
    try:
        payload = resp.json()
    except ValueError:
        return resp.text.strip() or resp.reason_phrase

    if isinstance(payload, dict):
        for key in ("detail", "message", "error"):
            if key in payload:
                value = payload[key]
                if isinstance(value, (dict, list)):
                    return json.dumps(value, ensure_ascii=False)
                return str(value)
        return json.dumps(payload, ensure_ascii=False)
    return str(payload)


def _management_request(
    method: str,
    endpoint: str,
    *,
    api_base: str,
    timeout: float,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    endpoint_path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
    url = f"{api_base.rstrip('/')}{endpoint_path}"

    request_kwargs: dict[str, Any] = {"timeout": timeout}
    if payload is not None:
        request_kwargs["json"] = payload

    try:
        response = httpx.request(method, url, **request_kwargs)
    except httpx.RequestError as exc:
        console.print(f"[red]❌ 无法连接到管理 API: {exc}[/red]")
        _print_management_api_hint(api_base)
        raise typer.Exit(1) from exc

    if response.status_code >= 400:
        detail = _extract_error_detail(response)
        console.print(f"[red]❌ 管理 API 请求失败 ({response.status_code}): {detail}[/red]")
        raise typer.Exit(1)

    if not response.content:
        return {}

    try:
        return response.json()
    except ValueError as exc:  # pragma: no cover - defensive
        console.print(f"[red]❌ 无法解析服务响应: {exc}[/red]")
        raise typer.Exit(1)


def _load_preset_source(name: str | None, file_path: Path | None) -> EnginePreset:
    """Resolve preset definition from builtin registry or local file."""

    if file_path is not None:
        return load_preset_file(file_path)
    if name:
        preset = get_builtin_preset(name)
        if preset is None:
            console.print(f"[red]未知预设 '{name}'。使用 'sage llm preset list' 查看可用项。[/red]")
            raise typer.Exit(1)
        return preset
    console.print("[red]请指定预设名称或 --file。[/red]")
    raise typer.Exit(1)


def _print_preset_plan(preset: EnginePreset) -> None:
    table = Table(show_header=True, header_style="bold", title=f"预设: {preset.name}")
    table.add_column("序号", justify="center")
    table.add_column("名称", overflow="fold")
    table.add_column("类型", justify="center")
    table.add_column("模型", overflow="fold")
    table.add_column("TP/PP", justify="center")
    table.add_column("端口", justify="center")
    table.add_column("标签", overflow="fold")
    for idx, engine in enumerate(preset.engines, start=1):
        table.add_row(
            str(idx),
            engine.name,
            engine.kind,
            engine.model,
            f"{engine.tensor_parallel}/{engine.pipeline_parallel}",
            str(engine.port or "auto"),
            engine.label or "-",
        )
    console.print(table)


def _fetch_cluster_status(api_base: str, timeout: float) -> dict[str, Any]:
    return _management_request(
        "GET",
        "/management/status",
        api_base=api_base,
        timeout=timeout,
    )


def _ensure_dict_list(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [item for item in data.values() if isinstance(item, dict)]
    return []


def _normalize_memory_gb(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None

    if numeric > 1_000_000:  # assume bytes
        return numeric / (1024**3)
    return numeric


def _format_memory_gb(value: Any) -> str:
    amount = _normalize_memory_gb(value)
    if amount is None:
        return "-"
    return f"{amount:.1f} GB"


def _format_uptime(value: Any) -> str:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return "-"

    if seconds < 60:
        return f"{int(seconds)}s"

    minutes, remaining = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m{remaining:02d}s"

    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m"


# Add subcommands
app.add_typer(config_app, name="config")
app.add_typer(model_app, name="model")
app.add_typer(engine_app, name="engine")
app.add_typer(preset_app, name="preset")


# ---------------------------------------------------------------------------
# Preset orchestration commands
# ---------------------------------------------------------------------------
@preset_app.command("list")
def list_presets(json_output: bool = typer.Option(False, "--json", help="JSON 输出")):
    """列出内置预设。"""

    presets = list_builtin_presets()
    if not presets:
        console.print("[yellow]当前没有定义任何内置预设。[/yellow]")
        return

    if json_output:
        typer.echo(
            json.dumps([preset.to_dict() for preset in presets], ensure_ascii=False, indent=2)
        )
        return

    table = Table(show_header=True, header_style="bold", title="LLM 预设列表")
    table.add_column("名称", overflow="fold")
    table.add_column("描述", overflow="fold")
    table.add_column("引擎数量", justify="center")

    for preset in presets:
        table.add_row(
            preset.name,
            preset.description or "-",
            str(len(preset.engines)),
        )

    console.print(table)


@preset_app.command("show")
def show_preset(
    name: str | None = typer.Option(None, "--name", "-n", help="预设名称"),
    file: Path | None = typer.Option(None, "--file", "-f", help="自定义预设文件"),
    json_output: bool = typer.Option(False, "--json", help="以 JSON 输出"),
):
    """展示预设详情。"""

    preset = _load_preset_source(name, file)
    data = preset.to_dict()
    if json_output:
        typer.echo(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        typer.echo(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def _rollback_engines(engine_ids: list[str], api_base: str, timeout: float) -> None:
    for engine_id in engine_ids:
        try:
            _management_request(
                "DELETE",
                f"/management/engines/{engine_id}",
                api_base=api_base,
                timeout=timeout,
            )
            console.print(f"[yellow]↩️ 已回滚引擎 {engine_id}[/yellow]")
        except typer.Exit:
            console.print(f"[red]⚠️ 回滚 {engine_id} 失败[/red]")


@preset_app.command("apply")
def apply_preset(
    name: str | None = typer.Option(None, "--name", "-n", help="预设名称"),
    file: Path | None = typer.Option(None, "--file", "-f", help="自定义预设文件"),
    api_port: int = typer.Option(
        SagePorts.GATEWAY_DEFAULT,
        "--api-port",
        help=f"控制平面端口 (默认 {SagePorts.GATEWAY_DEFAULT})",
    ),
    api_base: str | None = typer.Option(None, "--api-base", help="覆盖控制平面 API 基地址"),
    timeout: float = typer.Option(5.0, "--timeout", help="HTTP 超时时间 (秒)"),
    assume_yes: bool = typer.Option(False, "--yes", "-y", help="无需确认直接执行"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅展示计划，不执行"),
    no_rollback: bool = typer.Option(False, "--no-rollback", help="失败时不回滚已启动的引擎"),
):
    """根据预设启动一组引擎。"""

    preset = _load_preset_source(name, file)
    _print_preset_plan(preset)

    if dry_run:
        console.print("[blue]🔍 Dry-run 模式，仅展示计划。[/blue]")
        return

    if not assume_yes and not typer.confirm("确认按照以上计划启动引擎?", default=True):
        typer.echo("已取消。")
        return

    base_url = _resolve_api_base(api_base, api_port)
    started_ids: list[str] = []
    results: list[dict[str, Any]] = []
    rollback_enabled = not no_rollback

    for engine in preset.engines:
        console.print(f"[cyan]🚀 启动 {engine.name} ({engine.kind}) -> {engine.model}[/cyan]")
        payload = engine.to_payload()
        try:
            response = _management_request(
                "POST",
                "/management/engines",
                api_base=base_url,
                timeout=timeout,
                payload=payload,
            )
        except typer.Exit as exc:
            if rollback_enabled and started_ids:
                console.print("[yellow]⚠️ 启动失败，执行回滚...[/yellow]")
                _rollback_engines(started_ids, base_url, timeout)
            raise exc

        engine_id = response.get("engine_id") or response.get("id")
        if engine_id:
            started_ids.append(engine_id)
        results.append(
            {
                "engine_id": engine_id or "(pending)",
                "model": response.get("model_id") or engine.model,
                "port": response.get("port") or payload.get("port") or "auto",
                "status": response.get("status") or "STARTING",
                "kind": response.get("engine_kind") or engine.kind,
            }
        )

    table = Table(show_header=True, header_style="bold", title="启动结果")
    table.add_column("Engine ID", overflow="fold")
    table.add_column("类型", justify="center")
    table.add_column("模型", overflow="fold")
    table.add_column("端口", justify="center")
    table.add_column("状态", justify="center")

    for item in results:
        table.add_row(
            item["engine_id"],
            item["kind"],
            item["model"],
            str(item["port"]),
            item["status"],
        )

    console.print("[green]✅ 预设已应用。[/green]")
    console.print(table)


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
# Engine management commands
# ---------------------------------------------------------------------------


@engine_app.command("list")
def list_engines(
    api_port: int = typer.Option(
        SagePorts.GATEWAY_DEFAULT,
        "--api-port",
        help=f"控制平面端口 (默认 {SagePorts.GATEWAY_DEFAULT})",
    ),
    api_base: str | None = typer.Option(
        None,
        "--api-base",
        help="覆盖控制平面 API 基地址 (默认 http://localhost:<api-port>/v1)",
    ),
    timeout: float = typer.Option(5.0, "--timeout", help="HTTP 超时时间 (秒)"),
):
    """列出当前由控制平面管理的引擎。"""

    base_url = _resolve_api_base(api_base, api_port)
    cluster_status = _fetch_cluster_status(base_url, timeout)
    engines = _ensure_dict_list(
        cluster_status.get("engines")
        or cluster_status.get("engine_instances")
        or cluster_status.get("instances")
        or []
    )

    if not engines:
        console.print("[yellow]当前没有由控制平面管理的引擎。[/yellow]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Engine ID", overflow="fold")
    table.add_column("模型", overflow="fold")
    table.add_column("类型", justify="center")
    table.add_column("状态", justify="center")
    table.add_column("端口", justify="center")
    table.add_column("GPU", justify="center")
    table.add_column("PID", justify="center")
    table.add_column("Uptime", justify="center")

    for engine in engines:
        engine_id = engine.get("engine_id") or engine.get("id") or "-"
        model_name = engine.get("model_id") or engine.get("model") or "-"
        runtime_kind = engine.get("runtime") or engine.get("engine_kind")
        if not runtime_kind:
            metadata = engine.get("metadata") or {}
            runtime_kind = metadata.get("engine_kind")
        runtime_kind = runtime_kind or "llm"
        status_text = engine.get("status") or engine.get("state") or "-"
        listen_port = engine.get("port") or engine.get("listen_port") or "-"
        pid = engine.get("pid") or engine.get("process_id") or "-"
        uptime = engine.get("uptime_seconds") or engine.get("uptime") or engine.get("uptime_s")

        gpu_ids = engine.get("gpu_ids") or engine.get("gpus") or engine.get("devices")
        if isinstance(gpu_ids, list):
            gpu_text = ",".join(str(item) for item in gpu_ids) if gpu_ids else "CPU"
        else:
            gpu_text = str(gpu_ids) if gpu_ids is not None else "CPU"

        table.add_row(
            str(engine_id),
            str(model_name),
            str(runtime_kind),
            str(status_text),
            str(listen_port),
            gpu_text,
            str(pid),
            _format_uptime(uptime),
        )

    console.print(table)
    console.print(f"[green]共 {len(engines)} 个引擎。[/green]")


@engine_app.command("start")
def start_engine(
    model_id: str = typer.Argument(..., help="要启动的模型 ID"),
    api_port: int = typer.Option(
        SagePorts.GATEWAY_DEFAULT,
        "--api-port",
        help=f"控制平面端口 (默认 {SagePorts.GATEWAY_DEFAULT})",
    ),
    api_base: str | None = typer.Option(
        None,
        "--api-base",
        help="覆盖控制平面 API 基地址",
    ),
    timeout: float = typer.Option(5.0, "--timeout", help="HTTP 超时时间 (秒)"),
    engine_port: int | None = typer.Option(
        None,
        "--engine-port",
        help="显式指定新引擎监听端口",
    ),
    tensor_parallel: int | None = typer.Option(
        None,
        "--tensor-parallel",
        "-tp",
        help="Tensor 并行度 (直接透传给控制平面)",
    ),
    required_memory_gb: float | None = typer.Option(
        None,
        "--required-memory-gb",
        help="期望的显存需求 (GB)",
    ),
    engine_label: str | None = typer.Option(
        None,
        "--label",
        help="自定义标签，便于识别引擎",
    ),
    pipeline_parallel: int | None = typer.Option(
        None,
        "--pipeline-parallel",
        "-pp",
        help="Pipeline 并行度",
    ),
    max_concurrent: int | None = typer.Option(
        None,
        "--max-concurrent",
        help="最大并发请求数 (默认 256)",
    ),
    engine_kind: str = typer.Option(
        "llm",
        "--engine-kind",
        help="引擎类型 (llm, embedding, 或 finetune)",
    ),
    use_gpu: bool | None = typer.Option(
        None,
        "--use-gpu/--no-gpu",
        help="显式指定是否使用 GPU (默认: LLM 使用 GPU, Embedding 不使用)",
    ),
    # Finetune-specific parameters
    dataset_path: str | None = typer.Option(
        None,
        "--dataset",
        help="Fine-tune 数据集路径 (JSON/JSONL) [finetune 必需]",
    ),
    output_dir: str | None = typer.Option(
        None,
        "--output",
        help="Fine-tune 输出目录 (保存 checkpoint) [finetune 必需]",
    ),
    lora_rank: int = typer.Option(
        8,
        "--lora-rank",
        help="LoRA rank (1-128) [finetune]",
    ),
    lora_alpha: int = typer.Option(
        16,
        "--lora-alpha",
        help="LoRA alpha (1-256) [finetune]",
    ),
    learning_rate: float = typer.Option(
        5e-5,
        "--learning-rate",
        help="学习率 [finetune]",
    ),
    epochs: int = typer.Option(
        3,
        "--epochs",
        help="训练轮数 [finetune]",
    ),
    batch_size: int = typer.Option(
        4,
        "--batch-size",
        help="批次大小 [finetune]",
    ),
    gradient_accumulation_steps: int = typer.Option(
        1,
        "--gradient-accumulation",
        help="梯度累积步数 [finetune]",
    ),
    max_seq_length: int | None = typer.Option(
        None,
        "--max-seq-length",
        help="最大序列长度 [finetune]",
    ),
    use_flash_attention: bool = typer.Option(
        False,
        "--flash-attention/--no-flash-attention",
        help="使用 Flash Attention [finetune]",
    ),
    quantization_bits: int | None = typer.Option(
        None,
        "--quantization-bits",
        help="量化位数 (4/8) [finetune]",
    ),
    auto_download: bool = typer.Option(
        True,
        "--auto-download/--no-auto-download",
        help="自动下载模型 [finetune]",
    ),
):
    """请求启动新的 LLM, Embedding, 或 Finetune 引擎。"""

    base_url = _resolve_api_base(api_base, api_port)
    payload: dict[str, Any] = {"model_id": model_id}
    engine_kind_value = engine_kind.strip().lower()
    if engine_kind_value not in {"llm", "embedding", "finetune"}:
        console.print("[red]engine-kind 仅支持 'llm', 'embedding', 或 'finetune'.[/red]")
        raise typer.Exit(1)

    # Validate finetune-specific requirements
    if engine_kind_value == "finetune":
        if not dataset_path:
            console.print("[red]❌ --dataset 是 finetune 引擎的必需参数.[/red]")
            raise typer.Exit(1)
        if not output_dir:
            console.print("[red]❌ --output 是 finetune 引擎的必需参数.[/red]")
            raise typer.Exit(1)

        # Add finetune-specific parameters to payload
        payload["dataset_path"] = dataset_path
        payload["output_dir"] = output_dir
        payload["lora_rank"] = lora_rank
        payload["lora_alpha"] = lora_alpha
        payload["learning_rate"] = learning_rate
        payload["epochs"] = epochs
        payload["batch_size"] = batch_size
        payload["gradient_accumulation_steps"] = gradient_accumulation_steps
        if max_seq_length is not None:
            payload["max_seq_length"] = max_seq_length
        payload["use_flash_attention"] = use_flash_attention
        if quantization_bits is not None:
            payload["quantization_bits"] = quantization_bits
        payload["auto_download"] = auto_download

    if engine_port is not None:
        payload["port"] = engine_port
    if tensor_parallel is not None:
        payload["tensor_parallel_size"] = tensor_parallel
    if pipeline_parallel is not None:
        payload["pipeline_parallel_size"] = pipeline_parallel
    if required_memory_gb is not None:
        payload["required_memory_gb"] = required_memory_gb
    if engine_label:
        payload["engine_label"] = engine_label
    if max_concurrent is not None:
        payload["max_concurrent_requests"] = max_concurrent
    payload["engine_kind"] = engine_kind_value
    if use_gpu is not None:
        payload["use_gpu"] = use_gpu

    response = _management_request(
        "POST",
        "/management/engines",
        api_base=base_url,
        timeout=timeout,
        payload=payload,
    )

    engine_id = response.get("engine_id") or response.get("id") or "(pending)"
    model_name = response.get("model_id") or model_id
    status_text = response.get("status") or response.get("state") or "CREATED"
    assigned_port = response.get("port") or response.get("listen_port") or payload.get("port")

    console.print("[green]✅ 已提交引擎启动请求[/green]")
    console.print(f"  Engine ID : {engine_id}")
    console.print(f"  模型       : {model_name}")
    console.print(f"  状态       : {status_text}")
    console.print(f"  端口       : {assigned_port or '-'}")


@engine_app.command("stop")
def stop_engine(
    engine_id: str = typer.Argument(..., help="要停止的引擎 ID"),
    api_port: int = typer.Option(
        SagePorts.GATEWAY_DEFAULT,
        "--api-port",
        help=f"控制平面端口 (默认 {SagePorts.GATEWAY_DEFAULT})",
    ),
    api_base: str | None = typer.Option(
        None,
        "--api-base",
        help="覆盖控制平面 API 基地址",
    ),
    timeout: float = typer.Option(5.0, "--timeout", help="HTTP 超时时间 (秒)"),
):
    """请求停止指定的 LLM 引擎。"""

    base_url = _resolve_api_base(api_base, api_port)
    response = _management_request(
        "DELETE",
        f"/management/engines/{engine_id}",
        api_base=base_url,
        timeout=timeout,
    )

    status_text = response.get("status") or response.get("state") or "STOPPED"
    console.print(f"[green]✅ 已请求停止引擎 {engine_id} (状态: {status_text}).[/green]")


@engine_app.command("prune")
def prune_engines(
    api_port: int = typer.Option(
        SagePorts.GATEWAY_DEFAULT,
        "--api-port",
        help=f"控制平面端口 (默认 {SagePorts.GATEWAY_DEFAULT})",
    ),
    api_base: str | None = typer.Option(
        None,
        "--api-base",
        help="覆盖控制平面 API 基地址",
    ),
    timeout: float = typer.Option(5.0, "--timeout", help="HTTP 超时时间 (秒)"),
):
    """清理所有已停止或失败的引擎记录。"""

    base_url = _resolve_api_base(api_base, api_port)
    response = _management_request(
        "POST",
        "/management/engines/prune",
        api_base=base_url,
        timeout=timeout,
    )

    pruned_count = response.get("pruned_count", 0)
    console.print(f"[green]✅ 已清理 {pruned_count} 个已停止/失败的引擎记录。[/green]")


@app.command("gpu")
def gpu_status(
    api_port: int = typer.Option(
        SagePorts.GATEWAY_DEFAULT,
        "--api-port",
        help=f"控制平面端口 (默认 {SagePorts.GATEWAY_DEFAULT})",
    ),
    api_base: str | None = typer.Option(
        None,
        "--api-base",
        help="覆盖控制平面 API 基地址",
    ),
    timeout: float = typer.Option(5.0, "--timeout", help="HTTP 超时时间 (秒)"),
):
    """展示控制平面感知到的 GPU 状态。"""

    base_url = _resolve_api_base(api_base, api_port)
    cluster_status = _fetch_cluster_status(base_url, timeout)
    gpu_entries = _ensure_dict_list(
        cluster_status.get("gpus")
        or cluster_status.get("gpu_status")
        or cluster_status.get("system_status")
        or cluster_status.get("gpu")
        or []
    )

    if not gpu_entries:
        console.print("[yellow]控制平面未返回 GPU 信息。[/yellow]")
        return

    table = Table(title="GPU 资源", show_header=True, header_style="bold")
    table.add_column("GPU", overflow="fold")
    table.add_column("内存 (已用/总量)", justify="center")
    table.add_column("空闲", justify="center")
    table.add_column("利用率", justify="center")
    table.add_column("关联引擎", overflow="fold")

    for gpu in gpu_entries:
        idx = gpu.get("index")
        name = gpu.get("name") or "GPU"
        label = f"{idx}: {name}" if idx is not None else name

        used = gpu.get("memory_used_gb") or gpu.get("memory_used")
        total = gpu.get("memory_total_gb") or gpu.get("memory_total")
        free = gpu.get("memory_free_gb") or gpu.get("memory_free")

        util = gpu.get("utilization") or gpu.get("gpu_utilization")
        if isinstance(util, (int, float)):
            util_str = f"{util:.0f}%"
        else:
            util_str = str(util) if util is not None else "-"

        engines = gpu.get("engines") or gpu.get("engine_ids") or gpu.get("allocations")
        if isinstance(engines, list):
            engines_str = ", ".join(str(item) for item in engines) or "-"
        else:
            engines_str = str(engines) if engines is not None else "-"

        table.add_row(
            label,
            f"{_format_memory_gb(used)} / {_format_memory_gb(total)}",
            _format_memory_gb(free),
            util_str,
            engines_str,
        )

    console.print(table)


# ---------------------------------------------------------------------------
# Blocking service runner & fine-tune stub
# ---------------------------------------------------------------------------
@app.command("run")
def run_vllm_service(
    model: str = typer.Option("Qwen/Qwen2.5-1.5B-Instruct", "--model", "-m", help="生成模型"),
    speculative_model: str | None = typer.Option(
        None, "--speculative-model", help="投机采样模型 (Draft Model)"
    ),
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
        "speculative_model_id": speculative_model,
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
        0.7,
        "--gpu-memory",
        help="GPU 内存使用率 (0.1-1.0)，默认 0.7 以兼容消费级显卡",
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
    speculative_model: str = typer.Option(
        None,
        "--speculative-model",
        help="投机采样（Speculative Decoding）使用的草稿模型 (Draft Model)",
    ),
    background: bool = typer.Option(
        True,
        "--background/--foreground",
        help="后台运行（默认）或前台运行",
    ),
    with_embedding: bool = typer.Option(
        True,
        "--with-embedding/--no-embedding",
        help="同时启动 Embedding 服务（默认启用）",
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
        sage llm serve                           # 启动 LLM + Embedding 服务
        sage llm serve -m Qwen/Qwen2.5-7B-Instruct  # 指定模型
        sage llm serve --no-embedding            # 仅启动 LLM，不启动 Embedding
        sage llm serve --foreground              # 前台运行（阻塞）

    启动后可通过以下方式使用:

        from sage.llm import UnifiedInferenceClient

        client = UnifiedInferenceClient.create()
        response = client.chat([{"role": "user", "content": "Hello"}])
    """
    if LLMLauncher is None:
        console.print("[red]❌ LLMLauncher 不可用，请确保已安装 sage-common[/red]")
        raise typer.Exit(1)

    # Launch LLM service using unified launcher
    result = LLMLauncher.launch(
        model=model,
        port=port,
        host=host,
        gpu_memory=gpu_memory,
        max_model_len=max_model_len,
        tensor_parallel=tensor_parallel,
        speculative_model=speculative_model,
        background=background,
        verbose=True,
    )

    if not result.success:
        if result.error and "already running" not in result.error:
            console.print(f"[dim]请检查日志: {LOG_DIR / f'llm_api_server_{port}.log'}[/dim]")
        raise typer.Exit(1)

    if background:
        console.print("\n[dim]使用 'sage llm status' 查看状态[/dim]")
        console.print("[dim]使用 'sage llm stop' 停止服务[/dim]")
    else:
        # Foreground mode completed
        pass

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

        # Update service info with embedding PID
        if background:
            pid, config = LLMLauncher.load_service_info()
            if pid and config:
                config["embedding_pid"] = proc.pid
                config["embedding_port"] = embedding_port
                config["embedding_model"] = embedding_model
                LLMLauncher.save_service_info(pid, config)


@app.command("stop")
def stop_llm(
    force: bool = typer.Option(False, "--force", "-f", help="强制停止 (包括未记录的孤儿服务)"),
):
    """停止 LLM 推理服务。"""
    if LLMLauncher is None:
        console.print("[red]❌ LLMLauncher 不可用[/red]")
        raise typer.Exit(1)

    success = LLMLauncher.stop(verbose=True, force=force)
    if not success:
        raise typer.Exit(1)


@app.command("restart")
def restart_llm():
    """重启 LLM 推理服务（使用上次的配置）。"""
    if LLMLauncher is None:
        console.print("[red]❌ LLMLauncher 不可用[/red]")
        raise typer.Exit(1)

    # 获取当前配置
    pid, config = LLMLauncher.load_service_info()
    if not config:
        console.print("[yellow]⚠️  没有找到之前的服务配置，请使用 'sage llm serve' 启动[/yellow]")
        raise typer.Exit(1)

    console.print("[blue]🔄 重启 LLM 服务...[/blue]")

    # 停止服务
    LLMLauncher.stop(verbose=False)
    time.sleep(1)  # 等待端口释放

    # 使用保存的配置重新启动
    model = config.get("model", "Qwen/Qwen2.5-0.5B-Instruct")
    port = config.get("port", SagePorts.BENCHMARK_LLM)

    result = LLMLauncher.launch(
        model=model,
        port=port,
        background=True,
        verbose=True,
    )

    if result.success:
        console.print("[green]✅ LLM 服务重启成功[/green]")
    else:
        console.print(f"[red]❌ 重启失败: {result.error}[/red]")
        raise typer.Exit(1)


@app.command("status")
def status_llm():
    """查看 LLM 服务状态。"""

    import psutil

    if LLMLauncher is None:
        console.print("[red]❌ LLMLauncher 不可用[/red]")
        raise typer.Exit(1)

    pid, config = LLMLauncher.load_service_info()

    table = Table(title="LLM 服务状态", show_header=True, header_style="bold")
    table.add_column("属性")
    table.add_column("值")

    # Check process status based on saved PID
    saved_pid_running = False
    if pid and psutil.pid_exists(pid):
        try:
            proc = psutil.Process(pid)
            saved_pid_running = proc.is_running()
        except psutil.NoSuchProcess:
            pass

    # Check port status
    port = config.get("port", SagePorts.BENCHMARK_LLM) if config else SagePorts.BENCHMARK_LLM
    from sage.common.utils.system.network import is_port_occupied

    port_in_use = is_port_occupied("localhost", port)

    # Try to get actual service info via HTTP if port is in use
    actual_model = None
    service_healthy = False
    if port_in_use:
        try:
            import httpx

            resp = httpx.get(f"http://localhost:{port}/v1/models", timeout=5)
            if resp.status_code == 200:
                service_healthy = True
                models = resp.json().get("data", [])
                if models:
                    actual_model = models[0].get("id", "unknown")
        except Exception:
            pass

    # Determine overall status
    if saved_pid_running and port_in_use and service_healthy:
        status = "[green]运行中[/green]"
    elif port_in_use and service_healthy:
        # Service is running but PID file is stale
        status = "[green]运行中[/green] [dim](PID 文件已过时)[/dim]"
    elif port_in_use:
        # Port occupied but service not responding (may be starting)
        status = "[yellow]启动中...[/yellow]"
    else:
        status = "[red]已停止[/red]"

    table.add_row("状态", status)
    table.add_row("PID", str(pid) if pid else "-")
    table.add_row("端口", str(port))

    # Show model info - prefer actual model from API if available
    if actual_model:
        table.add_row("模型", actual_model)
    elif config:
        table.add_row("模型", config.get("model", "-"))
    else:
        table.add_row("模型", "-")

    if config:
        table.add_row("日志", config.get("log_file", "-"))
    table.add_row("API 端点", f"http://localhost:{port}/v1")

    console.print(table)

    # Health check summary
    if service_healthy:
        console.print("\n[green]✓[/green] 健康检查通过")
        if actual_model:
            console.print(f"  加载的模型: {actual_model}")
    elif port_in_use:
        console.print("\n[yellow]⚠️  服务正在启动中，请稍候...[/yellow]")

    # Check Embedding service status
    _show_embedding_status()


def _show_embedding_status():
    """显示 Embedding 服务状态。"""

    embedding_port = SagePorts.EMBEDDING_DEFAULT
    embedding_log = LOG_DIR / "embedding.log"

    # Check port status
    from sage.common.utils.system.network import is_port_occupied

    embedding_port_in_use = is_port_occupied("localhost", embedding_port)

    # Build table
    embed_table = Table(title="Embedding 服务状态", show_header=True, header_style="bold")
    embed_table.add_column("属性")
    embed_table.add_column("值")

    if embedding_port_in_use:
        embed_status = "[green]运行中[/green]"
    else:
        embed_status = "[red]已停止[/red]"

    embed_table.add_row("状态", embed_status)
    embed_table.add_row("端口", str(embedding_port))
    embed_table.add_row("日志", str(embedding_log) if embedding_log.exists() else "-")
    embed_table.add_row("API 端点", f"http://localhost:{embedding_port}/v1")

    console.print()
    console.print(embed_table)

    # Health check for embedding
    if embedding_port_in_use:
        try:
            import httpx

            resp = httpx.get(f"http://localhost:{embedding_port}/v1/models", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("data", [])
                if models:
                    console.print("\n[green]✓[/green] Embedding 健康检查通过")
                    console.print(f"  加载的模型: {models[0].get('id', 'unknown')}")
        except Exception as e:
            console.print(f"\n[yellow]⚠️  Embedding 健康检查失败: {e}[/yellow]")


@app.command("logs")
def view_logs(
    follow: bool = typer.Option(False, "--follow", "-f", help="实时跟踪日志"),
    lines: int = typer.Option(50, "--lines", "-n", help="显示最后 N 行"),
):
    """查看 LLM 服务日志。"""
    import os

    if LLMLauncher is None:
        console.print("[red]❌ LLMLauncher 不可用[/red]")
        raise typer.Exit(1)

    _, config = LLMLauncher.load_service_info()

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
