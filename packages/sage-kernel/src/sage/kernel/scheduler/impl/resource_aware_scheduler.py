"""
负载感知调度器 - Load-Aware Scheduler

根据当前系统负载和资源使用情况进行调度决策。
适合资源受限或负载波动的场景。

特点：
- 监控系统资源使用
- 根据负载动态调度
- 避免资源过载
- 平衡资源利用率

使用方式:
    # 方式 1: 字符串指定
    env = LocalEnvironment(scheduler="load_aware")

    # 方式 2: 实例化指定
    from sage.kernel.scheduler.impl import LoadAwareScheduler
    env = LocalEnvironment(scheduler=LoadAwareScheduler())
"""

import time
from typing import TYPE_CHECKING, Any, Dict

from sage.kernel.scheduler.api import BaseScheduler

if TYPE_CHECKING:
    from sage.kernel.runtime.graph.graph_node import TaskNode
    from sage.kernel.runtime.graph.service_node import ServiceNode
    from sage.kernel.runtime.service.base_service_task import BaseServiceTask
    from sage.kernel.runtime.task.base_task import BaseTask


class LoadAwareScheduler(BaseScheduler):
    """
    负载感知调度器

    根据系统当前负载动态决定任务调度。
    尊重 transformation.parallelism 设置。
    """

    def __init__(self, platform: str = "local", max_concurrent: int = 10):
        """
        初始化负载感知调度器

        Args:
            platform: 平台类型 ('local' 或 'remote')
            max_concurrent: 最大并发任务数
        """
        self.platform = platform
        self.max_concurrent = max_concurrent
        self.scheduled_count = 0
        self.total_latency = 0.0
        self.active_tasks = 0
        self.resource_utilization = []

    def schedule_task(self, task_node: "TaskNode", runtime_ctx=None) -> "BaseTask":
        """
        负载感知调度：根据当前负载决定调度时机

        Args:
            task_node: 任务节点
            runtime_ctx: 运行时上下文

        Returns:
            创建的任务实例
        """
        start_time = time.time()

        # 检查当前负载
        while self.active_tasks >= self.max_concurrent:
            time.sleep(0.01)  # 等待资源释放

        # 创建任务
        ctx = runtime_ctx if runtime_ctx is not None else task_node.ctx
        task = task_node.task_factory.create_task(task_node.name, ctx)

        # 更新状态
        self.active_tasks += 1
        self.scheduled_count += 1
        elapsed = time.time() - start_time
        self.total_latency += elapsed

        # 记录资源利用率
        utilization = self.active_tasks / self.max_concurrent
        self.resource_utilization.append(utilization)

        return task

    def task_completed(self):
        """任务完成时调用，释放资源"""
        self.active_tasks = max(0, self.active_tasks - 1)

    def schedule_service(
        self, service_node: "ServiceNode", runtime_ctx=None
    ) -> "BaseServiceTask":
        """
        调度服务节点

        Args:
            service_node: 服务节点
            runtime_ctx: 运行时上下文

        Returns:
            创建的服务任务实例
        """
        ctx = runtime_ctx if runtime_ctx is not None else service_node.ctx
        service_task = service_node.service_task_factory.create_service_task(ctx)
        return service_task

    def get_metrics(self) -> Dict[str, Any]:
        """
        获取调度器性能指标

        Returns:
            包含负载和资源利用率的指标
        """
        avg_latency = (
            self.total_latency / self.scheduled_count if self.scheduled_count > 0 else 0
        )
        avg_utilization = (
            sum(self.resource_utilization) / len(self.resource_utilization)
            if self.resource_utilization
            else 0
        )

        return {
            "scheduler_type": "LoadAware",
            "total_scheduled": self.scheduled_count,
            "avg_latency_ms": avg_latency * 1000,
            "active_tasks": self.active_tasks,
            "max_concurrent": self.max_concurrent,
            "avg_resource_utilization": avg_utilization,
            "platform": self.platform,
        }

    def shutdown(self):
        """关闭调度器"""
        self.resource_utilization.clear()


__all__ = ["LoadAwareScheduler"]
