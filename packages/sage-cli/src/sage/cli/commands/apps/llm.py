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

from sage.common.components.sage_llm.presets import (
    EnginePreset,
    get_builtin_preset,
    list_builtin_presets,
    load_preset_file,
)
from sage.common.config import ensure_hf_mirror_configured
from sage.common.config.ports import SagePorts
from sage.common.model_registry import fetch_recommended_models, vllm_registry

try:  # Optional dependency: middleware is not required for every CLI install
    from sage.common.components.sage_llm import VLLMService
except Exception:  # pragma: no cover - handled gracefully at runtime
    VLLMService = None  # type: ignore

try:
    from sage.common.components.sage_llm import (
        LLMAPIServer,
        LLMLauncher,
        LLMServerConfig,
    )
except Exception:  # pragma: no cover
    LLMAPIServer = None  # type: ignore
    LLMLauncher = None  # type: ignore
    LLMServerConfig = None  # type: ignore

# sage-gateway is now the unified gateway (includes Control Plane)
# UnifiedAPIServer has been removed from sage-common
GATEWAY_AVAILABLE = True
try:
    from sage.gateway.server import main as gateway_main  # noqa: F401
except ImportError:  # pragma: no cover
    GATEWAY_AVAILABLE = False

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
        "   请先启动 Gateway 服务，运行 [cyan]sage gateway start[/cyan]",
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
            gpu_text = ",".join(str(item) for item in gpu_ids) or "-"
        else:
            gpu_text = str(gpu_ids) if gpu_ids is not None else "-"

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
        help="引擎类型 (llm 或 embedding)",
    ),
    use_gpu: bool | None = typer.Option(
        None,
        "--use-gpu/--no-gpu",
        help="显式指定是否使用 GPU (默认: LLM 使用 GPU, Embedding 不使用)",
    ),
):
    """请求启动新的 LLM 引擎。"""

    base_url = _resolve_api_base(api_base, api_port)
    payload: dict[str, Any] = {"model_id": model_id}
    engine_kind_value = engine_kind.strip().lower()
    if engine_kind_value not in {"llm", "embedding"}:
        console.print("[red]engine-kind 仅支持 'llm' 或 'embedding'.[/red]")
        raise typer.Exit(1)

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
    drain: bool = typer.Option(
        False,
        "--drain",
        "-d",
        help="优雅关闭：等待现有请求完成后再停止引擎",
    ),
    timeout: float = typer.Option(5.0, "--timeout", help="HTTP 超时时间 (秒)"),
):
    """请求停止指定的 LLM 引擎。

    使用 --drain 选项可以优雅关闭引擎：引擎将停止接受新请求，
    等待现有请求处理完成后再停止。
    """
    base_url = _resolve_api_base(api_base, api_port)

    # Build URL with drain query parameter
    endpoint = f"/management/engines/{engine_id}"
    if drain:
        endpoint += "?drain=true"

    response = _management_request(
        "DELETE",
        endpoint,
        api_base=base_url,
        timeout=timeout,
    )

    status_text = response.get("status") or response.get("state") or "STOPPED"
    drained = response.get("drained", False)

    if drained:
        console.print(f"[green]✅ 引擎 {engine_id} 已优雅关闭 (状态: {status_text}).[/green]")
    else:
        console.print(f"[green]✅ 已请求停止引擎 {engine_id} (状态: {status_text}).[/green]")


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
# Service lifecycle commands (via Control Plane)
# ---------------------------------------------------------------------------

# PID file for Control Plane Gateway
GATEWAY_PID_FILE = SAGE_DIR / "gateway.pid"
GATEWAY_CONFIG_FILE = SAGE_DIR / "gateway.json"


def _save_gateway_info(pid: int, config: dict[str, Any]) -> None:
    """Save gateway process info for later management."""
    _ensure_dirs()
    GATEWAY_PID_FILE.write_text(str(pid))
    GATEWAY_CONFIG_FILE.write_text(json.dumps(config, indent=2))


def _load_gateway_info() -> tuple[int | None, dict[str, Any] | None]:
    """Load gateway process info."""
    if not GATEWAY_PID_FILE.exists():
        return None, None
    try:
        pid = int(GATEWAY_PID_FILE.read_text().strip())
        config = json.loads(GATEWAY_CONFIG_FILE.read_text()) if GATEWAY_CONFIG_FILE.exists() else {}
        return pid, config
    except Exception:
        return None, None


