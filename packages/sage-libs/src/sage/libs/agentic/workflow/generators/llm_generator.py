"""
LLM-driven Workflow Generator

Layer: L3 (Core - Research & Algorithm Library)

An advanced workflow generator that uses Large Language Models
to understand user intent and generate appropriate workflows.

This generator integrates with the existing Pipeline Builder
from sage-cli, providing a research-friendly interface.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

from .base import (
    BaseWorkflowGenerator,
    GenerationContext,
    GenerationResult,
    GenerationStrategy,
)


class LLMWorkflowGenerator(BaseWorkflowGenerator):
    """基于 LLM 的工作流生成器

    使用大语言模型理解用户意图并生成工作流。

    优点：
    - 能理解复杂、自然的语言描述
    - 可以处理新颖的需求
    - 泛化能力强

    缺点：
    - 需要 API 密钥和网络连接
    - 响应时间较长
    - 成本较高
    - 可能生成不完全正确的配置

    研究方向：
    - 如何提高生成准确率？
    - 如何减少 API 调用次数？
    - 如何结合 RAG 提供更好的上下文？
    - 如何验证生成的工作流？
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        use_rag: bool = True,
    ):
        """初始化 LLM 驱动的生成器

        Args:
            model: 模型名称，默认从环境变量读取
            api_key: API 密钥，默认从环境变量读取
            base_url: API base URL，默认从环境变量读取
            use_rag: 是否使用 RAG 增强生成（检索 SAGE 文档）
        """
        super().__init__(GenerationStrategy.LLM_DRIVEN)

        # API Key: 优先级顺序（不再隐式使用云端默认）
        # 1. 显式传入的参数
        # 2. SAGE_PIPELINE_BUILDER_API_KEY（专用于 Pipeline Builder）
        # 3. SAGE_CHAT_API_KEY（Gateway/Studio Chat 使用的密钥）
        # 4. SAGE_DEBUG_API_KEY（开发调试密钥）
        # 5. OPENAI_API_KEY（通用后备）
        self.api_key = (
            api_key
            or os.getenv("SAGE_PIPELINE_BUILDER_API_KEY")
            or os.getenv("SAGE_CHAT_API_KEY")
            or os.getenv("SAGE_DEBUG_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )

        # Model: 类似的优先级
        self.model = (
            model
            or os.getenv("SAGE_PIPELINE_BUILDER_MODEL")
            or os.getenv("SAGE_CHAT_MODEL")
            or os.getenv("SAGE_DEBUG_MODEL")
            or os.getenv("OPENAI_MODEL_NAME", "qwen-max")
        )

        # Base URL: 优先级（本地优先，无隐式云端默认）
        self.base_url = (
            base_url
            or os.getenv("SAGE_PIPELINE_BUILDER_BASE_URL")
            or os.getenv("SAGE_CHAT_BASE_URL")
            or os.getenv("SAGE_DEBUG_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
        )

        # 如果未提供 base_url，尝试探测本地端点（LLM 8001 → 8901）
        if not self.base_url:
            from sage.common.config.ports import SagePorts

            for port in [
                SagePorts.get_recommended_llm_port(),
                SagePorts.LLM_DEFAULT,
                SagePorts.BENCHMARK_LLM,
            ]:
                candidate = f"http://localhost:{port}/v1"
                if self._probe_endpoint(candidate):
                    self.base_url = candidate
                    break

        self.use_rag = use_rag

        # 检查依赖
        self._pipeline_builder_available = False
        try:
            from sage.cli.commands.apps import pipeline as pipeline_builder  # noqa: F401

            self._pipeline_builder_available = True
            logger.info("Pipeline Builder available for LLM generation")
        except ImportError:
            logger.warning("Pipeline Builder not available (sage-cli not installed)")

    def _probe_endpoint(self, url: str, timeout: float = 2.0) -> bool:
        """探测端点是否可用

        Args:
            url: 要探测的端点 URL
            timeout: 超时时间（秒）

        Returns:
            bool: 端点是否可用
        """
        try:
            import requests

            response = requests.get(f"{url.rstrip('/')}/models", timeout=timeout)
            return response.status_code == 200
        except Exception:
            return False

    def generate(self, context: GenerationContext) -> GenerationResult:
        """使用 LLM 生成工作流"""
        start_time = time.time()

        if not self._pipeline_builder_available:
            return GenerationResult(
                success=False,
                strategy_used=self.strategy,
                error="Pipeline Builder 不可用，请安装 sage-cli",
                generation_time=time.time() - start_time,
            )

        if not self.api_key:
            return GenerationResult(
                success=False,
                strategy_used=self.strategy,
                error="未配置 API 密钥，请设置 SAGE_PIPELINE_BUILDER_API_KEY 或 SAGE_CHAT_API_KEY",
                generation_time=time.time() - start_time,
            )

        try:
            # Step 1: 构建 Pipeline Builder 配置
            config = self._build_pipeline_builder_config()

            # Step 2: 构建需求描述
            requirements = self._build_requirements(context)

            # Step 3: 调用 Pipeline Builder 生成
            from sage.cli.commands.apps import pipeline as pipeline_builder

            generator = pipeline_builder.PipelinePlanGenerator(config)
            raw_plan = generator.generate(requirements, previous_plan=None, feedback=None)

            # Step 4: 转换为可视化格式
            visual_pipeline = self._convert_to_visual_format(raw_plan)

            # Step 5: 验证生成的工作流
            is_valid, errors = self.validate_workflow(raw_plan)
            if not is_valid:
                logger.warning(f"Generated workflow has validation errors: {errors}")

            # Step 6: 生成解释和建议
            explanation = self._generate_explanation(raw_plan, context)
            suggested_optimizations = self._suggest_optimizations(raw_plan, context)

            generation_time = time.time() - start_time

            return GenerationResult(
                success=True,
                visual_pipeline=visual_pipeline,
                raw_plan=raw_plan,
                strategy_used=self.strategy,
                confidence=0.85 if is_valid else 0.6,  # 降低无效工作流的置信度
                explanation=explanation,
                detected_intents=self._extract_intents(raw_plan),
                suggested_optimizations=suggested_optimizations,
                generation_time=generation_time,
                metadata={
                    "llm_model": self.model,
                    "use_rag": self.use_rag,
                    "validation_errors": errors if not is_valid else [],
                },
            )

        except Exception as e:
            logger.error(f"LLM workflow generation failed: {e}", exc_info=True)
            generation_time = time.time() - start_time

            return GenerationResult(
                success=False,
                strategy_used=self.strategy,
                error=str(e),
                generation_time=generation_time,
            )

    def _build_pipeline_builder_config(self):
        """构建 Pipeline Builder 配置"""
        from sage.cli.commands.apps import pipeline as pipeline_builder

        return pipeline_builder.BuilderConfig(
            backend="openai",
            model=self.model,
            base_url=self.base_url,
            api_key=self.api_key,
            domain_contexts=(),
            knowledge_base=None,
            knowledge_top_k=0 if not self.use_rag else 5,
            show_knowledge=False,
        )

    def _build_requirements(self, context: GenerationContext) -> dict[str, Any]:
        """构建需求描述"""
        # 合并用户输入和对话历史
        goal = context.user_input

        if context.conversation_history:
            user_inputs = [
                msg.get("content", "")
                for msg in context.conversation_history
                if msg.get("role") == "user"
            ]
            if len(user_inputs) > 1:
                goal = "\n".join(user_inputs[-3:])  # 最近3轮

        # 构建约束描述
        constraints_text = []
        if context.constraints:
            if "max_cost" in context.constraints:
                constraints_text.append(f"成本不超过 ${context.constraints['max_cost']}")
            if "max_latency" in context.constraints:
                constraints_text.append(f"延迟不超过 {context.constraints['max_latency']}秒")
            if "min_quality" in context.constraints:
                constraints_text.append(f"质量分数至少 {context.constraints['min_quality']}")

        return {
            "name": context.metadata.get("name", "用户自定义工作流"),
            "goal": goal,
            "data_sources": context.metadata.get("data_sources", ["文档知识库"]),
            "latency_budget": (
                context.constraints.get("max_latency", "实时响应优先")
                if context.constraints
                else "实时响应优先"
            ),
            "constraints": "；".join(constraints_text),
            "initial_prompt": context.user_input,
        }

    def _convert_to_visual_format(self, plan: dict[str, Any]) -> dict[str, Any]:
        """将 Pipeline Plan 转换为 Studio 可视化格式

        CRITICAL: 必须符合 SAGE Studio 的 VisualNode 格式要求：
        - type: 直接使用操作符类型（如 "retriever"），而非 "custom"
        - config: 配置直接在顶层，而非嵌套在 data 中
        - 必须遵循 Source -> Map -> Sink 的 dataflow 范式
        """
        nodes = []
        connections = []

        pipeline_info = plan.get("pipeline", {})

        # 辅助函数：将类名转换为 snake_case 的节点类型
        def _class_to_node_type(class_name: str) -> str:
            """将类名转换为节点类型
            例: SimpleRetriever -> simple_retriever
                OpenAIGenerator -> openai_generator
            """
            if not class_name:
                return "unknown"

            # 移除包路径，只保留类名
            class_name = class_name.split(".")[-1]

            # 将 CamelCase 转换为 snake_case
            import re

            s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", class_name)
            result = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

            return result

        # Source 节点
        source_config = plan.get("source", {})
        source_class = source_config.get("class", "")
        source_type = _class_to_node_type(source_class) or "file_source"

        nodes.append(
            {
                "id": "source-0",
                "type": source_type,  # ✅ 修正：直接使用操作符类型
                "label": source_config.get("summary", "数据源"),
                "position": {"x": 100, "y": 100},
                "config": source_config.get("params", {}),  # ✅ 修正：配置在顶层
            }
        )

        # Stage 节点（Map 操作符）
        stages = plan.get("stages", [])
        for idx, stage in enumerate(stages):
            stage_class = stage.get("class", "")
            stage_type = _class_to_node_type(stage_class) or f"unknown_stage_{idx}"

            node_id = f"stage-{idx}"
            nodes.append(
                {
                    "id": node_id,
                    "type": stage_type,  # ✅ 修正：直接使用操作符类型
                    "label": stage.get("summary", f"Stage {idx}"),
                    "position": {"x": 100 + (idx + 1) * 250, "y": 100},
                    "config": stage.get("params", {}),  # ✅ 修正：配置在顶层
                }
            )

            # 连接（符合 SAGE dataflow 范式）
            prev_id = "source-0" if idx == 0 else f"stage-{idx - 1}"
            connections.append(
                {
                    "id": f"conn-{idx}",
                    "source": prev_id,
                    "sourcePort": "output",  # ✅ 添加端口信息
                    "target": node_id,
                    "targetPort": "input",  # ✅ 添加端口信息
                }
            )

        # Sink 节点
        sink_config = plan.get("sink", {})
        sink_class = sink_config.get("class", "")
        sink_type = _class_to_node_type(sink_class) or "terminal_sink"

        sink_id = "sink-0"
        nodes.append(
            {
                "id": sink_id,
                "type": sink_type,  # ✅ 修正：直接使用操作符类型
                "label": sink_config.get("summary", "输出"),
                "position": {"x": 100 + (len(stages) + 1) * 250, "y": 100},
                "config": sink_config.get("params", {}),  # ✅ 修正：配置在顶层
            }
        )

        last_stage_id = f"stage-{len(stages) - 1}" if stages else "source-0"
        connections.append(
            {
                "id": f"conn-{len(stages)}",
                "source": last_stage_id,
                "sourcePort": "output",  # ✅ 添加端口信息
                "target": sink_id,
                "targetPort": "input",  # ✅ 添加端口信息
            }
        )

        return {
            "name": pipeline_info.get("name", "LLM生成的工作流"),
            "description": pipeline_info.get("description", ""),
            "nodes": nodes,
            "connections": connections,
            "metadata": {
                "generated_by": "LLMWorkflowGenerator",
                "llm_model": self.model,
                "version": "1.0",
            },
        }

    def _extract_intents(self, plan: dict[str, Any]) -> list[str]:
        """从生成的 plan 中提取意图"""
        intents = []

        stages = plan.get("stages", [])
        for stage in stages:
            class_name = stage.get("class", "").lower()

            if "retriev" in class_name:
                intents.append("rag")
            if "generat" in class_name:
                intents.append("generation")
            if "summar" in class_name:
                intents.append("summarize")
            if "analyt" in class_name:
                intents.append("analytics")

        return list(dict.fromkeys(intents))  # 去重

    def _generate_explanation(self, plan: dict[str, Any], context: GenerationContext) -> str:
        """生成解释文本"""
        stages = plan.get("stages", [])
        stage_summaries = [s.get("summary", "未知步骤") for s in stages]

        explanation = f"使用 {self.model} 生成的工作流，包含 {len(stages)} 个处理阶段：\n"
        for i, summary in enumerate(stage_summaries, 1):
            explanation += f"{i}. {summary}\n"

        return explanation

    def _suggest_optimizations(self, plan: dict[str, Any], context: GenerationContext) -> list[str]:
        """建议优化项"""
        suggestions = []

        stages = plan.get("stages", [])

        # 检查是否可以并行化
        if len(stages) > 3:
            suggestions.append("考虑并行化处理以降低延迟")

        # 检查是否使用了昂贵的模型
        for stage in stages:
            params = stage.get("params", {})
            if "gpt-4" in params.get("model_name", ""):
                suggestions.append("考虑使用更经济的模型（如 gpt-3.5-turbo）以降低成本")

        # 检查是否启用了流式输出
        has_streaming = any(s.get("params", {}).get("stream") for s in stages)
        if not has_streaming:
            suggestions.append("启用流式输出以提升用户体验")

        # 检查缓存机会
        if any("retriev" in s.get("class", "").lower() for s in stages):
            suggestions.append("考虑添加检索结果缓存以提高响应速度")

        return suggestions


__all__ = ["LLMWorkflowGenerator"]
