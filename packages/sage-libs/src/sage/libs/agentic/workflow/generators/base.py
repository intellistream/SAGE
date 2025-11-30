"""
Base Abstractions for Workflow Generation

Layer: L3 (Core - Research & Algorithm Library)

Defines the interface and data structures for workflow generation algorithms.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GenerationStrategy(str, Enum):
    """工作流生成策略类型"""

    RULE_BASED = "rule_based"  # 基于规则的简单生成
    LLM_DRIVEN = "llm_driven"  # LLM 驱动的智能生成
    TEMPLATE_BASED = "template_based"  # 基于模板的生成
    HYBRID = "hybrid"  # 混合策略
    LEARNING_BASED = "learning_based"  # 基于学习的生成（未来）


@dataclass
class GenerationContext:
    """工作流生成上下文"""

    user_input: str
    """用户的自然语言输入"""

    conversation_history: list[dict[str, str]] = field(default_factory=list)
    """对话历史，格式: [{"role": "user/assistant", "content": "..."}]"""

    domain: str | None = None
    """应用领域，如 "rag", "data_processing", "analytics" 等"""

    constraints: dict[str, Any] = field(default_factory=dict)
    """约束条件，如 max_cost, max_latency, min_quality"""

    preferences: dict[str, Any] = field(default_factory=dict)
    """用户偏好，如 prefer_local_models, enable_streaming 等"""

    existing_workflow: Any | None = None
    """现有工作流（如果是增量修改）"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """其他元数据"""


@dataclass
class GenerationResult:
    """工作流生成结果"""

    success: bool
    """是否成功生成"""

    workflow_graph: Any | None = None
    """生成的工作流图 (WorkflowGraph 格式，用于优化)"""

    visual_pipeline: dict[str, Any] | None = None
    """可视化 Pipeline 配置 (Studio 格式)"""

    raw_plan: dict[str, Any] | None = None
    """原始 Pipeline 配置 (SAGE Kernel 格式)"""

    strategy_used: GenerationStrategy | None = None
    """使用的生成策略"""

    confidence: float = 0.0
    """生成置信度 (0-1)"""

    explanation: str = ""
    """生成过程的解释"""

    detected_intents: list[str] = field(default_factory=list)
    """检测到的用户意图"""

    suggested_optimizations: list[str] = field(default_factory=list)
    """建议的优化项"""

    error: str | None = None
    """错误信息（如果失败）"""

    generation_time: float = 0.0
    """生成耗时（秒）"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """其他元数据"""


class BaseWorkflowGenerator(ABC):
    """工作流生成器基类

    所有工作流生成算法都应该继承这个基类，实现 generate() 方法。

    研究方向：
    - 如何从自然语言准确理解用户意图？
    - 如何选择合适的算子和参数？
    - 如何保证生成的工作流是可执行的？
    - 如何处理模糊或不完整的需求？
    - 如何利用历史对话上下文？
    """

    def __init__(self, strategy: GenerationStrategy):
        """初始化生成器

        Args:
            strategy: 生成策略类型
        """
        self.strategy = strategy

    @abstractmethod
    def generate(self, context: GenerationContext) -> GenerationResult:
        """生成工作流

        Args:
            context: 生成上下文，包含用户输入、对话历史等

        Returns:
            生成结果，包含工作流配置和元数据
        """
        pass

    def validate_workflow(self, workflow: dict[str, Any]) -> tuple[bool, list[str]]:
        """验证生成的工作流是否有效

        Args:
            workflow: 工作流配置

        Returns:
            (是否有效, 错误列表)
        """
        errors = []

        # 基础验证
        if not workflow.get("pipeline"):
            errors.append("缺少 pipeline 配置")

        if not workflow.get("source"):
            errors.append("缺少 source 节点")

        if not workflow.get("sink"):
            errors.append("缺少 sink 节点")

        # 检查 stages
        stages = workflow.get("stages", [])
        for i, stage in enumerate(stages):
            if not stage.get("class"):
                errors.append(f"Stage {i} 缺少 class 字段")
            if not stage.get("kind"):
                errors.append(f"Stage {i} 缺少 kind 字段")

        return len(errors) == 0, errors

    def estimate_confidence(self, context: GenerationContext, result: dict[str, Any]) -> float:
        """估计生成结果的置信度

        子类可以重写此方法实现更复杂的置信度计算

        Args:
            context: 生成上下文
            result: 生成结果

        Returns:
            置信度 (0-1)
        """
        # 简单实现：基于检测到的意图数量
        base_confidence = 0.5

        # 如果有对话历史，提高置信度
        if context.conversation_history:
            base_confidence += 0.1

        # 如果有明确的领域，提高置信度
        if context.domain:
            base_confidence += 0.1

        # 如果有约束条件，提高置信度
        if context.constraints:
            base_confidence += 0.1

        return min(base_confidence, 0.95)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy={self.strategy})"


__all__ = [
    "GenerationStrategy",
    "GenerationContext",
    "GenerationResult",
    "BaseWorkflowGenerator",
]