def _clear_gateway_info() -> None:
    """Clear gateway process info."""
    GATEWAY_PID_FILE.unlink(missing_ok=True)
    GATEWAY_CONFIG_FILE.unlink(missing_ok=True)


def _is_gateway_running(pid: int | None = None) -> bool:
    """Check if gateway is running."""
    import psutil

    if pid is None:
        pid, _ = _load_gateway_info()
    if pid is None:
        return False
    return psutil.pid_exists(pid)


def _check_existing_gateway(port: int) -> bool:
    """Check if there's already a SAGE Gateway running on the given port.

    Returns:
        True if a SAGE Gateway is running and healthy on this port
    """
    try:
        resp = httpx.get(f"http://localhost:{port}/health", timeout=2.0)
        if resp.status_code == 200:
            data = resp.json()
            # Check if it's a SAGE Gateway (has 'status' field)
            return data.get("status") == "healthy"
    except Exception:
        pass
    return False


def _wait_for_gateway(port: int, timeout: float = 30.0) -> bool:
    """Wait for gateway to be ready."""
    import time

    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = httpx.get(f"http://localhost:{port}/health", timeout=2.0)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _start_engine_via_api(
    api_base: str,
    model_id: str,
    engine_kind: str = "llm",
    port: int | None = None,
    tensor_parallel_size: int = 1,
    use_gpu: bool | None = None,
    extra_args: list[str] | None = None,
    timeout: float = 10.0,
) -> dict[str, Any] | None:
    """Start an engine via Control Plane management API."""
    payload = {
        "model_id": model_id,
        "engine_kind": engine_kind,
        "tensor_parallel_size": tensor_parallel_size,
    }
    if port is not None:
        payload["port"] = port
    if use_gpu is not None:
        payload["use_gpu"] = use_gpu
    if extra_args:
        payload["extra_args"] = extra_args

    try:
        resp = httpx.post(
            f"{api_base}/management/engines",
            json=payload,
            timeout=timeout,
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            console.print(f"[red]❌ 启动引擎失败: {_extract_error_detail(resp)}[/red]")
            return None
    except Exception as e:
        console.print(f"[red]❌ 启动引擎失败: {e}[/red]")
        return None


@app.command("serve")
def serve_llm(
    model: str = typer.Option(
        "Qwen/Qwen2.5-0.5B-Instruct",
        "--model",
        "-m",
        help="LLM 模型名称",
    ),
    gateway_port: int = typer.Option(
        SagePorts.GATEWAY_DEFAULT,
        "--gateway-port",
        "-g",
        help=f"Control Plane Gateway 端口 (默认: {SagePorts.GATEWAY_DEFAULT})",
    ),
    llm_port: int = typer.Option(
        SagePorts.BENCHMARK_LLM,
        "--llm-port",
        "-p",
        help=f"LLM 引擎端口 (默认: {SagePorts.BENCHMARK_LLM})",
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
    """启动 LLM 推理服务（通过 Control Plane）。

    使用 sageLLM Control Plane 启动统一的 API Gateway 和推理引擎。
    默认后台运行，可通过 'sage llm stop' 停止。

    架构:
        Gateway (8000) → LLM Engine (8901) + Embedding Engine (8090)

    示例:
        sage llm serve                              # 启动 Gateway + LLM + Embedding
        sage llm serve -m Qwen/Qwen2.5-7B-Instruct  # 指定 LLM 模型
        sage llm serve --no-embedding               # 仅启动 LLM，不启动 Embedding
        sage llm serve --foreground                 # 前台运行（阻塞）

    启动后可通过以下方式使用:

        from sage.common.components.sage_llm import UnifiedInferenceClient

        client = UnifiedInferenceClient.create()
        response = client.chat([{"role": "user", "content": "Hello"}])
    """
    import os
    import subprocess
    import sys

    if not GATEWAY_AVAILABLE:
        console.print("[red]❌ sage-gateway 不可用，请确保已安装 sage-gateway[/red]")
        raise typer.Exit(1)

    _ensure_dirs()
    ensure_hf_mirror_configured()

    # Check if gateway is already running (by our PID file)
    pid, config = _load_gateway_info()
    if pid and _is_gateway_running(pid):
        console.print(f"[yellow]⚠️  Control Plane Gateway 已在运行 (PID: {pid})[/yellow]")
        console.print(f"   端口: {config.get('gateway_port', gateway_port)}")
        console.print("   使用 'sage llm stop' 停止后重试，或使用 'sage llm engine start' 添加引擎")
        raise typer.Exit(0)

    # Check if there's an existing SAGE Gateway on the port (started by another user)
    existing_gateway = _check_existing_gateway(gateway_port)
    if existing_gateway:
        console.print(f"[green]✓[/green] 检测到现有 Gateway 运行在端口 {gateway_port}")
        console.print("   将复用现有 Gateway，直接启动引擎...")
        # Skip gateway startup, just start engines
        api_base = f"http://localhost:{gateway_port}/v1"

        # Start LLM engine (let Control Plane auto-assign port if needed)
        console.print("\n[blue]🎯 启动 LLM 引擎[/blue]")
        console.print(f"   模型: {model}")

        # Check if the specified LLM port is available
        llm_port_to_use: int | None = llm_port
        if not SagePorts.is_available(llm_port):
            console.print(f"   [yellow]端口 {llm_port} 已占用，将自动分配可用端口[/yellow]")
            llm_port_to_use = None  # Let Control Plane auto-assign

        extra_args = [
            f"--gpu-memory-utilization={gpu_memory}",
            f"--max-model-len={max_model_len}",
        ]

        llm_result = _start_engine_via_api(
            api_base=api_base,
            model_id=model,
            engine_kind="llm",
            port=llm_port_to_use,
            tensor_parallel_size=tensor_parallel,
            extra_args=extra_args,
            timeout=120.0,
        )

        if llm_result:
            actual_port = llm_result.get("port", llm_port_to_use)
            engine_id = llm_result.get("engine_id", "unknown")
            console.print(
                f"   [green]✓[/green] LLM 引擎已启动 (ID: {engine_id}, 端口: {actual_port})"
            )
        else:
            console.print("[yellow]⚠️  LLM 引擎启动失败[/yellow]")

        # Optionally start Embedding engine
        if with_embedding:
            console.print("\n[blue]🎯 启动 Embedding 引擎[/blue]")
            console.print(f"   模型: {embedding_model}")

            embed_port_to_use: int | None = embedding_port
            if not SagePorts.is_available(embedding_port):
                console.print(
                    f"   [yellow]端口 {embedding_port} 已占用，将自动分配可用端口[/yellow]"
                )
                embed_port_to_use = None

            embed_result = _start_engine_via_api(
                api_base=api_base,
                model_id=embedding_model,
                engine_kind="embedding",
                port=embed_port_to_use,
                use_gpu=False,
                timeout=60.0,
            )

            if embed_result:
                actual_port = embed_result.get("port", embed_port_to_use)
                engine_id = embed_result.get("engine_id", "unknown")
                console.print(
                    f"   [green]✓[/green] Embedding 引擎已启动 (ID: {engine_id}, 端口: {actual_port})"
                )
            else:
                console.print("[yellow]⚠️  Embedding 引擎启动失败[/yellow]")

        console.print("\n[green]✅ 引擎启动完成[/green]")
        console.print(f"   API Gateway: http://localhost:{gateway_port}/v1")
        console.print("\n[dim]使用 'sage llm engine list' 查看所有引擎[/dim]")
        return

    # Build extra args for vLLM
    extra_args = [
        f"--gpu-memory-utilization={gpu_memory}",
        f"--max-model-len={max_model_len}",
    ]

    console.print("[blue]🚀 启动 SAGE Gateway (Control Plane)[/blue]")
    console.print(f"   Gateway 端口: {gateway_port}")
    console.print(f"   主机: {host}")

    # Start sage-gateway as subprocess
    gateway_log = LOG_DIR / "gateway.log"
    gateway_cmd = [
        sys.executable,
        "-m",
        "sage.gateway.server",
    ]
    # Set environment variables for gateway configuration
    gateway_env = {
        **dict(os.environ),
        "SAGE_GATEWAY_ENABLE_CONTROL_PLANE": "true",
        "SAGE_GATEWAY_HOST": host,
        "SAGE_GATEWAY_PORT": str(gateway_port),
    }

    if background:
        with open(gateway_log, "w") as log_file:
            proc = subprocess.Popen(
                gateway_cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env=gateway_env,
            )
        gateway_pid = proc.pid
        console.print(f"   [green]✓[/green] Gateway 进程已启动 (PID: {gateway_pid})")
        console.print(f"   日志: {gateway_log}")

        # Wait for gateway to be ready
        console.print("   [dim]等待 Gateway 就绪...[/dim]")
        if not _wait_for_gateway(gateway_port, timeout=30.0):
            console.print("[red]❌ Gateway 启动超时[/red]")
            console.print(f"   请检查日志: {gateway_log}")
            raise typer.Exit(1)
        console.print("   [green]✓[/green] Gateway 已就绪")

        # Save gateway info
        gateway_config = {
            "gateway_port": gateway_port,
            "host": host,
            "llm_model": model,
            "llm_port": llm_port,
            "embedding_model": embedding_model if with_embedding else None,
            "embedding_port": embedding_port if with_embedding else None,
            "engines": [],
        }
        _save_gateway_info(gateway_pid, gateway_config)

        # Start LLM engine via Control Plane API
        api_base = f"http://localhost:{gateway_port}/v1"
        console.print("\n[blue]🎯 启动 LLM 引擎[/blue]")
        console.print(f"   模型: {model}")
        console.print(f"   TP: {tensor_parallel}")

        # Check if the specified LLM port is available
        llm_port_to_use: int | None = llm_port
        if not SagePorts.is_available(llm_port):
            console.print(f"   [yellow]端口 {llm_port} 已占用，将自动分配可用端口[/yellow]")
            llm_port_to_use = None  # Let Control Plane auto-assign
        else:
            console.print(f"   端口: {llm_port}")

        llm_result = _start_engine_via_api(
            api_base=api_base,
            model_id=model,
            engine_kind="llm",
            port=llm_port_to_use,
            tensor_parallel_size=tensor_parallel,
            extra_args=extra_args,
            timeout=120.0,  # LLM 启动可能需要较长时间
        )

        if llm_result:
            actual_port = llm_result.get("port", llm_port_to_use)
            engine_id = llm_result.get("engine_id", "unknown")
            console.print(
                f"   [green]✓[/green] LLM 引擎已启动 (ID: {engine_id}, 端口: {actual_port})"
            )
            gateway_config["engines"].append(
                {"id": engine_id, "kind": "llm", "model": model, "port": actual_port}
            )
        else:
            console.print("[yellow]⚠️  LLM 引擎启动失败，Gateway 仍在运行[/yellow]")

        # Optionally start Embedding engine
        if with_embedding:
            console.print("\n[blue]🎯 启动 Embedding 引擎[/blue]")
            console.print(f"   模型: {embedding_model}")

            embed_port_to_use: int | None = embedding_port
            if not SagePorts.is_available(embedding_port):
                console.print(
                    f"   [yellow]端口 {embedding_port} 已占用，将自动分配可用端口[/yellow]"
                )
                embed_port_to_use = None
            else:
                console.print(f"   端口: {embedding_port}")

            embed_result = _start_engine_via_api(
                api_base=api_base,
                model_id=embedding_model,
                engine_kind="embedding",
                port=embed_port_to_use,
                use_gpu=False,  # Embedding 默认不使用 GPU
                timeout=60.0,
            )

            if embed_result:
                actual_port = embed_result.get("port", embed_port_to_use)
                engine_id = embed_result.get("engine_id", "unknown")
                console.print(
                    f"   [green]✓[/green] Embedding 引擎已启动 (ID: {engine_id}, 端口: {actual_port})"
                )
                gateway_config["engines"].append(
                    {
                        "id": engine_id,
                        "kind": "embedding",
                        "model": embedding_model,
                        "port": actual_port,
                    }
                )
            else:
                console.print("[yellow]⚠️  Embedding 引擎启动失败[/yellow]")

        # Update gateway config with engine info
        _save_gateway_info(gateway_pid, gateway_config)

        console.print("\n[green]✅ 服务启动完成[/green]")
        console.print(f"   API Gateway: http://localhost:{gateway_port}/v1")
        console.print("\n[dim]使用 'sage llm status' 查看状态[/dim]")
        console.print("[dim]使用 'sage llm stop' 停止服务[/dim]")

    else:
        # Foreground mode - run gateway directly (blocking)
        console.print("[dim]前台模式，Ctrl+C 退出[/dim]")

        import uvicorn

        from sage.gateway.server import app as gateway_app

        try:
            uvicorn.run(
                gateway_app,
                host=host,
                port=gateway_port,
                log_level="info",
            )
        except KeyboardInterrupt:
            console.print("\n[yellow]收到中断信号，正在停止...[/yellow]")


@app.command("stop")
def stop_llm(
    force: bool = typer.Option(False, "--force", "-f", help="强制停止"),
):
    """停止 LLM 推理服务（Control Plane Gateway 和所有引擎）。"""
    import os
    import signal

    import psutil

    pid, config = _load_gateway_info()

    if pid is None:
        # Fallback to legacy LLMLauncher
        if LLMLauncher is not None:
            legacy_pid, _ = LLMLauncher.load_service_info()
            if legacy_pid:
                console.print("[dim]检测到旧版服务，使用 LLMLauncher 停止[/dim]")
                success = LLMLauncher.stop(verbose=True)
                if not success:
                    raise typer.Exit(1)
                return
        console.print("[yellow]⚠️  没有正在运行的服务[/yellow]")
        return

    if not _is_gateway_running(pid):
        console.print("[yellow]⚠️  Gateway 进程不存在，清理 PID 文件[/yellow]")
        _clear_gateway_info()
        return

    console.print(f"[blue]🛑 停止 Control Plane Gateway (PID: {pid})[/blue]")

    try:
        process = psutil.Process(pid)
        # First try graceful shutdown
        os.kill(pid, signal.SIGTERM)
        try:
            process.wait(timeout=10)
            console.print("[green]✓[/green] Gateway 已停止")
        except psutil.TimeoutExpired:
            if force:
                console.print("[yellow]⚠️  强制终止进程[/yellow]")
                os.kill(pid, signal.SIGKILL)
                process.wait(timeout=5)
                console.print("[green]✓[/green] Gateway 已强制停止")
            else:
                console.print("[yellow]⚠️  进程未能在超时时间内停止，使用 --force 强制终止[/yellow]")
                raise typer.Exit(1)
    except psutil.NoSuchProcess:
        console.print("[dim]进程已不存在[/dim]")
    except Exception as e:
        console.print(f"[red]❌ 停止失败: {e}[/red]")
        raise typer.Exit(1)

    _clear_gateway_info()
    console.print("[green]✅ 服务已停止[/green]")


@app.command("restart")
def restart_llm():
    """重启 LLM 推理服务（使用上次的配置）。"""
    pid, config = _load_gateway_info()

    if not config:
        # Fallback to legacy LLMLauncher
        if LLMLauncher is not None:
            legacy_pid, legacy_config = LLMLauncher.load_service_info()
            if legacy_config:
                console.print("[dim]检测到旧版配置，使用 LLMLauncher 重启[/dim]")
                LLMLauncher.stop(verbose=False)
                time.sleep(1)
                model = legacy_config.get("model", "Qwen/Qwen2.5-0.5B-Instruct")
                port = legacy_config.get("port", SagePorts.BENCHMARK_LLM)
                result = LLMLauncher.launch(model=model, port=port, background=True, verbose=True)
                if result.success:
                    console.print("[green]✅ LLM 服务重启成功[/green]")
                else:
                    console.print(f"[red]❌ 重启失败: {result.error}[/red]")
                    raise typer.Exit(1)
                return
        console.print("[yellow]⚠️  没有找到之前的服务配置，请使用 'sage llm serve' 启动[/yellow]")
        raise typer.Exit(1)

    console.print("[blue]🔄 重启 Control Plane 服务...[/blue]")

    # Stop current service
    stop_llm(force=False)
    time.sleep(2)  # Wait for ports to be released

    # Restart with saved config
    serve_llm(
        model=config.get("llm_model", "Qwen/Qwen2.5-0.5B-Instruct"),
        gateway_port=config.get("gateway_port", SagePorts.GATEWAY_DEFAULT),
        llm_port=config.get("llm_port", SagePorts.BENCHMARK_LLM),
        host=config.get("host", "0.0.0.0"),
        with_embedding=config.get("embedding_model") is not None,
        embedding_model=config.get("embedding_model", "BAAI/bge-small-zh-v1.5"),
        embedding_port=config.get("embedding_port", SagePorts.EMBEDDING_DEFAULT),
        background=True,
    )


@app.command("status")
def status_llm():
    """查看 LLM 服务状态。"""
    import socket

    import psutil

    pid, config = _load_gateway_info()

    # Check for legacy service
    legacy_pid, legacy_config = None, None
    if LLMLauncher is not None:
        legacy_pid, legacy_config = LLMLauncher.load_service_info()

    table = Table(title="Control Plane 服务状态", show_header=True, header_style="bold")
    table.add_column("属性")
    table.add_column("值")

    # Check gateway process status
    gateway_running = False
    if pid and psutil.pid_exists(pid):
        try:
            proc = psutil.Process(pid)
            gateway_running = proc.is_running()
        except psutil.NoSuchProcess:
            pass

    # Check gateway port
    gateway_port = (
        config.get("gateway_port", SagePorts.GATEWAY_DEFAULT)
        if config
        else SagePorts.GATEWAY_DEFAULT
    )
    gateway_port_in_use = False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        gateway_port_in_use = sock.connect_ex(("localhost", gateway_port)) == 0

    # Determine gateway status
    if gateway_running and gateway_port_in_use:
        gateway_status = "[green]运行中[/green]"
    elif gateway_port_in_use:
        gateway_status = "[yellow]端口被占用 (外部进程)[/yellow]"
    else:
        gateway_status = "[red]已停止[/red]"

    table.add_row("Gateway 状态", gateway_status)
    table.add_row("Gateway PID", str(pid) if pid else "-")
    table.add_row("Gateway 端口", str(gateway_port))

    if config:
        table.add_row("LLM 模型", config.get("llm_model", "-"))
        table.add_row("LLM 端口", str(config.get("llm_port", "-")))
        if config.get("embedding_model"):
            table.add_row("Embedding 模型", config.get("embedding_model", "-"))
            table.add_row("Embedding 端口", str(config.get("embedding_port", "-")))
        table.add_row("API 端点", f"http://localhost:{gateway_port}/v1")

        # Show engines
        engines = config.get("engines", [])
        if engines:
            engine_info = ", ".join(f"{e['kind']}:{e.get('id', 'unknown')}" for e in engines)
            table.add_row("引擎", engine_info)

    console.print(table)

    # Try to get detailed status from Control Plane API
    if gateway_port_in_use:
        try:
            resp = httpx.get(f"http://localhost:{gateway_port}/v1/management/status", timeout=5)
            if resp.status_code == 200:
                cluster_status = resp.json()
                console.print("\n[green]✓[/green] Control Plane 健康检查通过")

                # Show registered instances
                instances = cluster_status.get("instances", [])
                if instances:
                    inst_table = Table(title="注册的引擎实例", show_header=True)
                    inst_table.add_column("ID")
                    inst_table.add_column("类型")
                    inst_table.add_column("模型")
                    inst_table.add_column("端口")
                    inst_table.add_column("状态")

                    for inst in instances:
                        inst_table.add_row(
                            inst.get("instance_id", "-"),
                            inst.get("instance_type", "-"),
                            inst.get("model_name", "-"),
                            str(inst.get("port", "-")),
                            "[green]运行中[/green]"
                            if inst.get("is_healthy")
                            else "[red]异常[/red]",
                        )
                    console.print(inst_table)
        except Exception:
            # Control Plane API not available, try basic health check
            try:
                resp = httpx.get(f"http://localhost:{gateway_port}/health", timeout=5)
                if resp.status_code == 200:
                    console.print("\n[green]✓[/green] Gateway 健康检查通过")
            except Exception as e:
                console.print(f"\n[yellow]⚠️  健康检查失败: {e}[/yellow]")

    # Legacy service status
    if legacy_pid and not pid:
        console.print("\n[dim]检测到旧版服务配置:[/dim]")
        if psutil.pid_exists(legacy_pid):
            console.print(f"  PID: {legacy_pid} [green](运行中)[/green]")
        else:
            console.print(f"  PID: {legacy_pid} [red](已停止)[/red]")
        if legacy_config:
            console.print(f"  模型: {legacy_config.get('model', '-')}")
            console.print(f"  端口: {legacy_config.get('port', '-')}")


def _show_embedding_status():
    """显示 Embedding 服务状态。"""
    import socket

    embedding_port = SagePorts.EMBEDDING_DEFAULT
    embedding_log = LOG_DIR / "embedding.log"

    # Check port status
    embedding_port_in_use = False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        embedding_port_in_use = sock.connect_ex(("localhost", embedding_port)) == 0

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
