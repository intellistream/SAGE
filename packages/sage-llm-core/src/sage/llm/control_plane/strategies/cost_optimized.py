# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Cost-optimized scheduling strategy."""

from ..types import ExecutionInstance, ParallelismType, RequestMetadata, SchedulingDecision
from .base import SchedulingPolicy


class CostOptimizedPolicy(SchedulingPolicy):
    """Cost-optimized scheduling policy."""

    def __init__(self, price_per_gpu_hour: float = 1.0):
        super().__init__("CostOptimized")
        self.price_per_gpu_hour = price_per_gpu_hour

    def schedule(
        self,
        requests: list[RequestMetadata],
        instances: list[ExecutionInstance],
    ) -> list[SchedulingDecision]:
        """Schedule to minimize cost while meeting requirements."""
        decisions = []

        sorted_requests = self.prioritize(requests)

        for request in sorted_requests:
            available_instances = [i for i in instances if i.can_accept_request]
            if not available_instances:
                continue

            # Calculate cost for each instance
            instance_costs = []
            for instance in available_instances:
                cost = self._estimate_cost(request, instance)
                instance_costs.append((cost, instance))

            # Choose lowest cost instance that can meet SLO
            instance_costs.sort(key=lambda x: x[0])

            target_cost, target = instance_costs[0]

            decision = SchedulingDecision(
                request_id=request.request_id,
                target_instance_id=target.instance_id,
                parallelism_strategy=ParallelismType.TENSOR_PARALLEL,
                tensor_parallel_size=target.tensor_parallel_size,
                pipeline_parallel_size=target.pipeline_parallel_size,
                estimated_latency_ms=target.avg_latency_ms,
                estimated_cost=target_cost,
                reason=f"Cost-optimized scheduling (cost: ${target_cost:.4f})",
            )
            decisions.append(decision)

        return decisions

    def prioritize(self, requests: list[RequestMetadata]) -> list[RequestMetadata]:
        """Prioritize by cost budget and priority."""
        return sorted(requests, key=lambda r: (r.priority.value, r.cost_budget or float("inf")))

    def _estimate_cost(
        self,
        request: RequestMetadata,
        instance: ExecutionInstance,
    ) -> float:
        """Estimate cost for running request on instance."""
        # Estimate tokens (use max_tokens or default)
        estimated_tokens = request.max_tokens or 100

        # Estimate time in seconds
        if instance.throughput_tokens_per_sec > 0:
            estimated_time_sec = estimated_tokens / instance.throughput_tokens_per_sec
        else:
            estimated_time_sec = 1.0

        # Calculate cost based on GPU usage
        gpu_cost_per_sec = self.price_per_gpu_hour * instance.gpu_count / 3600

        return gpu_cost_per_sec * estimated_time_sec
