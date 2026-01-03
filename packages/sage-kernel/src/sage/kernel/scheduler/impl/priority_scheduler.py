"""
Priority Scheduler - Priority-based scheduling.

Schedule tasks based on priority levels.
High priority tasks get scheduled first.
"""

import heapq
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from sage.kernel.scheduler.api import BaseScheduler
from sage.kernel.scheduler.decision import PlacementDecision

if TYPE_CHECKING:
    from sage.kernel.runtime.graph.graph_node import TaskNode
    from sage.kernel.runtime.graph.service_node import ServiceNode


@dataclass(order=True)
class PrioritizedTask:
    """Priority task wrapper."""

    priority: int
    timestamp: float = field(compare=False)
    task_name: str = field(compare=False)


class PriorityScheduler(BaseScheduler):
    """Priority Scheduler - Priority-based intelligent scheduling."""

    def __init__(
        self,
        platform: str = "local",
        default_priority: int = 5,
        max_concurrent: int = 10,
        enable_aging: bool = True,
        aging_boost: int = 1,
        aging_threshold: float = 10.0,
    ):
        super().__init__()
        self.platform = platform
        self.default_priority = default_priority
        self.max_concurrent = max_concurrent
        self.enable_aging = enable_aging
        self.aging_boost = aging_boost
        self.aging_threshold = aging_threshold

        self.total_latency = 0.0
        self.active_tasks = 0
        self._priority_queue: list[PrioritizedTask] = []
        self._task_priorities: dict[str, int] = {}
        self._priority_distribution: dict[int, int] = {}
        self._preemptions = 0

        from sage.kernel.scheduler.node_selector import NodeSelector

        self.node_selector = NodeSelector(cache_ttl=0.5, enable_tracking=True)

    def _extract_priority(self, task_node: "TaskNode") -> int:
        """Extract priority from task node."""
        priority = self.default_priority
        if hasattr(task_node, "transformation") and task_node.transformation:
            if hasattr(task_node.transformation, "priority"):
                priority = getattr(task_node.transformation, "priority", priority)
        if hasattr(task_node, "priority"):
            priority = getattr(task_node, "priority", priority)
        return max(1, min(10, priority))

    def _apply_aging(self) -> None:
        """Apply priority aging to prevent starvation."""
        if not self.enable_aging:
            return
        current_time = time.time()
        new_queue = []
        for task in self._priority_queue:
            wait_time = current_time - task.timestamp
            if wait_time > self.aging_threshold:
                boosted_priority = task.priority - self.aging_boost
                new_queue.append(
                    PrioritizedTask(
                        priority=boosted_priority,
                        timestamp=task.timestamp,
                        task_name=task.task_name,
                    )
                )
            else:
                new_queue.append(task)
        self._priority_queue = new_queue
        heapq.heapify(self._priority_queue)

    def make_decision(self, task_node: "TaskNode") -> PlacementDecision:
        """Priority scheduling decision."""
        start_time = time.time()

        priority = self._extract_priority(task_node)
        self._task_priorities[task_node.name] = priority
        self._priority_distribution[priority] = self._priority_distribution.get(priority, 0) + 1

        delay = 0.0
        if self.active_tasks >= self.max_concurrent:
            self._apply_aging()
            while self.active_tasks >= self.max_concurrent:
                time.sleep(0.01)
                delay += 0.01

        target_node = None
        is_remote = task_node.task_factory.remote if hasattr(task_node, "task_factory") else False

        if is_remote:
            strategy = "balanced" if priority >= 7 else "pack"
            target_node = self.node_selector.select_best_node(strategy=strategy)
            if target_node:
                self.node_selector.track_task_placement(task_node.name, target_node)

        self.active_tasks += 1
        self.scheduled_count += 1
        elapsed = time.time() - start_time
        self.total_latency += elapsed

        node_info = ""
        if target_node:
            node = self.node_selector.get_node(target_node)
            node_info = node.hostname if node else target_node[:8]
        else:
            node_info = "default"

        decision = PlacementDecision(
            target_node=target_node,
            resource_requirements=None,
            delay=delay,
            immediate=(delay == 0),
            placement_strategy="priority",
            reason=f"Priority: {priority}/10, task={task_node.name}, node={node_info}",
        )
        self.decision_history.append(decision)
        return decision

    def make_service_decision(self, service_node: "ServiceNode") -> PlacementDecision:
        """Priority service scheduling decision."""
        self.scheduled_count += 1
        service_priority = 8

        target_node = self.node_selector.select_best_node(strategy="balanced")
        if target_node:
            self.node_selector.track_task_placement(service_node.service_name, target_node)

        decision = PlacementDecision(
            target_node=target_node,
            resource_requirements=None,
            delay=0.0,
            immediate=True,
            placement_strategy="priority",
            reason=f"Priority service: {service_node.service_name}, priority={service_priority}",
        )
        self.decision_history.append(decision)
        return decision

    def task_completed(self, task_name: str):
        """Task completion notification."""
        self.active_tasks = max(0, self.active_tasks - 1)
        self.node_selector.untrack_task(task_name)
        if task_name in self._task_priorities:
            del self._task_priorities[task_name]

    def get_metrics(self) -> dict[str, Any]:
        """Get scheduler performance metrics."""
        avg_latency = self.total_latency / self.scheduled_count if self.scheduled_count > 0 else 0
        total_priority = sum(p * c for p, c in self._priority_distribution.items())
        total_count = sum(self._priority_distribution.values())
        avg_priority = total_priority / total_count if total_count > 0 else self.default_priority

        return {
            "scheduler_type": "Priority",
            "total_scheduled": self.scheduled_count,
            "avg_latency_ms": avg_latency * 1000,
            "active_tasks": self.active_tasks,
            "max_concurrent": self.max_concurrent,
            "decisions": len(self.decision_history),
            "platform": self.platform,
            "default_priority": self.default_priority,
            "avg_priority": avg_priority,
            "priority_distribution": dict(self._priority_distribution),
            "enable_aging": self.enable_aging,
            "preemptions": self._preemptions,
        }

    def shutdown(self):
        """Shutdown scheduler."""
        super().shutdown()
        self._priority_queue.clear()
        self._task_priorities.clear()
        self._priority_distribution.clear()


__all__ = ["PriorityScheduler"]
