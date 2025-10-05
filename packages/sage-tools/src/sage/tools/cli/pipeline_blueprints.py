#!/usr/bin/env python3
"""Blueprint library describing reusable SAGE pipelines."""

from __future__ import annotations

import copy
import re
import textwrap
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", str(value or "").lower()).strip("-")
    return slug or "pipeline"


def _graph_kind(kind: str) -> str:
    normalized = (kind or "").lower()
    mapping = {
        "source": "source",
        "batch": "source",
        "stream": "source",
        "map": "tool",
        "tool": "tool",
        "agent": "agent",
        "service": "service",
        "router": "router",
        "sink": "sink",
    }
    return mapping.get(normalized, "tool")


@dataclass(frozen=True)
class SourceSpec:
    id: str
    title: str
    class_path: str
    kind: str = "source"
    params: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_plan(self) -> Dict[str, Any]:
        return {
            "class": self.class_path,
            "kind": self.kind,
            "params": copy.deepcopy(self.params),
            "summary": self.summary,
        }

    def to_graph_node(self, outputs: Sequence[str]) -> Dict[str, Any]:
        node = {
            "id": self.id,
            "title": self.title,
            "kind": _graph_kind(self.kind),
            "class": self.class_path,
            "params": copy.deepcopy(self.params),
        }
        if outputs:
            node["outputs"] = list(outputs)
        if self.metadata:
            node["metadata"] = copy.deepcopy(self.metadata)
        return node


@dataclass(frozen=True)
class StageSpec:
    id: str
    title: str
    kind: str
    class_path: str
    params: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_plan(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "class": self.class_path,
            "params": copy.deepcopy(self.params),
            "summary": self.summary,
        }

    def to_graph_node(
        self, inputs: Sequence[str], outputs: Sequence[str]
    ) -> Dict[str, Any]:
        node = {
            "id": self.id,
            "title": self.title,
            "kind": _graph_kind(self.kind),
            "class": self.class_path,
            "params": copy.deepcopy(self.params),
        }
        if inputs:
            node["inputs"] = list(inputs)
        if outputs:
            node["outputs"] = list(outputs)
        if self.metadata:
            node["metadata"] = copy.deepcopy(self.metadata)
        return node


@dataclass(frozen=True)
class SinkSpec:
    id: str
    title: str
    class_path: str
    kind: str = "sink"
    params: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_plan(self) -> Dict[str, Any]:
        plan = {
            "class": self.class_path,
            "params": copy.deepcopy(self.params),
            "summary": self.summary,
        }
        if self.kind:
            plan["kind"] = self.kind
        return plan

    def to_graph_node(self, inputs: Sequence[str]) -> Dict[str, Any]:
        node = {
            "id": self.id,
            "title": self.title,
            "kind": _graph_kind(self.kind),
            "class": self.class_path,
            "params": copy.deepcopy(self.params),
        }
        if inputs:
            node["inputs"] = list(inputs)
        if self.metadata:
            node["metadata"] = copy.deepcopy(self.metadata)
        return node


@dataclass(frozen=True)
class PipelineBlueprint:
    id: str
    title: str
    description: str
    keywords: Tuple[str, ...]
    source: SourceSpec
    stages: Tuple[StageSpec, ...]
    sink: SinkSpec
    services: Tuple[Dict[str, Any], ...] = ()
    monitors: Tuple[Dict[str, Any], ...] = ()
    notes: Tuple[str, ...] = ()
    graph_channels: Tuple[Dict[str, Any], ...] = ()
    graph_agents: Tuple[Dict[str, Any], ...] = ()

    def render_notes(self, feedback: Optional[str]) -> List[str]:
        notes = list(self.notes)
        if feedback and feedback.strip():
            notes.append(f"反馈: {feedback.strip()}")
        if not notes:
            notes.append("Blueprint-generated configuration for experimentation")
        return notes


