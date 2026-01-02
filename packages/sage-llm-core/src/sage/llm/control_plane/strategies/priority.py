# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Priority-based scheduling strategy."""

from ..types import (
    ExecutionInstance,
    ParallelismType,
    RequestMetadata,
    RequestPriority,
    SchedulingDecision,
)
from .base import SchedulingPolicy


class PriorityPolicy(SchedulingPolicy):
    """Priority-based scheduling policy."""

    def __init__(self):
        super().__init__("Priority")

    def schedule(
        self,
        requests: list[RequestMetadata],
        instances: list[ExecutionInstance],
    ) -> list[SchedulingDecision]:
        """Schedule high-priority requests first."""
        decisions = []

        # Sort by priority then arrival time
        sorted_requests = self.prioritize(requests)

        for request in sorted_requests:
            available_instances = [i for i in instances if i.can_accept_request]
            if not available_instances:
                continue

            # For high priority, prefer instances with better performance
            if request.priority in [RequestPriority.CRITICAL, RequestPriority.HIGH]:
                target = min(available_instances, key=lambda i: i.avg_latency_ms)
            else:
                target = min(available_instances, key=lambda i: i.current_load)

            decision = SchedulingDecision(
                request_id=request.request_id,
                target_instance_id=target.instance_id,
                parallelism_strategy=ParallelismType.TENSOR_PARALLEL,
                tensor_parallel_size=target.tensor_parallel_size,
                pipeline_parallel_size=target.pipeline_parallel_size,
                estimated_latency_ms=target.avg_latency_ms,
                estimated_cost=0.0,
                reason=f"Priority {request.priority.name} scheduling",
            )
            decisions.append(decision)

        return decisions

    def prioritize(self, requests: list[RequestMetadata]) -> list[RequestMetadata]:
        """Prioritize by priority level then arrival time."""
        return sorted(requests, key=lambda r: (r.priority.value, r.arrival_time))
