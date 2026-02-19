#!/usr/bin/env python3
"""Interactive pipeline builder powered by LLMs."""

from __future__ import annotations

import importlib
import json
import os
import re
import textwrap
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer
import yaml  # type: ignore[import-untyped]
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from sage.cli import templates
from sage.cli.commands.apps.pipeline_domain import load_custom_contexts, load_domain_contexts
from sage.cli.commands.apps.pipeline_knowledge import (
    PipelineKnowledgeBase,
    build_query_payload,
    get_default_knowledge_base,
)
from sage.cli.core.exceptions import CLIException
from sage.cli.templates import pipeline_blueprints as blueprints
from sage.common.config.output_paths import get_sage_paths
from sage.kernel.api.base_environment import BaseEnvironment
from sage.kernel.api.local_environment import LocalEnvironment

try:  # pragma: no cover - optional dependency at runtime only
    from isagellm import UnifiedInferenceClient

    OPENAI_AVAILABLE = True
    OPENAI_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - runtime check
    OPENAI_AVAILABLE = False
    OPENAI_IMPORT_ERROR = exc
    UnifiedInferenceClient = object  # type: ignore


DEFAULT_BACKEND = os.getenv("SAGE_PIPELINE_BUILDER_BACKEND", "openai")
DEFAULT_MODEL = os.getenv("SAGE_PIPELINE_BUILDER_MODEL") or os.getenv(
    "TEMP_GENERATOR_MODEL",
    "qwen-turbo-2025-02-11",
)
DEFAULT_BASE_URL = os.getenv("SAGE_PIPELINE_BUILDER_BASE_URL") or os.getenv(
    "TEMP_GENERATOR_BASE_URL"
)
DEFAULT_API_KEY = os.getenv("SAGE_PIPELINE_BUILDER_API_KEY") or os.getenv("TEMP_GENERATOR_API_KEY")


SYSTEM_PROMPT = textwrap.dedent(
    """
    You are SAGE Pipeline Builder, an expert in configuring Streaming-Augmented Generative Execution pipelines.
    Produce a *single* JSON object that can be saved as a YAML config for the SAGE CLI.

    Required JSON structure:
    {
      "pipeline": {
        "name": str,
        "description": str,
        "version": "1.0.0",
        "type": "local" | "remote"
      },
      "source": { ... },
      "stages": [
        {
          "id": str,
          "kind": "map" | "batch" | "service",
          "class": str,  # Python class path within SAGE
          "params": { ... },
          "summary": str
        }
      ],
      "sink": { ... },
      "services": [
        {
          "name": str,
          "class": str,
          "params": { ... }
        }
      ],
      "monitors": [ ... ],
      "notes": [str]
    }

    Rules:
    - Populate concrete SAGE component class paths (e.g. "sage.libs.rag.retriever.Wiki18FAISSRetriever").
    - When unsure, choose sensible defaults that work out-of-the-box.
    - Always include at least one stage and a sink.
    - Ensure identifiers are slugified (lowercase, hyphen-separated).
    - Parameters must be JSON-serializable and concise.
    - Never wrap the JSON in markdown fences or add commentary outside the JSON.
    """
).strip()


GRAPH_SYSTEM_PROMPT = textwrap.dedent(
    """
    You are SAGE Pipeline Architect, an expert agent workflow designer.
    Create expressive multi-stage graph pipelines that can include agents, tools, services,
    and messaging channels. Support branching, multi-agent orchestration, shared memories,
    and control flows whenever helpful.

    Produce a single JSON object with the structure:
    {
        "pipeline": {
            "name": str,
            "description": str,
            "version": "1.0.0",
            "type": "local" | "remote"
        },
        "graph": {
            "nodes": [
                {
                    "id": str,
                    "title": str,
                    "kind": "source" | "agent" | "tool" | "service" | "sink" | "router",
                    "class": str,
                    "params": { ... },
                    "inputs": [str],  # upstream node IDs
                    "outputs": [str],
                    "metadata": { ... }
                }
            ],
            "channels": [
                {
                    "id": str,
                    "type": "memory" | "event" | "queue" | "stream",
                    "description": str,
                    "participants": [str]
                }
            ]
        },
        "agents": [
            {
                "id": str,
                "role": str,
                "goals": [str],
                "tools": [str],
                "memory": {
                    "type": str,
                    "config": { ... }
                }
            }
        ],
        "services": [ ... ],
        "monitors": [ ... ],
        "notes": [str]
    }

    Guidelines:
    - Encourage the use of multiple agents when the task benefits from specialization.
    - Use inputs/outputs to express the DAG; omit when not relevant.
    - Fill params with concrete configuration that can run on SAGE where possible.
    - Include channels when agents need to coordinate or share state.
    - Ensure node IDs are unique kebab-case strings. Outputs list may be omitted when obvious.
    - Prefer referencing existing SAGE components (e.g. sage.libs.rag.*, examples.*) but
      custom classes are allowed if necessary—describe them in notes.
    """
).strip()


console = Console()
app = typer.Typer(help="🧠 使用大模型交互式创建 SAGE pipeline 配置")


def _render_blueprint_panel(
    matches: Sequence[tuple[blueprints.PipelineBlueprint, float]],
) -> Panel:
    lines: list[str] = []
    for index, (blueprint, score) in enumerate(matches, start=1):
        lines.append(
            textwrap.dedent(
                f"""
                [{index}] {blueprint.title} ({blueprint.id})
                匹配度: {score:.2f} | 关键词: {", ".join(blueprint.keywords) or "通用"}
                场景: {blueprint.description}
                """
            ).strip()
        )
    body = "\n\n".join(lines) or "暂无可用蓝图"
    return Panel(body, title="蓝图库候选", style="magenta")


def _render_template_panel(
    matches: Sequence[templates.TemplateMatch],
) -> Panel:
    lines: list[str] = []
    for index, match in enumerate(matches, start=1):
        template = match.template
        lines.append(
            textwrap.dedent(
                f"""
                [{index}] {template.title} ({template.id})
                匹配度: {match.score:.2f} | 标签: {", ".join(template.tags) or "通用"}
                示例: {template.example_path}
                场景: {template.description}
                """
            ).strip()
        )
    body = "\n\n".join(lines) or "暂无应用模板"
    return Panel(body, title="应用模板推荐", style="green")


def _blueprint_contexts(
    matches: Sequence[tuple[blueprints.PipelineBlueprint, float]],
) -> tuple[str, ...]:
    return tuple(
        blueprints.render_blueprint_prompt(blueprint, score) for blueprint, score in matches
    )


def _template_contexts(
    matches: Sequence[templates.TemplateMatch],
) -> tuple[str, ...]:
    return tuple(match.template.render_prompt(match.score) for match in matches)


class PipelineBuilderError(RuntimeError):
    """Raised when the builder cannot produce a valid plan."""


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "pipeline"


