#!/usr/bin/env python3
"""Interactive pipeline builder powered by LLMs."""

from __future__ import annotations

import json
import os
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from sage.common.config.output_paths import get_sage_paths

try:  # pragma: no cover - optional dependency at runtime only
    from sage.libs.utils.openaiclient import OpenAIClient

    OPENAI_AVAILABLE = True
    OPENAI_IMPORT_ERROR: Optional[Exception] = None
except Exception as exc:  # pragma: no cover - runtime check
    OPENAI_AVAILABLE = False
    OPENAI_IMPORT_ERROR = exc
    OpenAIClient = object  # type: ignore


DEFAULT_BACKEND = os.getenv("SAGE_PIPELINE_BUILDER_BACKEND", "openai")
DEFAULT_MODEL = os.getenv("SAGE_PIPELINE_BUILDER_MODEL") or os.getenv(
    "SAGE_CHAT_MODEL",
    "qwen-turbo-2025-02-11",
)
DEFAULT_BASE_URL = os.getenv("SAGE_PIPELINE_BUILDER_BASE_URL") or os.getenv(
    "SAGE_CHAT_BASE_URL"
)
DEFAULT_API_KEY = os.getenv("SAGE_PIPELINE_BUILDER_API_KEY") or os.getenv(
    "SAGE_CHAT_API_KEY"
)


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


console = Console()
app = typer.Typer(help="🧠 使用大模型交互式创建 SAGE pipeline 配置")


class PipelineBuilderError(RuntimeError):
    """Raised when the builder cannot produce a valid plan."""


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "pipeline"


def _extract_json_object(text: str) -> Dict[str, Any]:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?", "", candidate, count=1).strip()
        candidate = re.sub(r"```$", "", candidate, count=1).strip()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    brace_match = re.search(r"\{.*\}", candidate, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group())
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise PipelineBuilderError(f"LLM returned invalid JSON: {exc}") from exc

    raise PipelineBuilderError("无法解析大模型返回的 JSON，请重试或调整描述。")


def _validate_plan(plan: Dict[str, Any]) -> None:
    if "pipeline" not in plan or "stages" not in plan or "sink" not in plan:
        raise PipelineBuilderError(
            "生成的配置缺少必要字段 (pipeline/stages/sink)。请尝试提供更多需求细节。"
        )

    if not isinstance(plan["stages"], list) or not plan["stages"]:
        raise PipelineBuilderError("stages 字段必须是非空列表。")

    pipeline_block = plan["pipeline"]
    if "name" not in pipeline_block:
        pipeline_block["name"] = "untitled-pipeline"
    if "type" not in pipeline_block:
        pipeline_block["type"] = "local"
    if "version" not in pipeline_block:
        pipeline_block["version"] = "1.0.0"


@dataclass
class BuilderConfig:
    backend: str
    model: str
    base_url: Optional[str]
    api_key: Optional[str]
    domain_contexts: Tuple[str, ...]


class PipelinePlanGenerator:
    def __init__(self, config: BuilderConfig) -> None:
        self.config = config
        self._client = None  # type: Optional[Any]

        if self.config.backend != "mock":
            if not OPENAI_AVAILABLE:
                message = "未能导入 OpenAIClient：{}".format(OPENAI_IMPORT_ERROR)
                raise PipelineBuilderError(message)
            self._client = OpenAIClient(
                model_name=self.config.model,
                base_url=self.config.base_url,
                api_key=self.config.api_key,
                seed=42,
            )

    def generate(
        self,
        requirements: Dict[str, Any],
        previous_plan: Optional[Dict[str, Any]] = None,
        feedback: Optional[str] = None,
    ) -> Dict[str, Any]:
        if self.config.backend == "mock":
            return self._mock_plan(requirements, previous_plan, feedback)

        assert self._client is not None  # for type checker
        user_prompt = self._build_prompt(requirements, previous_plan, feedback)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        console.print("🤖 正在请求大模型生成配置...", style="cyan")
        response = self._client.generate(messages, max_tokens=1200, temperature=0.2)
        plan = _extract_json_object(response)
        _validate_plan(plan)
        return plan

    def _build_prompt(
        self,
        requirements: Dict[str, Any],
        previous_plan: Optional[Dict[str, Any]],
        feedback: Optional[str],
    ) -> str:
        blocks = [
            "请根据以下需求生成符合 SAGE 框架的 pipeline 配置 JSON：",
            json.dumps(requirements, ensure_ascii=False, indent=2),
        ]

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

        blocks.append(
            "严格输出单个 JSON 对象，不要包含 markdown、注释或多余文字。"
        )
        return "\n\n".join(blocks)

    @staticmethod
    def _mock_plan(
        requirements: Dict[str, Any],
        previous_plan: Optional[Dict[str, Any]],
        feedback: Optional[str],
    ) -> Dict[str, Any]:
        name = _slugify(requirements.get("name") or "demo-pipeline")
        description = requirements.get("goal", "Auto-generated pipeline")
        plan = {
            "pipeline": {
                "name": name,
                "description": description,
                "version": "1.0.0",
                "type": "local",
            },
            "source": {
                "class": "examples.rag.rag_simple.SimpleQuestionSource",
                "params": {"questions": ["示例问题"]},
                "summary": "Sample in-memory question list",
            },
            "stages": [
                {
                    "id": "retriever",
                    "kind": "map",
                    "class": "examples.rag.rag_simple.SimpleRetriever",
                    "params": {},
                    "summary": "Keyword-based retriever for demo",
                },
                {
                    "id": "promptor",
                    "kind": "map",
                    "class": "examples.rag.rag_simple.SimplePromptor",
                    "params": {},
                    "summary": "Builds prompts for generator",
                },
                {
                    "id": "generator",
                    "kind": "map",
                    "class": "sage.libs.rag.generator.OpenAIGenerator",
                    "params": {
                        "method": "openai",
                        "model_name": DEFAULT_MODEL,
                        "base_url": DEFAULT_BASE_URL,
                        "api_key": "${OPENAI_API_KEY}",
                    },
                    "summary": "LLM generator via OpenAI-compatible endpoint",
                },
            ],
            "sink": {
                "class": "examples.rag.rag_simple.SimpleTerminalSink",
                "params": {},
                "summary": "Print answers to console",
            },
            "services": [],
            "monitors": [],
            "notes": [
                "Mock backend生成，仅用于离线测试。",
                "部署时请完善数据源与生成模型参数。",
            ],
        }

        if feedback and "file" in feedback.lower():
            plan["sink"] = {
                "class": "sage.libs.io_utils.file.FileSink",
                "params": {"path": "output/pipeline_results.txt"},
                "summary": "Persist results to local file",
            }

        return plan


