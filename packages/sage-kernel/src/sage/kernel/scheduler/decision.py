"""
PlacementDecision - 调度决策数据结构

Scheduler 的返回值，表示调度决策而不是任务实例。
Dispatcher 根据决策调用 PlacementExecutor 执行放置。

架构原则（Issue #1437）：
- PlacementDecision 使用 ResourceSpec 类型化资源规格（不再是 dict[str, Any]）
- 不含任何后端运行时特定类型（无 Ray/Flownet 内部类型）
- 提供 to_schema() 方法输出标准化 PlacementSchema 供 Flownet 消费
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from sage.kernel.scheduler.schema import (
    PlacementSchema,
    PlacementStrategy,
    ResourceSpec,
    parse_memory,
)

if TYPE_CHECKING:
    pass


@dataclass
class PlacementDecision:
    """
    调度决策：Scheduler.make_decision() 的返回值

    职责分离：
    - Scheduler 返回决策（这个类）
    - Dispatcher 协调执行
    - PlacementExecutor 执行放置

    决策内容：
    1. 放置位置（target_node）
    2. 资源需求（resource 字段，类型化 ResourceSpec）
    3. 调度时机（delay, immediate）
    4. 放置策略（placement_strategy，使用 PlacementStrategy 枚举）
    5. 元数据（reason, priority）
    """

    # ===== 放置位置 =====
    target_node: str | None = None
    """目标节点提示（逻辑 ID，非后端内部 ID）
    - None: 由运行时决定负载均衡
    - "node-xxx": 指定逻辑节点
    - "local": 强制本地执行
    """

    # ===== 资源需求（类型化，无旧版 dict）=====
    resource: ResourceSpec = field(default_factory=ResourceSpec)
    """资源规格声明（ResourceSpec 强类型 Schema）
    示例:
        ResourceSpec(cpu=4, gpu=1, memory_bytes=8*1024**3)
        ResourceSpec(affinity_tags={"zone": "us-west"})
    """

    # ===== 调度时机 =====
    delay: float = 0.0
    """延迟调度时间（秒）
    - 0.0: 立即调度
    - > 0: 延迟指定秒数后调度
    """

    immediate: bool = True
    """是否立即调度
    - True: 立即执行
    - False: 可以批量延迟调度
    """

    # ===== 放置策略 =====
    placement_strategy: PlacementStrategy = PlacementStrategy.DEFAULT
    """放置策略（PlacementStrategy 枚举，后端无关）
    - DEFAULT: 由运行时自行决定负载均衡
    - SPREAD: 分散放置（尽量不同节点）
    - PACK: 紧凑放置（尽量相同节点）
    - AFFINITY: 亲和性放置（靠近数据源）
    - ANTI_AFFINITY: 反亲和性（远离特定任务）
    """

    affinity_tasks: list[str] = field(default_factory=list)
    """亲和性任务 ID 列表（需要靠近的任务）"""

    anti_affinity_tasks: list[str] = field(default_factory=list)
    """反亲和性任务 ID 列表（需要远离的任务）"""

    # ===== 元数据 =====
    reason: str = ""
    """决策原因（用于日志和调试）
    示例: "Load-aware: node-2 has lowest CPU usage"
    """

    priority: int = 0
    """调度优先级（数值越大优先级越高）
    - 0: 普通优先级
    - > 0: 高优先级
    - < 0: 低优先级
    """

    metadata: dict[str, Any] = field(default_factory=dict)
    """额外的元数据（用于扩展）"""

    def to_schema(self) -> PlacementSchema:
        """转换为标准化 PlacementSchema（供 Flownet 消费）

        Returns:
            PlacementSchema - 不含任何后端特定类型的放置决策 Schema
        """
        return PlacementSchema(
            resource=self.resource,
            strategy=self.placement_strategy,
            target_node_hint=self.target_node,
            delay_seconds=self.delay,
            priority=self.priority,
            affinity_task_ids=list(self.affinity_tasks),
            anti_affinity_task_ids=list(self.anti_affinity_tasks),
            reason=self.reason,
            metadata=dict(self.metadata),
        )

    def __repr__(self) -> str:
        """可读的字符串表示"""
        parts = [f"target_node={self.target_node}"]

        if not self.resource.is_empty():
            parts.append(f"resource={self.resource!r}")

        if self.delay > 0:
            parts.append(f"delay={self.delay}s")

        if self.placement_strategy != PlacementStrategy.DEFAULT:
            parts.append(f"strategy={self.placement_strategy.value}")

        if self.reason:
            parts.append(f"reason='{self.reason}'")

        return "PlacementDecision(" + ", ".join(parts) + ")"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            "target_node": self.target_node,
            "resource": self.resource.to_dict(),
            "delay": self.delay,
            "immediate": self.immediate,
            "placement_strategy": self.placement_strategy.value,
            "affinity_tasks": list(self.affinity_tasks),
            "anti_affinity_tasks": list(self.anti_affinity_tasks),
            "reason": self.reason,
            "priority": self.priority,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlacementDecision:
        """从字典创建（用于反序列化）"""
        resource_data = data.get("resource")
        resource = ResourceSpec.from_dict(resource_data) if resource_data else ResourceSpec()
        strategy_raw = data.get("placement_strategy", "default")
        strategy = PlacementStrategy(strategy_raw)
        return cls(
            target_node=data.get("target_node"),
            resource=resource,
            delay=data.get("delay", 0.0),
            immediate=data.get("immediate", True),
            placement_strategy=strategy,
            affinity_tasks=data.get("affinity_tasks", []),
            anti_affinity_tasks=data.get("anti_affinity_tasks", []),
            reason=data.get("reason", ""),
            priority=data.get("priority", 0),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def immediate_default(cls, reason: str = "") -> PlacementDecision:
        """快捷方法：立即使用默认配置调度"""
        return cls(
            target_node=None,
            resource=ResourceSpec(),
            delay=0.0,
            immediate=True,
            placement_strategy=PlacementStrategy.DEFAULT,
            reason=reason or "Immediate default placement",
        )

    @classmethod
    def with_resources(
        cls,
        cpu: float | None = None,
        gpu: float | None = None,
        memory: int | str | None = None,
        reason: str = "",
    ) -> PlacementDecision:
        """快捷方法：指定资源需求

        Args:
            cpu: CPU 核心数需求
            gpu: GPU 数量需求
            memory: 内存需求（整数字节数或字符串如 "8GB"）
            reason: 决策原因
        """
        memory_bytes: int | None = None
        if memory is not None:
            memory_bytes = parse_memory(memory)

        spec = ResourceSpec(cpu=cpu, gpu=gpu, memory_bytes=memory_bytes)
        return cls(
            target_node=None,
            resource=spec,
            delay=0.0,
            immediate=True,
            placement_strategy=PlacementStrategy.DEFAULT,
            reason=reason or f"Resource requirements: cpu={cpu}, gpu={gpu}, memory={memory}",
        )

    @classmethod
    def with_node(
        cls,
        node_id: str,
        strategy: PlacementStrategy = PlacementStrategy.DEFAULT,
        reason: str = "",
    ) -> PlacementDecision:
        """快捷方法：指定目标节点"""
        return cls(
            target_node=node_id,
            resource=ResourceSpec(),
            delay=0.0,
            immediate=True,
            placement_strategy=strategy,
            reason=reason or f"Target node: {node_id}",
        )

    @classmethod
    def with_delay(cls, delay_seconds: float, reason: str = "") -> PlacementDecision:
        """快捷方法：延迟调度"""
        return cls(
            target_node=None,
            resource=ResourceSpec(),
            delay=delay_seconds,
            immediate=False,
            placement_strategy=PlacementStrategy.DEFAULT,
            reason=reason or f"Delayed by {delay_seconds}s",
        )


__all__ = ["PlacementDecision"]
