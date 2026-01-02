# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""FIFO (First-In-First-Out) scheduling strategy."""

from ..types import ExecutionInstance, ParallelismType, RequestMetadata, SchedulingDecision
from .base import SchedulingPolicy


class FIFOPolicy(SchedulingPolicy):
    """First-In-First-Out scheduling policy."""

    def __init__(self):
        super().__init__("FIFO")

    def schedule(
        self,
        requests: list[RequestMetadata],
        instances: list[ExecutionInstance],
    ) -> list[SchedulingDecision]:
        """Schedule requests in FIFO order to least loaded instances."""
        decisions = []

        # Sort requests by arrival time
        sorted_requests = sorted(requests, key=lambda r: r.arrival_time)

        for request in sorted_requests:
            # Find least loaded available instance
            available_instances = [i for i in instances if i.can_accept_request]
            if not available_instances:
                continue

            target = min(available_instances, key=lambda i: i.current_load)

            decision = SchedulingDecision(
                request_id=request.request_id,
                target_instance_id=target.instance_id,
                parallelism_strategy=ParallelismType.TENSOR_PARALLEL,
                tensor_parallel_size=target.tensor_parallel_size,
                pipeline_parallel_size=target.pipeline_parallel_size,
                estimated_latency_ms=target.avg_latency_ms,
                estimated_cost=0.0,
                reason="FIFO scheduling to least loaded instance",
            )
            decisions.append(decision)

        return decisions

    def prioritize(self, requests: list[RequestMetadata]) -> list[RequestMetadata]:
        """Prioritize by arrival time (FIFO)."""
        return sorted(requests, key=lambda r: r.arrival_time)