def _render_plan(plan: Dict[str, Any]) -> None:
    pipeline_meta = plan.get("pipeline", {})
    console.print(
        Panel.fit(
            f"名称: [cyan]{pipeline_meta.get('name', '-') }[/cyan]\n"
            f"描述: {pipeline_meta.get('description', '-') }\n"
            f"类型: {pipeline_meta.get('type', '-') }",
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


def _plan_to_yaml(plan: Dict[str, Any]) -> str:
    data = dict(plan)
    stages = data.pop("stages", [])

    # Flatten stages into numbered keys for readability in YAML
    data["stages"] = stages
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


def _save_plan(plan: Dict[str, Any], output: Optional[Path], overwrite: bool) -> Path:
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


def _collect_requirements(
    name: Optional[str],
    goal: Optional[str],
    requirements_path: Optional[Path],
    interactive: bool,
) -> Dict[str, Any]:
    requirements: Dict[str, Any] = {}

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
            raise PipelineBuilderError(
                f"非交互模式下必须提供: {', '.join(missing)}"
            )
        return requirements

    if "name" not in requirements:
        requirements["name"] = typer.prompt("Pipeline 名称", default="My Pipeline")
    if "goal" not in requirements:
        requirements["goal"] = typer.prompt(
            "主要目标", default="构建一个问答型 RAG pipeline"
        )

    if "data_sources" not in requirements:
        requirements["data_sources"] = typer.prompt(
            "数据来源 (可留空)", default="文档知识库"
        )
    if "latency_budget" not in requirements:
        requirements["latency_budget"] = typer.prompt(
            "延迟/吞吐需求 (可留空)", default="实时体验优先"
        )
    if "constraints" not in requirements:
        requirements["constraints"] = typer.prompt(
            "特殊约束 (可留空)", default=""
        )

    return requirements


@app.command("build")
def build_pipeline(  # noqa: D401 - Typer handles CLI docs
    name: Optional[str] = typer.Option(None, help="Pipeline 名称"),
    goal: Optional[str] = typer.Option(None, help="Pipeline 目标描述"),
    backend: str = typer.Option(
        DEFAULT_BACKEND,
        help="LLM 后端 (openai/compatible/mock)",
    ),
    model: Optional[str] = typer.Option(None, help="LLM 模型名称"),
    base_url: Optional[str] = typer.Option(None, help="LLM Base URL"),
    api_key: Optional[str] = typer.Option(None, help="LLM API Key"),
    requirements_path: Optional[Path] = typer.Option(
        None,
        exists=False,
        help="需求 JSON 文件路径，提供已有输入以跳过交互",
    ),
    output: Optional[Path] = typer.Option(
        None,
        help="输出 YAML 文件路径 (可为目录)",
    ),
    overwrite: bool = typer.Option(False, help="允许覆盖已存在的文件"),
    non_interactive: bool = typer.Option(
        False, help="非交互模式 (需要同时提供名称和目标)"
    ),
) -> None:
    """使用大模型交互式生成 SAGE pipeline 配置。"""

    resolved_model = model or DEFAULT_MODEL
    resolved_base_url = base_url or DEFAULT_BASE_URL
    resolved_api_key = api_key or DEFAULT_API_KEY

    if backend != "mock" and not resolved_api_key:
        raise PipelineBuilderError(
            "未提供 API Key。请通过 --api-key 或环境变量 SAGE_PIPELINE_BUILDER_API_KEY/SAGE_CHAT_API_KEY 设置。"
        )

    requirements = _collect_requirements(
        name,
        goal,
        requirements_path,
        interactive=not non_interactive,
    )

    config = BuilderConfig(
        backend=backend,
        model=resolved_model,
        base_url=resolved_base_url,
        api_key=resolved_api_key,
    )

    generator = PipelinePlanGenerator(config)

    plan: Optional[Dict[str, Any]] = None
    feedback: Optional[str] = None

    for iteration in range(1, 6):
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
        if not feedback.strip():
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


__all__ = ["app"]
