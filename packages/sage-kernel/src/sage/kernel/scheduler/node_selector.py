"""
NodeSelector - 资源感知的节点选择器

集成到 Scheduler 中，根据集群资源状态和任务需求选择最优节点。

核心功能：
1. 实时监控集群资源状态（CPU、GPU、内存、自定义资源）
2. 根据任务需求匹配合适的节点
3. 支持多种调度策略（负载均衡、资源匹配、亲和性等）
4. 跟踪节点任务分配历史

示例用法:
    selector = NodeSelector()

    # 根据资源需求选择节点
    node_id = selector.select_best_node(
        cpu_required=4,
        gpu_required=1,
        memory_required=8*1024**3
    )
"""

import time
from dataclasses import dataclass
from typing import Any

try:
    import ray

    RAY_AVAILABLE = True
except ImportError:
    RAY_AVAILABLE = False


@dataclass
class NodeResources:
    """节点资源信息"""

    node_id: str
    hostname: str
    address: str

    # 总资源
    total_cpu: float
    total_gpu: float
    total_memory: int
    custom_resources: dict[str, float]

    # 可用资源
    available_cpu: float
    available_gpu: float
    available_memory: int

    # 使用率
    cpu_usage: float  # 0.0 - 1.0
    gpu_usage: float  # 0.0 - 1.0
    memory_usage: float  # 0.0 - 1.0

    # 任务分配历史
    task_count: int = 0
    alive: bool = True

    def can_fit(
        self, cpu_required: float = 0, gpu_required: float = 0, memory_required: int = 0
    ) -> bool:
        """检查节点是否能容纳任务"""
        return (
            self.available_cpu >= cpu_required
            and self.available_gpu >= gpu_required
            and self.available_memory >= memory_required
        )

    def compute_score(
        self,
        strategy: str = "balanced",
        cpu_weight: float = 0.4,
        gpu_weight: float = 0.4,
        memory_weight: float = 0.2,
    ) -> float:
        """
        计算节点得分（越低越好）

        Args:
            strategy: 调度策略
                - "balanced": 负载均衡（选择使用率最低的节点）
                - "pack": 紧凑放置（选择使用率最高但能容纳的节点）
                - "spread": 分散放置（选择任务数最少的节点）
            cpu_weight: CPU 使用率权重
            gpu_weight: GPU 使用率权重
            memory_weight: 内存使用率权重

        Returns:
            节点得分
        """
        if strategy == "balanced":
            # 负载均衡：综合使用率越低越好
            return (
                self.cpu_usage * cpu_weight
                + self.gpu_usage * gpu_weight
                + self.memory_usage * memory_weight
            )
        elif strategy == "pack":
            # 紧凑放置：使用率越高越好（但要能容纳）
            return -(
                self.cpu_usage * cpu_weight
                + self.gpu_usage * gpu_weight
                + self.memory_usage * memory_weight
            )
        elif strategy == "spread":
            # 分散放置：任务数越少越好
            return float(self.task_count)
        else:
            return self.cpu_usage


