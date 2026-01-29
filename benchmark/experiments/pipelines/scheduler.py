"""
HeadNodeScheduler: 限制 Source 和 Sink 在 Head 节点执行
=======================================================

基于 LocalSinkScheduler 扩展，同时限制 Source 和 Sink 节点。

工作原理:
- Source 节点 → 绑定到 head 节点
- Sink 节点 → 绑定到 head 节点
- 其他节点 → 使用 Ray 默认负载均衡

使用场景:
- RemoteEnvironment 远程执行计算
- Source 从本地读取数据
- Sink 输出到本地可见
"""

from __future__ import annotations

import socket
from typing import Optional

from sage.kernel.scheduler.api import BaseScheduler
from sage.kernel.scheduler.decision import PlacementDecision


class HeadNodeScheduler(BaseScheduler):
    """
    Head 节点调度器：将 Source 和 Sink 节点放到 head 节点执行

    工作原理:
    - Source 节点 → 绑定到 head 节点（数据输入）
    - Sink 节点 → 绑定到 head 节点（结果输出）
    - 其他节点 → 使用 Ray 默认负载均衡（计算在集群分布）

    使用场景:
    - RemoteEnvironment 远程执行计算
    - 数据源和结果输出需要在本地可见

    注意: 需要在 Ray 集群环境中运行
    """

    def __init__(self, head_node_id: Optional[str] = None):
        """
        初始化调度器

        Args:
            head_node_id: 指定 head 节点 ID，如果为 None 则自动获取当前节点
        """
        super().__init__()
        self.local_hostname = socket.gethostname()
        self._head_node_id = head_node_id
        self._cached_node_id: Optional[str] = None

    def _get_head_node_id(self) -> Optional[str]:
        """获取 head 节点的 Ray node ID"""
        if self._head_node_id is not None:
            return self._head_node_id

        if self._cached_node_id is not None:
            return self._cached_node_id

        try:
            import ray

            if not ray.is_initialized():
                return None

            # 获取当前节点的 node ID（假设当前节点是 head）
            current_node_id = ray.get_runtime_context().get_node_id()
            self._cached_node_id = current_node_id
            return current_node_id
        except Exception:
            return None

    def _is_source_or_sink(self, task_name: str) -> tuple[bool, str]:
        """判断是否是 Source 或 Sink 节点

        Returns:
            (is_source_or_sink, node_type)
        """
        task_name_lower = task_name.lower()

        if "source" in task_name_lower:
            return True, "source"
        if "sink" in task_name_lower:
            return True, "sink"

        return False, ""

    def make_decision(self, task_node) -> PlacementDecision:
        """根据任务类型决定放置策略"""
        task_name = getattr(task_node, "name", str(task_node))

        is_head_bound, node_type = self._is_source_or_sink(task_name)

        if is_head_bound:
            head_node_id = self._get_head_node_id()

            if head_node_id:
                return PlacementDecision(
                    target_node=head_node_id,
                    placement_strategy="affinity",
                    reason=f"{node_type.capitalize()} bound to head node: {self.local_hostname} (node_id: {head_node_id[:8]}...)",
                )
            else:
                return PlacementDecision(
                    placement_strategy="default",
                    reason=f"{node_type.capitalize()}: Could not get head node ID, using default scheduling",
                )

        # 其他任务使用默认调度（分布到集群）
        return PlacementDecision(
            placement_strategy="default",
            reason="Default load balancing for compute tasks",
        )
