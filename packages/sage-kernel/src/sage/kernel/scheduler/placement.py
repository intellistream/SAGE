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
- 使用 Ray API 将任务放置到指定物理节点
- 处理资源需求和放置策略
"""

from typing import TYPE_CHECKING, Any, Union

from sage.kernel.utils.ray.ray_utils import normalize_extra_python_paths

if TYPE_CHECKING:
    from sage.kernel.runtime.graph.graph_node import TaskNode
    from sage.kernel.runtime.graph.service_node import ServiceNode
    from sage.kernel.runtime.service.local_service_task import LocalServiceTask
    from sage.kernel.runtime.task.local_task import LocalTask
    from sage.kernel.scheduler.decision import PlacementDecision
    from sage.kernel.utils.ray.actor import ActorWrapper


class PlacementExecutor:
    """
    统一的放置执行器 - 纯执行者

    重构后职责：
    1. 接收 PlacementDecision（来自 Scheduler）
    2. 根据决策执行物理放置：
       - 本地任务：创建 LocalTask
       - 远程任务：创建 RayTask 并指定物理节点
    3. 将高层决策转换为底层 Ray API 调用：
       - target_node → NodeAffinitySchedulingStrategy
       - resource_requirements → num_cpus, num_gpus, memory
       - placement_strategy → Ray scheduling strategy
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
    ) -> Union["LocalTask", "ActorWrapper"]:
        """
        根据调度决策执行物理放置

        执行流程：
        1. 确定运行时上下文
        2. 根据 task_node.remote 决定创建本地或远程任务
           - 本地任务：直接创建 LocalTask
           - 远程任务：根据决策构建 Ray options，创建 RayTask
        3. 更新放置统计信息

        Args:
            task_node: 任务节点
            decision: 调度决策（来自 Scheduler.make_decision()）
            runtime_ctx: 运行时上下文（可选）

        Returns:
            创建的任务实例（LocalTask 或 ActorWrapper 包装的 RayTask）
        """
        # 1. 确定上下文
        ctx = runtime_ctx if runtime_ctx is not None else task_node.ctx

        # 2. 创建任务
        is_remote = task_node.task_factory.remote

        task: LocalTask | ActorWrapper
        if is_remote:
            # 远程任务：使用决策创建 Ray Actor
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
                "resource_requirements": decision.resource_requirements,
                "decision": decision,
            }
        )

        return task

    def _place_local_task(self, task_node: "TaskNode", ctx) -> Union["LocalTask", "ActorWrapper"]:
        """
        放置本地任务（直接创建 LocalTask）

        Args:
            task_node: 任务节点
            ctx: 运行时上下文

        Returns:
            LocalTask 实例（本地模式）或 ActorWrapper（远程模式）
        """
        # 使用 TaskFactory 创建本地任务
        task = task_node.task_factory.create_task(task_node.name, ctx)
        return task

    def _place_remote_task(
        self, task_node: "TaskNode", ctx, decision: "PlacementDecision"
    ) -> "ActorWrapper":
        """
        放置远程任务（创建 Ray Actor 并指定节点）

        这是 PlacementExecutor 的核心功能：
        将高层调度决策转换为底层 Ray API 调用

        Args:
            task_node: 任务节点
            ctx: 运行时上下文
            decision: 调度决策

        Returns:
            ActorWrapper 包装的 RayTask
        """
        # 构建 Ray Actor 选项（根据决策）
        ray_options = self._build_ray_options(decision)

        # 添加 runtime_env 支持： TaskFactory 获取 extra_python_paths
        extra_python_paths = normalize_extra_python_paths(
            getattr(task_node.task_factory, "extra_python_paths", None)
        )
        if extra_python_paths:
            runtime_env = {"env_vars": {"PYTHONPATH": ":".join(extra_python_paths)}}
            ray_options["runtime_env"] = runtime_env

        # 创建 Ray Actor
        from sage.kernel.runtime.task.ray_task import RayTask
        from sage.kernel.utils.ray.actor import ActorWrapper

        # Get operator_factory with explicit typing
        operator_factory = task_node.task_factory.operator_factory  # type: ignore[has-type]
        task_actor = RayTask.options(**ray_options).remote(  # type: ignore[attr-defined]
            ctx, operator_factory
        )

        # 包装为 ActorWrapper
        task = ActorWrapper(task_actor)

        return task

    def _build_ray_options(self, decision: "PlacementDecision") -> dict[str, Any]:
        """
        将调度决策转换为 Ray Actor 创建选项

        这是关键转换层：高层决策 → 底层 Ray API

        Args:
            decision: 调度决策

        Returns:
            Ray options 字典
        """
        options: dict[str, Any] = {"lifetime": "detached"}

        # === 指定目标节点 ===
        if decision.target_node:
            try:
                from ray.util.scheduling_strategies import (
                    NodeAffinitySchedulingStrategy,
                )

                options["scheduling_strategy"] = NodeAffinitySchedulingStrategy(
                    node_id=decision.target_node,
                    soft=False,  # 硬要求：必须放到指定节点
                )
            except ImportError:
                # Ray 版本不支持 NodeAffinitySchedulingStrategy
                pass

        # === 指定资源需求 ===
        if decision.resource_requirements:
            resources = decision.resource_requirements

            # CPU
            if "cpu" in resources:
                options["num_cpus"] = resources["cpu"]

            # GPU
            if "gpu" in resources:
                options["num_gpus"] = resources["gpu"]

            # 内存
            if "memory" in resources:
                memory_bytes = self._parse_memory(resources["memory"])
                options["memory"] = memory_bytes

            # 自定义资源
            custom_resources = {}
            for key, value in resources.items():
                if key not in ["cpu", "gpu", "memory"]:
                    custom_resources[key] = value

            if custom_resources:
                options["resources"] = custom_resources

        return options

    def _parse_memory(self, memory) -> int:
        """
        解析内存字符串为字节数

        Args:
            memory: 内存大小（字符串如 "8GB" 或整数字节数）

        Returns:
            内存字节数
        """
        if isinstance(memory, int):
            return memory

        if isinstance(memory, str):
            memory = memory.upper()
            if "GB" in memory:
                return int(float(memory.replace("GB", "")) * 1024**3)
            elif "MB" in memory:
                return int(float(memory.replace("MB", "")) * 1024**2)
            elif "KB" in memory:
                return int(float(memory.replace("KB", "")) * 1024)

        return 1024**3  # 默认 1GB

    def place_service(
        self,
        service_node: "ServiceNode",
        decision: "PlacementDecision",
        runtime_ctx=None,
    ) -> Union["LocalServiceTask", "ActorWrapper"]:
        """
        根据调度决策放置服务

        Args:
            service_node: 服务节点
            decision: 调度决策
            runtime_ctx: 运行时上下文（可选）

        Returns:
            创建的服务实例（LocalServiceTask 或 ActorWrapper 包装的 RayServiceTask）
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
