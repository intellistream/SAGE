#!/usr/bin/env python3
"""LLM configuration commands for SAGE."""

from pathlib import Path

import typer
import yaml  # type: ignore[import-untyped]

from sage.cli.utils.llm_detection import LLMServiceInfo, detect_all_services

app = typer.Typer(help="🤖 LLM 服务配置自动化")


def _load_yaml(path: Path) -> dict:
    """Load YAML file, returning an empty dict if the file is blank."""
    content = path.read_text(encoding="utf-8")
    data = yaml.safe_load(content) if content.strip() else None
    return data or {}


def _write_yaml(path: Path, data: dict) -> None:
    """Persist YAML dictionary with stable formatting."""
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _default_config_path() -> Path | None:
    """寻找默认的配置文件路径"""
    candidates = [
        Path.cwd() / "config" / "config.yaml",
        Path.cwd() / "config.yaml",
        Path.cwd() / "examples" / "config" / "config.yaml",
        Path.home() / ".sage" / "config.yaml",
    ]

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _select_service(
    detections: list[LLMServiceInfo], assume_yes: bool, preferred_section: str | None
) -> LLMServiceInfo:
    """选择要使用的服务"""
    if preferred_section:
        preferred_section = preferred_section.lower()
        for service in detections:
            if service.generator_section == preferred_section:
                return service

    if len(detections) == 1 or assume_yes:
        return detections[0]

    typer.echo("🔍 检测到多个可用的本地 LLM 服务：")
    for idx, service in enumerate(detections, start=1):
        typer.echo(f"  {idx}. {service.description} -> generator.{service.generator_section}")

    choice = typer.prompt("请选择要使用的服务编号", default="1")
    try:
        selection = int(choice)
        return detections[selection - 1]
    except (ValueError, IndexError):
        typer.echo("❌ 无效的选择，操作已取消。")
        raise typer.Exit(1)


@app.command("auto")
def auto_update_generator(
    config_path: Path | None = typer.Option(
        None,
        "--config-path",
        "-c",
        help="配置文件路径，默认自动探测 config/config.yaml 等常用位置",
    ),
    prefer: str | None = typer.Option(
        None,
        "--prefer",
        help="优先检测的服务类型（ollama / vllm）",
    ),
    model_name: str | None = typer.Option(
        None,
        "--model-name",
        "-m",
        help="指定要写入的模型名称（默认使用检测到的第一个模型）",
    ),
    section: str | None = typer.Option(
        None,
        "--section",
        "-s",
        help="目标 generator 子配置（remote / vllm 等），默认依据服务类型",
    ),
    auth_token: str | None = typer.Option(
        None,
        "--auth-token",
        "-t",
        help="用于vLLM服务的认证token（如果需要）",
    ),
    assume_yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="无需交互确认，自动选取检测到的第一个服务和模型",
    ),
    create_backup: bool = typer.Option(
        True,
        "--backup/--no-backup",
        help="更新前创建配置文件备份",
    ),
):
    """自动检测本地 LLM 服务并更新 generator 配置。"""

    resolved_path = config_path or _default_config_path()
    if not resolved_path:
        typer.echo("❌ 未找到默认配置文件，请通过 --config-path 指定。")
        raise typer.Exit(1)

    resolved_path = resolved_path.expanduser().resolve()
    if not resolved_path.exists():
        typer.echo(f"❌ 配置文件不存在: {resolved_path}")
        raise typer.Exit(1)

    prefer_normalized = prefer.lower() if prefer else None
    if prefer_normalized and prefer_normalized not in {"ollama", "vllm"}:
        typer.echo("❌ --prefer 仅支持 ollama 或 vllm。")
        raise typer.Exit(1)

    detections = detect_all_services(prefer_normalized, auth_token=auth_token)
    if not detections:
        typer.echo("⚠️ 未检测到支持的本地 LLM 服务。")
        raise typer.Exit(1)

    selected = _select_service(detections, assume_yes, section)

    available_models = selected.models
    chosen_model = model_name or selected.default_model
    if model_name and model_name not in available_models:
        typer.echo(f"⚠️ 指定的模型 {model_name} 未出现在服务返回的列表中，将按原样写入配置。")
    elif not model_name and len(available_models) > 1 and not assume_yes:
        typer.echo("📋 服务提供的模型列表：")
        for idx, item in enumerate(available_models, start=1):
            typer.echo(f"  {idx}. {item}")

        model_choice = typer.prompt("请选择模型编号（默认第一个）", default="1")
        try:
            chosen_idx = int(model_choice) - 1
            chosen_model = available_models[chosen_idx]
        except (ValueError, IndexError):
            typer.echo("❌ 无效的模型选择，使用默认模型。")
            chosen_model = selected.default_model

    target_section = section or selected.generator_section
    typer.echo("✅ 即将更新配置：")
    typer.echo(f"  服务: {selected.description}")
    typer.echo(f"  配置段: generator.{target_section}")
    typer.echo(f"  URL: {selected.base_url}")
    typer.echo(f"  模型: {chosen_model}")
    if auth_token:
        typer.echo(f"  认证: {auth_token}")

    if not assume_yes and not typer.confirm("确认更新？"):
        typer.echo("❌ 操作已取消。")
        raise typer.Exit(0)

    if create_backup:
        backup_path = Path(f"{resolved_path}.bak")
        backup_path.write_bytes(resolved_path.read_bytes())
        typer.echo(f"🗂️ 已创建备份: {backup_path}")

    config_data = _load_yaml(resolved_path)
    generator = config_data.setdefault("generator", {})
    section_data: dict[str, str] = generator.setdefault(target_section, {})

    # Preserve existing API key/seed unless explicitly overridden
    section_data.setdefault("method", "openai")
    section_data["base_url"] = selected.base_url
    section_data["model_name"] = chosen_model

    # Update API key if auth_token was provided
    if auth_token:
        section_data["api_key"] = auth_token

    _write_yaml(resolved_path, config_data)

    typer.echo("✅ 配置已更新：")
    typer.echo(f"  文件: {resolved_path}")
    typer.echo(f"  generator.{target_section}.base_url = {selected.base_url}")
    typer.echo(f"  generator.{target_section}.model_name = {chosen_model}")
    if auth_token:
        typer.echo(f"  generator.{target_section}.api_key = {auth_token}")

    raise typer.Exit(0)
