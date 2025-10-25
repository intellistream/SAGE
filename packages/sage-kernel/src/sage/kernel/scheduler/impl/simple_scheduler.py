"""
FIFO 调度器 - First-In-First-Out Baseline

最简单的调度策略：按任务到达顺序调度。
适合作为对比实验的 baseline。

特点：
- 简单、可预测
- 按 FIFO 顺序调度
- 尊重 operator 级别的并行度设置
- 适合负载均匀的场景

架构（重构后）：
- 纯决策者：返回 PlacementDecision，不执行放置
- 不持有 PlacementExecutor
- Dispatcher 协调决策和执行

使用方式:
    # 方式 1: 字符串指定
    env = LocalEnvironment(scheduler="fifo")

    # 方式 2: 实例化指定
    from sage.kernel.scheduler.impl import FIFOScheduler
    env = LocalEnvironment(scheduler=FIFOScheduler())
"""

import time
from typing import TYPE_CHECKING, Any

from sage.kernel.scheduler.api import BaseScheduler
from sage.kernel.scheduler.decision import PlacementDecision

if TYPE_CHECKING:
    from sage.kernel.runtime.graph.graph_node import TaskNode
    from sage.kernel.runtime.graph.service_node import ServiceNode


class FIFOScheduler(BaseScheduler):
    """
    FIFO 调度器 - 纯决策者

    按照任务到达顺序调度，不进行任何重新排序。
    尊重 transformation.parallelism 设置。
    作为最简单的 baseline。

    职责：
    - 制定调度决策：按 FIFO 顺序，立即调度
    - 返回决策对象：PlacementDecision
    - 不执行放置：由 Dispatcher 协调 PlacementExecutor 执行
    """

    def __init__(self, platform: str = "local"):
        """
        初始化 FIFO 调度器

        Args:
            platform: 平台类型 ('local' 或 'remote')
                     这是元数据，不影响调度决策
        """
        super().__init__()
        self.platform = platform
        self.total_latency = 0.0
        self.start_times: dict[str, float] = {}

    def make_decision(self, task_node: "TaskNode") -> PlacementDecision:
        """
        FIFO 调度决策：立即使用默认配置调度

        FIFO 策略最简单：
        1. 不考虑优先级
        2. 不考虑负载
        3. 立即调度
        4. 使用 Ray 默认负载均衡

        Args:
            task_node: 任务节点（包含 transformation 和 parallelism 信息）

        Returns:
            PlacementDecision: 调度决策
        """
        start_time = time.time()

        # FIFO 决策：立即调度到默认节点
        self.scheduled_count += 1

        decision = PlacementDecision.immediate_default(
            reason=f"FIFO order: #{self.scheduled_count}"
        )

        # 记录决策历史
        self.decision_history.append(decision)

        # 记录调度指标
        elapsed = time.time() - start_time
        self.total_latency += elapsed
        self.start_times[task_node.name] = start_time

        return decision

    def make_service_decision(self, service_node: "ServiceNode") -> PlacementDecision:
        """
        FIFO 服务调度决策

        对于 FIFO 调度器，服务也按照到达顺序立即调度。

        Args:
            service_node: 服务节点

        Returns:
            PlacementDecision: 服务调度决策
        """
        self.scheduled_count += 1

        decision = PlacementDecision.immediate_default(
            reason=f"FIFO service: {service_node.service_name} (#{self.scheduled_count})"
        )

        self.decision_history.append(decision)
        return decision

    def get_metrics(self) -> dict[str, Any]:
        """
        获取 FIFO 调度器的性能指标

        Returns:
            指标字典
        """
        avg_latency = self.total_latency / self.scheduled_count if self.scheduled_count > 0 else 0
        return {
            "scheduler_type": "FIFO",
            "total_scheduled": self.scheduled_count,
            "avg_latency_ms": avg_latency * 1000,
            "decisions": len(self.decision_history),
            "platform": self.platform,
        }

    def shutdown(self):
        """关闭调度器"""
        super().shutdown()
        self.start_times.clear()


__all__ = ["FIFOScheduler"]
