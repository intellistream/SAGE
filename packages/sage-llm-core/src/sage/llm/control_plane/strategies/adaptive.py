# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Adaptive scheduling strategy that switches between strategies based on conditions."""

from ..types import ExecutionInstance, RequestMetadata, RequestPriority, SchedulingDecision
from .base import SchedulingPolicy
from .cost_optimized import CostOptimizedPolicy
from .priority import PriorityPolicy
from .slo_aware import SLOAwarePolicy


class AdaptivePolicy(SchedulingPolicy):
    """Adaptive policy that switches between strategies based on conditions."""

    def __init__(self):
        super().__init__("Adaptive")
        self.slo_policy = SLOAwarePolicy()
        self.cost_policy = CostOptimizedPolicy()
        self.priority_policy = PriorityPolicy()

        # Thresholds
        self.high_load_threshold = 0.8
        self.slo_violation_threshold = 0.1

    def schedule(
        self,
        requests: list[RequestMetadata],
        instances: list[ExecutionInstance],
    ) -> list[SchedulingDecision]:
        """Adaptively choose scheduling strategy."""

        # Calculate system metrics
        avg_load = sum(i.current_load for i in instances) / len(instances) if instances else 0
        has_slo_requests = any(r.slo_deadline_ms for r in requests)
        has_high_priority = any(
            r.priority in [RequestPriority.CRITICAL, RequestPriority.HIGH] for r in requests
        )

        # Choose policy based on conditions
        if has_high_priority:
            policy: SchedulingPolicy = self.priority_policy
            reason = "high priority requests detected"
        elif has_slo_requests and avg_load > self.high_load_threshold:
            policy = self.slo_policy
            reason = "SLO requests under high load"
        elif avg_load < 0.3:
            policy = self.cost_policy
            reason = "low load, optimizing for cost"
        else:
            policy = self.slo_policy
            reason = "default SLO-aware scheduling"

        decisions = policy.schedule(requests, instances)

        # Add adaptive metadata
        for decision in decisions:
            decision.metadata["adaptive_policy"] = policy.name
            decision.metadata["adaptive_reason"] = reason

        return decisions

    def prioritize(self, requests: list[RequestMetadata]) -> list[RequestMetadata]:
        """Use priority policy for prioritization."""
        return self.priority_policy.prioritize(requests)
