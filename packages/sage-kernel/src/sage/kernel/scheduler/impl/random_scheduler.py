"""
Random Scheduler - Random node selection.

Uses random strategy to select target nodes for task scheduling.
Used as a comparison baseline simulating unintelligent random allocation.

Features:
- Random node selection (no optimization)
- Simple, low overhead
- Suitable for uniform load, homogeneous nodes
- Can be used as baseline for comparison

Usage:
    env = LocalEnvironment(scheduler="random")
"""

import random
import time
from typing import TYPE_CHECKING, Any

from sage.kernel.scheduler.api import BaseScheduler
from sage.kernel.scheduler.decision import PlacementDecision

if TYPE_CHECKING:
    from sage.kernel.runtime.graph.graph_node import TaskNode
    from sage.kernel.runtime.graph.service_node import ServiceNode


class RandomScheduler(BaseScheduler):
    """Random Scheduler - Random node selection."""

    def __init__(self, platform: str = "local", seed: int | None = None):
        super().__init__()
        self.platform = platform
        self.total_latency = 0.0
        self._rng = random.Random(seed)

        from sage.kernel.scheduler.node_selector import NodeSelector

        self.node_selector = NodeSelector(cache_ttl=1.0, enable_tracking=True)

    def make_decision(self, task_node: "TaskNode") -> PlacementDecision:
        """Random scheduling decision: randomly select an available node."""
        start_time = time.time()

        target_node = None
        reason = "Random selection"

        is_remote = task_node.task_factory.remote if hasattr(task_node, "task_factory") else False

        if is_remote:
            nodes = self.node_selector.list_available_nodes()
            if nodes:
                selected = self._rng.choice(nodes)
                target_node = selected.node_id
                reason = f"Random: selected {selected.hostname} from {len(nodes)} nodes"
                self.node_selector.track_task_placement(task_node.name, target_node)

        self.scheduled_count += 1
        elapsed = time.time() - start_time
        self.total_latency += elapsed

        decision = PlacementDecision(
            target_node=target_node,
            resource_requirements=None,
            delay=0.0,
            immediate=True,
            placement_strategy="random",
            reason=reason,
        )

        self.decision_history.append(decision)
        return decision

    def make_service_decision(self, service_node: "ServiceNode") -> PlacementDecision:
        """Random service scheduling decision."""
        self.scheduled_count += 1

        nodes = self.node_selector.list_available_nodes()
        target_node = None

        if nodes:
            selected = self._rng.choice(nodes)
            target_node = selected.node_id
            self.node_selector.track_task_placement(service_node.service_name, target_node)

        decision = PlacementDecision(
            target_node=target_node,
            resource_requirements=None,
            delay=0.0,
            immediate=True,
            placement_strategy="random",
            reason=f"Random service placement: {service_node.service_name}",
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
            "scheduler_type": "Random",
            "total_scheduled": self.scheduled_count,
            "avg_latency_ms": avg_latency * 1000,
            "decisions": len(self.decision_history),
            "platform": self.platform,
        }

    def shutdown(self):
        """Shutdown scheduler."""
        super().shutdown()


__all__ = ["RandomScheduler"]
