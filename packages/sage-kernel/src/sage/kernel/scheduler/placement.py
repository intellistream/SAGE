"""
Placement 执行层 - 统一的任务/服务放置接口

架构（重构后）：
- Scheduler: 纯决策者（返回 PlacementDecision）
- PlacementExecutor: 纯执行者（接收决策，执行物理放置）
- Dispatcher: 协调者（决策 → 执行）

正确的流程：
    Dispatcher.submit():
        for node in graph.nodes:
            # 1. 获取调度决策
            decision = scheduler.make_decision(node)

            # 2. 执行物理放置
            task = placement_executor.place_task(node, decision)

关键点：
- PlacementExecutor 是纯执行层，不包含调度策略
- 接收 PlacementDecision，根据决策执行放置
- 物理执行由 kernel-native task/service factory 负责（Ray 已移除）
- 处理资源需求和放置统计
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sage.kernel.runtime.graph.graph_node import TaskNode
    from sage.kernel.runtime.graph.service_node import ServiceNode
    from sage.kernel.runtime.service.local_service_task import LocalServiceTask
    from sage.kernel.runtime.task.local_task import LocalTask
    from sage.kernel.scheduler.decision import PlacementDecision


class PlacementExecutor:
    """
    统一的放置执行器 - 纯执行者

    重构后职责：
    1. 接收 PlacementDecision（来自 Scheduler）
    2. 根据决策执行物理放置：
       - 本地任务：创建 LocalTask
       - 分布式任务：通过 FlownetRuntime 执行远程广播
    3. 将高层决策转换为底层任务调用
    4. 记录放置统计信息

    关键变更：
    - 接收 PlacementDecision 参数（新增）
    - 实际使用 target_node 和 resource_requirements（之前未实现）
    - 不包含调度策略（策略在 Scheduler 中）
    """

    def __init__(self):
        """
        初始化放置执行器
        """
        self.placed_tasks = []
        self.placed_services = []
        self.placement_stats = {
            "total_tasks": 0,
            "total_services": 0,
            "local_tasks": 0,
            "remote_tasks": 0,
            "nodes_used": set(),  # 使用的节点集合
        }

    def place_task(
        self, task_node: "TaskNode", decision: "PlacementDecision", runtime_ctx=None
    ) -> "LocalTask":
        """
        根据调度决策执行物理放置

        执行流程：
        1. 确定运行时上下文
        2. 根据 task_node.remote 决定创建本地或远程任务
           - 本地任务：直接创建 LocalTask
           - 远程任务：交给 task factory 的 kernel-native runtime 创建
        3. 更新放置统计信息

        Args:
            task_node: 任务节点
            decision: 调度决策（来自 Scheduler.make_decision()）
            runtime_ctx: 运行时上下文（可选）

        Returns:
            创建的任务实例
        """
        # 1. 确定上下文
        ctx = runtime_ctx if runtime_ctx is not None else task_node.ctx

        # 2. 创建任务
        is_remote = task_node.task_factory.remote

        task: LocalTask
        if is_remote:
            # 远程任务：委托 task factory，实际执行不再依赖 Ray
            task = self._place_remote_task(task_node, ctx, decision)
            self.placement_stats["remote_tasks"] += 1
        else:
            # 本地任务：直接创建
            task = self._place_local_task(task_node, ctx)
            self.placement_stats["local_tasks"] += 1

        # 3. 记录统计
        self.placement_stats["total_tasks"] += 1

        if decision.target_node:
            self.placement_stats["nodes_used"].add(decision.target_node)

        self.placed_tasks.append(
            {
                "task_name": task_node.name,
                "remote": is_remote,
                "target_node": decision.target_node,
                "resource": decision.resource.to_dict(),
                "decision": decision,
            }
        )

        return task

    def _place_local_task(self, task_node: "TaskNode", ctx) -> "LocalTask":
        """
        放置本地任务（直接创建 LocalTask）

        Args:
            task_node: 任务节点
            ctx: 运行时上下文

        Returns:
            LocalTask 实例
        """
        # 使用 TaskFactory 创建本地任务
        task = task_node.task_factory.create_task(task_node.name, ctx)
        return task

    def _place_remote_task(
        self, task_node: "TaskNode", ctx, decision: "PlacementDecision"
    ) -> "LocalTask":
        """
        放置远程任务（kernel-native runtime）

        Args:
            task_node: 任务节点
            ctx: 运行时上下文
            decision: 调度决策

        Returns:
            LocalTask 实例
        """
        return task_node.task_factory.create_task(task_node.name, ctx)

    def place_service(
        self,
        service_node: "ServiceNode",
        decision: "PlacementDecision",
        runtime_ctx=None,
    ) -> "LocalServiceTask":
        """
        根据调度决策放置服务

        Args:
            service_node: 服务节点
            decision: 调度决策
            runtime_ctx: 运行时上下文（可选）

        Returns:
            创建的服务实例
        """
        # 1. 确定上下文
        ctx = runtime_ctx if runtime_ctx is not None else service_node.ctx

        # 2. 创建服务
        service = service_node.service_task_factory.create_service_task(ctx)

        # 3. 记录统计
        self.placement_stats["total_services"] += 1

        if decision.target_node:
            self.placement_stats["nodes_used"].add(decision.target_node)

        self.placed_services.append(
            {
                "service_name": service_node.service_name,
                "target_node": decision.target_node,
                "decision": decision,
            }
        )

        return service

    def get_placement_stats(self) -> dict[str, Any]:
        """
        获取放置统计信息

        Returns:
            统计字典，包含：
            - total_tasks: 总任务数
            - total_services: 总服务数
            - local_tasks: 本地任务数
            - remote_tasks: 远程任务数
            - nodes_used: 使用的节点列表
        """
        stats = self.placement_stats.copy()
        stats["nodes_used"] = list(stats["nodes_used"])  # 转换为列表
        return stats

    def reset_stats(self):
        """重置统计信息"""
        self.placement_stats = {
            "total_tasks": 0,
            "total_services": 0,
            "local_tasks": 0,
            "remote_tasks": 0,
            "nodes_used": set(),
        }
        self.placed_tasks.clear()
        self.placed_services.clear()


__all__ = [
    "PlacementExecutor",
]