class NodeSelector:
    """
    资源感知的节点选择器

    职责：
    1. 监控集群资源状态
    2. 根据任务需求选择最优节点
    3. 跟踪节点任务分配
    4. 支持多种调度策略
    """

    def __init__(self, cache_ttl: float = 0.5, enable_tracking: bool = True):
        """
        初始化节点选择器

        Args:
            cache_ttl: 资源信息缓存时间（秒）
            enable_tracking: 是否启用任务分配跟踪
        """
        self.cache_ttl = cache_ttl
        self.enable_tracking = enable_tracking

        # 缓存
        self.node_cache: dict[str, NodeResources] = {}
        self.last_update: float = 0

        # 任务分配跟踪
        self.node_task_count: dict[str, int] = {}  # node_id -> task_count
        self.task_node_map: dict[str, str] = {}  # task_name -> node_id

    def _update_node_cache(self) -> None:
        """更新节点资源信息缓存"""
        if not RAY_AVAILABLE:
            return

        current_time = time.time()
        if current_time - self.last_update < self.cache_ttl:
            return  # 缓存还有效

        try:
            # 获取节点列表和资源信息
            nodes = ray.nodes()
            available_resources = ray.available_resources()

            new_cache = {}

            for node in nodes:
                if not node.get("Alive", False):
                    continue

                node_id = node["NodeID"]
                resources = node.get("Resources", {})

                # 提取资源信息
                total_cpu = resources.get("CPU", 0.0)
                total_gpu = resources.get("GPU", 0.0)
                total_memory = resources.get("memory", 0)

                # 估算可用资源（简化版）
                # 注意：ray.available_resources() 是全局的，这里做粗略估算
                available_cpu = available_resources.get("CPU", 0.0)
                available_gpu = available_resources.get("GPU", 0.0)
                available_memory = available_resources.get("memory", 0)

                # 计算使用率
                cpu_usage = 1.0 - (available_cpu / total_cpu) if total_cpu > 0 else 0.0
                gpu_usage = 1.0 - (available_gpu / total_gpu) if total_gpu > 0 else 0.0
                memory_usage = 1.0 - (available_memory / total_memory) if total_memory > 0 else 0.0

                # 限制范围
                cpu_usage = max(0.0, min(1.0, cpu_usage))
                gpu_usage = max(0.0, min(1.0, gpu_usage))
                memory_usage = max(0.0, min(1.0, memory_usage))

                # 提取自定义资源
                custom_resources = {}
                for key, value in resources.items():
                    if key not in [
                        "CPU",
                        "GPU",
                        "memory",
                        "object_store_memory",
                        "node",
                    ]:
                        custom_resources[key] = value

                # 获取任务数
                task_count = self.node_task_count.get(node_id, 0)

                # 创建节点资源对象
                node_res = NodeResources(
                    node_id=node_id,
                    hostname=node.get("NodeManagerHostname", "unknown"),
                    address=node.get("NodeManagerAddress", "unknown"),
                    total_cpu=total_cpu,
                    total_gpu=total_gpu,
                    total_memory=total_memory,
                    custom_resources=custom_resources,
                    available_cpu=available_cpu,
                    available_gpu=available_gpu,
                    available_memory=available_memory,
                    cpu_usage=cpu_usage,
                    gpu_usage=gpu_usage,
                    memory_usage=memory_usage,
                    task_count=task_count,
                    alive=True,
                )

                new_cache[node_id] = node_res

            self.node_cache = new_cache
            self.last_update = current_time

        except Exception:
            # Ray 未初始化或其他错误，静默忽略
            pass

    def get_all_nodes(self) -> list[NodeResources]:
        """
        获取集群中所有活跃节点的资源信息

        Returns:
            节点资源信息列表
        """
        self._update_node_cache()
        # 同步最新的 task_count（因为缓存期间 task_count 可能已更新）
        for node_id, node_res in self.node_cache.items():
            node_res.task_count = self.node_task_count.get(node_id, 0)
        return list(self.node_cache.values())

    def get_node(self, node_id: str) -> NodeResources | None:
        """获取指定节点的资源信息"""
        self._update_node_cache()
        return self.node_cache.get(node_id)

    def select_best_node(
        self,
        cpu_required: float = 0,
        gpu_required: float = 0,
        memory_required: int = 0,
        custom_resources: dict[str, float] | None = None,
        strategy: str = "balanced",
        exclude_nodes: list[str] | None = None,
    ) -> str | None:
        """
        根据资源需求和调度策略选择最优节点

        这是核心方法，供 Scheduler 调用

        Args:
            cpu_required: 需要的 CPU 核心数
            gpu_required: 需要的 GPU 数量
            memory_required: 需要的内存（字节）
            custom_resources: 自定义资源需求
            strategy: 调度策略
                - "balanced": 负载均衡（默认）
                - "pack": 紧凑放置
                - "spread": 分散放置
            exclude_nodes: 排除的节点列表

        Returns:
            最优节点 ID，如果没有满足条件的节点则返回 None
        """
        nodes = self.get_all_nodes()

        if not nodes:
            return None

        # 过滤满足资源需求的节点
        candidate_nodes = []
        for node in nodes:
            # 排除指定节点
            if exclude_nodes and node.node_id in exclude_nodes:
                continue

            # 检查是否能容纳任务
            if not node.can_fit(cpu_required, gpu_required, memory_required):
                continue

            # 检查自定义资源
            if custom_resources:
                can_fit_custom = True
                for res_name, res_required in custom_resources.items():
                    if node.custom_resources.get(res_name, 0) < res_required:
                        can_fit_custom = False
                        break
                if not can_fit_custom:
                    continue

            candidate_nodes.append(node)

        if not candidate_nodes:
            return None

        # 根据策略计算得分并选择最优节点
        scored_nodes = [(node, node.compute_score(strategy)) for node in candidate_nodes]

        # 按得分排序（越低越好）
        scored_nodes.sort(key=lambda x: x[1])

        return scored_nodes[0][0].node_id

    def select_least_loaded_node(self) -> str | None:
        """
        选择负载最低的节点（快捷方法）

        Returns:
            节点 ID，如果没有可用节点则返回 None
        """
        return self.select_best_node(strategy="balanced")

    def select_node_with_gpu(self, min_gpu_count: float = 1) -> str | None:
        """
        选择有足够 GPU 的节点（快捷方法）

        Args:
            min_gpu_count: 最小 GPU 数量

        Returns:
            节点 ID，如果没有满足条件的节点则返回 None
        """
        return self.select_best_node(gpu_required=min_gpu_count, strategy="balanced")

    def select_spread_node(self) -> str | None:
        """
        选择任务数最少的节点（分散放置，快捷方法）

        Returns:
            节点 ID
        """
        return self.select_best_node(strategy="spread")

    def select_pack_node(
        self, cpu_required: float = 0, gpu_required: float = 0, memory_required: int = 0
    ) -> str | None:
        """
        选择使用率最高但能容纳任务的节点（紧凑放置，快捷方法）

        Args:
            cpu_required: CPU 需求
            gpu_required: GPU 需求
            memory_required: 内存需求

        Returns:
            节点 ID
        """
        return self.select_best_node(
            cpu_required=cpu_required,
            gpu_required=gpu_required,
            memory_required=memory_required,
            strategy="pack",
        )

    def track_task_placement(self, task_name: str, node_id: str) -> None:
        """
        跟踪任务分配到节点

        Args:
            task_name: 任务名称
            node_id: 节点 ID
        """
        if not self.enable_tracking:
            return

        self.task_node_map[task_name] = node_id
        self.node_task_count[node_id] = self.node_task_count.get(node_id, 0) + 1

    def untrack_task(self, task_name: str) -> None:
        """
        取消跟踪任务（任务完成时调用）

        Args:
            task_name: 任务名称
        """
        if not self.enable_tracking:
            return

        node_id = self.task_node_map.pop(task_name, None)
        if node_id:
            self.node_task_count[node_id] = max(0, self.node_task_count.get(node_id, 0) - 1)

    def get_node_task_count(self, node_id: str) -> int:
        """获取节点上的任务数"""
        return self.node_task_count.get(node_id, 0)

    def get_cluster_stats(self) -> dict[str, Any]:
        """
        获取集群统计信息

        Returns:
            包含集群资源统计的字典
        """
        nodes = self.get_all_nodes()

        if not nodes:
            return {
                "node_count": 0,
                "total_cpu": 0,
                "total_gpu": 0,
                "total_memory": 0,
                "available_cpu": 0,
                "available_gpu": 0,
                "available_memory": 0,
                "avg_cpu_usage": 0,
                "avg_gpu_usage": 0,
                "avg_memory_usage": 0,
                "total_tasks": 0,
            }

        total_cpu = sum(n.total_cpu for n in nodes)
        total_gpu = sum(n.total_gpu for n in nodes)
        total_memory = sum(n.total_memory for n in nodes)

        available_cpu = sum(n.available_cpu for n in nodes)
        available_gpu = sum(n.available_gpu for n in nodes)
        available_memory = sum(n.available_memory for n in nodes)

        avg_cpu_usage = sum(n.cpu_usage for n in nodes) / len(nodes)
        avg_gpu_usage = sum(n.gpu_usage for n in nodes) / len(nodes)
        avg_memory_usage = sum(n.memory_usage for n in nodes) / len(nodes)

        total_tasks = sum(self.node_task_count.values())

        return {
            "node_count": len(nodes),
            "total_cpu": total_cpu,
            "total_gpu": total_gpu,
            "total_memory": total_memory,
            "available_cpu": available_cpu,
            "available_gpu": available_gpu,
            "available_memory": available_memory,
            "avg_cpu_usage": avg_cpu_usage,
            "avg_gpu_usage": avg_gpu_usage,
            "avg_memory_usage": avg_memory_usage,
            "total_tasks": total_tasks,
            "nodes": [
                {
                    "node_id": n.node_id,
                    "hostname": n.hostname,
                    "cpu_usage": n.cpu_usage,
                    "gpu_usage": n.gpu_usage,
                    "memory_usage": n.memory_usage,
                    "task_count": n.task_count,
                }
                for n in nodes
            ],
        }


__all__ = ["NodeSelector", "NodeResources"]
