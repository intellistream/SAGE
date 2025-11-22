"""
Intelligent Workflow Generator for SAGE Studio

这个模块整合了两种工作流算法：
1. Workflow Generation (从对话生成工作流)
2. Workflow Optimization (可选的性能优化)

Layer: L6 (Studio Services)
Dependencies: sage-cli (pipeline builder), sage-libs (workflow optimizer)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from sage.common.logging.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WorkflowGenerationRequest:
    """工作流生成请求"""

    user_input: str
    """用户的自然语言描述"""

    session_messages: list[dict[str, Any]] | None = None
    """对话历史（可选）"""

    constraints: dict[str, Any] | None = None
    """约束条件（可选），如 max_cost, max_latency, min_quality"""

    enable_optimization: bool = False
    """是否启用工作流优化"""

    optimization_strategy: str = "greedy"
    """优化策略: greedy, parallelization, noop"""


@dataclass
class WorkflowGenerationResult:
    """工作流生成结果"""

    success: bool
    """是否成功"""

    visual_pipeline: dict[str, Any] | None = None
    """可视化 Pipeline（Studio 格式）"""

    raw_plan: dict[str, Any] | None = None
    """原始 Pipeline 配置"""

    optimization_applied: bool = False
    """是否应用了优化"""

    optimization_metrics: dict[str, Any] | None = None
    """优化指标（如果应用了优化）"""

    error: str | None = None
    """错误信息"""

    message: str = ""
    """给用户的提示信息"""


class WorkflowGenerator:
    """智能工作流生成器

    整合了 Pipeline Builder (LLM驱动生成) 和 Workflow Optimizer (性能优化)
    """

    def __init__(self):
        """初始化生成器"""
        self._pipeline_builder_available = False
        self._workflow_optimizer_available = False
        self._check_dependencies()

    def _check_dependencies(self):
        """检查依赖是否可用"""
        # 检查 Pipeline Builder
        try:
            from sage.cli.commands.apps import pipeline as pipeline_builder

            self._pipeline_builder_available = True
            logger.info("Pipeline Builder available")
        except ImportError:
            logger.warning("Pipeline Builder not available (sage-cli not installed)")

        # 检查 Workflow Optimizer
        try:
            from sage.libs.agentic.workflow import BaseOptimizer, WorkflowGraph
            from sage.libs.agentic.workflow.optimizers import (
                GreedyOptimizer,
                ParallelizationOptimizer,
            )

            self._workflow_optimizer_available = True
            logger.info("Workflow Optimizer available")
        except ImportError:
            logger.warning("Workflow Optimizer not available (sage-libs.workflow not installed)")

    def generate(self, request: WorkflowGenerationRequest) -> WorkflowGenerationResult:
        """生成工作流

        Args:
            request: 生成请求

        Returns:
            生成结果
        """
        # Step 1: 使用 Pipeline Builder 生成初始工作流
        generation_result = self._generate_initial_workflow(request)

        if not generation_result.success:
            return generation_result

        # Step 2: (可选) 应用工作流优化
        if request.enable_optimization and self._workflow_optimizer_available:
            try:
                optimization_result = self._optimize_workflow(
                    generation_result.raw_plan,
                    request.constraints or {},
                    request.optimization_strategy,
                )

                if optimization_result["success"]:
                    generation_result.optimization_applied = True
                    generation_result.optimization_metrics = optimization_result["metrics"]
                    generation_result.message += (
                        f"\n✨ 已应用 {request.optimization_strategy} 优化策略"
                    )
                    logger.info(f"Workflow optimization applied: {optimization_result['metrics']}")

            except Exception as e:
                logger.warning(f"Workflow optimization failed (non-critical): {e}")
                # 优化失败不影响主流程，继续使用未优化的版本

        return generation_result

    def _generate_initial_workflow(
        self, request: WorkflowGenerationRequest
    ) -> WorkflowGenerationResult:
        """使用 Pipeline Builder 生成初始工作流"""
        if not self._pipeline_builder_available:
            return WorkflowGenerationResult(
                success=False,
                error="Pipeline Builder 不可用，请安装 sage-cli",
                message="抱歉，工作流生成功能当前不可用",
            )

        try:
            from sage.cli.commands.apps import pipeline as pipeline_builder

            # 构建配置
            config = pipeline_builder.BuilderConfig(
                backend="openai",
                model=os.getenv("SAGE_PIPELINE_BUILDER_MODEL", "qwen-max"),
                base_url=os.getenv(
                    "SAGE_PIPELINE_BUILDER_BASE_URL",
                    "https://dashscope.aliyuncs.com/compatible-mode/v1",
                ),
                api_key=(
                    os.getenv("SAGE_PIPELINE_BUILDER_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
                ),
                domain_contexts=(),
                knowledge_base=None,
                knowledge_top_k=0,
                show_knowledge=False,
            )

            # 构建需求描述
            requirements = self._build_requirements(request)

            # 生成 Pipeline
            generator = pipeline_builder.PipelinePlanGenerator(config)
            plan = generator.generate(requirements, previous_plan=None, feedback=None)

            # 转换为 Studio 可视化格式
            visual_pipeline = self._convert_to_visual_format(plan)

            return WorkflowGenerationResult(
                success=True,
                visual_pipeline=visual_pipeline,
                raw_plan=plan,
                message="✅ 工作流已生成，您可以在画布中查看和编辑",
            )

        except Exception as e:
            logger.error(f"Workflow generation failed: {e}", exc_info=True)
            return WorkflowGenerationResult(
                success=False, error=str(e), message=f"抱歉，工作流生成失败：{e}"
            )

    def _build_requirements(self, request: WorkflowGenerationRequest) -> dict[str, Any]:
        """构建 Pipeline 生成需求

        将用户输入和对话历史转换为 Pipeline Builder 的需求格式
        """
        # 基础需求
        requirements = {
            "name": "用户自定义工作流",
            "goal": request.user_input,
            "data_sources": ["文档知识库"],
            "latency_budget": "实时响应优先",
            "constraints": "",
            "initial_prompt": request.user_input,
        }

        # 如果有对话历史，提取更多上下文
        if request.session_messages:
            # 提取用户的所有输入
            user_inputs = [
                msg.get("content", "")
                for msg in request.session_messages
                if msg.get("role") == "user"
            ]

            # 如果有多轮对话，合并上下文
            if len(user_inputs) > 1:
                requirements["goal"] = "\n".join(user_inputs[-3:])  # 最近3轮

        # 添加约束条件
        if request.constraints:
            constraints_text = []
            if "max_cost" in request.constraints:
                constraints_text.append(f"成本不超过 ${request.constraints['max_cost']}")
            if "max_latency" in request.constraints:
                constraints_text.append(f"延迟不超过 {request.constraints['max_latency']}秒")
            if "min_quality" in request.constraints:
                constraints_text.append(f"质量分数至少 {request.constraints['min_quality']}")

            requirements["constraints"] = "；".join(constraints_text)

        return requirements

    def _convert_to_visual_format(self, plan: dict[str, Any]) -> dict[str, Any]:
        """将 Pipeline Plan 转换为 Studio 可视化格式

        Studio 需要的格式:
        {
            "name": str,
            "description": str,
            "nodes": [{"id", "type", "position", "data": {...}}],
            "connections": [{"id", "source", "target"}]
        }
        """
        nodes = []
        connections = []

        pipeline_info = plan.get("pipeline", {})

        # 创建 Source 节点
        source_config = plan.get("source", {})
        source_class = source_config.get("class", "")
        source_type = source_class.split(".")[-1] if source_class else "FileSource"

        nodes.append(
            {
                "id": "source-0",
                "type": "custom",
                "position": {"x": 100, "y": 100},
                "data": {
                    "label": "数据源",
                    "nodeId": source_type,
                    "description": source_config.get("summary", "数据源"),
                    "status": "idle",
                    "config": source_config.get("params", {}),
                },
            }
        )

        # 创建 Stage 节点
        stages = plan.get("stages", [])
        for idx, stage in enumerate(stages):
            stage_class = stage.get("class", "")
            stage_type = stage_class.split(".")[-1] if stage_class else f"Stage{idx}"

            node_id = f"stage-{idx}"
            nodes.append(
                {
                    "id": node_id,
                    "type": "custom",
                    "position": {"x": 100 + (idx + 1) * 250, "y": 100},
                    "data": {
                        "label": stage.get("summary", f"Stage {idx}"),
                        "nodeId": stage_type,
                        "description": stage.get("summary", ""),
                        "status": "idle",
                        "config": stage.get("params", {}),
                    },
                }
            )

            # 连接前一个节点
            prev_id = "source-0" if idx == 0 else f"stage-{idx - 1}"
            connections.append(
                {
                    "id": f"conn-{idx}",
                    "source": prev_id,
                    "target": node_id,
                    "type": "smoothstep",
                    "animated": True,
                }
            )

        # 创建 Sink 节点
        sink_config = plan.get("sink", {})
        sink_class = sink_config.get("class", "")
        sink_type = sink_class.split(".")[-1] if sink_class else "PrintSink"

        sink_id = "sink-0"
        nodes.append(
            {
                "id": sink_id,
                "type": "custom",
                "position": {"x": 100 + (len(stages) + 1) * 250, "y": 100},
                "data": {
                    "label": "输出",
                    "nodeId": sink_type,
                    "description": sink_config.get("summary", "输出结果"),
                    "status": "idle",
                    "config": sink_config.get("params", {}),
                },
            }
        )

        # 连接最后一个 stage 到 sink
        last_stage_id = f"stage-{len(stages) - 1}" if stages else "source-0"
        connections.append(
            {
                "id": f"conn-{len(stages)}",
                "source": last_stage_id,
                "target": sink_id,
                "type": "smoothstep",
                "animated": True,
            }
        )

        return {
            "name": pipeline_info.get("name", "生成的工作流"),
            "description": pipeline_info.get("description", ""),
            "nodes": nodes,
            "connections": connections,
            "metadata": {
                "generated_by": "sage_studio_workflow_generator",
                "version": "1.0",
            },
        }

    def _optimize_workflow(
        self, plan: dict[str, Any], constraints: dict[str, Any], strategy: str
    ) -> dict[str, Any]:
        """使用 Workflow Optimizer 优化工作流

        注意：这是未来功能的占位符。
        当前 Pipeline Plan 格式与 WorkflowGraph 格式不同，需要转换逻辑。

        Args:
            plan: Pipeline Plan (来自 Pipeline Builder)
            constraints: 约束条件
            strategy: 优化策略

        Returns:
            优化结果
        """
        # TODO: 实现 Pipeline Plan → WorkflowGraph 的转换
        # TODO: 应用优化器
        # TODO: 将优化后的 WorkflowGraph 转回 Pipeline Plan

        logger.warning("Workflow optimization is not yet implemented (requires format conversion)")

        return {
            "success": False,
            "message": "工作流优化功能开发中",
            "metrics": {},
        }


# 全局单例
_workflow_generator: WorkflowGenerator | None = None


def get_workflow_generator() -> WorkflowGenerator:
    """获取全局 Workflow Generator 实例"""
    global _workflow_generator
    if _workflow_generator is None:
        _workflow_generator = WorkflowGenerator()
    return _workflow_generator


def generate_workflow_from_chat(
    user_input: str,
    session_messages: list[dict[str, Any]] | None = None,
    enable_optimization: bool = False,
) -> WorkflowGenerationResult:
    """从对话生成工作流的便捷函数

    Args:
        user_input: 用户的当前输入
        session_messages: 对话历史
        enable_optimization: 是否启用优化

    Returns:
        工作流生成结果
    """
    generator = get_workflow_generator()

    request = WorkflowGenerationRequest(
        user_input=user_input,
        session_messages=session_messages,
        enable_optimization=enable_optimization,
    )

    return generator.generate(request)


__all__ = [
    "WorkflowGenerator",
    "WorkflowGenerationRequest",
    "WorkflowGenerationResult",
    "get_workflow_generator",
    "generate_workflow_from_chat",
]