BLUEPRINT_LIBRARY: Tuple[PipelineBlueprint, ...] = (
    PipelineBlueprint(
        id="rag-simple-demo",
        title="Simple RAG Demo",
        description="Use the examples.rag.rag_simple operators to run an end-to-end retrieval and answer pipeline.",
        keywords=(
            "rag",
            "qa",
            "retrieval",
            "demo",
            "support",
            "问答",
            "客户支持",
            "客服",
            "知识助手",
        ),
        source=SourceSpec(
            id="question-source",
            title="Question Source",
            class_path="examples.rag.rag_simple.SimpleQuestionSource",
            summary="Emit curated customer-style questions from the rag_simple example.",
        ),
        stages=(
            StageSpec(
                id="retriever",
                title="Keyword Retriever",
                kind="map",
                class_path="examples.rag.rag_simple.SimpleRetriever",
                summary="Lookup canned snippets matching question keywords.",
                metadata={"description": "Deterministic dictionary-based retriever"},
            ),
            StageSpec(
                id="prompt-builder",
                title="Prompt Builder",
                kind="map",
                class_path="examples.rag.rag_simple.SimplePromptor",
                summary="Combine context and question into a generation prompt.",
            ),
            StageSpec(
                id="generator",
                title="Answer Generator",
                kind="map",
                class_path="examples.rag.rag_simple.SimpleGenerator",
                summary="Create a formatted answer using rule-based heuristics.",
            ),
        ),
        sink=SinkSpec(
            id="terminal-sink",
            title="Terminal Sink",
            class_path="examples.rag.rag_simple.SimpleTerminalSink",
            summary="Pretty-print answers to the terminal with context snippets.",
        ),
        notes=(
            "基于 examples.rag.rag_simple 模块构建，适合离线演示",
            "无需外部服务或大模型依赖即可运行",
        ),
        graph_channels=(
            {
                "id": "qa-context",
                "type": "memory",
                "description": "Retriever and generator share contextual snippets",
                "participants": ["retriever", "generator"],
            },
        ),
        graph_agents=(
            {
                "id": "qa-orchestrator",
                "role": "Answer Coordinator",
                "goals": [
                    "解析客户提问并选取合适知识片段",
                    "输出清晰的答案与下一步建议",
                ],
                "tools": ["retriever", "generator"],
                "memory": {"type": "scratchpad", "config": {"channel": "qa-context"}},
            },
        ),
    ),
    PipelineBlueprint(
        id="hello-world-batch",
        title="Hello World Batch Processor",
        description="Demonstrates a batch pipeline that uppercases greeting messages.",
        keywords=("batch", "hello", "tutorial", "uppercase"),
        source=SourceSpec(
            id="hello-source",
            title="Hello Batch Source",
            class_path="examples.tutorials.hello_world.HelloBatch",
            kind="batch",
            params={"max_count": 5},
            summary="Generate a finite series of 'Hello, World!' strings.",
        ),
        stages=(
            StageSpec(
                id="uppercase",
                title="Uppercase Formatter",
                kind="map",
                class_path="examples.tutorials.hello_world.UpperCaseMap",
                summary="Convert each greeting to uppercase text.",
            ),
        ),
        sink=SinkSpec(
            id="console-printer",
            title="Console Printer",
            class_path="examples.tutorials.hello_world.PrintSink",
            summary="Print processed greetings to standard output.",
        ),
        notes=(
            "来源：examples.tutorials.hello_world 示例",
            "演示批处理来源、Map 转换与终端汇聚",
        ),
    ),
    PipelineBlueprint(
        id="hello-world-log",
        title="Hello World Log Printer",
        description="Extends the hello world batch example with a reusable logging sink from sage.libs.",
        keywords=("batch", "logging", "demo"),
        source=SourceSpec(
            id="hello-log-source",
            title="Hello Batch Source",
            class_path="examples.tutorials.hello_world.HelloBatch",
            kind="batch",
            params={"max_count": 3},
            summary="Emit a few greeting messages for structured logging.",
        ),
        stages=(
            StageSpec(
                id="uppercase",
                title="Uppercase Formatter",
                kind="map",
                class_path="examples.tutorials.hello_world.UpperCaseMap",
                summary="Normalize messages to uppercase before logging.",
            ),
        ),
        sink=SinkSpec(
            id="structured-print",
            title="Structured Print Sink",
            class_path="sage.libs.io_utils.sink.PrintSink",
            summary="Stream outputs to console/logs using the reusable PrintSink operator.",
            params={"quiet": False},
        ),
        notes=(
            "结合 tutorials 示例与 sage.libs.io_utils.PrintSink 组件",
            "适合演示如何接入内置工具库的通用算子",
        ),
    ),
    PipelineBlueprint(
        id="rag-multimodal-fusion",
        title="Multimodal Landmark QA",
        description="Fuse text and image context for landmark questions, then generate structured answers with an LLM.",
        keywords=(
            "rag",
            "qa",
            "multimodal",
            "fusion",
            "landmark",
            "图像",
            "多模态",
        ),
        source=SourceSpec(
            id="landmark-question-source",
            title="Landmark Question Source",
            class_path="examples.rag.qa_multimodal_fusion.MultimodalQuestionSource",
            summary="Emit landmark-themed questions covering位置、属性与建筑背景。",
        ),
        stages=(
            StageSpec(
                id="multimodal-retriever",
                title="Multimodal Fusion Retriever",
                kind="map",
                class_path="examples.rag.qa_multimodal_fusion.MultimodalFusionRetriever",
                summary="Combine text and synthetic image embeddings to retrieve landmark context.",
                metadata={
                    "description": "演示多模态嵌入融合及可配置检索策略",
                    "modalities": ["text", "image"],
                },
            ),
            StageSpec(
                id="qa-promptor",
                title="QA Prompt Builder",
                kind="map",
                class_path="sage.libs.rag.promptor.QAPromptor",
                params={
                    "template": textwrap.dedent(
                        """
                        基于以下多模态检索结果回答问题：

                        检索到的相关信息：
                        {retrieved_context}

                        原始问题：{original_query}

                        请提供准确、详细的回答，结合文本和视觉信息：
                        """
                    ).strip(),
                    "max_context_length": 2000,
                },
                summary="Turn fusion results into an LLM-ready prompt with contextual metadata.",
            ),
            StageSpec(
                id="generator",
                title="OpenAI Generator",
                kind="map",
                class_path="sage.libs.rag.generator.OpenAIGenerator",
                params={
                    "model_name": "gpt-3.5-turbo",
                    "temperature": 0.7,
                    "max_tokens": 300,
                },
                summary="Generate structured responses using an OpenAI-compatible model.",
                metadata={"requires": "OPENAI_API_KEY"},
            ),
        ),
        sink=SinkSpec(
            id="terminal-json",
            title="Terminal JSON Sink",
            class_path="sage.libs.io_utils.sink.TerminalSink",
            params={"output_format": "json", "pretty_print": True},
            summary="Render responses in JSON format for inspection or downstream tooling.",
        ),
        notes=(
            "基于 examples.rag.qa_multimodal_fusion 模块",
            "需要可用的 OpenAI 兼容推理服务或替换生成算子",
            "多模态融合可扩展至 SageDB 或外部向量库",
        ),
        graph_channels=(
            {
                "id": "fusion-context-channel",
                "type": "memory",
                "description": "共享多模态检索结果，供 prompt 构建与生成阶段复用",
                "participants": ["multimodal-retriever", "qa-promptor", "generator"],
            },
        ),
        graph_agents=(
            {
                "id": "multimodal-strategist",
                "role": "Landmark Knowledge Curator",
                "goals": [
                    "整合多模态检索结果",
                    "生成详尽且可信的地标答案",
                ],
                "tools": ["multimodal-retriever", "generator"],
                "memory": {
                    "type": "scratchpad",
                    "config": {"channel": "fusion-context-channel"},
                },
            },
        ),
    ),
)

