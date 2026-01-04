#!/usr/bin/env python3
"""Catalog of reusable application templates derived from SAGE examples."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from typing import Any

from sage.cli.templates import pipeline_blueprints


@dataclass(frozen=True)
class ApplicationTemplate:
    """Reusable application template built from a pipeline blueprint."""

    id: str
    title: str
    description: str
    tags: tuple[str, ...]
    example_path: str
    blueprint_id: str
    default_requirements: dict[str, Any]
    guidance: str
    notes: tuple[str, ...] = ()

    def blueprint(self) -> pipeline_blueprints.PipelineBlueprint:
        blueprint = _BLUEPRINT_INDEX.get(self.blueprint_id)
        if blueprint is None:
            raise KeyError(f"Blueprint '{self.blueprint_id}' not found for template '{self.id}'")
        return blueprint

    def pipeline_plan(self) -> dict[str, Any]:
        """Return a deep copy of the pipeline plan for this template."""

        blueprint = self.blueprint()
        return pipeline_blueprints.build_pipeline_plan(
            blueprint,
            self.default_requirements,
            feedback=None,
        )

    def graph_plan(self) -> dict[str, Any] | None:
        blueprint = self.blueprint()
        return pipeline_blueprints.build_graph_plan(
            blueprint,
            self.default_requirements,
            feedback=None,
        )

    def render_prompt(self, score: float | None = None) -> str:
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
            标签: {", ".join(self.tags) or "通用"}
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


def list_templates() -> tuple[ApplicationTemplate, ...]:
    return TEMPLATE_LIBRARY


def list_template_ids() -> tuple[str, ...]:
    return tuple(template.id for template in TEMPLATE_LIBRARY)


def get_template(template_id: str) -> ApplicationTemplate:
    for template in TEMPLATE_LIBRARY:
        if template.id == template_id:
            return template
    raise KeyError(f"Unknown application template: {template_id}")


def match_templates(
    requirements: dict[str, Any],
    top_k: int = 5,
) -> list[TemplateMatch]:
    candidates = [
        TemplateMatch(template=template, score=_score_template(requirements, template))
        for template in TEMPLATE_LIBRARY
    ]
    candidates.sort(key=lambda item: item.score, reverse=True)
    top = candidates[: top_k or 1]
    if all(match.template.id != DEFAULT_TEMPLATE_ID for match in top):
        top.append(TemplateMatch(get_template(DEFAULT_TEMPLATE_ID), 0.1))
    return top


def _score_template(requirements: dict[str, Any], template: ApplicationTemplate) -> float:
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


def _requirements_text(requirements: dict[str, Any]) -> str:
    parts: list[str] = []
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


def _notes(*values: str) -> tuple[str, ...]:
    cleaned: list[str] = []
    for value in values:
        value = value.strip()
        if value:
            cleaned.append(value)
    return tuple(cleaned)


TEMPLATE_LIBRARY: tuple[ApplicationTemplate, ...] = (
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
            "description": "使用sage.benchmark.benchmark_rag.implementations.rag_simple中的算子，演示从提问到答案的完整流程",
        },
        guidance=textwrap.dedent(
            """
            适合客服场景的FAQ自动答复。可直接运行，无需远程服务，强调演示友好性。
            可扩展：替换检索器为真实向量库、改造生成器为大模型API。
            """
        ),
        notes=_notes(
            "基于 sage.benchmark.benchmark_rag.implementations.rag_simple 模块",
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
        notes=_notes("依赖 sage.libs.io.sink.PrintSink 组件。"),
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
            "源自 sage.benchmark.benchmark_rag.implementations.qa_multimodal_fusion",
            "默认使用 OpenAIGenerator，需要配置 API Key",
            "可扩展：替换多模态检索器为 SageVDB / 向量数据库",
        ),
    ),
    ApplicationTemplate(
        id="rag-dense-milvus",
        title="Milvus 密集向量检索问答",
        description="生产级 RAG 系统，使用 Milvus 向量数据库进行大规模语义检索，支持 BGE 嵌入模型。",
        tags=(
            "rag",
            "qa",
            "milvus",
            "dense",
            "vector",
            "embedding",
            "向量检索",
            "向量数据库",
            "生产环境",
            "语义搜索",
        ),
        example_path="examples/rag/qa_dense_retrieval_milvus.py",
        blueprint_id="rag-dense-milvus",
        default_requirements={
            "name": "milvus-dense-qa",
            "goal": "构建基于 Milvus 的生产级语义问答系统",
            "description": "使用密集向量检索和大模型生成，支持大规模知识库",
        },
        guidance=textwrap.dedent(
            """
            适合生产环境的大规模语义检索场景，支持百万级文档检索。
            需要预先使用 build_milvus_dense_index.py 构建向量索引。
            可配置不同的嵌入模型（BGE、OpenAI、sentence-transformers等）。
            """
        ),
        notes=_notes(
            "基于 examples/rag/qa_dense_retrieval_milvus.py",
            "需要运行中的 Milvus 服务实例",
            "需要预先构建向量索引",
            "支持分布式部署和高并发查询",
        ),
    ),
    ApplicationTemplate(
        id="rag-rerank",
        title="重排序增强检索问答",
        description="两阶段检索架构：初始召回 + BGE 重排序，显著提升检索精确度。",
        tags=(
            "rag",
            "qa",
            "rerank",
            "reranker",
            "precision",
            "重排序",
            "精确度",
            "两阶段",
            "召回",
            "精排",
        ),
        example_path="examples/rag/qa_rerank.py",
        blueprint_id="rag-rerank",
        default_requirements={
            "name": "rerank-qa-system",
            "goal": "构建高精度的重排序问答系统",
            "description": "通过两阶段检索优化答案质量：粗排召回 + 精细重排",
        },
        guidance=textwrap.dedent(
            """
            适合对答案精确度要求高的场景。第一阶段召回更多候选（如 top-20），
            第二阶段使用 BGE cross-encoder 重排序选出最相关的结果（如 top-5）。
            相比单阶段检索，可显著提升精确度，但计算成本稍高。
            """
        ),
        notes=_notes(
            "基于 examples/rag/qa_rerank.py",
            "两阶段架构：Chroma 召回 + BGE Reranker 精排",
            "需要配置向量数据库和 BGE reranker 模型",
            "适合高精度场景如法律、医疗、金融问答",
        ),
    ),
    ApplicationTemplate(
        id="rag-bm25-sparse",
        title="BM25 关键词检索问答",
        description="传统关键词检索，基于 BM25 算法进行词法匹配，无需向量化。",
        tags=(
            "rag",
            "qa",
            "bm25",
            "sparse",
            "keyword",
            "关键词",
            "稀疏检索",
            "词法",
            "传统检索",
        ),
        example_path="examples/rag/qa_bm25_retrieval.py",
        blueprint_id="rag-bm25-sparse",
        default_requirements={
            "name": "bm25-keyword-qa",
            "goal": "构建基于关键词匹配的问答系统",
            "description": "使用 BM25 算法进行传统文本检索，适合精确词匹配场景",
        },
        guidance=textwrap.dedent(
            """
            BM25 是经典的词法检索算法，适合：
            1. 精确关键词匹配场景
            2. 资源受限环境（无需 GPU 和向量化）
            3. 与密集检索结合的混合检索系统
            相比语义检索，在专有名词和精确匹配方面表现更好。
            """
        ),
        notes=_notes(
            "基于 examples/rag/qa_bm25_retrieval.py",
            "无需向量化，计算成本低",
            "适合关键词精确匹配场景",
            "可与密集检索结合形成混合检索",
        ),
    ),
    ApplicationTemplate(
        id="agent-workflow",
        title="LLM 智能体工作流",
        description="自主智能体系统，支持 LLM 规划、工具调用和复杂任务执行。",
        tags=(
            "agent",
            "llm",
            "planning",
            "tool",
            "mcp",
            "智能体",
            "工具调用",
            "规划",
            "自主",
            "任务执行",
        ),
        example_path="examples/agents/agent.py",
        blueprint_id="agent-workflow",
        default_requirements={
            "name": "autonomous-agent",
            "goal": "构建自主规划和执行任务的智能体",
            "description": "使用 LLM 进行任务规划，调用 MCP 工具完成复杂任务",
        },
        guidance=textwrap.dedent(
            """
            智能体系统适合需要多步骤推理和工具调用的复杂任务：
            1. LLM Planner 负责任务分解和规划
            2. MCP Registry 管理可用工具
            3. Agent Runtime 执行规划并调用工具
            支持的场景：数据分析、代码生成、信息收集、自动化操作等。
            """
        ),
        notes=_notes(
            "基于 examples/agents/agent.py",
            "支持 Model Context Protocol (MCP) 工具标准",
            "需要配置 LLM API 和工具库",
            "适合复杂的多步骤推理任务",
        ),
    ),
    ApplicationTemplate(
        id="rag-memory-enhanced",
        title="记忆增强对话问答",
        description="支持多轮对话的 RAG 系统，通过记忆服务维护上下文状态。",
        tags=(
            "rag",
            "memory",
            "conversation",
            "multi-turn",
            "dialogue",
            "记忆",
            "对话",
            "上下文",
            "多轮",
            "会话",
        ),
        example_path="examples/memory/rag_memory_pipeline.py",
        blueprint_id="rag-memory-enhanced",
        default_requirements={
            "name": "conversational-rag",
            "goal": "构建支持多轮对话的上下文感知问答系统",
            "description": "使用记忆服务存储历史对话，实现上下文连贯的问答",
        },
        guidance=textwrap.dedent(
            """
            记忆增强 RAG 适合对话式应用：
            1. 自动存储问答历史到记忆服务
            2. 检索时考虑历史上下文
            3. 生成时保持对话连贯性
            记忆服务使用 ChromaDB 或其他向量库作为存储后端。
            """
        ),
        notes=_notes(
            "基于 examples/memory/rag_memory_pipeline.py",
            "使用服务架构管理会话状态",
            "支持长期记忆和短期记忆",
            "适合客服机器人、个人助手等对话应用",
        ),
    ),
    ApplicationTemplate(
        id="multimodal-cross-search",
        title="跨模态搜索引擎",
        description="支持文本、图像及融合检索的多模态搜索系统，可配置融合策略。",
        tags=(
            "multimodal",
            "cross-modal",
            "search",
            "fusion",
            "image",
            "text",
            "跨模态",
            "搜索",
            "图文",
            "检索",
        ),
        example_path="examples/multimodal/cross_modal_search.py",
        blueprint_id="multimodal-cross-search",
        default_requirements={
            "name": "cross-modal-search",
            "goal": "构建跨模态搜索引擎",
            "description": "支持文本、图像和融合三种检索模式的多模态搜索",
        },
        guidance=textwrap.dedent(
            """
            跨模态搜索支持三种检索模式：
            1. 纯文本检索：使用文本嵌入
            2. 纯图像检索：使用图像嵌入
            3. 融合检索：可配置加权平均、RRF 等融合策略
            适合电商、新闻、社交媒体等图文混合场景。
            """
        ),
        notes=_notes(
            "基于 examples/multimodal/cross_modal_search.py",
            "支持多种融合策略配置",
            "可使用 SageVDB 或其他多模态向量库",
            "适合图文混合检索场景",
        ),
    ),
)

DEFAULT_TEMPLATE_ID = TEMPLATE_LIBRARY[0].id
