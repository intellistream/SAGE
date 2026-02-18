#!/usr/bin/env python3
"""Blueprint library describing reusable SAGE pipelines."""

from __future__ import annotations

import copy
import re
import textwrap
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any


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
    params: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_plan(self) -> dict[str, Any]:
        return {
            "class": self.class_path,
            "kind": self.kind,
            "params": copy.deepcopy(self.params),
            "summary": self.summary,
        }

    def to_graph_node(self, outputs: Sequence[str]) -> dict[str, Any]:
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
    params: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_plan(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "class": self.class_path,
            "params": copy.deepcopy(self.params),
            "summary": self.summary,
        }

    def to_graph_node(self, inputs: Sequence[str], outputs: Sequence[str]) -> dict[str, Any]:
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
    params: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_plan(self) -> dict[str, Any]:
        plan = {
            "class": self.class_path,
            "params": copy.deepcopy(self.params),
            "summary": self.summary,
        }
        if self.kind:
            plan["kind"] = self.kind
        return plan

    def to_graph_node(self, inputs: Sequence[str]) -> dict[str, Any]:
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
    keywords: tuple[str, ...]
    source: SourceSpec
    stages: tuple[StageSpec, ...]
    sink: SinkSpec
    services: tuple[dict[str, Any], ...] = ()
    monitors: tuple[dict[str, Any], ...] = ()
    notes: tuple[str, ...] = ()
    graph_channels: tuple[dict[str, Any], ...] = ()
    graph_agents: tuple[dict[str, Any], ...] = ()

    def render_notes(self, feedback: str | None) -> list[str]:
        notes = list(self.notes)
        if feedback and feedback.strip():
            notes.append(f"反馈: {feedback.strip()}")
        if not notes:
            notes.append("Blueprint-generated configuration for experimentation")
        return notes