def _extract_json_object(text: str) -> dict[str, Any]:
    console.print(f"[dim]LLM response (first 500 chars): {text[:500]}[/dim]")  # Debug
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?", "", candidate, count=1).strip()
        candidate = re.sub(r"```$", "", candidate, count=1).strip()

    try:
        result = json.loads(candidate)
        console.print(f"[dim]Parsed JSON keys: {list(result.keys())}[/dim]")  # Debug
        return result
    except json.JSONDecodeError:
        pass

    brace_match = re.search(r"\{.*\}", candidate, re.DOTALL)
    if brace_match:
        try:
            result = json.loads(brace_match.group())
            console.print(f"[dim]Parsed JSON keys (from brace match): {list(result.keys())}[/dim]")
            return result
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise PipelineBuilderError(f"LLM returned invalid JSON: {exc}") from exc

    raise PipelineBuilderError("无法解析大模型返回的 JSON，请重试或调整描述。")


def _validate_plan(plan: dict[str, Any]) -> None:
    if "pipeline" not in plan or "stages" not in plan or "sink" not in plan:
        raise PipelineBuilderError(
            "生成的配置缺少必要字段 (pipeline/stages/sink)。请尝试提供更多需求细节。"
        )

    if not isinstance(plan["stages"], list) or not plan["stages"]:
        raise PipelineBuilderError("stages 字段必须是非空列表。")

    if not isinstance(plan.get("sink"), dict) or not plan["sink"].get("class"):
        raise PipelineBuilderError("sink 字段必须是包含 class 的对象。")

    source = plan.get("source")
    if source is not None and not isinstance(source, dict):
        raise PipelineBuilderError("source 字段必须是对象。")

    pipeline_block = plan["pipeline"]
    if "name" not in pipeline_block:
        pipeline_block["name"] = "untitled-pipeline"
    if "type" not in pipeline_block:
        pipeline_block["type"] = "local"
    if "version" not in pipeline_block:
        pipeline_block["version"] = "1.0.0"

    for stage in plan["stages"]:
        if not isinstance(stage, dict):
            raise PipelineBuilderError("stages 列表中的元素必须是对象。")
        stage_id = stage.get("id")
        stage["id"] = _slugify(str(stage_id)) if stage_id else _slugify(stage.get("class", "stage"))
        if not stage.get("class"):
            raise PipelineBuilderError("每个 stage 必须包含 class 字段。")
        params = stage.get("params", {})
        if params is None:
            stage["params"] = {}
        elif not isinstance(params, dict):
            raise PipelineBuilderError("stage 的 params 必须是对象 (key/value)。")


def _validate_graph_plan(plan: dict[str, Any]) -> None:
    pipeline_meta = plan.get("pipeline")
    graph = plan.get("graph")

    if not isinstance(pipeline_meta, dict):
        raise PipelineBuilderError("graph 配置缺少 pipeline 信息。")
    if not isinstance(graph, dict):
        raise PipelineBuilderError("graph 配置缺少 graph 节点定义。")

    nodes = graph.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise PipelineBuilderError("graph.nodes 必须是非空列表。")

    seen_ids: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            raise PipelineBuilderError("graph.nodes 中的元素必须是对象。")
        node_id = node.get("id")
        if not node_id:
            raise PipelineBuilderError("每个节点都需要 id。")
        slugified = _slugify(str(node_id))
        node["id"] = slugified
        if slugified in seen_ids:
            raise PipelineBuilderError(f"节点 id 重复 : {slugified}")
        seen_ids.add(slugified)

        if not node.get("class"):
            raise PipelineBuilderError(f"节点 {slugified} 缺少 class 字段。")

        for key in ("inputs", "outputs"):
            if key in node and node[key] is not None and not isinstance(node[key], list):
                raise PipelineBuilderError(f"节点 {slugified} 的 {key} 字段必须是列表。")

    channels = graph.get("channels") or []
    if not isinstance(channels, list):
        raise PipelineBuilderError("graph.channels 必须是列表。")
    for channel in channels:
        if not isinstance(channel, dict):
            raise PipelineBuilderError("graph.channels 中的元素必须是对象。")
        if not channel.get("id"):
            raise PipelineBuilderError("每个 channel 需要 id。")

    for block_name in ("agents", "services", "monitors"):
        if (
            block_name in plan
            and plan[block_name] is not None
            and not isinstance(plan[block_name], list)
        ):
            raise PipelineBuilderError(f"{block_name} 字段必须是列表。")

    notes = plan.get("notes")
    if notes is not None and not isinstance(notes, list):
        raise PipelineBuilderError("notes 字段必须是字符串列表。")


