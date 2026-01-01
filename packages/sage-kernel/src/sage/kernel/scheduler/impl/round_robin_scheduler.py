"""
Round Robin Scheduler - Fair round-robin scheduling.

Uses round-robin strategy to evenly distribute tasks across nodes.
Ensures each node receives equal number of tasks (long-term).

Features:
- Fair scheduling: Even task distribution
- Simple and efficient: O(1) scheduling overhead
- Suitable for homogeneous nodes, uniform tasks
- Does not consider node load differences

Usage:
    env = LocalEnvironment(scheduler="round_robin")
"""

import time
from typing import TYPE_CHECKING, Any

from sage.kernel.scheduler.api import BaseScheduler
from sage.kernel.scheduler.decision import PlacementDecision

if TYPE_CHECKING:
    from sage.kernel.runtime.graph.graph_node import TaskNode
    from sage.kernel.runtime.graph.service_node import ServiceNode


class RoundRobinScheduler(BaseScheduler):
    """Round Robin Scheduler - Even task distribution."""

    def __init__(self, platform: str = "local"):
        super().__init__()
        self.platform = platform
        self.total_latency = 0.0
        self._current_index = 0
        self._cached_nodes: list[str] = []
        self._cache_time = 0.0
        self._cache_ttl = 5.0

        from sage.kernel.scheduler.node_selector import NodeSelector

        self.node_selector = NodeSelector(cache_ttl=5.0, enable_tracking=True)

    def _get_next_node(self) -> str | None:
        """Get next node to schedule to (round-robin)."""
        current_time = time.time()

        if current_time - self._cache_time > self._cache_ttl:
            nodes = self.node_selector.list_available_nodes()
            self._cached_nodes = [n.node_id for n in nodes]
            self._cache_time = current_time
            if self._current_index >= len(self._cached_nodes):
                self._current_index = 0

        if not self._cached_nodes:
            return None

        node_id = self._cached_nodes[self._current_index]
        self._current_index = (self._current_index + 1) % len(self._cached_nodes)

        return node_id

    def make_decision(self, task_node: "TaskNode") -> PlacementDecision:
        """Round-robin scheduling decision: select next node."""
        start_time = time.time()

        target_node = None
        reason = "Round-robin selection"

        is_remote = task_node.task_factory.remote if hasattr(task_node, "task_factory") else False

        if is_remote:
            target_node = self._get_next_node()
            if target_node:
                node_info = self.node_selector.get_node(target_node)
                hostname = node_info.hostname if node_info else target_node[:8]
                reason = f"RoundRobin: selected {hostname} (index={self._current_index - 1})"
                self.node_selector.track_task_placement(task_node.name, target_node)

        self.scheduled_count += 1
        elapsed = time.time() - start_time
        self.total_latency += elapsed

        decision = PlacementDecision(
            target_node=target_node,
            resource_requirements=None,
            delay=0.0,
            immediate=True,
            placement_strategy="round_robin",
            reason=reason,
        )

        self.decision_history.append(decision)
        return decision

    def make_service_decision(self, service_node: "ServiceNode") -> PlacementDecision:
        """Round-robin service scheduling decision."""
        self.scheduled_count += 1

        target_node = self._get_next_node()
        if target_node:
            self.node_selector.track_task_placement(service_node.service_name, target_node)

        decision = PlacementDecision(
            target_node=target_node,
            resource_requirements=None,
            delay=0.0,
            immediate=True,
            placement_strategy="round_robin",
            reason=f"RoundRobin service: {service_node.service_name}",
        )

        self.decision_history.append(decision)
        return decision

    def task_completed(self, task_name: str):
        """Task completion notification."""
        self.node_selector.untrack_task(task_name)

    def get_metrics(self) -> dict[str, Any]:
        """Get scheduler performance metrics."""
        avg_latency = self.total_latency / self.scheduled_count if self.scheduled_count > 0 else 0
        return {
            "scheduler_type": "RoundRobin",
            "total_scheduled": self.scheduled_count,
            "avg_latency_ms": avg_latency * 1000,
            "decisions": len(self.decision_history),
            "platform": self.platform,
            "current_index": self._current_index,
            "nodes_count": len(self._cached_nodes),
        }

    def shutdown(self):
        """Shutdown scheduler."""
        super().shutdown()
        self._cached_nodes.clear()


__all__ = ["RoundRobinScheduler"]