DEFAULT_BLUEPRINT = BLUEPRINT_LIBRARY[0]


def requirements_text(requirements: Dict[str, Any]) -> str:
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


def compute_match_score(requirements: Dict[str, Any], blueprint: PipelineBlueprint) -> float:
    text = requirements_text(requirements)
    if not text:
        return 0.2

    score = 0.0
    for keyword in blueprint.keywords:
        term = keyword.lower()
        if not term:
            continue
        if term in text:
            score += 1.0
        else:
            tokens = [token for token in term.replace("/", " ").split() if token]
            if tokens and all(token in text for token in tokens):
                score += 0.6
    if blueprint.id in text:
        score += 0.5
    if blueprint.title.lower() in text:
        score += 0.4
    length_bonus = min(0.4, 0.05 * max(0, len(text.split()) - 5))
    score += length_bonus
    if blueprint.keywords:
        score = score / len(blueprint.keywords)
    return max(0.0, min(1.2, score))


def match_blueprints(
    requirements: Dict[str, Any],
    top_k: int = 3,
) -> List[Tuple[PipelineBlueprint, float]]:
    candidates = [
        (blueprint, compute_match_score(requirements, blueprint))
        for blueprint in BLUEPRINT_LIBRARY
    ]
    candidates.sort(key=lambda item: item[1], reverse=True)
    top = candidates[: top_k or 1]
    if all(bp is not DEFAULT_BLUEPRINT for bp, _ in top):
        top.append((DEFAULT_BLUEPRINT, 0.1))
    return top


