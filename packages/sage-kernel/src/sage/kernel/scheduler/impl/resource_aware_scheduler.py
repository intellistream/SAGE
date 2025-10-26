"""
负载感知调度器 - Load-Aware Scheduler

根据当前系统负载和资源使用情况进行调度决策。
适合资源受限或负载波动的场景。

特点：
- 监控系统资源使用
- 根据负载动态调度
- 避免资源过载
- 平衡资源利用率

架构（重构后）：
- 纯决策者：返回 PlacementDecision，不执行放置
- 不持有 PlacementExecutor
- Dispatcher 协调决策和执行

使用方式:
    # 方式 1: 字符串指定
    env = LocalEnvironment(scheduler="load_aware")

    # 方式 2: 实例化指定
    from sage.kernel.scheduler.impl import LoadAwareScheduler
    env = LocalEnvironment(scheduler=LoadAwareScheduler(max_concurrent=10))
"""

import time
from typing import TYPE_CHECKING, Any

from sage.kernel.scheduler.api import BaseScheduler
from sage.kernel.scheduler.decision import PlacementDecision

if TYPE_CHECKING:
    from sage.kernel.runtime.graph.graph_node import TaskNode
    from sage.kernel.runtime.graph.service_node import ServiceNode


class LoadAwareScheduler(BaseScheduler):
    """
    负载感知调度器 - 资源感知的智能调度

    核心功能：
    1. 监控集群资源状态（CPU、GPU、内存）
    2. 根据任务需求选择最优节点
    3. 负载均衡调度
    4. 跟踪任务分配

    调度策略：
    - 分析任务的资源需求（从 transformation 中提取）
    - 使用 NodeSelector 选择负载最低且满足需求的节点
    - 控制并发数避免过载
    - 返回节点分配决策
    """

    def __init__(
        self,
        platform: str = "local",
        max_concurrent: int = 10,
        strategy: str = "balanced",
    ):
        """
        初始化负载感知调度器

        Args:
            platform: 平台类型 ('local' 或 'remote')
            max_concurrent: 最大并发任务数
            strategy: 调度策略
                - "balanced": 负载均衡（默认）
                - "pack": 紧凑放置
                - "spread": 分散放置
        """
        super().__init__()
        self.platform = platform
        self.max_concurrent = max_concurrent
        self.strategy = strategy
        self.total_latency = 0.0
        self.active_tasks = 0
        self.resource_utilization: list[float] = []

        # 集成 NodeSelector（资源感知核心）
        from sage.kernel.scheduler.node_selector import NodeSelector

        self.node_selector = NodeSelector(cache_ttl=0.5, enable_tracking=True)

    def make_decision(self, task_node: "TaskNode") -> PlacementDecision:
        """
        负载感知调度决策：基于资源状态和任务需求选择最优节点

        决策流程：
        1. 检查并发限制
        2. 提取任务资源需求
        3. 使用 NodeSelector 选择最优节点
        4. 跟踪任务分配
        5. 返回节点分配决策

        Args:
            task_node: 任务节点

        Returns:
            PlacementDecision: 包含目标节点和资源需求的决策
        """
        start_time = time.time()

        # === 步骤 1: 检查并发限制（负载控制）===
        delay = 0.0
        while self.active_tasks >= self.max_concurrent:
            time.sleep(0.01)  # 等待资源释放
            delay += 0.01

        # === 步骤 2: 提取任务资源需求 ===
        cpu_required = 1.0
        gpu_required = 0.0
        memory_required = 0
        custom_resources: dict[str, float] = {}

        if hasattr(task_node, "transformation") and task_node.transformation:
            # CPU 需求
            if hasattr(task_node.transformation, "cpu_required"):
                cpu_required = getattr(task_node.transformation, "cpu_required", cpu_required)

            # GPU 需求
            if hasattr(task_node.transformation, "gpu_required"):
                gpu_required = getattr(task_node.transformation, "gpu_required", gpu_required)

            # 内存需求
            if hasattr(task_node.transformation, "memory_required"):
                memory_str = getattr(task_node.transformation, "memory_required", None)
                if memory_str:
                    memory_required = self._parse_memory(memory_str)

            # 自定义资源
            if hasattr(task_node.transformation, "custom_resources"):
                custom_resources = getattr(
                    task_node.transformation, "custom_resources", custom_resources
                )

        # === 步骤 3: 使用 NodeSelector 选择最优节点 ===
        target_node = None

        # 只有远程模式才需要选择节点
        if task_node.task_factory.remote if hasattr(task_node, "task_factory") else False:
            target_node = self.node_selector.select_best_node(
                cpu_required=cpu_required,
                gpu_required=gpu_required,
                memory_required=memory_required,
                custom_resources=custom_resources if custom_resources else None,
                strategy=self.strategy,
            )

            # 跟踪任务分配
            if target_node:
                self.node_selector.track_task_placement(task_node.name, target_node)

        # === 步骤 4: 构建资源需求字典 ===
        resource_requirements = {}
        if cpu_required > 0:
            resource_requirements["cpu"] = cpu_required
        if gpu_required > 0:
            resource_requirements["gpu"] = gpu_required
        if memory_required > 0:
            resource_requirements["memory"] = memory_required
        if custom_resources:
            resource_requirements.update(custom_resources)

        # === 步骤 5: 更新状态 ===
        self.active_tasks += 1
        self.scheduled_count += 1
        elapsed = time.time() - start_time
        self.total_latency += elapsed

        # 记录资源利用率
        utilization = self.active_tasks / self.max_concurrent
        self.resource_utilization.append(utilization)

        # === 步骤 6: 返回决策 ===
        # 获取节点信息用于日志
        node_info = ""
        if target_node:
            node_res = self.node_selector.get_node(target_node)
            if node_res:
                node_info = f"{node_res.hostname} (CPU:{node_res.cpu_usage:.1%}, GPU:{node_res.gpu_usage:.1%})"
            else:
                node_info = target_node[:8]
        else:
            node_info = "default"

        decision = PlacementDecision(
            target_node=target_node,
            resource_requirements=(resource_requirements if resource_requirements else None),
            delay=delay,
            immediate=(delay == 0),
            placement_strategy=self.strategy,
            reason=f"LoadAware: task={task_node.name}, node={node_info}, "
            + f"req=[CPU:{cpu_required}, GPU:{gpu_required}], active={self.active_tasks}",
        )

        self.decision_history.append(decision)
        return decision

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

        return 0

    def make_service_decision(self, service_node: "ServiceNode") -> PlacementDecision:
        """
        负载感知的服务调度决策

        服务通常需要长期运行，因此需要更谨慎的资源分配：
        1. 提取服务的资源需求
        2. 选择资源充足且负载低的节点
        3. 优先使用 spread 策略避免单点故障

        Args:
            service_node: 服务节点

        Returns:
            PlacementDecision: 服务调度决策
        """
        start_time = time.time()

        # === 步骤 1: 提取服务资源需求 ===
        cpu_required = 1.0
        gpu_required = 0.0
        memory_required = 0
        custom_resources: dict[str, float] = {}

        if hasattr(service_node, "service_class"):
            service_class = getattr(service_node, "service_class", None)
            if service_class:
                # CPU 需求
                cpu_required = getattr(service_class, "cpu_required", cpu_required)

                # GPU 需求
                gpu_required = getattr(service_class, "gpu_required", gpu_required)

                # 内存需求
                memory_str = getattr(service_class, "memory_required", None)
                if memory_str:
                    memory_required = self._parse_memory(memory_str)

                # 自定义资源
                custom_resources = getattr(service_class, "custom_resources", custom_resources)

        # === 步骤 2: 使用 NodeSelector 选择节点（优先使用 spread 策略）===
        # 服务通常需要长期运行，使用 spread 策略避免单点故障
        service_strategy = "spread"
        target_node = self.node_selector.select_best_node(
            cpu_required=cpu_required,
            gpu_required=gpu_required,
            memory_required=memory_required,
            custom_resources=custom_resources if custom_resources else None,
            strategy=service_strategy,
        )

        # 跟踪服务分配
        if target_node:
            self.node_selector.track_task_placement(service_node.service_name, target_node)

        # === 步骤 3: 构建资源需求字典 ===
        resource_requirements = {}
        if cpu_required > 0:
            resource_requirements["cpu"] = cpu_required
        if gpu_required > 0:
            resource_requirements["gpu"] = gpu_required
        if memory_required > 0:
            resource_requirements["memory"] = memory_required
        if custom_resources:
            resource_requirements.update(custom_resources)

        # === 步骤 4: 更新状态 ===
        self.scheduled_count += 1
        elapsed = time.time() - start_time
        self.total_latency += elapsed

        # === 步骤 5: 返回决策 ===
        node_info = ""
        if target_node:
            node_res = self.node_selector.get_node(target_node)
            if node_res:
                node_info = f"{node_res.hostname} (CPU:{node_res.cpu_usage:.1%}, tasks:{node_res.task_count})"
            else:
                node_info = target_node[:8]
        else:
            node_info = "default"

        decision = PlacementDecision(
            target_node=target_node,
            resource_requirements=(resource_requirements if resource_requirements else None),
            delay=0.0,  # 服务立即调度
            immediate=True,
            placement_strategy=service_strategy,
            reason=f"LoadAware Service: {service_node.service_name}, node={node_info}, "
            + f"req=[CPU:{cpu_required}, GPU:{gpu_required}], strategy={service_strategy}",
        )

        self.decision_history.append(decision)
        return decision

    def task_completed(self, task_name: str):
        """
        任务完成时调用，释放资源并取消跟踪

        注意：这个方法应该由 Dispatcher 在任务完成时调用

        Args:
            task_name: 任务名称
        """
        self.active_tasks = max(0, self.active_tasks - 1)

        # 取消任务跟踪
        self.node_selector.untrack_task(task_name)

    def get_metrics(self) -> dict[str, Any]:
        """
        获取调度器性能指标

        Returns:
            包含负载和资源利用率的指标
        """
        avg_latency = self.total_latency / self.scheduled_count if self.scheduled_count > 0 else 0
        avg_utilization = (
            sum(self.resource_utilization) / len(self.resource_utilization)
            if self.resource_utilization
            else 0
        )

        # 获取集群统计
        cluster_stats = self.node_selector.get_cluster_stats()

        return {
            "scheduler_type": "LoadAware",
            "total_scheduled": self.scheduled_count,
            "avg_latency_ms": avg_latency * 1000,
            "active_tasks": self.active_tasks,
            "max_concurrent": self.max_concurrent,
            "avg_resource_utilization": avg_utilization,
            "decisions": len(self.decision_history),
            "platform": self.platform,
            "strategy": self.strategy,
            # 集群资源统计
            "cluster": cluster_stats,
        }

    def shutdown(self):
        """关闭调度器"""
        super().shutdown()
        self.resource_utilization.clear()


__all__ = ["LoadAwareScheduler"]
