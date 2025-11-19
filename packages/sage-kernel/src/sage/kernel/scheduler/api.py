"""
Scheduler API - 调度器核心 API 定义

架构原则（重构后）：
1. 职责分离：
   - Scheduler: 纯决策者（返回 PlacementDecision，不执行放置）
   - PlacementExecutor: 纯执行者（接收决策，执行物理放置）
   - Dispatcher: 协调者（决策 → 执行）

2. 对用户透明：
   - 用户只需在创建 Environment 时指定调度策略
   - 并行度是 operator 级别的 - 在定义 transformation 时指定
   - 调度策略是应用级别的 - 在 Environment 中配置

用户使用示例:
    # 应用级别指定调度策略
    env = LocalEnvironment(scheduler="fifo")  # 或 "load_aware", "priority" 等

    # operator 级别指定并行度和资源需求
    (env.from_source(MySource)
        .map(MyOperator, parallelism=4, cpu_required=4, memory_required="8GB")
        .filter(MyFilter, parallelism=2)
        .sink(MySink))

    env.submit()  # Dispatcher 协调 Scheduler 和 Placement

开发者使用示例（对比不同调度策略）:
    from sage.kernel.scheduler.impl import FIFOScheduler, LoadAwareScheduler

    # 策略 1: FIFO
    env1 = LocalEnvironment(scheduler=FIFOScheduler())

    # 策略 2: 负载感知
    env2 = LocalEnvironment(scheduler=LoadAwareScheduler(max_concurrent=10))

正确流程:
    Dispatcher.submit():
        for node in graph.nodes:
            # 1. 获取调度决策
            decision = scheduler.make_decision(node)

            # 2. 根据决策等待（如果需要）
            if decision.delay > 0:
                time.sleep(decision.delay)

            # 3. 执行物理放置
            task = placement_executor.place_task(node, decision)

            # 4. 保存任务实例
            self.tasks[node.name] = task
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Union

if TYPE_CHECKING:
    from sage.kernel.runtime.graph.graph_node import TaskNode
    from sage.kernel.runtime.graph.service_node import ServiceNode
    from sage.kernel.runtime.service.local_service_task import LocalServiceTask
    from sage.kernel.runtime.task.local_task import LocalTask
    from sage.kernel.scheduler.decision import PlacementDecision
    from sage.kernel.utils.ray.actor import ActorWrapper


class BaseScheduler(ABC):
    """
    调度器抽象基类 - 纯决策者

    重要架构变更：
    - Scheduler 不再持有 placement_executor（解耦）
    - Scheduler 返回 PlacementDecision，不返回 Task（职责分离）
    - Dispatcher 协调 Scheduler 和 PlacementExecutor（中介者模式）

    调度器在 Environment 级别配置，对用户透明。
    并行度在 operator 级别指定（transformation.parallelism）。

    职责：
    1. 分析任务节点信息（并行度、资源需求等）
    2. 评估系统状态（负载、资源可用性等）
    3. 制定调度决策（何时、何处、如何放置）
    4. 返回决策对象（不执行放置）
    """

    def __init__(self):
        """
        初始化调度器

        注意：Scheduler 不再持有 placement_executor
              PlacementExecutor 由 Dispatcher 持有和管理
        """
        self.scheduled_count = 0
        self.decision_history = []

    @abstractmethod
    def make_decision(self, task_node: "TaskNode") -> "PlacementDecision":
        """
        制定任务调度决策（核心方法）

        这是 Scheduler 的核心职责：分析并返回调度决策，不执行放置。

        调度器根据以下因素做出决策：
        - task_node.transformation.parallelism (并行度)
        - task_node.transformation 的资源需求（cpu_required, memory_required等）
        - 当前系统负载和资源可用性
        - 调度策略（FIFO、优先级、负载感知等）

        Args:
            task_node: 任务节点（包含 transformation 和 parallelism 信息）

        Returns:
            PlacementDecision: 调度决策对象，包含：
                - target_node: 目标物理节点
                - resource_requirements: 资源需求
                - delay: 延迟时间
                - placement_strategy: 放置策略
                - reason: 决策原因

        示例:
            decision = scheduler.make_decision(task_node)
            # decision = PlacementDecision(
            #     target_node="worker-node-2",
            #     resource_requirements={"cpu": 4, "memory": "8GB"},
            #     delay=0.0,
            #     reason="Load-aware: node-2 has lowest CPU usage"
            # )
        """
        pass

    def make_service_decision(self, service_node: "ServiceNode") -> "PlacementDecision":
        """
        制定服务调度决策

        服务通常需要特殊处理（如固定节点、持久化等）
        子类可以重写此方法提供自定义逻辑。

        Args:
            service_node: 服务节点

        Returns:
            PlacementDecision: 服务放置决策
        """
        # 默认实现：使用立即默认配置
        from sage.kernel.scheduler.decision import PlacementDecision

        return PlacementDecision.immediate_default(
            reason=f"Service placement: {service_node.service_name}"
        )

    def schedule_task(
        self, task_node: "TaskNode", runtime_ctx=None
    ) -> Union["LocalTask", "ActorWrapper"]:
        """
        调度任务（兼容性方法）

        这是一个高级 API，用于直接创建和调度任务。
        内部调用 make_decision() 获取调度决策，然后通过任务工厂创建任务。

        使用场景：
        - 单元测试和集成测试
        - 简单调度场景（不需要显式处理决策）
        - 与现有代码兼容

        Args:
            task_node: 任务节点
            runtime_ctx: 运行时上下文（如果为 None，使用 task_node.ctx）

        Returns:
            创建的任务实例（LocalTask 或 ActorWrapper）
        """
        # 调用核心决策方法
        decision = self.make_decision(task_node)

        # 根据决策延迟（如果需要）
        if hasattr(decision, "delay") and decision.delay > 0:
            import time

            time.sleep(decision.delay)

        # 通过任务工厂创建任务
        ctx = runtime_ctx if runtime_ctx is not None else task_node.ctx
        task = task_node.task_factory.create_task(task_node.name, ctx)

        return task

    def schedule_service(
        self, service_node: "ServiceNode", runtime_ctx=None
    ) -> Union["LocalServiceTask", "ActorWrapper"]:
        """
        调度服务（兼容性方法）

        这是一个高级 API，用于直接创建和调度服务。
        内部调用 make_service_decision() 获取调度决策，然后通过服务工厂创建服务。

        Args:
            service_node: 服务节点
            runtime_ctx: 运行时上下文（如果为 None，使用 service_node.ctx）

        Returns:
            创建的服务任务实例（LocalServiceTask 或 ActorWrapper）
        """
        # 调用服务决策方法
        decision = self.make_service_decision(service_node)

        # 根据决策延迟（如果需要）
        if hasattr(decision, "delay") and decision.delay > 0:
            import time

            time.sleep(decision.delay)

        # 通过服务工厂创建服务
        ctx = runtime_ctx if runtime_ctx is not None else service_node.ctx
        service = service_node.service_task_factory.create_service_task(ctx)

        return service

    def task_completed(self, task_name: str):
        """
        任务完成通知

        当任务完成或停止时，Dispatcher 会调用此方法通知调度器。
        调度器可以更新内部状态，释放资源计数器等。

        默认实现为空，子类可以重写以实现资源跟踪等功能。

        Args:
            task_name: 已完成的任务名称
        """
        pass

    def get_metrics(self) -> dict[str, Any]:
        """
        获取调度器性能指标（供开发者对比不同策略）

        Returns:
            指标字典，例如：
            {
                'scheduler_type': 'FIFO',
                'total_scheduled': 100,
                'avg_latency_ms': 45.2,
                'decisions': 100
            }
        """
        return {
            "scheduler_type": self.__class__.__name__,
            "scheduled_count": self.scheduled_count,
            "decisions": len(self.decision_history),
        }

    def shutdown(self):
        """关闭调度器，释放资源"""
        self.decision_history.clear()


__all__ = ["BaseScheduler"]