def select_blueprint(requirements: Dict[str, Any]) -> PipelineBlueprint:
    return match_blueprints(requirements, top_k=1)[0][0]


def build_pipeline_plan(
    blueprint: PipelineBlueprint,
    requirements: Dict[str, Any],
    feedback: Optional[str] = None,
) -> Dict[str, Any]:
    plan = {
        "pipeline": {
            "name": _slugify(requirements.get("name") or blueprint.id),
            "description": requirements.get("goal") or blueprint.description,
            "version": "1.0.0",
            "type": "local",
        },
        "source": blueprint.source.to_plan(),
        "stages": [stage.to_plan() for stage in blueprint.stages],
        "sink": blueprint.sink.to_plan(),
        "services": [copy.deepcopy(service) for service in blueprint.services],
        "monitors": [copy.deepcopy(monitor) for monitor in blueprint.monitors],
        "notes": blueprint.render_notes(feedback),
    }
    return plan


def build_graph_plan(
    blueprint: PipelineBlueprint,
    requirements: Dict[str, Any],
    feedback: Optional[str] = None,
) -> Dict[str, Any]:
    components: List[Any] = [blueprint.source, *blueprint.stages, blueprint.sink]
    nodes: List[Dict[str, Any]] = []

    for index, component in enumerate(components):
        prev_id = components[index - 1].id if index > 0 else None
        next_id = components[index + 1].id if index + 1 < len(components) else None

        if isinstance(component, SourceSpec):
            outputs = [next_id] if next_id else []
            nodes.append(component.to_graph_node(outputs))
        elif isinstance(component, StageSpec):
            inputs = [prev_id] if prev_id else []
            outputs = [next_id] if next_id else []
            nodes.append(component.to_graph_node(inputs, outputs))
        else:
            inputs = [prev_id] if prev_id else []
            nodes.append(component.to_graph_node(inputs))

    channels = [copy.deepcopy(channel) for channel in blueprint.graph_channels]
    if feedback and feedback.strip():
        channels.append(
            {
                "id": f"{blueprint.id}-feedback",
                "type": "event",
                "description": feedback.strip(),
                "participants": [components[0].id, components[-1].id],
            }
        )

    plan = {
        "pipeline": {
            "name": _slugify(requirements.get("name") or f"{blueprint.id}-graph"),
            "description": requirements.get("goal") or blueprint.description,
            "version": "1.0.0",
            "type": "local",
        },
        "graph": {
            "nodes": nodes,
            "channels": channels,
        },
        "agents": [copy.deepcopy(agent) for agent in blueprint.graph_agents],
        "services": [copy.deepcopy(service) for service in blueprint.services],
        "monitors": [copy.deepcopy(monitor) for monitor in blueprint.monitors],
        "notes": blueprint.render_notes(feedback),
    }
    return plan


def render_blueprint_prompt(blueprint: PipelineBlueprint, score: float) -> str:
    component_lines = [
        f"source → {blueprint.source.class_path}",
        *[f"{stage.id} ({stage.kind}) → {stage.class_path}" for stage in blueprint.stages],
        f"sink → {blueprint.sink.class_path}",
    ]
    components_block = "\n".join(f"- {line}" for line in component_lines)
    notes_line = "; ".join(blueprint.notes) if blueprint.notes else "无"

    summary = textwrap.dedent(
        f"""
        Blueprint: {blueprint.title} ({blueprint.id})
        Match confidence: {score:.2f}
        适用关键词: {', '.join(blueprint.keywords) or '通用'}
        场景描述: {blueprint.description}
        主要组件:
        {components_block}
        备注: {notes_line}
        """
    ).strip()
    return summary


__all__ = [
    "SourceSpec",
    "StageSpec",
    "SinkSpec",
    "PipelineBlueprint",
    "BLUEPRINT_LIBRARY",
    "DEFAULT_BLUEPRINT",
    "match_blueprints",
    "select_blueprint",
    "build_pipeline_plan",
    "build_graph_plan",
    "render_blueprint_prompt",
]
