"""
PlacementDecision - 调度决策数据结构

Scheduler 的返回值，表示调度决策而不是任务实例。
Dispatcher 根据决策调用 PlacementExecutor 执行放置。
"""

from dataclasses import dataclass, field
from typing import Any


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
    2. 资源需求（resource_requirements）
    3. 调度时机（delay, immediate）
    4. 放置策略（placement_strategy）
    5. 元数据（reason, priority）
    """

    # ===== 放置位置 =====
    target_node: str | None = None
    """目标物理节点 ID（Ray node_id）
    - None: 使用 Ray 默认负载均衡
    - "node-xxx": 指定节点
    - "local": 强制本地执行
    """

    # ===== 资源需求 =====
    resource_requirements: dict[str, Any] | None = None
    """资源需求配置
    示例: {"cpu": 4, "gpu": 1, "memory": "8GB", "custom_resource": 2}
    - cpu: CPU 核心数
    - gpu: GPU 数量
    - memory: 内存大小（支持字符串如 "8GB" 或字节数）
    - 自定义资源: 用户定义的资源类型
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
    placement_strategy: str = "default"
    """放置策略类型
    - "default": Ray 默认负载均衡
    - "spread": 分散放置（尽量不同节点）
    - "pack": 紧凑放置（尽量相同节点）
    - "affinity": 亲和性放置（靠近数据源）
    - "anti_affinity": 反亲和性（远离特定任务）
    """

    affinity_tasks: list[str] | None = None
    """亲和性任务列表（需要靠近的任务名）"""

    anti_affinity_tasks: list[str] | None = None
    """反亲和性任务列表（需要远离的任务名）"""

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

    def __repr__(self) -> str:
        """可读的字符串表示"""
        parts = [
            "PlacementDecision(",
            f"target_node={self.target_node}",
        ]

        if self.resource_requirements:
            parts.append(f"resources={self.resource_requirements}")

        if self.delay > 0:
            parts.append(f"delay={self.delay}s")

        if self.placement_strategy != "default":
            parts.append(f"strategy={self.placement_strategy}")

        if self.reason:
            parts.append(f"reason='{self.reason}'")

        return ", ".join(parts) + ")"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            "target_node": self.target_node,
            "resource_requirements": self.resource_requirements,
            "delay": self.delay,
            "immediate": self.immediate,
            "placement_strategy": self.placement_strategy,
            "affinity_tasks": self.affinity_tasks,
            "anti_affinity_tasks": self.anti_affinity_tasks,
            "reason": self.reason,
            "priority": self.priority,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlacementDecision":
        """从字典创建（用于反序列化）"""
        return cls(**data)

    @classmethod
    def immediate_default(cls, reason: str = "") -> "PlacementDecision":
        """快捷方法：立即使用默认配置调度"""
        return cls(
            target_node=None,
            resource_requirements=None,
            delay=0.0,
            immediate=True,
            placement_strategy="default",
            reason=reason or "Immediate default placement",
        )

    @classmethod
    def with_resources(
        cls,
        cpu: int | None = None,
        gpu: int | None = None,
        memory: int | str | None = None,  # Accept both int and str
        reason: str = "",
    ) -> "PlacementDecision":
        """快捷方法：指定资源需求"""
        resources: dict[str, int | str] = {}
        if cpu is not None:
            resources["cpu"] = cpu
        if gpu is not None:
            resources["gpu"] = gpu
        if memory is not None:
            resources["memory"] = memory

        return cls(
            target_node=None,
            resource_requirements=resources if resources else None,
            delay=0.0,
            immediate=True,
            placement_strategy="default",
            reason=reason or f"Resource requirements: {resources}",
        )

    @classmethod
    def with_node(
        cls, node_id: str, strategy: str = "default", reason: str = ""
    ) -> "PlacementDecision":
        """快捷方法：指定目标节点"""
        return cls(
            target_node=node_id,
            resource_requirements=None,
            delay=0.0,
            immediate=True,
            placement_strategy=strategy,
            reason=reason or f"Target node: {node_id}",
        )

    @classmethod
    def with_delay(cls, delay_seconds: float, reason: str = "") -> "PlacementDecision":
        """快捷方法：延迟调度"""
        return cls(
            target_node=None,
            resource_requirements=None,
            delay=delay_seconds,
            immediate=False,
            placement_strategy="default",
            reason=reason or f"Delayed by {delay_seconds}s",
        )


__all__ = ["PlacementDecision"]
