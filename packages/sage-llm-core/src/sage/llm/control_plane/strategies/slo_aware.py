# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""SLO-aware scheduling strategy with deadline consideration."""

from datetime import datetime

from ..types import ExecutionInstance, ParallelismType, RequestMetadata, SchedulingDecision
from .base import SchedulingPolicy


class SLOAwarePolicy(SchedulingPolicy):
    """SLO-aware scheduling policy with deadline consideration."""

    def __init__(self):
        super().__init__("SLO-Aware")

    def schedule(
        self,
        requests: list[RequestMetadata],
        instances: list[ExecutionInstance],
    ) -> list[SchedulingDecision]:
        """Schedule requests considering SLO deadlines."""
        decisions = []

        sorted_requests = self.prioritize(requests)

        for request in sorted_requests:
            available_instances = [i for i in instances if i.can_accept_request]
            if not available_instances:
                continue

            # Calculate urgency based on deadline
            deadline_urgency = self._calculate_urgency(request)

            # For urgent requests, prioritize fast instances
            if deadline_urgency > 0.7:
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
                reason=f"SLO-aware scheduling (urgency: {deadline_urgency:.2f})",
                confidence=1.0 - deadline_urgency,
            )
            decisions.append(decision)

        return decisions

    def prioritize(self, requests: list[RequestMetadata]) -> list[RequestMetadata]:
        """Prioritize by deadline urgency."""
        return sorted(requests, key=lambda r: self._calculate_urgency(r), reverse=True)

    def _calculate_urgency(self, request: RequestMetadata) -> float:
        """Calculate urgency score (0.0 to 1.0)."""
        if not request.slo_deadline_ms:
            return 0.0

        elapsed_ms = (datetime.now() - request.arrival_time).total_seconds() * 1000
        remaining_ms = request.slo_deadline_ms - elapsed_ms

        if remaining_ms <= 0:
            return 1.0  # Already missed deadline

        # Urgency increases as deadline approaches
        return min(1.0, elapsed_ms / request.slo_deadline_ms)
