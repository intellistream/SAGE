"""
Scheduling Declaration Schema - 调度声明模式

SAGE L3 (Kernel) 层定义的资源规格和放置决策的声明式 Schema。

架构原则（Issue #1437）：
- SAGE 拥有调度声明语义（ResourceSpec + PlacementSchema）
- Flownet 运行时消费此 Schema 并执行具体放置
- Schema 本身不包含任何运行时特定类型（无 Ray/Flownet 内部类型泄漏）
- 调度器输出仅包含 schema 类型，不含后端相关类型

使用示例::

    # 声明资源需求
    spec = ResourceSpec(cpu=4, gpu=1, memory_bytes=8 * 1024**3)

    # 带亲和性
    spec = ResourceSpec(
        cpu=2,
        affinity_tags={"zone": "us-west"},
        anti_affinity_tags={"role": "gateway"},
    )

    # 声明放置策略
    from sage.kernel.scheduler.schema import PlacementStrategy, PlacementSchema
    schema = PlacementSchema(
        resource=spec,
        strategy=PlacementStrategy.SPREAD,
        target_node_hint="node-1",
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PlacementStrategy(str, Enum):
    """放置策略枚举

    SAGE 声明侧定义的策略语义，由 Flownet 运行时负责具体实现。
    """

    DEFAULT = "default"
    """默认放置：由后端运行时自行决定负载均衡"""

    SPREAD = "spread"
    """分散放置：尽量将任务分散到不同节点"""

    PACK = "pack"
    """紧凑放置：尽量将任务聚集到同一节点"""

    AFFINITY = "affinity"
    """亲和性放置：靠近指定标签的节点/任务"""

    ANTI_AFFINITY = "anti_affinity"
    """反亲和性放置：远离指定标签的节点/任务"""


@dataclass
class ResourceSpec:
    """资源规格声明 Schema

    SAGE 声明侧的资源需求描述，与后端无关。
    Flownet 运行时消费此类型并将其映射到底层调度原语。

    所有字段均为可选，未指定表示无约束（由后端自由分配）。

    字段说明：
        cpu: 所需 CPU 核心数，支持分数（如 0.5）
        gpu: 所需 GPU 数量，支持分数（如 0.5）
        memory_bytes: 所需内存字节数（整数）
        custom_resources: 自定义资源，键为资源名称，值为数量
        affinity_tags: 亲和性标签约束，任务应调度到匹配这些标签的节点
        anti_affinity_tags: 反亲和性标签约束，任务应避开匹配这些标签的节点
    """

    cpu: float | None = None
    """CPU 核心数需求（如 1, 2, 0.5）"""

    gpu: float | None = None
    """GPU 数量需求（如 1, 2, 0.5）"""

    memory_bytes: int | None = None
    """内存需求（字节数），使用 parse_memory() 从字符串解析"""

    custom_resources: dict[str, float] = field(default_factory=dict)
    """自定义资源需求，示例: {"tpu": 1.0, "fpga": 2.0}"""

    affinity_tags: dict[str, str] = field(default_factory=dict)
    """亲和性标签约束，示例: {"zone": "us-west", "role": "compute"}"""

    anti_affinity_tags: dict[str, str] = field(default_factory=dict)
    """反亲和性标签约束，示例: {"role": "gateway"}"""

    def is_empty(self) -> bool:
        """检查是否为空规格（无任何资源约束）"""
        return (
            self.cpu is None
            and self.gpu is None
            and self.memory_bytes is None
            and not self.custom_resources
            and not self.affinity_tags
            and not self.anti_affinity_tags
        )

    def validate(self) -> None:
        """验证资源规格的合法性

        Raises:
            ValueError: 当资源值非法时（如负数）
        """
        if self.cpu is not None and self.cpu < 0:
            raise ValueError(f"cpu must be non-negative, got {self.cpu}")
        if self.gpu is not None and self.gpu < 0:
            raise ValueError(f"gpu must be non-negative, got {self.gpu}")
        if self.memory_bytes is not None and self.memory_bytes < 0:
            raise ValueError(f"memory_bytes must be non-negative, got {self.memory_bytes}")
        for name, amount in self.custom_resources.items():
            if amount < 0:
                raise ValueError(f"custom_resource '{name}' must be non-negative, got {amount}")

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典"""
        return {
            "cpu": self.cpu,
            "gpu": self.gpu,
            "memory_bytes": self.memory_bytes,
            "custom_resources": dict(self.custom_resources),
            "affinity_tags": dict(self.affinity_tags),
            "anti_affinity_tags": dict(self.anti_affinity_tags),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResourceSpec:
        """从字典反序列化"""
        return cls(
            cpu=data.get("cpu"),
            gpu=data.get("gpu"),
            memory_bytes=data.get("memory_bytes"),
            custom_resources=data.get("custom_resources", {}),
            affinity_tags=data.get("affinity_tags", {}),
            anti_affinity_tags=data.get("anti_affinity_tags", {}),
        )

    @classmethod
    def from_legacy_dict(cls, legacy: dict[str, Any]) -> ResourceSpec:
        """从旧版资源字典迁移（向后兼容转换辅助）

        旧版格式示例::

            {"cpu": 4, "gpu": 1, "memory": "8GB"}

        Args:
            legacy: 旧版 resource_requirements 字典（可能含字符串 memory）
        """
        memory_bytes: int | None = None
        raw_memory = legacy.get("memory")
        if raw_memory is not None:
            memory_bytes = parse_memory(raw_memory)

        return cls(
            cpu=legacy.get("cpu"),
            gpu=legacy.get("gpu"),
            memory_bytes=memory_bytes,
            custom_resources={
                k: float(v) for k, v in legacy.items() if k not in ("cpu", "gpu", "memory")
            },
        )

    def __repr__(self) -> str:
        parts = []
        if self.cpu is not None:
            parts.append(f"cpu={self.cpu}")
        if self.gpu is not None:
            parts.append(f"gpu={self.gpu}")
        if self.memory_bytes is not None:
            parts.append(f"memory={format_memory(self.memory_bytes)}")
        if self.custom_resources:
            parts.append(f"custom={self.custom_resources}")
        if self.affinity_tags:
            parts.append(f"affinity={self.affinity_tags}")
        if self.anti_affinity_tags:
            parts.append(f"anti_affinity={self.anti_affinity_tags}")
        return f"ResourceSpec({', '.join(parts) if parts else 'unconstrained'})"


@dataclass
class PlacementSchema:
    """放置决策 Schema

    SAGE 调度器输出的标准化放置决策契约。
    - 不含任何后端运行时类型（无 Ray/Flownet 内部对象）
    - Flownet PlacementSchemaAdapter 消费此类型并映射到运行时原语

    字段说明：
        resource: 资源规格声明（ResourceSpec）
        strategy: 放置策略（PlacementStrategy 枚举）
        target_node_hint: 目标节点提示（逻辑节点 ID，不依赖后端实现）
        delay_seconds: 延迟调度秒数（0 表示立即）
        priority: 调度优先级（数值越大越优先）
        affinity_task_ids: 需要靠近的任务 ID 列表（亲和性语义）
        anti_affinity_task_ids: 需要远离的任务 ID 列表（反亲和性语义）
        reason: 决策原因说明（调试/日志用途）
        metadata: 可扩展元数据
    """

    resource: ResourceSpec = field(default_factory=ResourceSpec)
    """资源规格声明"""

    strategy: PlacementStrategy = PlacementStrategy.DEFAULT
    """放置策略"""

    target_node_hint: str | None = None
    """目标节点提示（逻辑 ID，非后端内部 ID）"""

    delay_seconds: float = 0.0
    """延迟调度秒数，0 表示立即调度"""

    priority: int = 0
    """调度优先级，数值越大越优先（默认 0）"""

    affinity_task_ids: list[str] = field(default_factory=list)
    """亲和性任务 ID 列表（应调度到靠近这些任务的节点）"""

    anti_affinity_task_ids: list[str] = field(default_factory=list)
    """反亲和性任务 ID 列表（应避开这些任务所在节点）"""

    reason: str = ""
    """决策原因说明（调试/日志用途）"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """可扩展元数据"""

    def validate(self) -> None:
        """验证 PlacementSchema 合法性

        Raises:
            ValueError: 当字段值非法时
        """
        self.resource.validate()
        if self.delay_seconds < 0:
            raise ValueError(f"delay_seconds must be non-negative, got {self.delay_seconds}")

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典"""
        return {
            "resource": self.resource.to_dict(),
            "strategy": self.strategy.value,
            "target_node_hint": self.target_node_hint,
            "delay_seconds": self.delay_seconds,
            "priority": self.priority,
            "affinity_task_ids": list(self.affinity_task_ids),
            "anti_affinity_task_ids": list(self.anti_affinity_task_ids),
            "reason": self.reason,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlacementSchema:
        """从字典反序列化"""
        return cls(
            resource=ResourceSpec.from_dict(data.get("resource", {})),
            strategy=PlacementStrategy(data.get("strategy", "default")),
            target_node_hint=data.get("target_node_hint"),
            delay_seconds=data.get("delay_seconds", 0.0),
            priority=data.get("priority", 0),
            affinity_task_ids=data.get("affinity_task_ids", []),
            anti_affinity_task_ids=data.get("anti_affinity_task_ids", []),
            reason=data.get("reason", ""),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def immediate(cls, reason: str = "") -> PlacementSchema:
        """快捷方法：立即使用默认配置调度"""
        return cls(
            resource=ResourceSpec(),
            strategy=PlacementStrategy.DEFAULT,
            reason=reason or "Immediate default placement",
        )

    @classmethod
    def with_resources(
        cls,
        cpu: float | None = None,
        gpu: float | None = None,
        memory: int | str | None = None,
        strategy: PlacementStrategy = PlacementStrategy.DEFAULT,
        reason: str = "",
    ) -> PlacementSchema:
        """快捷方法：指定资源需求创建 PlacementSchema

        Args:
            cpu: CPU 核心数需求
            gpu: GPU 数量需求
            memory: 内存需求（整数字节数或字符串如 "8GB"）
            strategy: 放置策略
            reason: 决策原因
        """
        memory_bytes: int | None = None
        if memory is not None:
            memory_bytes = parse_memory(memory)

        spec = ResourceSpec(cpu=cpu, gpu=gpu, memory_bytes=memory_bytes)
        return cls(
            resource=spec,
            strategy=strategy,
            reason=reason or f"Resources: cpu={cpu}, gpu={gpu}, memory={memory}",
        )

    def __repr__(self) -> str:
        parts = [f"strategy={self.strategy.value}"]
        if not self.resource.is_empty():
            parts.append(f"resource={self.resource!r}")
        if self.target_node_hint:
            parts.append(f"node={self.target_node_hint!r}")
        if self.delay_seconds > 0:
            parts.append(f"delay={self.delay_seconds}s")
        if self.priority != 0:
            parts.append(f"priority={self.priority}")
        return f"PlacementSchema({', '.join(parts)})"


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

_MEMORY_UNITS: dict[str, int] = {
    "b": 1,
    "kb": 1024,
    "mb": 1024**2,
    "gb": 1024**3,
    "tb": 1024**4,
    "k": 1024,
    "m": 1024**2,
    "g": 1024**3,
    "t": 1024**4,
}


def parse_memory(value: int | str) -> int:
    """将内存描述解析为字节数

    Args:
        value: 整数（字节数）或字符串（如 "8GB", "512MB", "1024"）

    Returns:
        内存字节数（整数）

    Raises:
        ValueError: 当格式无效时

    Examples::

        parse_memory(1024)       # → 1024
        parse_memory("8GB")      # → 8589934592
        parse_memory("512mb")    # → 536870912
        parse_memory("1024")     # → 1024
    """
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    s = str(value).strip().lower()
    # 纯数字字符串
    if s.isdigit():
        return int(s)
    # 带单位
    for unit, multiplier in sorted(_MEMORY_UNITS.items(), key=lambda x: -len(x[0])):
        if s.endswith(unit):
            numeric_part = s[: -len(unit)].strip()
            if not numeric_part:
                raise ValueError(f"Invalid memory value: {value!r}")
            return int(float(numeric_part) * multiplier)
    raise ValueError(
        f"Cannot parse memory value: {value!r}. "
        f"Expected integer bytes or string with unit (e.g. '8GB', '512MB')."
    )


def format_memory(bytes_value: int) -> str:
    """将字节数格式化为可读字符串

    Examples::

        format_memory(1024)         # → "1.0KB"
        format_memory(8589934592)   # → "8.0GB"
    """
    for unit in ("TB", "GB", "MB", "KB"):
        divisor = _MEMORY_UNITS[unit.lower()]
        if bytes_value >= divisor:
            return f"{bytes_value / divisor:.1f}{unit}"
    return f"{bytes_value}B"


__all__ = [
    "PlacementStrategy",
    "ResourceSpec",
    "PlacementSchema",
    "parse_memory",
    "format_memory",
]
