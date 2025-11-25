"""
Intelligent Workflow Generator for SAGE Studio

这个模块是 sage-libs workflow generators 的包装器，
为 SAGE Studio 提供简单的调用接口。

实际的生成算法位于: sage.libs.agentic.workflow.generators

Layer: L6 (Studio Services)
Dependencies: sage-libs (workflow generators)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


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
    """是否启用工作流优化（未来功能）"""

    use_llm: bool = True
    """是否使用 LLM 生成（False 则使用规则）"""

    optimization_strategy: str = "greedy"
    """优化策略: greedy, parallelization, noop（未来功能）"""


@dataclass
class WorkflowGenerationResult:
    """工作流生成结果"""

    success: bool
    visual_pipeline: dict[str, Any] | None = None
    raw_plan: dict[str, Any] | None = None
    message: str = ""
    error: str | None = None
    optimization_applied: bool = False
    optimization_metrics: dict[str, Any] | None = None


class WorkflowGenerator:
    """工作流生成器包装类

    将 sage-libs 生成器暴露给 Studio API，
    支持基于规则和基于 LLM 的两种生成策略。
    """

    def __init__(self):
        """初始化生成器"""
        self.rule_based_generator = None
        self.llm_generator = None

    def generate(
        self,
        user_input: str,
        session_messages: list[dict[str, Any]] | None = None,
        constraints: dict[str, Any] | None = None,
        use_llm: bool = True,
    ) -> WorkflowGenerationResult:
        """生成工作流

        Args:
            user_input: 用户自然语言描述
            session_messages: 对话历史
            constraints: 约束条件
            use_llm: True=使用LLM生成，False=使用规则生成

        Returns:
            WorkflowGenerationResult
        """
        try:
            from sage.libs.agentic.workflow import GenerationContext
            from sage.libs.agentic.workflow.generators import (
                LLMWorkflowGenerator,
                RuleBasedWorkflowGenerator,
            )

            # 创建生成上下文
            context = GenerationContext(
                user_input=user_input,
                conversation_history=session_messages or [],
                constraints=constraints or {},
            )

            # 选择生成器
            if use_llm:
                if self.llm_generator is None:
                    self.llm_generator = LLMWorkflowGenerator()
                generator = self.llm_generator
            else:
                if self.rule_based_generator is None:
                    self.rule_based_generator = RuleBasedWorkflowGenerator()
                generator = self.rule_based_generator

            # 执行生成
            result = generator.generate(context)

            if not result.success:
                return WorkflowGenerationResult(
                    success=False, error=result.error or "未知错误", message="工作流生成失败"
                )

            return WorkflowGenerationResult(
                success=True,
                visual_pipeline=result.visual_pipeline,
                raw_plan=result.raw_plan,
                message=result.explanation or "工作流生成成功",
            )

        except ImportError as e:
            logger.error(f"Failed to import workflow generators: {e}")
            return WorkflowGenerationResult(
                success=False, error=str(e), message="缺少依赖，无法生成工作流"
            )
        except Exception as e:
            logger.error(f"Workflow generation failed: {e}", exc_info=True)
            return WorkflowGenerationResult(
                success=False, error=str(e), message=f"工作流生成失败: {e}"
            )


def generate_workflow_from_chat(
    user_input: str,
    session_messages: list[dict[str, Any]] | None = None,
    enable_optimization: bool = False,
    use_llm: bool = True,
) -> WorkflowGenerationResult:
    """从聊天会话生成工作流（便捷函数）

    Args:
        user_input: 用户输入
        session_messages: 会话历史
        enable_optimization: 是否启用优化（未来功能）
        use_llm: 是否使用LLM（默认True）

    Returns:
        WorkflowGenerationResult
    """
    generator = WorkflowGenerator()
    result = generator.generate(
        user_input=user_input, session_messages=session_messages, use_llm=use_llm
    )

    # TODO: 未来可以在这里调用 sage-libs 的优化算法
    if enable_optimization and result.success:
        logger.info("Workflow optimization requested but not yet implemented")
        # from sage.libs.agentic.workflow.optimization import optimize_workflow
        # optimized = optimize_workflow(result.visual_pipeline, strategy="greedy")
        # result.visual_pipeline = optimized
        # result.optimization_applied = True

    return result


__all__ = [
    "WorkflowGenerator",
    "WorkflowGenerationRequest",
    "WorkflowGenerationResult",
    "generate_workflow_from_chat",
]
