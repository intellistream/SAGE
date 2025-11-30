"""
Rule-based Workflow Generator

Layer: L3 (Core - Research & Algorithm Library)

A simple rule-based workflow generator that uses keyword matching
and predefined templates to generate workflows.

This is the simplest generation strategy, useful for:
- Well-defined domains with clear patterns
- Quick prototyping
- Baseline for comparing more advanced generators
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .base import (
    BaseWorkflowGenerator,
    GenerationContext,
    GenerationResult,
    GenerationStrategy,
)


class RuleBasedWorkflowGenerator(BaseWorkflowGenerator):
    """基于规则的工作流生成器

    使用关键词匹配和预定义模板生成工作流。

    优点：
    - 快速、可预测
    - 不需要外部 API
    - 易于理解和调试

    缺点：
    - 无法处理复杂或新颖的需求
    - 需要手动维护规则库
    - 泛化能力有限
    """

    # 意图关键词映射
    INTENT_KEYWORDS = {
        "rag": {
            "keywords": [
                "检索",
                "retrieval",
                "向量",
                "vector",
                "知识库",
                "knowledge",
                "文档",
                "document",
                "搜索",
                "search",
                "rag",
            ],
            "confidence": 0.9,
        },
        "summarize": {
            "keywords": ["总结", "概括", "summary", "summarize", "摘要"],
            "confidence": 0.85,
        },
        "analytics": {
            "keywords": ["统计", "分析", "analytics", "report", "指标", "metrics"],
            "confidence": 0.8,
        },
        "generation": {
            "keywords": ["生成", "创建", "写", "generate", "create", "write", "llm"],
            "confidence": 0.85,
        },
        "translation": {
            "keywords": ["翻译", "translate", "转换", "convert"],
            "confidence": 0.9,
        },
        "qa": {
            "keywords": ["问答", "qa", "question", "answer", "回答", "解答"],
            "confidence": 0.85,
        },
    }

    def __init__(self):
        """初始化基于规则的生成器"""
        super().__init__(GenerationStrategy.RULE_BASED)

    def generate(self, context: GenerationContext) -> GenerationResult:
        """使用规则生成工作流"""
        start_time = time.time()

        # Step 1: 检测意图
        detected_intents = self._detect_intents(context)

        if not detected_intents:
            return GenerationResult(
                success=False,
                strategy_used=self.strategy,
                error="无法识别用户意图，请提供更明确的描述",
                generation_time=time.time() - start_time,
            )

        # Step 2: 根据意图构建工作流
        visual_pipeline = self._build_visual_pipeline(detected_intents, context)

        # Step 3: 生成 raw plan (可选，用于 SAGE Kernel 执行)
        raw_plan = self._build_raw_plan(detected_intents, context)

        # Step 4: 估计置信度
        confidence = self._calculate_confidence(detected_intents, context)

        # Step 5: 生成解释
        explanation = self._generate_explanation(detected_intents)

        generation_time = time.time() - start_time

        return GenerationResult(
            success=True,
            visual_pipeline=visual_pipeline,
            raw_plan=raw_plan,
            strategy_used=self.strategy,
            confidence=confidence,
            explanation=explanation,
            detected_intents=detected_intents,
            generation_time=generation_time,
            metadata={"rule_based": True, "intents_count": len(detected_intents)},
        )

    def _detect_intents(self, context: GenerationContext) -> list[str]:
        """检测用户意图"""
        # 合并用户输入和对话历史
        all_text = context.user_input.lower()

        if context.conversation_history:
            for msg in context.conversation_history[-3:]:  # 只看最近3轮
                if msg.get("role") == "user":
                    all_text += " " + msg.get("content", "").lower()

        # 匹配关键词
        detected = []
        for intent, config in self.INTENT_KEYWORDS.items():
            for keyword in config["keywords"]:
                if keyword in all_text:
                    detected.append(intent)
                    break

        # 去重并保持顺序
        return list(dict.fromkeys(detected))

    def _build_visual_pipeline(
        self, intents: list[str], context: GenerationContext
    ) -> dict[str, Any]:
        """构建可视化 Pipeline（Studio 格式）

        CRITICAL: 必须符合 SAGE Studio 的 VisualNode 格式要求：
        - type: 直接使用操作符类型（如 "file_source"），而非 "custom"
        - config: 配置直接在顶层，而非嵌套在 data 中
        - label: 必须是顶层字段
        - 必须遵循 Source -> Map -> Sink 的 dataflow 范式
        """
        nodes = []
        connections = []
        order = 0

        def add_node(
            node_id: str, label: str, node_type: str, description: str, config: dict | None = None
        ) -> str:
            """添加节点（符合 VisualNode 格式）"""
            nonlocal order
            nodes.append(
                {
                    "id": node_id,
                    "type": node_type,  # ✅ 直接使用操作符类型
                    "label": label,  # ✅ label 在顶层
                    "position": {"x": 100 + order * 250, "y": 100},
                    "config": config or self._get_default_config(node_type),  # ✅ config 在顶层
                }
            )
            order += 1
            return node_id

        def connect(source_id: str, target_id: str):
            """添加连接（包含端口信息）"""
            connections.append(
                {
                    "id": f"conn-{len(connections)}",
                    "source": source_id,
                    "sourcePort": "output",  # ✅ 添加端口信息
                    "target": target_id,
                    "targetPort": "input",  # ✅ 添加端口信息
                }
            )

        # 起始节点（Source）
        prev_id = add_node(
            "node-input",
            "User Input",
            "file_source",
            "用户输入数据源",
            config={"source_type": "memory", "data": []},
        )

        # RAG 链
        if "rag" in intents or "qa" in intents:
            # 文档加载器可以省略（已经包含在 source 中）

            splitter_id = add_node(
                "node-splitter", "Text Splitter", "character_splitter", "文本分块"
            )
            connect(prev_id, splitter_id)
            prev_id = splitter_id

            # 嵌入可以作为检索器的一部分

            retriever_id = add_node("node-retriever", "Retriever", "chroma_retriever", "向量检索")
            connect(prev_id, retriever_id)
            prev_id = retriever_id

            promptor_id = add_node("node-promptor", "Promptor", "qa_promptor", "构建提示词")
            connect(prev_id, promptor_id)
            prev_id = promptor_id

        # LLM 节点（几乎所有场景都需要）
        if "generation" in intents or "qa" in intents or "summarize" in intents:
            llm_id = add_node("node-llm", "LLM", "openai_generator", "语言模型生成")
            connect(prev_id, llm_id)
            prev_id = llm_id

        # 后处理节点
        if "summarize" in intents:
            summary_id = add_node("node-summary", "Summarizer", "post_processor", "文本摘要")
            connect(prev_id, summary_id)
            prev_id = summary_id

        if "analytics" in intents:
            analytics_id = add_node("node-analytics", "Analytics", "analytics", "数据分析")
            connect(prev_id, analytics_id)
            prev_id = analytics_id

        # 输出节点（Sink）
        output_id = add_node("node-output", "Output", "terminal_sink", "输出结果")
        connect(prev_id, output_id)

        return {
            "name": self._generate_pipeline_name(intents),
            "description": context.user_input[:100],
            "nodes": nodes,
            "connections": connections,
            "metadata": {
                "generated_by": "RuleBasedWorkflowGenerator",
                "intents": intents,
                "version": "1.0",
            },
        }

    def _build_raw_plan(self, intents: list[str], context: GenerationContext) -> dict[str, Any]:
        """构建原始 Pipeline 配置（SAGE Kernel 格式）"""
        stages = []

        # 根据意图添加 stages
        if "rag" in intents or "qa" in intents:
            stages.extend(
                [
                    {
                        "id": "splitter",
                        "kind": "map",
                        "class": "sage.libs.rag.chunk.SimpleSplitter",
                        "params": {"chunk_size": 500, "chunk_overlap": 50},
                        "summary": "文本分块",
                    },
                    {
                        "id": "retriever",
                        "kind": "map",
                        "class": "sage.middleware.operators.rag.retriever.ChromaRetriever",
                        "params": {
                            "persist_directory": str(Path.home() / ".sage" / "vector_db"),
                            "collection_name": "sage_docs",
                            "top_k": 5,
                        },
                        "summary": "向量检索",
                    },
                    {
                        "id": "promptor",
                        "kind": "map",
                        "class": "sage.middleware.operators.rag.promptor.QAPromptor",
                        "params": {},
                        "summary": "构建QA提示词",
                    },
                ]
            )

        # LLM 生成
        if "generation" in intents or "qa" in intents or "summarize" in intents:
            stages.append(
                {
                    "id": "generator",
                    "kind": "map",
                    "class": "sage.middleware.operators.rag.generator.OpenAIGenerator",
                    "params": {
                        "model_name": "gpt-3.5-turbo",
                        "temperature": 0.7,
                        "stream": True,
                    },
                    "summary": "LLM生成",
                }
            )

        return {
            "pipeline": {
                "name": self._generate_pipeline_name(intents),
                "description": context.user_input[:100],
            },
            "source": {
                "class": "sage.libs.foundation.io.source.FileSource",
                "params": {"file_path": "data/sample.txt"},
                "summary": "文件数据源",
            },
            "stages": stages,
            "sink": {
                "class": "sage.libs.foundation.io.sink.TerminalSink",
                "params": {},
                "summary": "终端输出",
            },
        }

    def _get_default_config(self, node_type: str) -> dict[str, Any]:
        """获取节点的默认配置"""
        configs = {
            "UserInput": {},
            "FileSource": {"file_path": "data/sample.txt", "encoding": "utf-8"},
            "SimpleSplitter": {"chunk_size": 500, "chunk_overlap": 50},
            "Embedding": {"model_name": "BAAI/bge-small-zh-v1.5", "device": "cpu"},
            "ChromaRetriever": {
                "persist_directory": str(Path.home() / ".sage" / "vector_db"),
                "collection_name": "sage_docs",
                "top_k": 5,
            },
            "QAPromptor": {},
            "OpenAIGenerator": {
                "model_name": "gpt-3.5-turbo",
                "temperature": 0.7,
                "stream": True,
            },
            "PostProcessor": {"max_length": 200},
            "Analytics": {"metrics": ["count", "avg_length"]},
            "TerminalSink": {},
        }
        return configs.get(node_type, {})

    def _calculate_confidence(self, intents: list[str], context: GenerationContext) -> float:
        """计算生成置信度"""
        base_confidence = 0.5

        # 基于检测到的意图数量
        base_confidence += min(len(intents) * 0.1, 0.3)

        # 有对话历史
        if context.conversation_history:
            base_confidence += 0.1

        # 有明确领域
        if context.domain:
            base_confidence += 0.1

        return min(base_confidence, 0.9)

    def _generate_pipeline_name(self, intents: list[str]) -> str:
        """生成 Pipeline 名称"""
        if not intents:
            return "通用工作流"

        intent_names = {
            "rag": "RAG检索",
            "qa": "问答",
            "summarize": "摘要",
            "analytics": "分析",
            "generation": "生成",
            "translation": "翻译",
        }

        names = [intent_names.get(i, i) for i in intents[:2]]
        return " + ".join(names) + "工作流"

    def _generate_explanation(self, intents: list[str]) -> str:
        """生成解释文本"""
        intent_explanations = {
            "rag": "检测到文档检索需求，添加了文档加载、分块、向量化和检索节点",
            "qa": "检测到问答需求，添加了检索和问答生成节点",
            "summarize": "检测到摘要需求，添加了文本摘要节点",
            "analytics": "检测到分析需求，添加了数据分析节点",
            "generation": "检测到内容生成需求，添加了LLM生成节点",
            "translation": "检测到翻译需求，添加了翻译节点",
        }

        explanations = [intent_explanations.get(i, f"检测到{i}需求") for i in intents]

        return "基于规则的工作流生成：\n" + "\n".join(f"- {exp}" for exp in explanations)


__all__ = ["RuleBasedWorkflowGenerator"]
