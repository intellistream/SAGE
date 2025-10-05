#!/usr/bin/env python3
"""Catalog of reusable application templates derived from SAGE examples."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from sage.tools.cli import pipeline_blueprints


@dataclass(frozen=True)
class ApplicationTemplate:
    """Reusable application template built from a pipeline blueprint."""

    id: str
    title: str
    description: str
    tags: Tuple[str, ...]
    example_path: str
    blueprint_id: str
    default_requirements: Dict[str, Any]
    guidance: str
    notes: Tuple[str, ...] = ()

    def blueprint(self) -> pipeline_blueprints.PipelineBlueprint:
        blueprint = _BLUEPRINT_INDEX.get(self.blueprint_id)
        if blueprint is None:
            raise KeyError(f"Blueprint '{self.blueprint_id}' not found for template '{self.id}'")
        return blueprint

    def pipeline_plan(self) -> Dict[str, Any]:
        """Return a deep copy of the pipeline plan for this template."""

        blueprint = self.blueprint()
        return pipeline_blueprints.build_pipeline_plan(
            blueprint,
            self.default_requirements,
            feedback=None,
        )

    def graph_plan(self) -> Optional[Dict[str, Any]]:
        blueprint = self.blueprint()
        return pipeline_blueprints.build_graph_plan(
            blueprint,
            self.default_requirements,
            feedback=None,
        )

    def render_prompt(self, score: Optional[float] = None) -> str:
        """Render a prompt snippet describing the template for LLM guidance."""

        plan = self.pipeline_plan()
        stages = plan.get("stages", [])
        stage_lines = [
            f"              • {stage['id']}: {stage['class']} ({stage.get('summary', '')})"
            for stage in stages
        ]
        stage_text = "\n".join(stage_lines) if stage_lines else "              • (无阶段信息)"
        note_lines = [f"- {note}" for note in plan.get("notes", []) if note]
        notes_text = "\n".join(note_lines) if note_lines else "  - 无"
        score_line = f"匹配度: {score:.2f}" if score is not None else ""
        source_class = plan.get("source", {}).get("class", "<unknown>")
        sink_class = plan.get("sink", {}).get("class", "<unknown>")
        prompt = textwrap.dedent(
            f"""
            模板: {self.title} ({self.id}) {score_line}
            示例路径: {self.example_path}
            标签: {', '.join(self.tags) or '通用'}
            描述: {self.description}

            默认Pipeline:
              Source: {source_class}
{stage_text}
              Sink: {sink_class}

            注意事项:
            {notes_text}

            额外指导:
            {self.guidance.strip()}
            """
        ).strip()
        return prompt


@dataclass(frozen=True)
class TemplateMatch:
    template: ApplicationTemplate
    score: float


def list_templates() -> Tuple[ApplicationTemplate, ...]:
    return TEMPLATE_LIBRARY


def list_template_ids() -> Tuple[str, ...]:
    return tuple(template.id for template in TEMPLATE_LIBRARY)


def get_template(template_id: str) -> ApplicationTemplate:
    for template in TEMPLATE_LIBRARY:
        if template.id == template_id:
            return template
    raise KeyError(f"Unknown application template: {template_id}")


def match_templates(
    requirements: Dict[str, Any],
    top_k: int = 5,
) -> List[TemplateMatch]:
    candidates = [
        TemplateMatch(template=template, score=_score_template(requirements, template))
        for template in TEMPLATE_LIBRARY
    ]
    candidates.sort(key=lambda item: item.score, reverse=True)
    top = candidates[: top_k or 1]
    if all(match.template.id != DEFAULT_TEMPLATE_ID for match in top):
        top.append(TemplateMatch(get_template(DEFAULT_TEMPLATE_ID), 0.1))
    return top


def _score_template(requirements: Dict[str, Any], template: ApplicationTemplate) -> float:
    text = _requirements_text(requirements)
    if not text:
        return 0.2

    score = 0.0
    for tag in template.tags:
        term = tag.lower()
        if not term:
            continue
        if term in text:
            score += 1.0
        else:
            tokens = [token for token in term.replace("/", " ").split() if token]
            if tokens and all(token in text for token in tokens):
                score += 0.6
    if template.id in text:
        score += 0.4
    if template.title.lower() in text:
        score += 0.4
    length_bonus = min(0.4, 0.05 * max(0, len(text.split()) - 5))
    score += length_bonus
    if template.tags:
        score = score / len(template.tags)
    return max(0.0, min(1.2, score))


def _requirements_text(requirements: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in (
        "goal",
        "initial_prompt",
        "description",
        "notes",
        "constraints",
        "data_sources",
        "name",
    ):
        value = requirements.get(key)
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            parts.extend(str(item) for item in value)
        elif isinstance(value, dict):
            parts.extend(str(v) for v in value.values())
        else:
            parts.append(str(value))
    return " ".join(parts).lower()


_BLUEPRINT_INDEX = {blueprint.id: blueprint for blueprint in pipeline_blueprints.BLUEPRINT_LIBRARY}


def _notes(*values: str) -> Tuple[str, ...]:
    cleaned: List[str] = []
    for value in values:
        value = value.strip()
        if value:
            cleaned.append(value)
    return tuple(cleaned)


TEMPLATE_LIBRARY: Tuple[ApplicationTemplate, ...] = (
    ApplicationTemplate(
        id="rag-simple-demo",
        title="客服知识助手 (RAG Simple)",
        description="面向客服问答的简化RAG工作流，使用内置示例算子即可离线演示。",
    tags=("rag", "qa", "support", "问答", "客户支持", "知识助手"),
        example_path="examples/rag/rag_simple.py",
        blueprint_id="rag-simple-demo",
        default_requirements={
            "name": "customer-support-rag",
            "goal": "构建客服知识助手，针对常见问题进行检索增强回答",
            "description": "使用examples.rag.rag_simple中的算子，演示从提问到答案的完整流程",
        },
        guidance=textwrap.dedent(
            """
            适合客服场景的FAQ自动答复。可直接运行，无需远程服务，强调演示友好性。
            可扩展：替换检索器为真实向量库、改造生成器为大模型API。
            """
        ),
        notes=_notes(
            "基于 examples.rag.rag_simple 模块",
            "默认配置为本地演示，可逐步替换为生产组件",
        ),
    ),
    ApplicationTemplate(
        id="hello-world-batch",
        title="Hello World 批处理管道",
        description="教学用途的批处理示例，从批数据源到终端打印，展示基本算子组合。",
        tags=("batch", "tutorial", "hello", "入门"),
        example_path="examples/tutorials/hello_world.py",
        blueprint_id="hello-world-batch",
        default_requirements={
            "name": "hello-world-batch",
            "goal": "快速体验 SAGE 的批处理操作",
            "description": "从HelloBatch批处理源开始，将消息转大写并输出到终端",
        },
        guidance=textwrap.dedent(
            """
            作为教学或单元测试模板，演示批处理执行模型。可扩展：替换UpperCaseMap为数据清洗或格式化逻辑。
            """
        ),
        notes=_notes("无外部依赖，适合快速验证环境配置。"),
    ),
    ApplicationTemplate(
        id="hello-world-log",
        title="结构化日志打印管道",
        description="基于Hello World示例，使用通用PrintSink输出结构化日志。",
        tags=("batch", "logging", "demo", "日志"),
        example_path="examples/tutorials/hello_world.py",
        blueprint_id="hello-world-log",
        default_requirements={
            "name": "hello-world-logging",
            "goal": "演示如何复用通用 PrintSink 组件输出结构化日志",
            "description": "批量生成问候语，上游转大写，下游通过 PrintSink 输出",
        },
        guidance=textwrap.dedent(
            """
            适合作为日志/监控集成的起点，可将 PrintSink 替换为 Kafka、Webhook 等下游。
            """
        ),
        notes=_notes("依赖 sage.libs.io_utils.sink.PrintSink 组件。"),
    ),
    ApplicationTemplate(
        id="rag-multimodal-fusion",
        title="多模态地标问答助手",
        description="结合文本与图像特征的多模态检索，再通过LLM生成答案，演示高级RAG场景。",
        tags=(
            "rag",
            "multimodal",
            "fusion",
            "qa",
            "多模态",
            "图像",
        ),
        example_path="examples/rag/qa_multimodal_fusion.py",
        blueprint_id="rag-multimodal-fusion",
        default_requirements={
            "name": "multimodal-landmark-qa",
            "goal": "回答关于地标建筑的多模态问答",
            "description": "融合文本与图像嵌入检索，调用LLM生成结构化答案",
        },
        guidance=textwrap.dedent(
            """
            需要可用的OpenAI兼容模型或自建推理服务。若无远程模型，可将生成阶段替换为规则模板或本地模型。
            模板展示了如何在Promptor阶段注入自定义模板以及如何配置多模态检索输出。
            """
        ),
        notes=_notes(
            "源自 examples.rag.qa_multimodal_fusion",
            "默认使用 OpenAIGenerator，需要配置 API Key",
            "可扩展：替换多模态检索器为 SageDB / 向量数据库",
        ),
    ),
)

DEFAULT_TEMPLATE_ID = TEMPLATE_LIBRARY[0].id