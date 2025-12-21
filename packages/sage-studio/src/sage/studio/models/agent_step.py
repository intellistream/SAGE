"""
Agent 执行步骤数据模型

Multi-Agent 系统执行过程中的步骤表示，用于前后端通信和 UI 展示。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepType(str, Enum):
    """步骤类型

    表示 Agent 执行过程中的不同步骤类型。
    """

    REASONING = "reasoning"  # 推理思考
    TOOL_CALL = "tool_call"  # 工具调用
    TOOL_RESULT = "tool_result"  # 工具返回
    RESPONSE = "response"  # 最终回复


class StepStatus(str, Enum):
    """步骤状态

    表示单个执行步骤的当前状态。
    """

    PENDING = "pending"  # 等待执行
    RUNNING = "running"  # 正在执行
    COMPLETED = "completed"  # 执行完成
    FAILED = "failed"  # 执行失败


@dataclass
class AgentStep:
    """Agent 执行步骤

    表示 Multi-Agent 系统执行过程中的一个步骤，
    用于前端展示推理过程和工具调用。

    Attributes:
        step_id: 步骤唯一标识符
        type: 步骤类型（推理、工具调用、工具结果、响应）
        content: 步骤内容描述
        status: 步骤当前状态
        metadata: 附加元数据（如工具名称、参数等）

    Example:
        >>> step = AgentStep.create(StepType.REASONING, "分析用户意图...")
        >>> step.to_dict()
        {'step_id': '...', 'type': 'reasoning', 'content': '分析用户意图...', ...}
    """

    step_id: str
    type: StepType
    content: str
    status: StepStatus = StepStatus.COMPLETED
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        type: StepType | str,
        content: str,
        status: StepStatus | str = StepStatus.COMPLETED,
        **metadata: Any,
    ) -> AgentStep:
        """便捷创建方法

        Args:
            type: 步骤类型，可以是 StepType 枚举或字符串
            content: 步骤内容描述
            status: 步骤状态，默认为 COMPLETED
            **metadata: 附加元数据，如 tool_name 等

        Returns:
            AgentStep: 创建的步骤实例

        Example:
            >>> step = AgentStep.create("reasoning", "正在分析...")
            >>> step = AgentStep.create(StepType.TOOL_CALL, "调用搜索工具", tool_name="search")
        """
        if isinstance(type, str):
            type = StepType(type)
        if isinstance(status, str):
            status = StepStatus(status)

        return cls(
            step_id=str(uuid.uuid4())[:8],
            type=type,
            content=content,
            status=status,
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于 JSON 序列化）

        Returns:
            dict: 包含所有字段的字典，枚举值转换为字符串

        Example:
            >>> step = AgentStep.create(StepType.REASONING, "思考中...")
            >>> data = step.to_dict()
            >>> data["type"]
            'reasoning'
        """
        return {
            "step_id": self.step_id,
            "type": self.type.value,
            "content": self.content,
            "status": self.status.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentStep:
        """从字典创建实例

        Args:
            data: 包含步骤数据的字典

        Returns:
            AgentStep: 反序列化的步骤实例

        Example:
            >>> data = {"step_id": "abc123", "type": "reasoning", ...}
            >>> step = AgentStep.from_dict(data)
        """
        return cls(
            step_id=data["step_id"],
            type=StepType(data["type"]),
            content=data["content"],
            status=StepStatus(data["status"]),
            metadata=data.get("metadata", {}),
        )

    def with_status(self, status: StepStatus | str) -> AgentStep:
        """返回更新状态后的新实例

        Args:
            status: 新的状态值

        Returns:
            AgentStep: 带有新状态的步骤副本
        """
        if isinstance(status, str):
            status = StepStatus(status)
        return AgentStep(
            step_id=self.step_id,
            type=self.type,
            content=self.content,
            status=status,
            metadata=self.metadata,
        )


# ============================================================================
# 便捷工厂函数
# ============================================================================


def reasoning_step(content: str, **metadata: Any) -> AgentStep:
    """创建推理步骤

    Args:
        content: 推理内容描述
        **metadata: 附加元数据

    Returns:
        AgentStep: 类型为 REASONING 的步骤

    Example:
        >>> step = reasoning_step("分析用户的问题类型...")
    """
    return AgentStep.create(StepType.REASONING, content, **metadata)


def tool_call_step(content: str, tool_name: str, **metadata: Any) -> AgentStep:
    """创建工具调用步骤

    Args:
        content: 调用描述
        tool_name: 工具名称
        **metadata: 附加元数据（如参数等）

    Returns:
        AgentStep: 类型为 TOOL_CALL，状态为 RUNNING 的步骤

    Example:
        >>> step = tool_call_step("搜索知识库...", "knowledge_search", query="SAGE是什么")
    """
    return AgentStep.create(
        StepType.TOOL_CALL,
        content,
        status=StepStatus.RUNNING,
        tool_name=tool_name,
        **metadata,
    )


def tool_result_step(content: str, tool_name: str, **metadata: Any) -> AgentStep:
    """创建工具结果步骤

    Args:
        content: 结果内容描述
        tool_name: 工具名称
        **metadata: 附加元数据（如结果数量等）

    Returns:
        AgentStep: 类型为 TOOL_RESULT 的步骤

    Example:
        >>> step = tool_result_step("找到 5 条相关记录", "knowledge_search", count=5)
    """
    return AgentStep.create(
        StepType.TOOL_RESULT,
        content,
        tool_name=tool_name,
        **metadata,
    )


def response_step(content: str, **metadata: Any) -> AgentStep:
    """创建最终响应步骤

    Args:
        content: 响应内容
        **metadata: 附加元数据

    Returns:
        AgentStep: 类型为 RESPONSE 的步骤

    Example:
        >>> step = response_step("根据检索结果，SAGE是一个...")
    """
    return AgentStep.create(StepType.RESPONSE, content, **metadata)


# 导出列表
__all__ = [
    "StepType",
    "StepStatus",
    "AgentStep",
    "reasoning_step",
    "tool_call_step",
    "tool_result_step",
    "response_step",
]