BLUEPRINT_LIBRARY: tuple[PipelineBlueprint, ...] = (
    PipelineBlueprint(
        id="rag-simple-demo",
        title="Simple RAG Demo",
        description="Use the sage.benchmark.benchmark_rag.implementations.rag_simple operators to run an end-to-end retrieval and answer pipeline.",
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
            class_path="sage.benchmark.benchmark_rag.implementations.rag_simple.SimpleQuestionSource",
            summary="Emit curated customer-style questions from the rag_simple example.",
        ),
        stages=(
            StageSpec(
                id="retriever",
                title="Keyword Retriever",
                kind="map",
                class_path="sage.benchmark.benchmark_rag.implementations.rag_simple.SimpleRetriever",
                summary="Lookup canned snippets matching question keywords.",
                metadata={"description": "Deterministic dictionary-based retriever"},
            ),
            StageSpec(
                id="prompt-builder",
                title="Prompt Builder",
                kind="map",
                class_path="sage.benchmark.benchmark_rag.implementations.rag_simple.SimplePromptor",
                summary="Combine context and question into a generation prompt.",
            ),
            StageSpec(
                id="generator",
                title="Answer Generator",
                kind="map",
                class_path="sage.benchmark.benchmark_rag.implementations.rag_simple.SimpleGenerator",
                summary="Create a formatted answer using rule-based heuristics.",
            ),
        ),
        sink=SinkSpec(
            id="terminal-sink",
            title="Terminal Sink",
            class_path="sage.benchmark.benchmark_rag.implementations.rag_simple.SimpleTerminalSink",
            summary="Pretty-print answers to the terminal with context snippets.",
        ),
        notes=(
            "基于 sage.benchmark.benchmark_rag.implementations.rag_simple 模块构建，适合离线演示",
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
            class_path="sage.libs.io.sink.PrintSink",
            summary="Stream outputs to console/logs using the reusable PrintSink operator.",
            params={"quiet": False},
        ),
        notes=(
            "结合 tutorials 示例与 sage.libs.io.PrintSink 组件",
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
            class_path="sage.benchmark.benchmark_rag.implementations.qa_multimodal_fusion.MultimodalQuestionSource",
            summary="Emit landmark-themed questions covering位置、属性与建筑背景。",
        ),
        stages=(
            StageSpec(
                id="multimodal-retriever",
                title="Multimodal Fusion Retriever",
                kind="map",
                class_path="sage.benchmark.benchmark_rag.implementations.qa_multimodal_fusion.MultimodalFusionRetriever",
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
                class_path="sage.middleware.operators.rag.generator.OpenAIGenerator",
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
            class_path="sage.libs.io.sink.TerminalSink",
            params={"output_format": "json", "pretty_print": True},
            summary="Render responses in JSON format for inspection or downstream tooling.",
        ),
        notes=(
            "基于 sage.benchmark.benchmark_rag.implementations.qa_multimodal_fusion 模块",
            "需要可用的 OpenAI 兼容推理服务或替换生成算子",
            "多模态融合可扩展至 SageVDB 或外部向量库",
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
    PipelineBlueprint(
        id="rag-dense-milvus",
        title="Dense Vector Retrieval with Milvus",
        description="Production-ready RAG pipeline using Milvus for dense vector retrieval with OpenAI-compatible LLM generation.",
        keywords=(
            "rag",
            "qa",
            "milvus",
            "dense",
            "vector",
            "embedding",
            "向量检索",
            "向量数据库",
            "生产环境",
        ),
        source=SourceSpec(
            id="jsonl-question-source",
            title="JSONL Question Source",
            class_path="sage.libs.io.batch.JSONLBatch",
            params={
                "data_path": "./data/questions.jsonl",
                "field_query": "query",
            },
            summary="Load questions from a JSONL file for batch processing.",
        ),
        stages=(
            StageSpec(
                id="milvus-retriever",
                title="Milvus Dense Retriever",
                kind="map",
                class_path="sage.libs.rag.retriever.MilvusDenseRetriever",
                params={
                    "dimension": 768,
                    "top_k": 5,
                    "milvus_dense": {
                        "collection_name": "knowledge_base",
                        "uri": "http://localhost:19530",
                    },
                    "embedding": {
                        "method": "bge-base-zh-v1.5",
                    },
                },
                summary="Retrieve top-k relevant chunks from Milvus vector database using dense embeddings.",
                metadata={
                    "description": "使用BGE嵌入模型进行语义检索",
                    "requires": "Milvus服务",
                },
            ),
            StageSpec(
                id="qa-promptor",
                title="QA Prompt Builder",
                kind="map",
                class_path="sage.libs.rag.promptor.QAPromptor",
                params={
                    "template": "Context: {context}\nQuestion: {question}\nAnswer:",
                    "max_context_length": 2000,
                },
                summary="Format retrieved context and question into LLM prompt.",
            ),
            StageSpec(
                id="llm-generator",
                title="LLM Answer Generator",
                kind="map",
                class_path="sage.middleware.operators.rag.generator.OpenAIGenerator",
                params={
                    "model_name": "gpt-3.5-turbo",
                    "temperature": 0.7,
                    "max_tokens": 256,
                },
                summary="Generate answers using OpenAI-compatible model API.",
                metadata={"requires": "OPENAI_API_KEY or compatible endpoint"},
            ),
        ),
        sink=SinkSpec(
            id="terminal-sink",
            title="Terminal Output Sink",
            class_path="sage.libs.io.sink.TerminalSink",
            params={},
            summary="Display Q&A results in terminal.",
        ),
        notes=(
            "基于 examples/rag/qa_dense_retrieval_milvus.py",
            "需要运行中的 Milvus 服务实例",
            "需要预先构建向量索引 (使用 build_milvus_dense_index.py)",
            "适合生产环境的大规模语义检索场景",
        ),
    ),
    PipelineBlueprint(
        id="rag-rerank",
        title="Retrieval with Reranking",
        description="Enhanced RAG pipeline using initial retrieval followed by BGE reranker for precision improvement.",
        keywords=(
            "rag",
            "qa",
            "rerank",
            "reranker",
            "precision",
            "重排序",
            "精确度优化",
            "两阶段检索",
        ),
        source=SourceSpec(
            id="jsonl-batch-source",
            title="JSONL Batch Source",
            class_path="sage.libs.io.batch.JSONLBatch",
            params={
                "data_path": "./data/questions.jsonl",
            },
            summary="Batch load questions from JSONL file.",
        ),
        stages=(
            StageSpec(
                id="chroma-retriever",
                title="Chroma Vector Retriever",
                kind="map",
                class_path="sage.libs.rag.retriever.ChromaRetriever",
                params={
                    "collection_name": "documents",
                    "top_k": 20,
                },
                summary="First-stage retrieval: fetch top-20 candidate chunks from Chroma.",
                metadata={"description": "召回阶段，优先覆盖率"},
            ),
            StageSpec(
                id="bge-reranker",
                title="BGE Reranker",
                kind="map",
                class_path="sage.libs.rag.reranker.BGEReranker",
                params={
                    "model_name": "bge-reranker-base",
                    "top_k": 5,
                },
                summary="Second-stage reranking: use BGE cross-encoder to select top-5 most relevant chunks.",
                metadata={"description": "精排阶段，提升精确度"},
            ),
            StageSpec(
                id="qa-promptor",
                title="QA Prompt Builder",
                kind="map",
                class_path="sage.libs.rag.promptor.QAPromptor",
                summary="Build generation prompt with reranked context.",
            ),
            StageSpec(
                id="generator",
                title="OpenAI Generator",
                kind="map",
                class_path="sage.middleware.operators.rag.generator.OpenAIGenerator",
                params={
                    "model_name": "gpt-3.5-turbo",
                    "temperature": 0.7,
                },
                summary="Generate final answer from reranked context.",
            ),
        ),
        sink=SinkSpec(
            id="terminal-sink",
            title="Terminal Sink",
            class_path="sage.libs.io.sink.TerminalSink",
            summary="Output Q&A results to terminal.",
        ),
        notes=(
            "基于 examples/rag/qa_rerank.py",
            "两阶段检索：召回 (Chroma) + 精排 (BGE Reranker)",
            "适合高精度要求的问答场景",
            "需要配置 Chroma 向量库和 OpenAI API",
        ),
    ),
    PipelineBlueprint(
        id="rag-bm25-sparse",
        title="BM25 Sparse Retrieval",
        description="Traditional keyword-based retrieval using sparse vector matching for lexical search.",
        keywords=(
            "rag",
            "qa",
            "bm25",
            "sparse",
            "keyword",
            "关键词检索",
            "稀疏检索",
            "词法匹配",
        ),
        source=SourceSpec(
            id="jsonl-source",
            title="JSONL Batch Source",
            class_path="sage.libs.io.batch.JSONLBatch",
            params={
                "data_path": "./data/questions.jsonl",
            },
            summary="Read questions from JSONL file.",
        ),
        stages=(
            StageSpec(
                id="sparse-retriever",
                title="Milvus Sparse Retriever",
                kind="map",
                class_path="sage.libs.rag.retriever.MilvusSparseRetriever",
                params={
                    "collection_name": "sparse_index",
                    "top_k": 5,
                    "milvus_sparse": {
                        "uri": "http://localhost:19530",
                    },
                },
                summary="Retrieve documents using sparse vector (BM25-like) matching in Milvus.",
                metadata={"description": "基于稀疏向量的传统检索方法"},
            ),
            StageSpec(
                id="qa-promptor",
                title="QA Promptor",
                kind="map",
                class_path="sage.libs.rag.promptor.QAPromptor",
                summary="Format sparse retrieval results into QA prompt.",
            ),
            StageSpec(
                id="generator",
                title="OpenAI Generator",
                kind="map",
                class_path="sage.middleware.operators.rag.generator.OpenAIGenerator",
                params={
                    "model_name": "gpt-3.5-turbo",
                },
                summary="Generate answer from keyword-matched context.",
            ),
        ),
        sink=SinkSpec(
            id="terminal-sink",
            title="Terminal Sink",
            class_path="sage.libs.io.sink.TerminalSink",
            summary="Print results to terminal.",
        ),
        notes=(
            "基于 examples/rag/qa_bm25_retrieval.py",
            "使用 MilvusSparseRetriever 进行稀疏向量检索",
            "适合精确词匹配场景或作为混合检索的一部分",
            "计算成本低，适合资源受限环境",
        ),
    ),
    PipelineBlueprint(
        id="agent-workflow",
        title="LLM Agent with Tool Calling",
        description="Autonomous agent workflow with LLM planning and MCP tool registry for complex task execution.",
        keywords=(
            "agent",
            "llm",
            "planning",
            "tool",
            "mcp",
            "智能体",
            "工具调用",
            "自主规划",
            "任务执行",
        ),
        source=SourceSpec(
            id="query-source",
            title="Query Iterator Source",
            class_path="examples.agents.agent.iter_queries",
            params={
                "type": "local",
                "data_path": "./data/agent_queries.jsonl",
                "field_query": "query",
            },
            summary="Load agent tasks from JSONL file.",
        ),
        stages=(
            StageSpec(
                id="agent-runtime",
                title="Agent Runtime Operator",
                kind="agent",
                class_path="sage.middleware.operators.agentic.runtime.AgentRuntimeOperator",
                params={
                    "profile": {
                        "name": "ResearchAgent",
                        "role": "autonomous researcher",
                        "language": "zh",
                        "tone": "concise",
                        "goals": [
                            "拆解复杂任务",
                            "调用工具获取证据",
                            "输出可验证结论",
                        ],
                    },
                    "generator": {
                        "method": "openai",
                        "model_name": "gpt-4o-mini",
                        "base_url": "https://api.openai.com/v1",
                    },
                    "planner": {
                        "max_steps": 5,
                        "enable_repair": True,
                        "topk_tools": 6,
                    },
                    "tools": [
                        {
                            "module": "examples.tutorials.agents.calculator_tool",
                            "class": "CalculatorTool",
                        },
                        {
                            "module": "examples.tutorials.agents.search_tool",
                            "class": "SearchTool",
                        },
                    ],
                    "runtime": {
                        "max_steps": 6,
                        "summarizer": "reuse_generator",
                    },
                },
                summary="Turn-key agent runtime (profile + planner + registry + workflow) for drag-and-drop pipelines.",
                metadata={"description": "L4 预设智能体算子，可直接接入 Studio 拖拽式工作流"},
            ),
        ),
        sink=SinkSpec(
            id="terminal-sink",
            title="Terminal Result Sink",
            class_path="sage.libs.io.sink.TerminalSink",
            summary="Display agent execution results and reasoning traces.",
        ),
        services=(
            {
                "id": "mcp-server",
                "type": "tool_registry",
                "config": {"protocol": "mcp", "tools_path": "./tools/"},
            },
        ),
        notes=(
            "基于 examples/agents/agent.py",
            "支持 LLM 自主规划和工具调用",
            "需要配置 MCP 工具和 OpenAI API",
            "适合复杂的多步骤任务执行场景",
        ),
        graph_agents=(
            {
                "id": "task-executor",
                "role": "Autonomous Task Agent",
                "goals": [
                    "理解用户意图",
                    "规划执行步骤",
                    "调用工具完成任务",
                ],
                "tools": ["llm-planner", "mcp-registry"],
            },
        ),
    ),
    PipelineBlueprint(
        id="rag-memory-enhanced",
        title="Memory-Enhanced RAG Pipeline",
        description="RAG pipeline with conversation memory service for context-aware multi-turn Q&A.",
        keywords=(
            "rag",
            "memory",
            "conversation",
            "service",
            "multi-turn",
            "记忆",
            "对话",
            "上下文",
            "多轮问答",
        ),
        source=SourceSpec(
            id="question-batch",
            title="Question Batch Source",
            class_path="examples.memory.rag_memory_pipeline.QuestionSource",
            params={
                "max_index": 5,
                "questions": [
                    "什么是健康饮食？",
                    "如何保持良好的睡眠？",
                    "运动的好处有哪些？",
                ],
            },
            summary="Emit sequential questions for memory demonstration.",
        ),
        stages=(
            StageSpec(
                id="memory-retriever",
                title="Memory-Aware Retriever",
                kind="map",
                class_path="examples.memory.rag_memory_pipeline.Retriever",
                summary="Retrieve context from memory service based on conversation history.",
                metadata={"description": "结合历史对话的检索器"},
            ),
            StageSpec(
                id="qa-promptor",
                title="QA Promptor",
                kind="map",
                class_path="sage.libs.rag.promptor.QAPromptor",
                summary="Build prompt with historical context.",
            ),
            StageSpec(
                id="generator",
                title="OpenAI Generator",
                kind="map",
                class_path="sage.middleware.operators.rag.generator.OpenAIGenerator",
                params={
                    "model_name": "gpt-3.5-turbo",
                },
                summary="Generate context-aware answers.",
            ),
            StageSpec(
                id="memory-writer",
                title="Memory Writer",
                kind="map",
                class_path="examples.memory.rag_memory_pipeline.Writer",
                summary="Store Q&A pairs into memory service for future retrieval.",
                metadata={"description": "写入对话历史到记忆服务"},
            ),
        ),
        sink=SinkSpec(
            id="print-sink",
            title="Print Sink",
            class_path="examples.memory.rag_memory_pipeline.PrintSink",
            summary="Display Q&A with conversation context.",
        ),
        services=(
            {
                "id": "rag_memory",
                "type": "memory_service",
                "class": "examples.memory.rag_memory_service.RAGMemoryService",
                "config": {
                    "storage_backend": "chromadb",
                    "collection_name": "conversation_memory",
                },
            },
        ),
        notes=(
            "基于 examples/memory/rag_memory_pipeline.py",
            "支持多轮对话的上下文记忆",
            "使用服务架构管理会话状态",
            "适合需要历史感知的对话式应用",
        ),
        graph_channels=(
            {
                "id": "memory-channel",
                "type": "service",
                "description": "Shared conversation memory across retrieval and writing",
                "participants": ["memory-retriever", "memory-writer"],
            },
        ),
    ),
    PipelineBlueprint(
        id="multimodal-cross-search",
        title="Cross-Modal Search Engine",
        description="Search across text and image modalities with multimodal database support.",
        keywords=(
            "multimodal",
            "cross-modal",
            "search",
            "fusion",
            "image",
            "text",
            "跨模态",
            "多模态搜索",
            "图文检索",
        ),
        source=SourceSpec(
            id="multimodal-query-source",
            title="Multimodal Query Source",
            class_path="sage.libs.io.batch.JSONLBatch",
            params={
                "data_path": "./data/multimodal_queries.jsonl",
            },
            summary="Load queries containing both text and image embeddings.",
        ),
        stages=(
            StageSpec(
                id="cross-modal-retriever",
                title="Cross-Modal Retriever",
                kind="map",
                class_path="sage.middleware.components.sage_db.python.multimodal_sage_db.create_text_image_db",
                params={
                    "dimension": 512,
                    "fusion_strategy": "weighted_average",
                    "text_weight": 0.6,
                    "image_weight": 0.4,
                },
                summary="Retrieve from multimodal database with configurable fusion.",
                metadata={
                    "description": "支持文本、图像和融合检索策略",
                    "modalities": ["text", "image"],
                },
            ),
        ),
        sink=SinkSpec(
            id="json-sink",
            title="JSON Output Sink",
            class_path="sage.libs.io.sink.TerminalSink",
            params={
                "output_format": "json",
                "pretty_print": True,
            },
            summary="Output multimodal search results in JSON format.",
        ),
        notes=(
            "基于 examples/multimodal/cross_modal_search.py",
            "支持纯文本、纯图像和融合检索三种模式",
            "可配置不同的融合策略 (加权平均、RRF等)",
            "适合图文混合检索场景如电商、新闻、社交媒体",
        ),
    ),
)

DEFAULT_BLUEPRINT = BLUEPRINT_LIBRARY[0]


def requirements_text(requirements: dict[str, Any]) -> str:
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


def compute_match_score(requirements: dict[str, Any], blueprint: PipelineBlueprint) -> float:
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
    requirements: dict[str, Any],
    top_k: int = 3,
) -> list[tuple[PipelineBlueprint, float]]:
    candidates = [
        (blueprint, compute_match_score(requirements, blueprint)) for blueprint in BLUEPRINT_LIBRARY
    ]
    candidates.sort(key=lambda item: item[1], reverse=True)
    top = candidates[: top_k or 1]
    if all(bp is not DEFAULT_BLUEPRINT for bp, _ in top):
        top.append((DEFAULT_BLUEPRINT, 0.1))
    return top


def select_blueprint(requirements: dict[str, Any]) -> PipelineBlueprint:
    return match_blueprints(requirements, top_k=1)[0][0]


def build_pipeline_plan(
    blueprint: PipelineBlueprint,
    requirements: dict[str, Any],
    feedback: str | None = None,
) -> dict[str, Any]:
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
    requirements: dict[str, Any],
    feedback: str | None = None,
) -> dict[str, Any]:
    components: list[Any] = [blueprint.source, *blueprint.stages, blueprint.sink]
    nodes: list[dict[str, Any]] = []

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
        适用关键词: {", ".join(blueprint.keywords) or "通用"}
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
