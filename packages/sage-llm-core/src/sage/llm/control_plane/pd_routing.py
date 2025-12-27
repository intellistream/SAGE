# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""PD-aware routing for Prefilling/Decoding separation."""

import logging

from .types import (
    ExecutionInstance,
    ExecutionInstanceType,
    PDSeparationConfig,
    RequestMetadata,
)

logger = logging.getLogger(__name__)


class PDRoutingStrategy:
    """Strategy for routing requests to prefilling/decoding instances."""

    def __init__(self, pd_config: PDSeparationConfig):
        """Initialize PD routing strategy.

        Args:
            pd_config: PD separation configuration
        """
        self.pd_config = pd_config

    def determine_request_phase(
        self, request: RequestMetadata, avg_output_tokens: float = 100.0
    ) -> ExecutionInstanceType | None:
        """Determine if request should go to prefilling or decoding phase.

        Args:
            request: Request metadata
            avg_output_tokens: Average output tokens for the model

        Returns:
            ExecutionInstanceType: PREFILLING, DECODING, or HYBRID
        """
        if not self.pd_config.enabled:
            return ExecutionInstanceType.HYBRID

        # Estimate input tokens
        input_tokens = self._estimate_input_tokens(request)

        # Estimate output tokens
        output_tokens = request.max_tokens or int(avg_output_tokens)

        # Use routing policy to decide
        if self.pd_config.routing_policy == "threshold":
            return self._route_by_threshold(input_tokens, output_tokens, request)
        elif self.pd_config.routing_policy == "adaptive":
            return self._route_adaptive(input_tokens, output_tokens, request)
        else:
            return ExecutionInstanceType.HYBRID

    def _route_by_threshold(
        self,
        input_tokens: int,
        output_tokens: int,
        request: RequestMetadata,
    ) -> ExecutionInstanceType:
        """Route by static thresholds."""
        # Long input → Prefilling
        if input_tokens > self.pd_config.prefilling_threshold_input_tokens:
            return ExecutionInstanceType.PREFILLING

        # High input/output ratio → Prefilling
        if output_tokens > 0:
            ratio = input_tokens / output_tokens
            if ratio > self.pd_config.prefilling_threshold_ratio:
                return ExecutionInstanceType.PREFILLING

        # Otherwise → Decoding
        return ExecutionInstanceType.DECODING

    def _route_adaptive(
        self,
        input_tokens: int,
        output_tokens: int,
        request: RequestMetadata,
    ) -> ExecutionInstanceType:
        """Adaptive routing considering multiple factors."""
        # Priority considerations
        if request.priority.value < 1 and output_tokens < 500:  # CRITICAL or HIGH
            # High priority requests → minimize latency → Decoding
            return ExecutionInstanceType.DECODING

        # SLO considerations
        if request.slo_deadline_ms and request.slo_deadline_ms < 100:
            # Tight SLO → Decoding (lower latency)
            return ExecutionInstanceType.DECODING

        # Default heuristic
        return self._route_by_threshold(input_tokens, output_tokens, request)

    def _estimate_input_tokens(self, request: RequestMetadata) -> int:
        """Estimate input tokens from request.

        Simple heuristic: ~4 characters per token
        """
        prompt = getattr(request, "prompt", None)
        if prompt and isinstance(prompt, str):
            return len(prompt) // 4
        # Conservative estimate
        return 100

    def filter_instances_by_type(
        self,
        instances: list[ExecutionInstance],
        target_type: ExecutionInstanceType,
    ) -> list[ExecutionInstance]:
        """Filter instances that can accept target request type.

        Args:
            instances: List of execution instances
            target_type: Target instance type (PREFILLING, DECODING, or HYBRID)

        Returns:
            Filtered list of suitable instances
        """
        if target_type == ExecutionInstanceType.PREFILLING:
            return [i for i in instances if i.can_accept_prefilling_request()]
        elif target_type == ExecutionInstanceType.DECODING:
            return [i for i in instances if i.can_accept_decoding_request()]
        else:  # HYBRID
            return [i for i in instances if i.can_accept_request]

    @staticmethod
    def get_instance_specialization(
        instance: ExecutionInstance,
    ) -> dict[str, float]:
        """Get specialization metrics for an instance.

        Returns dict with:
        - prefilling_score: 0.0-1.0 for prefilling suitability
        - decoding_score: 0.0-1.0 for decoding suitability
        """
        scores = {"prefilling_score": 0.0, "decoding_score": 0.0}

        if instance.instance_type == ExecutionInstanceType.PREFILLING:
            scores["prefilling_score"] = 1.0
            scores["decoding_score"] = 0.0
        elif instance.instance_type == ExecutionInstanceType.DECODING:
            scores["prefilling_score"] = 0.0
            scores["decoding_score"] = 1.0
        elif instance.instance_type == ExecutionInstanceType.HYBRID:
            # Hybrid instances score based on current load
            if instance.prefilling_active_requests > instance.decoding_active_requests:
                scores["prefilling_score"] = 0.8
                scores["decoding_score"] = 0.6
            else:
                scores["prefilling_score"] = 0.6
                scores["decoding_score"] = 0.8
        else:  # GENERAL
            scores["prefilling_score"] = 0.7
            scores["decoding_score"] = 0.7

        return scores

    def recommend_parallelism_config(
        self,
        instance: ExecutionInstance,
        request: RequestMetadata,
        target_type: ExecutionInstanceType | None = None,
    ) -> dict[str, int]:
        """Recommend parallelism configuration based on instance type.

        Args:
            instance: Target execution instance
            request: Request metadata
            target_type: Target request type (if known)

        Returns:
            Dict with 'tensor_parallel_size' and 'pipeline_parallel_size'
        """
        if target_type is None:
            target_type = instance.instance_type

        if target_type == ExecutionInstanceType.PREFILLING and instance.prefilling_config:
            return {
                "tensor_parallel_size": (instance.prefilling_config.tensor_parallel_size),
                "pipeline_parallel_size": (instance.prefilling_config.pipeline_parallel_size),
            }
        elif target_type == ExecutionInstanceType.DECODING and instance.decoding_config:
            return {
                "tensor_parallel_size": (instance.decoding_config.tensor_parallel_size),
                "pipeline_parallel_size": (instance.decoding_config.pipeline_parallel_size),
            }
        else:
            # Default: use instance's general parallelism config
            return {
                "tensor_parallel_size": instance.tensor_parallel_size,
                "pipeline_parallel_size": instance.pipeline_parallel_size,
            }