def _expand_params(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _expand_params(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_expand_params(item) for item in value]
    if isinstance(value, str):
        return os.path.expandvars(os.path.expanduser(value))
    return value


def _import_attr(path: str) -> Any:
    try:
        module_name, attr_name = path.rsplit(".", 1)
    except ValueError as exc:  # pragma: no cover - defensive
        raise CLIException(f"Invalid class path: {path}") from exc

    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise CLIException(f"无法导入模块 {module_name}: {exc}") from exc

    try:
        return getattr(module, attr_name)
    except AttributeError as exc:
        raise CLIException(f"模块 {module_name} 不包含 {attr_name}") from exc


def _ensure_pipeline_dict(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise CLIException("Pipeline 配置必须是字典结构。")
    return data


def _create_environment(
    plan: dict[str, Any], host: str | None, port: int | None
) -> BaseEnvironment:
    pipeline_meta = plan.get("pipeline") or {}
    pipeline_name = pipeline_meta.get("name", "sage-pipeline")
    env_settings = plan.get("environment") or {}
    env_config = _expand_params(env_settings.get("config") or {})

    env_type = (pipeline_meta.get("type") or "local").lower()
    if env_type in ("remote", "flownet"):
        from sage.kernel.api.flownet_environment import FlownetEnvironment  # import lazily

        placement = env_settings.get("placement_policy") or None
        return FlownetEnvironment(
            name=pipeline_name,
            config=env_config,
            placement_policy=placement,
        )

    return LocalEnvironment(name=pipeline_name, config=env_config)


def _register_services(env: BaseEnvironment, services: list[dict[str, Any]]) -> None:
    for service in services or []:
        name = service.get("name")
        class_path = service.get("class")
        if not name or not class_path:
            raise CLIException("每个 service 需要 name 和 class 字段。")

        service_class = _import_attr(class_path)
        args = service.get("args") or []
        if not isinstance(args, list):
            raise CLIException(f"Service {name} 的 args 必须是数组。")
        params = _expand_params(service.get("params") or {})
        env.register_service(name, service_class, *args, **params)


def _apply_source(env: BaseEnvironment, source: dict[str, Any]):
    if not source:
        raise CLIException("Pipeline 缺少 source 定义。")

    class_path = source.get("class")
    if not class_path:
        raise CLIException("source 需要提供 class 字段。")

    function_class = _import_attr(class_path)
    args = source.get("args") or []
    if not isinstance(args, list):
        raise CLIException("source 的 args 必须是数组。")
    params = _expand_params(source.get("params") or {})
    kind = (source.get("kind") or "batch").lower()

    if kind in {"batch", "collection"}:
        return env.from_batch(function_class, *args, **params)
    if kind in {"source", "stream"}:
        return env.from_source(function_class, *args, **params)
    if kind == "future":
        future_name = params.get("name") or source.get("id") or "future"
        return env.from_future(future_name)

    # Default to from_source for unknown kinds
    return env.from_source(function_class, *args, **params)


def _apply_stage(stream, stage: dict[str, Any]):
    class_path = stage.get("class")
    if not class_path:
        raise CLIException("stage 缺少 class 字段。")

    function_class = _import_attr(class_path)
    args = stage.get("args") or []
    if not isinstance(args, list):
        raise CLIException(f"stage {stage.get('id')} 的 args 必须是数组。")
    params = _expand_params(stage.get("params") or {})
    kind = (stage.get("kind") or "map").lower()

    if kind in {"map", "service", "batch"}:
        return stream.map(function_class, *args, **params)
    if kind == "flatmap":
        return stream.flatmap(function_class, *args, **params)
    if kind == "filter":
        return stream.filter(function_class, *args, **params)
    if kind == "keyby":
        strategy = params.pop("strategy", "hash")
        return stream.keyby(function_class, strategy=strategy, *args, **params)
    if kind == "sink":
        stream.sink(function_class, *args, **params)
        return stream

    console.print(f"[yellow]⚠️ 未知的 stage 类型 {kind}，默认使用 map。[/yellow]")
    return stream.map(function_class, *args, **params)


def _apply_sink(stream, sink: dict[str, Any]):
    if not sink:
        raise CLIException("Pipeline 缺少 sink 定义。")

    class_path = sink.get("class")
    if not class_path:
        raise CLIException("sink 需要提供 class 字段。")

    function_class = _import_attr(class_path)
    args = sink.get("args") or []
    if not isinstance(args, list):
        raise CLIException("sink 的 args 必须是数组。")
    params = _expand_params(sink.get("params") or {})
    stream.sink(function_class, *args, **params)


def _load_pipeline_file(path: Path) -> dict[str, Any]:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CLIException(f"找不到 pipeline 配置文件: {path}") from exc
    except OSError as exc:
        raise CLIException(f"读取 pipeline 文件失败: {exc}") from exc

    try:
        data = yaml.safe_load(content) or {}
    except yaml.YAMLError as exc:
        raise CLIException(f"解析 YAML 失败: {exc}") from exc

    return _ensure_pipeline_dict(data)


@dataclass
class BuilderConfig:
    backend: str
    model: str | None
    base_url: str | None
    api_key: str | None
    domain_contexts: tuple[str, ...] = ()
    knowledge_base: PipelineKnowledgeBase | None = None
    knowledge_top_k: int = 6
    show_knowledge: bool = False


@dataclass
class GraphBuilderConfig:
    backend: str
    model: str
    base_url: str | None
    api_key: str | None
    domain_contexts: tuple[str, ...] = ()
    knowledge_base: PipelineKnowledgeBase | None = None
    knowledge_top_k: int = 6
    show_knowledge: bool = False


class PipelinePlanGenerator:
    def __init__(self, config: BuilderConfig) -> None:
        self.config = config
        self._client: Any | None = None
        self._last_knowledge_contexts: tuple[str, ...] = ()
        self._blueprint_matches: tuple[tuple[blueprints.PipelineBlueprint, float], ...] = ()
        self._last_blueprint_contexts: tuple[str, ...] = ()
        self._template_matches: tuple[templates.TemplateMatch, ...] = ()
        self._last_template_contexts: tuple[str, ...] = ()

        if self.config.backend != "mock":
            if not OPENAI_AVAILABLE:
                message = f"未能导入 UnifiedInferenceClient：{OPENAI_IMPORT_ERROR}"
                raise PipelineBuilderError(message)
            # 使用工厂方法创建 UnifiedInferenceClient
            self._client = UnifiedInferenceClient.create(
                default_llm_model=self.config.model,
            )

    def generate(
        self,
        requirements: dict[str, Any],
        previous_plan: dict[str, Any] | None = None,
        feedback: str | None = None,
    ) -> dict[str, Any]:
        knowledge_contexts: tuple[str, ...] = ()
        if self.config.knowledge_base is not None:
            try:
                query_payload = build_query_payload(requirements, previous_plan, feedback)
                results = self.config.knowledge_base.search(
                    query_payload,
                    top_k=self.config.knowledge_top_k,
                )
                knowledge_contexts = tuple(item.text for item in results)
                self._last_knowledge_contexts = knowledge_contexts
            except Exception as exc:  # pragma: no cover - defensive
                console.print(f"[yellow]检索知识库时出错，将继续使用内建上下文: {exc}[/yellow]")
                self._last_knowledge_contexts = ()

        if self.config.show_knowledge and knowledge_contexts:
            console.print(
                Panel(
                    "\n\n".join(knowledge_contexts),
                    title="知识库检索结果",
                    style="blue",
                )
            )

        self._template_matches = tuple(templates.match_templates(requirements, top_k=3))
        self._last_template_contexts = _template_contexts(self._template_matches)
        if self._template_matches and self.config.show_knowledge:
            console.print(_render_template_panel(self._template_matches))

        if self.config.backend == "mock":
            self._blueprint_matches = tuple(blueprints.match_blueprints(requirements))
            self._last_blueprint_contexts = _blueprint_contexts(self._blueprint_matches)
            if self._blueprint_matches and self.config.show_knowledge:
                console.print(_render_blueprint_panel(self._blueprint_matches))
            return self._blueprint_plan(requirements, previous_plan, feedback)

        self._blueprint_matches = tuple(blueprints.match_blueprints(requirements))
        if self._blueprint_matches and self.config.show_knowledge:
            console.print(_render_blueprint_panel(self._blueprint_matches))
        self._last_blueprint_contexts = _blueprint_contexts(self._blueprint_matches)

        assert self._client is not None  # for type checker
        user_prompt = self._build_prompt(
            requirements,
            previous_plan,
            feedback,
            knowledge_contexts,
            self._last_template_contexts,
            self._last_blueprint_contexts,
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        console.print("🤖 正在请求大模型生成配置...", style="cyan")
        response = self._client.chat(messages, max_tokens=1200, temperature=0.2)
        plan = _extract_json_object(response)
        _validate_plan(plan)
        return plan

    def _build_prompt(
        self,
        requirements: dict[str, Any],
        previous_plan: dict[str, Any] | None,
        feedback: str | None,
        knowledge_contexts: tuple[str, ...],
        template_contexts: tuple[str, ...],
        blueprint_contexts: tuple[str, ...],
    ) -> str:
        blocks = [
            "请根据以下需求生成符合 SAGE 框架的 pipeline 配置 JSON：",
            json.dumps(requirements, ensure_ascii=False, indent=2),
        ]

        if template_contexts:
            blocks.append("以下应用模板仅作灵感参考，请结合需求自行设计：")
            for idx, snippet in enumerate(template_contexts, start=1):
                blocks.append(f"模板[{idx}]:\n{snippet.strip()}")

        if blueprint_contexts:
            blocks.append("以下蓝图可直接复用或在此基础上扩展：")
            for idx, snippet in enumerate(blueprint_contexts, start=1):
                blocks.append(f"蓝图[{idx}]:\n{snippet.strip()}")

        if knowledge_contexts:
            blocks.append("以下是从 SAGE 知识库检索到的参考信息：")
            for idx, snippet in enumerate(knowledge_contexts, start=1):
                blocks.append(f"知识[{idx}]:\n{snippet.strip()}")

        if self.config.domain_contexts:
            blocks.append("以下是与 SAGE 管道构建相关的参考资料：")
            for idx, snippet in enumerate(self.config.domain_contexts, start=1):
                blocks.append(f"参考[{idx}]:\n{snippet.strip()}")

        if previous_plan:
            blocks.append("这是上一版配置供参考：")
            blocks.append(json.dumps(previous_plan, ensure_ascii=False, indent=2))

        if feedback:
            blocks.append("请遵循以下修改意见更新配置：")
            blocks.append(feedback.strip())

        blocks.append("严格输出单个 JSON 对象，不要包含 markdown、注释或多余文字。")
        return "\n\n".join(blocks)

    def _blueprint_plan(
        self,
        requirements: dict[str, Any],
        previous_plan: dict[str, Any] | None,
        feedback: str | None,
    ) -> dict[str, Any]:
        blueprint = (
            self._blueprint_matches[0][0]
            if self._blueprint_matches
            else blueprints.DEFAULT_BLUEPRINT
        )
        return blueprints.build_pipeline_plan(blueprint, requirements, feedback)


class GraphPlanGenerator:
    def __init__(self, config: GraphBuilderConfig) -> None:
        self.config = config
        self._client: Any | None = None
        self._last_knowledge_contexts: tuple[str, ...] = ()
        self._blueprint_matches: tuple[tuple[blueprints.PipelineBlueprint, float], ...] = ()
        self._last_blueprint_contexts: tuple[str, ...] = ()

        if self.config.backend != "mock":
            if not OPENAI_AVAILABLE:
                message = f"未能导入 UnifiedInferenceClient：{OPENAI_IMPORT_ERROR}"
                raise PipelineBuilderError(message)
            # 使用工厂方法创建 UnifiedInferenceClient
            self._client = UnifiedInferenceClient.create(
                default_llm_model=self.config.model,
            )

    def generate(
        self,
        requirements: dict[str, Any],
        previous_plan: dict[str, Any] | None = None,
        feedback: str | None = None,
    ) -> dict[str, Any]:
        knowledge_contexts: tuple[str, ...] = ()
        if self.config.knowledge_base is not None:
            try:
                query_payload = build_query_payload(requirements, previous_plan, feedback)
                results = self.config.knowledge_base.search(
                    query_payload, top_k=self.config.knowledge_top_k
                )
                knowledge_contexts = tuple(item.text for item in results)
                self._last_knowledge_contexts = knowledge_contexts
            except Exception as exc:  # pragma: no cover - defensive
                console.print(f"[yellow]检索知识库时出错，将继续使用静态上下文: {exc}[/yellow]")
                self._last_knowledge_contexts = ()

        if self.config.show_knowledge and knowledge_contexts:
            console.print(
                Panel(
                    "\n\n".join(knowledge_contexts),
                    title="知识库检索结果",
                    style="blue",
                )
            )

        self._template_matches = tuple(templates.match_templates(requirements, top_k=4))
        self._last_template_contexts = _template_contexts(self._template_matches)
        if self._template_matches and self.config.show_knowledge:
            console.print(_render_template_panel(self._template_matches))

        if self.config.backend == "mock":
            self._blueprint_matches = tuple(blueprints.match_blueprints(requirements))
            self._last_blueprint_contexts = _blueprint_contexts(self._blueprint_matches)
            if self._blueprint_matches and self.config.show_knowledge:
                console.print(_render_blueprint_panel(self._blueprint_matches))
            return self._blueprint_plan(requirements, previous_plan, feedback)

        self._blueprint_matches = tuple(blueprints.match_blueprints(requirements))
        if self._blueprint_matches and self.config.show_knowledge:
            console.print(_render_blueprint_panel(self._blueprint_matches))
        self._last_blueprint_contexts = _blueprint_contexts(self._blueprint_matches)

        assert self._client is not None
        user_prompt = self._build_prompt(
            requirements,
            previous_plan,
            feedback,
            knowledge_contexts,
            self._last_template_contexts,
            self._last_blueprint_contexts,
        )
        messages = [
            {"role": "system", "content": GRAPH_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        console.print("🤖 正在请求大模型设计图谱...", style="cyan")
        response = self._client.chat(messages, max_tokens=1600, temperature=0.35)
        plan = _extract_json_object(response)
        return plan

    def _build_prompt(
        self,
        requirements: dict[str, Any],
        previous_plan: dict[str, Any] | None,
        feedback: str | None,
        knowledge_contexts: tuple[str, ...],
        template_contexts: tuple[str, ...],
        blueprint_contexts: tuple[str, ...],
    ) -> str:
        blocks: list[str] = [
            "请根据以下需求设计一个多智能体 SAGE pipeline 图谱：",
            json.dumps(requirements, ensure_ascii=False, indent=2),
        ]

        if template_contexts:
            blocks.append("以下应用模板可作为参考灵感，请主动规划合适的多智能体结构：")
            for idx, snippet in enumerate(template_contexts, start=1):
                blocks.append(f"模板[{idx}]:\n{snippet.strip()}")

        if blueprint_contexts:
            blocks.append("以下蓝图可作为起点进行扩展：")
            for idx, snippet in enumerate(blueprint_contexts, start=1):
                blocks.append(f"蓝图[{idx}]:\n{snippet.strip()}")

        if knowledge_contexts:
            blocks.append("以下是从 SAGE 知识库检索到的参考信息：")
            for idx, snippet in enumerate(knowledge_contexts, start=1):
                blocks.append(f"知识[{idx}]:\n{snippet.strip()}")

        if self.config.domain_contexts:
            blocks.append("以下是与 SAGE 组件相关的参考资料：")
            for idx, snippet in enumerate(self.config.domain_contexts, start=1):
                blocks.append(f"参考[{idx}]:\n{snippet.strip()}")

        if previous_plan:
            blocks.append("上一版图谱结构供参考：")
            blocks.append(json.dumps(previous_plan, ensure_ascii=False, indent=2))

        if feedback:
            blocks.append("请依据以下反馈调整图谱：")
            blocks.append(feedback.strip())

        blocks.append("严格输出单个 JSON 对象，不要包含 markdown、注释或多余文字。")
        return "\n\n".join(blocks)

    def _blueprint_plan(
        self,
        requirements: dict[str, Any],
        previous_plan: dict[str, Any] | None,
        feedback: str | None,
    ) -> dict[str, Any]:
        blueprint = (
            self._blueprint_matches[0][0]
            if self._blueprint_matches
            else blueprints.DEFAULT_BLUEPRINT
        )
        return blueprints.build_graph_plan(blueprint, requirements, feedback)


def _render_plan(plan: dict[str, Any]) -> None:
    pipeline_meta = plan.get("pipeline", {})
    console.print(
        Panel.fit(
            f"名称: [cyan]{pipeline_meta.get('name', '-')}[/cyan]\n"
            f"描述: {pipeline_meta.get('description', '-')}\n"
            f"类型: {pipeline_meta.get('type', '-')}",
            title="Pipeline 元信息",
            style="green",
        )
    )

    table = Table(title="阶段概览", show_header=True, header_style="bold blue")
    table.add_column("ID", style="cyan")
    table.add_column("类型")
    table.add_column("类路径")
    table.add_column("摘要")

    for stage in plan.get("stages", []):
        table.add_row(
            stage.get("id", "-"),
            stage.get("kind", "-"),
            stage.get("class", "-"),
            stage.get("summary", ""),
        )
    console.print(table)

    notes = plan.get("notes") or []
    if notes:
        console.print(Panel("\n".join(f"• {note}" for note in notes), title="Notes"))


def _plan_to_yaml(plan: dict[str, Any]) -> str:
    data = dict(plan)
    stages = data.pop("stages", [])

    # Flatten stages into numbered keys for readability in YAML
    data["stages"] = stages
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


def render_pipeline_plan(plan: dict[str, Any]) -> None:
    _render_plan(plan)


def _graph_plan_to_yaml(plan: dict[str, Any]) -> str:
    return yaml.safe_dump(plan, allow_unicode=True, sort_keys=False)


def _save_plan(plan: dict[str, Any], output: Path | None, overwrite: bool) -> Path:
    yaml_text = _plan_to_yaml(plan)
    if output is None:
        default_name = _slugify(plan.get("pipeline", {}).get("name", "pipeline"))
        output_dir = get_sage_paths().output_dir / "pipelines"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{default_name}.yaml"
    else:
        output_path = Path(output).expanduser().resolve()
        if output_path.is_dir():
            default_name = _slugify(plan.get("pipeline", {}).get("name", "pipeline"))
            output_path = output_path / f"{default_name}.yaml"
        output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists() and not overwrite:
        raise PipelineBuilderError(f"文件已存在: {output_path}。使用 --overwrite 强制覆盖。")

    output_path.write_text(yaml_text, encoding="utf-8")
    return output_path


def _preview_yaml(yaml_text: str) -> None:
    syntax = Syntax(yaml_text, "yaml", theme="monokai", line_numbers=False)
    console.print(Panel(syntax, title="YAML 预览"))


def pipeline_plan_to_yaml(plan: dict[str, Any]) -> str:
    return _plan_to_yaml(plan)


def preview_pipeline_plan(plan: dict[str, Any]) -> None:
    yaml_text = _plan_to_yaml(plan)
    _preview_yaml(yaml_text)


def save_pipeline_plan(plan: dict[str, Any], output: Path | None, overwrite: bool) -> Path:
    return _save_plan(plan, output, overwrite)


def execute_pipeline_plan(
    plan: dict[str, Any],
    autostop: bool = True,
    host: str | None = None,
    port: int | None = None,
    *,
    console_override: Console | None = None,
) -> str | None:
    """Apply a pipeline configuration and submit it to the target environment."""

    log_console = console_override or console

    env = _create_environment(plan, host, port)

    services = plan.get("services") or []
    if services:
        log_console.print(f"🔧 注册 {len(services)} 个服务...")
        _register_services(env, services)

    source = plan.get("source")
    if not source:
        raise PipelineBuilderError("Pipeline plan must include a 'source' configuration")
    log_console.print("🚰 配置 source")
    stream = _apply_source(env, source)

    stages = plan.get("stages") or []
    for stage in stages:
        stage_id = stage.get("id", "stage")
        log_console.print(f"➡️  应用阶段: {stage_id}")
        stream = _apply_stage(stream, stage)

    sink = plan.get("sink")
    if not sink:
        raise PipelineBuilderError("Pipeline plan must include a 'sink' configuration")
    log_console.print("🛬 配置终端 sink")
    _apply_sink(stream, sink)

    if plan.get("monitors"):
        log_console.print("[yellow]📈 当前版本暂未自动配置 monitors，需手动集成。[/yellow]")

    log_console.print("🚀 提交 pipeline...")
    job_uuid = env.submit(autostop=autostop)  # type: ignore[call-arg]

    if job_uuid:
        log_console.print(f"✅ Pipeline 已提交，作业 UUID: [green]{job_uuid}[/green]")
    else:
        log_console.print("✅ Pipeline 已提交。")

    if autostop:
        log_console.print("🎉 批处理完成并自动清理。")
    else:
        log_console.print("⏳ Pipeline 正在运行，可使用 'sage job list' 查看状态。")

    return job_uuid


def _collect_requirements(
    name: str | None,
    goal: str | None,
    requirements_path: Path | None,
    interactive: bool,
) -> dict[str, Any]:
    requirements: dict[str, Any] = {}

    if requirements_path:
        path = Path(requirements_path).expanduser().resolve()
        if not path.exists():
            raise PipelineBuilderError(f"找不到需求文件: {path}")
        requirements = json.loads(path.read_text(encoding="utf-8"))

    if name:
        requirements["name"] = name
    if goal:
        requirements["goal"] = goal

    if not interactive:
        missing = [key for key in ("name", "goal") if key not in requirements]
        if missing:
            raise PipelineBuilderError(f"非交互模式下必须提供: {', '.join(missing)}")
        return requirements

    if "name" not in requirements:
        requirements["name"] = typer.prompt("Pipeline 名称", default="My Pipeline")
    if "goal" not in requirements:
        requirements["goal"] = typer.prompt("主要目标", default="构建一个问答型 RAG pipeline")

    if "data_sources" not in requirements:
        requirements["data_sources"] = typer.prompt("数据来源 (可留空)", default="文档知识库")
    if "latency_budget" not in requirements:
        requirements["latency_budget"] = typer.prompt(
            "延迟/吞吐需求 (可留空)", default="实时体验优先"
        )
    if "constraints" not in requirements:
        requirements["constraints"] = typer.prompt("特殊约束 (可留空)", default="")

    return requirements


@app.command("build")
def build_pipeline(  # noqa: D401 - Typer handles CLI docs
    name: str | None = typer.Option(None, help="Pipeline 名称"),
    goal: str | None = typer.Option(None, help="Pipeline 目标描述"),
    backend: str = typer.Option(
        DEFAULT_BACKEND,
        help="LLM 后端 (openai/compatible/mock)",
    ),
    model: str | None = typer.Option(None, help="LLM 模型名称"),
    base_url: str | None = typer.Option(None, help="LLM Base URL"),
    api_key: str | None = typer.Option(None, help="LLM API Key"),
    requirements_path: Path | None = typer.Option(
        None,
        exists=False,
        help="需求 JSON 文件路径，提供已有输入以跳过交互",
    ),
    output: Path | None = typer.Option(
        None,
        help="输出 YAML 文件路径 (可为目录)",
    ),
    overwrite: bool = typer.Option(False, help="允许覆盖已存在的文件"),
    non_interactive: bool = typer.Option(False, help="非交互模式 (需要同时提供名称和目标)"),
    context_limit: int = typer.Option(
        4,
        "--context-limit",
        min=0,
        max=12,
        help="提示中包含的示例配置数量",
    ),
    context_file: list[Path] = typer.Option(
        [],
        "--context-file",
        "-c",
        help="额外上下文文件 (纯文本)，可重复指定",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    show_contexts: bool = typer.Option(False, "--show-contexts", help="打印用于提示的大模型上下文"),
    disable_knowledge: bool = typer.Option(
        False,
        "--no-knowledge",
        help="禁用从本地知识库自动检索上下文",
    ),
    knowledge_top_k: int = typer.Option(
        5,
        "--knowledge-top-k",
        min=1,
        max=12,
        help="每次检索返回的知识片段数量",
    ),
    show_knowledge: bool = typer.Option(
        False,
        "--show-knowledge",
        help="打印知识库检索结果",
    ),
    embedding_method: str | None = typer.Option(
        None,
        "--embedding-method",
        "-e",
        help="知识库检索使用的 embedding 方法 (hash/openai/hf/zhipu 等)",
    ),
    embedding_model: str | None = typer.Option(
        None,
        "--embedding-model",
        help="Embedding 模型名称 (如 text-embedding-3-small)",
    ),
) -> None:
    """使用大模型交互式生成 SAGE pipeline 配置。"""

    resolved_model = model or DEFAULT_MODEL
    resolved_base_url = base_url or DEFAULT_BASE_URL
    resolved_api_key = api_key or DEFAULT_API_KEY

    if backend != "mock" and not resolved_api_key:
        raise PipelineBuilderError(
            "未提供 API Key。请通过 --api-key 或环境变量 SAGE_PIPELINE_BUILDER_API_KEY/TEMP_GENERATOR_API_KEY 设置。"
        )

    requirements = _collect_requirements(
        name,
        goal,
        requirements_path,
        interactive=not non_interactive,
    )

    try:
        domain_contexts = list(load_domain_contexts(limit=context_limit))
    except Exception as exc:  # pragma: no cover - defensive
        raise PipelineBuilderError(f"加载默认上下文失败: {exc}") from exc

    if context_file:
        try:
            custom_contexts = load_custom_contexts(tuple(context_file))
            domain_contexts.extend(custom_contexts)
        except RuntimeError as exc:
            raise PipelineBuilderError(str(exc)) from exc

    if show_contexts and domain_contexts:
        console.print(
            Panel(
                "\n\n".join(domain_contexts),
                title="LLM 提示上下文",
                style="magenta",
            )
        )

    knowledge_base: PipelineKnowledgeBase | None = None
    if not disable_knowledge:
        try:
            knowledge_base = get_default_knowledge_base(
                embedding_method=embedding_method,
                embedding_model=embedding_model,
            )
            # Show which embedding method is being used
            method_name = embedding_method or os.getenv("SAGE_PIPELINE_EMBEDDING_METHOD", "hash")
            console.print(f"🎯 知识库使用 [cyan]{method_name}[/cyan] embedding 方法", style="dim")
        except Exception as exc:
            console.print(f"[yellow]初始化知识库失败，将继续使用静态上下文: {exc}[/yellow]")

    config = BuilderConfig(
        backend=backend,
        model=resolved_model,
        base_url=resolved_base_url,
        api_key=resolved_api_key,
        domain_contexts=tuple(domain_contexts),
        knowledge_base=knowledge_base,
        knowledge_top_k=knowledge_top_k,
        show_knowledge=show_knowledge,
    )

    generator = PipelinePlanGenerator(config)

    plan: dict[str, Any] | None = None
    feedback: str | None = None

    for _iteration in range(1, 6):
        try:
            plan = generator.generate(requirements, plan, feedback)
        except PipelineBuilderError as exc:
            console.print(f"[red]生成失败: {exc}[/red]")
            if non_interactive:
                raise
            if not typer.confirm("是否重新尝试生成？", default=True):
                raise
            feedback = typer.prompt("请提供更详细的需求或修改建议")
            continue

        _render_plan(plan)

        if non_interactive:
            break

        if typer.confirm("对配置满意吗？", default=True):
            break

        feedback = typer.prompt(
            "请输入需要调整的点（例如修改某一阶段/替换组件）",
            default="",
        )
        if not feedback or not feedback.strip():
            console.print("未提供修改意见，保持当前版本。", style="yellow")
            break

    if plan is None:
        raise PipelineBuilderError("未能生成有效的 pipeline 配置。")

    yaml_text = _plan_to_yaml(plan)
    _preview_yaml(yaml_text)

    if not non_interactive and not typer.confirm("是否保存该配置?", default=True):
        console.print("操作已取消，未写入文件。", style="yellow")
        return

    output_path = _save_plan(plan, output, overwrite)
    console.print(f"✅ 配置已保存到: [green]{output_path}[/green]")


@app.command("run")
def run_pipeline(
    config: Path = typer.Argument(..., exists=False, help="Pipeline YAML 配置文件"),
    autostop: bool = typer.Option(
        True, "--autostop/--no-autostop", help="提交后是否等待批处理完成"
    ),
    host: str | None = typer.Option(
        None,
        "--host",
        help="远程环境 JobManager 主机 (仅当 pipeline.type=remote 时生效)",
    ),
    port: int | None = typer.Option(
        None,
        "--port",
        min=1,
        max=65535,
        help="远程环境 JobManager 端口 (仅当 pipeline.type=remote 时生效)",
    ),
) -> None:
    """加载 YAML 配置并运行 SAGE pipeline。"""

    try:
        config_path = Path(config).expanduser().resolve()
        plan = _load_pipeline_file(config_path)

        pipeline_meta = plan.get("pipeline") or {}
        pipeline_name = pipeline_meta.get("name", config_path.stem)

        console.print(
            Panel.fit(
                f"名称: [cyan]{pipeline_name}[/cyan]\n类型: {pipeline_meta.get('type', 'local')}\n来源: {config_path}",
                title="运行 Pipeline",
                style="blue",
            )
        )

        execute_pipeline_plan(
            plan,
            autostop=autostop,
            host=host,
            port=port,
            console_override=console,
        )

    except CLIException as exc:
        console.print(f"[red]❌ {exc}[/red]")
        raise typer.Exit(1) from exc


@app.command("analyze-embedding")
def analyze_embedding_methods(
    query: str = typer.Argument(..., help="测试查询文本"),
    top_k: int = typer.Option(3, "--top-k", "-k", min=1, max=10, help="返回 Top-K 结果数量"),
    methods: list[str] | None = typer.Option(
        None,
        "--method",
        "-m",
        help="指定要比较的 embedding 方法（可多次使用）",
    ),
    show_vectors: bool = typer.Option(False, "--show-vectors", help="显示向量详情"),
) -> None:
    """分析和比较不同 embedding 方法在 Pipeline Builder 知识库上的检索效果。

    这个命令帮助你选择最适合你场景的 embedding 方法。

    示例:
        sage pipeline analyze-embedding "如何构建 RAG pipeline"
        sage pipeline analyze-embedding "向量检索" -m hash -m openai -m hf
    """
    from sage.common.components.sage_embedding.registry import EmbeddingRegistry

    # 如果没有指定方法，使用默认的几个常用方法
    if not methods:
        all_methods = EmbeddingRegistry.list_methods()
        # 优先选择免费/本地方法
        default_methods = []
        for m in ["hash", "mockembedder", "hf"]:
            if m in all_methods:
                default_methods.append(m)
        methods = default_methods[:3] if default_methods else all_methods[:3]

    console.print(
        Panel(
            f"🔍 查询: [cyan]{query}[/cyan]\n"
            f"📊 对比方法: {', '.join(methods)}\n"
            f"📚 知识库: SAGE Pipeline Builder",
            title="Embedding 方法分析",
            style="blue",
        )
    )

    results_by_method = {}

    for method in methods:
        try:
            console.print(f"\n⚙️  测试方法: [cyan]{method}[/cyan]")

            # 创建使用该 embedding 方法的知识库
            kb = PipelineKnowledgeBase(
                max_chunks=500,  # 使用较小的数据集加快测试
                allow_download=False,
                embedding_method=method,
            )

            # 执行检索
            import time

            start = time.time()
            search_results = kb.search(query, top_k=top_k)
            elapsed = time.time() - start

            results_by_method[method] = {
                "results": search_results,
                "time": elapsed,
                "dimension": (
                    len(search_results[0].vector)
                    if search_results and search_results[0].vector
                    else 0
                ),
            }

            console.print(
                f"   ✓ 检索完成 (耗时: {elapsed * 1000:.2f}ms, 维度: {results_by_method[method]['dimension']})"
            )

        except Exception as exc:
            console.print(f"   ✗ [red]{method} 失败: {exc}[/red]")
            continue

    if not results_by_method:
        console.print("[red]所有方法都失败了，请检查配置。[/red]")
        raise typer.Exit(1)

    # 显示对比结果
    console.print("\n" + "=" * 80)
    console.print("[bold green]📊 检索结果对比[/bold green]\n")

    for method, data in results_by_method.items():
        console.print(f"[bold cyan]━━━ {method.upper()} ━━━[/bold cyan]")
        console.print(f"⏱️  耗时: {data['time'] * 1000:.2f}ms | 📐 维度: {data['dimension']}")

        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("排名", style="dim", width=4)
        table.add_column("得分", justify="right", width=8)
        table.add_column("类型", width=8)
        table.add_column("文本片段", width=60)

        for idx, chunk in enumerate(data["results"], 1):
            preview = (
                chunk.text[:100].replace("\n", " ") + "..."
                if len(chunk.text) > 100
                else chunk.text.replace("\n", " ")
            )
            table.add_row(
                f"#{idx}",
                f"{chunk.score:.4f}",
                chunk.kind,
                preview,
            )

        console.print(table)

        if show_vectors and data["results"]:
            first_vec = data["results"][0].vector
            if first_vec:
                vec_preview = str(first_vec[:10])[:-1] + ", ...]"
                console.print(f"   向量示例: {vec_preview}\n")

        console.print()

    # 推荐最佳方法
    console.print("[bold yellow]💡 推荐建议:[/bold yellow]\n")

    fastest = min(results_by_method.items(), key=lambda x: x[1]["time"])
    console.print(f"⚡ 最快方法: [green]{fastest[0]}[/green] ({fastest[1]['time'] * 1000:.2f}ms)")

    # 简单的相关性评估（基于平均得分）
    avg_scores = {
        method: (
            sum(r.score for r in data["results"]) / len(data["results"]) if data["results"] else 0
        )
        for method, data in results_by_method.items()
    }
    best_relevance = max(avg_scores.items(), key=lambda x: x[1])
    console.print(
        f"🎯 最相关方法: [green]{best_relevance[0]}[/green] (平均得分: {best_relevance[1]:.4f})"
    )

    console.print(
        f"\n💡 [dim]使用推荐方法:[/dim] "
        f"[cyan]sage pipeline build --embedding-method {best_relevance[0]}[/cyan]"
    )


@app.command("create-embedding")
def create_embedding_pipeline(
    template: str = typer.Option(
        "rag",
        "--template",
        "-t",
        help="Pipeline 模板类型: rag, knowledge-base, hybrid-search, multi-strategy",
    ),
    embedding_method: str = typer.Option(
        "hf",
        "--embedding-method",
        "-e",
        help="Embedding 方法 (hf/openai/jina/zhipu/cohere/bedrock/ollama/siliconcloud/nvidia_openai/sagellm)",
    ),
    embedding_model: str | None = typer.Option(
        None,
        "--embedding-model",
        "-m",
        help="Embedding 模型名称（未指定则使用默认）",
    ),
    engine: str = typer.Option(
        "sagellm",
        "--engine",
        help="推理引擎 (仅支持 sagellm)",
    ),
    use_vllm: bool = typer.Option(
        False,
        "--vllm",
        help="[已移除] vllm 已在 v0.3.0 移除",
    ),
    llm_model: str | None = typer.Option(
        None,
        "--llm-model",
        help="LLM 模型名称（RAG 模板需要）",
    ),
    dense_method: str | None = typer.Option(
        None,
        "--dense-method",
        help="Hybrid 模板：Dense embedding 方法",
    ),
    sparse_method: str | None = typer.Option(
        None,
        "--sparse-method",
        help="Hybrid 模板：Sparse embedding 方法（默认 bm25s）",
    ),
    query_method: str | None = typer.Option(
        None,
        "--query-method",
        help="Multi-strategy 模板：查询用 embedding 方法（快速）",
    ),
    doc_method: str | None = typer.Option(
        None,
        "--doc-method",
        help="Multi-strategy 模板：文档用 embedding 方法（高质量）",
    ),
    batch_method: str | None = typer.Option(
        None,
        "--batch-method",
        help="Multi-strategy 模板：批量处理用 embedding 方法",
    ),
    chunk_size: int = typer.Option(512, "--chunk-size", help="文档分块大小"),
    chunk_overlap: int = typer.Option(50, "--chunk-overlap", help="分块重叠大小"),
    batch_size: int = typer.Option(32, "--batch-size", help="批处理大小"),
    enable_cache: bool = typer.Option(True, "--cache/--no-cache", help="启用缓存"),
    normalize: bool = typer.Option(True, "--normalize/--no-normalize", help="向量归一化"),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="输出 YAML 文件路径",
    ),
    overwrite: bool = typer.Option(False, "--overwrite", help="覆盖已存在的文件"),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="交互式配置模板参数",
    ),
) -> None:
    """使用预定义模板创建基于 EmbeddingService 的 pipeline。

    支持的模板:
    - rag: RAG pipeline with embedding service
    - knowledge-base: 高吞吐量知识库构建
    - hybrid-search: Dense + Sparse 混合检索
    - multi-strategy: 智能路由多策略 embedding

    示例:
        # 创建 HuggingFace RAG pipeline
        sage pipeline create-embedding -t rag -e hf -m BAAI/bge-small-zh-v1.5

        # 创建 sageLLM 高性能知识库构建（默认引擎）
        sage pipeline create-embedding -t knowledge-base

        # 创建混合检索 pipeline
        sage pipeline create-embedding -t hybrid-search --dense-method openai --sparse-method bm25s

        # 创建多策略智能路由
        sage pipeline create-embedding -t multi-strategy --query-method hash --doc-method openai
    """
    from .pipeline_embedding import generate_embedding_pipeline

    # 交互式配置
    if interactive:
        console.print(
            Panel(
                "🎯 交互式 Embedding Pipeline 配置向导",
                style="cyan",
            )
        )

        template_choices = ["rag", "knowledge-base", "hybrid-search", "multi-strategy"]
        template = typer.prompt(
            "选择模板类型",
            type=str,
            default=template,
            show_choices=True,
        )

        if template not in template_choices:
            console.print(f"[red]无效的模板: {template}[/red]")
            raise typer.Exit(1)

        embedding_method = typer.prompt(
            "Embedding 方法 (hf/openai/jina/zhipu/cohere/bedrock/ollama/siliconcloud/nvidia_openai/sagellm)",
            type=str,
            default=embedding_method,
        )

        if embedding_method not in ["sagellm", "hash", "mockembedder"]:
            embedding_model = typer.prompt(
                "Embedding 模型名称",
                type=str,
                default=embedding_model or "",
            )

        engine = typer.prompt(
            "推理引擎 (仅支持 sagellm)",
            type=str,
            default=engine,
        )

        if template == "rag":
            llm_model = typer.prompt(
                "LLM 模型名称",
                type=str,
                default=llm_model or "Qwen/Qwen2.5-7B-Instruct",
            )
        elif template == "hybrid-search":
            dense_method = typer.prompt(
                "Dense embedding 方法",
                type=str,
                default=dense_method or embedding_method,
            )
            sparse_method = typer.prompt(
                "Sparse embedding 方法",
                type=str,
                default=sparse_method or "bm25s",
            )
        elif template == "multi-strategy":
            query_method = typer.prompt(
                "查询用 embedding 方法 (快速)",
                type=str,
                default=query_method or "hash",
            )
            doc_method = typer.prompt(
                "文档用 embedding 方法 (高质量)",
                type=str,
                default=doc_method or embedding_method,
            )
            batch_method = typer.prompt(
                "批量处理用 embedding 方法",
                type=str,
                default=batch_method or engine if engine == "sagellm" else embedding_method,
            )

    # 构建参数
    kwargs = {
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "batch_size": batch_size,
        "enable_cache": enable_cache,
        "normalize": normalize,
    }

    # 根据模板类型添加特定参数
    if template == "rag":
        if not llm_model:
            llm_model = "Qwen/Qwen2.5-7B-Instruct"
        kwargs["llm_model"] = llm_model
    elif template == "hybrid-search":
        if not dense_method:
            dense_method = embedding_method
        if not sparse_method:
            sparse_method = "bm25s"
        kwargs["dense_method"] = dense_method
        kwargs["sparse_method"] = sparse_method
        # dense_model 使用 embedding_model
        if embedding_model:
            kwargs["dense_model"] = embedding_model
    elif template == "multi-strategy":
        if not query_method:
            query_method = "hash"
        if not doc_method:
            doc_method = embedding_method
        if not batch_method:
            batch_method = engine if engine == "sagellm" else embedding_method
        kwargs["query_method"] = query_method
        kwargs["doc_method"] = doc_method
        kwargs["batch_method"] = batch_method

    # 生成配置
    # Handle removed --vllm flag
    if use_vllm:
        console.print(
            "[red]Error:[/red] --vllm has been removed in SAGE v0.3.0. Use --engine sagellm instead."
        )
        raise typer.Exit(1)

    console.print(
        Panel(
            f"📋 模板: [cyan]{template}[/cyan]\n"
            f"🔧 Embedding: [cyan]{embedding_method}[/cyan]\n"
            f"🚀 引擎: [cyan]{engine}[/cyan]",
            title="生成 Pipeline 配置",
            style="blue",
        )
    )

    try:
        plan = generate_embedding_pipeline(
            use_case=template,
            embedding_method=embedding_method,
            embedding_model=embedding_model,
            engine=engine,
            **kwargs,
        )
    except ValueError as exc:
        console.print(f"[red]生成失败: {exc}[/red]")
        raise typer.Exit(1) from exc

    # 显示配置
    _render_plan(plan)

    # 预览 YAML
    yaml_text = _plan_to_yaml(plan)
    _preview_yaml(yaml_text)

    # 保存
    if not interactive or typer.confirm("保存配置?", default=True):
        output_path = _save_plan(plan, output, overwrite)
        console.print(f"✅ 配置已保存到: [green]{output_path}[/green]")

        # 提示如何运行
        console.print(f"\n💡 运行此 pipeline:\n   [cyan]sage pipeline run {output_path}[/cyan]")
    else:
        console.print("[yellow]未保存配置。[/yellow]")


__all__ = [
    "app",
    "BuilderConfig",
    "GraphBuilderConfig",
    "PipelinePlanGenerator",
    "GraphPlanGenerator",
    "PipelineBuilderError",
    "render_pipeline_plan",
    "pipeline_plan_to_yaml",
    "preview_pipeline_plan",
    "save_pipeline_plan",
    "execute_pipeline_plan",
    "create_embedding_pipeline",
    "analyze_embedding_methods",
]
