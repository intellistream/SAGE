"""Domain knowledge helpers for the SAGE pipeline builder."""

from __future__ import annotations

import textwrap
from collections.abc import Iterable, Mapping, MutableMapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from sage.common.config.output_paths import get_sage_paths  # type: ignore[import-untyped]

_BASE_GUIDE = textwrap.dedent(
    """
    SAGE Pipeline 配置速览：
    - `pipeline`: 定义名称、描述、版本和运行类型（local/remote）。
    - `source`: 数据入口组件，负责产生或读取输入。
    - `stages`: 有序的算子列表，每个算子包含 `id/kind/class/params/summary`。
      - kind 决定调度方式：`map`（逐条处理）、`batch`（批处理）、`service`（长驻服务）。
      - class 使用 Python 全路径，例如 `sage.libs.rag.retriever.Wiki18FAISSRetriever`。
    - `sink`: 结果落地组件，通常为本地或远程持久化。
    - `services`: pipeline 运行时依赖的配套服务。
    - `monitors`: 监控与观测器，可选。
    - `notes`: 文字提示或待办项。
    生成配置时请确保：
    1. 至少包含一个 stage 和一个 sink。
    2. 组件参数均为 JSON 可序列化对象（字符串、数字、布尔、数组、对象）。
    3. 使用短横线风格的 slug 作为标识符（例如 `qa-generator`）。
    4. 为每个阶段提供 concise 的 summary 说明其职责。
    """
).strip()


@dataclass
class _ExampleSummary:
    text: str
    components: Mapping[str, set[str]]


def _ensure_project_root() -> Path:
    paths = get_sage_paths()
    project_root = getattr(paths, "project_root", None)
    if project_root is None:
        project_root = Path.cwd()
    return Path(project_root)


def _trim(text: str, limit: int = 1200) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _summarize_stage(stage: Mapping[str, object]) -> str:
    identifier = str(stage.get("id", "stage"))
    kind = str(stage.get("kind", "map"))
    class_path = str(stage.get("class", "<unknown>"))
    summary = str(stage.get("summary", ""))
    params = stage.get("params", {})
    param_keys = ", ".join(sorted(params.keys())) if isinstance(params, dict) else ""
    parts = [f"- {identifier} [{kind}] -> {class_path}"]
    if summary:
        parts.append(f"  {summary}")
    if param_keys:
        parts.append(f"  params: {param_keys}")
    return "\n".join(parts)


def _summarize_pipeline_file(path: Path) -> _ExampleSummary | None:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    pipeline_meta = data.get("pipeline") or {}
    name = str(pipeline_meta.get("name", path.stem))
    description = str(pipeline_meta.get("description", ""))
    pipeline_type = str(pipeline_meta.get("type", "local"))

    lines: list[str] = [
        f"Pipeline 示例: {name} ({path.name})",
        f"类型: {pipeline_type}",
    ]
    if description:
        lines.append(f"描述: {description}")

    components: MutableMapping[str, set[str]] = {
        "sources": set(),
        "stages": set(),
        "sinks": set(),
        "services": set(),
        "monitors": set(),
    }

    source = data.get("source") or {}
    if isinstance(source, Mapping):
        source_class = str(source.get("class", ""))
        if source_class:
            components["sources"].add(source_class)
            summary = str(source.get("summary", ""))
            lines.append(f"Source -> {source_class}{' — ' + summary if summary else ''}")

    stages = data.get("stages") or []
    if isinstance(stages, list) and stages:
        lines.append("Stages:")
        for stage in stages:
            if not isinstance(stage, Mapping):
                continue
            stage_summary = _summarize_stage(stage)
            if stage_summary:
                lines.append(stage_summary)
            class_path = str(stage.get("class", ""))
            if class_path:
                components["stages"].add(class_path)

    sink = data.get("sink") or {}
    if isinstance(sink, Mapping):
        sink_class = str(sink.get("class", ""))
        if sink_class:
            components["sinks"].add(sink_class)
            summary = str(sink.get("summary", ""))
            lines.append(f"Sink -> {sink_class}{' — ' + summary if summary else ''}")

    services = data.get("services") or []
    if isinstance(services, list):
        active_services = []
        for service in services:
            if not isinstance(service, Mapping):
                continue
            service_class = str(service.get("class", ""))
            if service_class:
                components["services"].add(service_class)
                service_name = str(service.get("name", service_class.split(".")[-1]))
                active_services.append(f"  - {service_name}: {service_class}")
        if active_services:
            lines.append("Services:")
            lines.extend(active_services)

    monitors = data.get("monitors") or []
    if isinstance(monitors, list):
        active_monitors = []
        for monitor in monitors:
            if not isinstance(monitor, Mapping):
                continue
            monitor_class = str(monitor.get("class", ""))
            if monitor_class:
                components["monitors"].add(monitor_class)
                active_monitors.append(f"  - {monitor_class}")
        if active_monitors:
            lines.append("Monitors:")
            lines.extend(active_monitors)

    notes = data.get("notes") or []
    if isinstance(notes, list) and notes:
        preview = "; ".join(str(note) for note in notes[:2])
        lines.append(f"Notes: {preview}")

    snippet = "\n".join(lines).strip()
    snippet = _trim(snippet)
    if not snippet:
        return None

    return _ExampleSummary(snippet, components)


def _format_component_catalog(components: Mapping[str, Iterable[str]]) -> str:
    lines = ["SAGE Pipeline 组件速查表:"]
    for key in ("sources", "stages", "sinks", "services", "monitors"):
        values = sorted(set(components.get(key, [])))
        if not values:
            continue
        pretty_key = key.capitalize()
        lines.append(f"{pretty_key}:")
        for value in values:
            lines.append(f"  - {value}")
    return _trim("\n".join(lines).strip())


@lru_cache(maxsize=32)
def load_domain_contexts(limit: int = 4) -> tuple[str, ...]:
    """Return contextual snippets describing SAGE pipelines for LLM prompting."""

    limit = max(0, int(limit))
    contexts: list[str] = [_BASE_GUIDE]

    project_root = _ensure_project_root()
    example_dir = project_root / "examples" / "config"
    component_map: dict[str, set[str]] = {
        "sources": set(),
        "stages": set(),
        "sinks": set(),
        "services": set(),
        "monitors": set(),
    }

    if example_dir.exists():
        summaries: list[_ExampleSummary] = []
        for path in sorted(example_dir.glob("*.yaml")):
            summary = _summarize_pipeline_file(path)
            if summary is None:
                continue
            summaries.append(summary)
            for key, values in summary.components.items():
                component_map[key].update(values)

        for item in summaries[:limit]:
            contexts.append(item.text)

    catalog = _format_component_catalog(component_map)
    if catalog:
        contexts.append(catalog)

    return tuple(ctx for ctx in contexts if ctx.strip())


def load_custom_contexts(paths: Iterable[Path]) -> tuple[str, ...]:
    """Read additional context snippets from user-provided files."""

    snippets: list[str] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:  # pragma: no cover - error handled by caller
            raise RuntimeError(f"无法读取上下文文件 {path}: {exc}") from exc
        cleaned = text.strip()
        if cleaned:
            snippets.append(cleaned)
    return tuple(snippets)


__all__ = ["load_domain_contexts", "load_custom_contexts"]
