"""
Studio Pipeline 数据模型

这些模型仅用于 UI 表示和序列化，不包含执行逻辑。
实际执行由 SAGE Kernel 的 DataStream API 完成。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

# Agent Step 模型（Multi-Agent 系统）
from sage.studio.models.agent_step import (
    AgentStep,
    StepStatus,
    StepType,
    reasoning_step,
    response_step,
    tool_call_step,
    tool_result_step,
)


class PipelineStatus(Enum):
    """Pipeline 状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeStatus(Enum):
    """节点执行状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class VisualNode:
    """
    可视化节点模型（仅用于 UI 表示）

    这个模型描述节点在 UI 中的表现，不包含执行逻辑。
    执行时会被转换为 SAGE 的 Operator。
    """

    id: str
    type: str  # 节点类型，如 "rag.generator", "rag.retriever"
    label: str
    position: dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0})  # UI 坐标
    config: dict[str, Any] = field(default_factory=dict)  # 节点配置参数

    # UI 状态（不参与执行）
    selected: bool = False
    collapsed: bool = False

    # 执行状态（由 SAGE 引擎提供）
    status: NodeStatus = NodeStatus.PENDING
    error_message: str | None = None
    execution_time: float = 0.0


@dataclass
class VisualConnection:
    """
    可视化连接模型（仅用于 UI 表示）

    描述节点之间的数据流连接。
    """

    id: str
    source_node_id: str
    source_port: str  # 输出端口名称
    target_node_id: str
    target_port: str  # 输入端口名称

    # UI 属性
    animated: bool = False
    label: str = ""


@dataclass
class VisualPipeline:
    """
    可视化 Pipeline 模型（仅用于 UI 表示和序列化）

    这是 Studio 的核心数据模型，描述一个完整的 Pipeline。
    不包含执行逻辑，执行时会被 PipelineBuilder 转换为 SAGE DataStream。

    Usage:
        # 在 UI 中创建
        pipeline = VisualPipeline(
            id="pipeline-123",
            name="RAG Pipeline",
            nodes=[...],
            connections=[...]
        )

        # 转换为 SAGE Pipeline 并执行
        from sage.studio.services.pipeline_builder import PipelineBuilder
        builder = PipelineBuilder()
        env = builder.build(pipeline)
        job = env.execute()
    """

    id: str
    name: str
    description: str = ""

    # Pipeline 结构
    nodes: list[VisualNode] = field(default_factory=list)
    connections: list[VisualConnection] = field(default_factory=list)

    # 元数据
    created_at: float | None = None
    updated_at: float | None = None
    tags: list[str] = field(default_factory=list)

    # 执行配置
    execution_mode: str = "local"  # "local", "distributed"

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典（用于 API 传输和持久化）"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "nodes": [
                {
                    "id": node.id,
                    "type": node.type,
                    "label": node.label,
                    "position": node.position,
                    "config": node.config,
                }
                for node in self.nodes
            ],
            "connections": [
                {
                    "id": conn.id,
                    "source": conn.source_node_id,
                    "sourcePort": conn.source_port,
                    "target": conn.target_node_id,
                    "targetPort": conn.target_port,
                }
                for conn in self.connections
            ],
            "executionMode": self.execution_mode,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VisualPipeline":
        """从字典反序列化"""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            nodes=[
                VisualNode(
                    id=node["id"],
                    type=node["type"],
                    label=node["label"],
                    position=node.get("position", {"x": 0, "y": 0}),
                    config=node.get("config", {}),
                )
                for node in data.get("nodes", [])
            ],
            connections=[
                VisualConnection(
                    id=conn.get("id", f"{conn['source']}-{conn['target']}"),
                    source_node_id=conn["source"],
                    source_port=conn.get("sourcePort", "output"),
                    target_node_id=conn["target"],
                    target_port=conn.get("targetPort", "input"),
                )
                for conn in data.get("connections", [])
            ],
            execution_mode=data.get("executionMode", "local"),
            created_at=data.get("createdAt"),
            updated_at=data.get("updatedAt"),
            tags=data.get("tags", []),
        )


@dataclass
class PipelineExecution:
    """
    Pipeline 执行状态模型

    记录一次 Pipeline 的执行状态。
    实际执行由 SAGE 引擎完成，这里只是状态的表示层。
    """

    id: str  # 执行 ID（对应 SAGE Job ID）
    pipeline_id: str
    status: PipelineStatus = PipelineStatus.PENDING

    # 时间信息
    start_time: float | None = None
    end_time: float | None = None
    execution_time: float = 0.0

    # 执行结果
    error_message: str | None = None
    node_statuses: dict[str, NodeStatus] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)

    # SAGE Job 引用
    sage_job_id: str | None = None
