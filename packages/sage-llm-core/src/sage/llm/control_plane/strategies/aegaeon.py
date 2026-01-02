# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Aegaeon scheduling policy for multi-model LLM serving.

Based on: Aegaeon: Effective GPU Pooling for Concurrent LLM Serving (SOSP'25)
Core algorithms:
- Algorithm 1: Grouped prefill-phase scheduling
- Algorithm 2: Batched decoding-phase scheduling
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from ..types import (
    ExecutionInstance,
    ExecutionInstanceType,
    ParallelismType,
    RequestMetadata,
    SchedulingDecision,
)
from .base import SchedulingPolicy


@dataclass
class PrefillGroup:
    """Group of requests for the same model in prefill phase."""

    model_name: str
    requests: list[RequestMetadata] = field(default_factory=list)
    max_size: int = 8  # MAX_GPSIZE from paper

    @property
    def size(self) -> int:
        return len(self.requests)

    @property
    def is_full(self) -> bool:
        return self.size >= self.max_size

    def can_add(self, request: RequestMetadata) -> bool:
        return not self.is_full and request.model_name == self.model_name


@dataclass
class DecodingBatch:
    """Batch of decoding requests for the same model."""

    model_name: str
    requests: list[RequestMetadata] = field(default_factory=list)
    time_quota: float = 0.0  # q_i in seconds - allocated quota per round
    remaining_quota: float = 0.0  # Remaining quota in current round
    decoding_step_time: float = 0.025  # t_i estimated (25ms)
    tokens_executed: int = 0  # Total tokens executed in this batch
    last_execution_time: float = 0.0  # Timestamp of last execution

    @property
    def n_value(self) -> float:
        """Calculate n_i = d / t_i."""
        tbt_deadline = self._get_tbt_deadline()
        return tbt_deadline / self.decoding_step_time if self.decoding_step_time > 0 else 1.0

    def _get_tbt_deadline(self) -> float:
        """Get TBT deadline in seconds."""
        if self.requests:
            # Use tbt_slo_ms if available, otherwise fall back to slo_deadline_ms
            for req in self.requests:
                if req.tbt_slo_ms:
                    return req.tbt_slo_ms / 1000.0
                if req.slo_deadline_ms:
                    return req.slo_deadline_ms / 1000.0
        return 0.1  # Default 100ms

    def consume_quota(self, time_spent: float) -> float:
        """Consume quota and return remaining quota."""
        self.remaining_quota = max(0, self.remaining_quota - time_spent)
        return self.remaining_quota

    def reset_quota(self):
        """Reset remaining quota to full time_quota for new round."""
        self.remaining_quota = self.time_quota


class AegaeonPolicy(SchedulingPolicy):
    """Aegaeon scheduling policy.

    Key features:
    - Prefill: Grouped scheduling to minimize auto-scaling overhead
    - Decoding: Weighted round-robin with SLO-aware time quota
    - Token-level preemptive scheduling
    """

    def __init__(
        self,
        max_group_size: int = 8,
        qmax: float = 4.0,
        min_alpha: float = 0.5,
        estimated_scaling_overhead: float = 1.0,
        use_dynamic_scaling_overhead: bool = True,
    ):
        """Initialize Aegaeon policy.

        Args:
            max_group_size: MAX_GPSIZE - max requests per group
            qmax: QMAX - maximum time quota in seconds
            min_alpha: Minimum α for SLO guarantee
            estimated_scaling_overhead: c - auto-scaling overhead in seconds
            use_dynamic_scaling_overhead: Whether to calculate scaling overhead dynamically
        """
        super().__init__(name="aegaeon")
        self.max_group_size = max_group_size
        self.qmax = qmax
        self.min_alpha = min_alpha
        self.estimated_scaling_overhead = estimated_scaling_overhead
        self.use_dynamic_scaling_overhead = use_dynamic_scaling_overhead

        # Model switching overhead cache (model_name, tp_size) -> overhead_seconds
        self._scaling_overhead_cache: dict[tuple[str, int], float] = {}

        # Prefill state: instance_id -> list of PrefillGroup
        self.prefill_job_queues: dict[str, list[PrefillGroup]] = defaultdict(list)

        # Decoding state: instance_id -> list of DecodingBatch
        self.decoding_work_lists: dict[str, list[DecodingBatch]] = defaultdict(list)

        # Running requests tracking for preemption
        self.running_requests: dict[str, RequestMetadata] = {}

    def _get_scaling_overhead(
        self,
        model_name: str,
        tp_size: int,
    ) -> float:
        """Calculate model switching overhead based on model size and TP configuration.

        Based on Aegaeon paper Figure 4:
        - Small models (< 7B): 0.5-0.8s
        - Medium models (7B-13B): 0.8-1.5s
        - Large models (> 13B): 1.5-2.5s
        - Scaling with TP: overhead increases with TP size
        """
        if not self.use_dynamic_scaling_overhead:
            return self.estimated_scaling_overhead

        cache_key = (model_name, tp_size)
        if cache_key in self._scaling_overhead_cache:
            return self._scaling_overhead_cache[cache_key]

        # Estimate model size from name
        base_overhead = 1.0  # Default 1.0s

        if any(size in model_name.lower() for size in ["1b", "3b", "6b"]):
            base_overhead = 0.6
        elif any(size in model_name.lower() for size in ["7b", "8b"]):
            base_overhead = 1.0
        elif any(size in model_name.lower() for size in ["13b", "14b"]):
            base_overhead = 1.3
        elif any(size in model_name.lower() for size in ["30b", "33b", "34b"]):
            base_overhead = 1.8
        elif any(size in model_name.lower() for size in ["65b", "70b"]):
            base_overhead = 2.2

        # Scale with TP size (more GPUs = more coordination overhead)
        tp_scaling = 1.0 + (tp_size - 1) * 0.1  # +10% per additional TP rank
        overhead = base_overhead * tp_scaling

        self._scaling_overhead_cache[cache_key] = overhead
        return overhead

    def _calculate_slo_violation_risk(self, request: RequestMetadata) -> float:
        """Calculate SLO violation risk score (0-1, higher = more urgent)."""
        if not request.last_token_time or not request.tbt_slo_ms:
            return 0.0

        # Calculate time since last token
        now = datetime.now()
        time_since_last = (now - request.last_token_time).total_seconds() * 1000

        # Risk = (actual_tbt / slo_tbt), capped at 1.0
        risk = min(1.0, time_since_last / request.tbt_slo_ms)
        return risk

    def _check_and_preempt(
        self,
        instances: list[ExecutionInstance],
    ) -> list[RequestMetadata]:
        """Check running requests and preempt those at high SLO violation risk.

        Returns:
            List of preempted requests to be rescheduled
        """
        preempted = []

        for instance in instances:
            if instance.instance_type != ExecutionInstanceType.DECODING:
                continue

            work_list = self.decoding_work_lists[instance.instance_id]

            for batch in work_list:
                high_risk_requests = []
                safe_requests = []

                for req in batch.requests:
                    risk = self._calculate_slo_violation_risk(req)

                    # Preempt if risk > 0.8 and request is preemptible
                    if risk > 0.8 and req.can_be_preempted:
                        high_risk_requests.append((risk, req))
                    else:
                        safe_requests.append(req)

                # Sort by risk (highest first) and preempt
                high_risk_requests.sort(key=lambda x: x[0], reverse=True)

                if high_risk_requests:
                    # Keep highest risk requests in batch, preempt others
                    for _, req in high_risk_requests[:1]:  # Keep top 1 high-risk
                        safe_requests.append(req)

                    for _, req in high_risk_requests[1:]:  # Preempt the rest
                        preempted.append(req)
                        if req.request_id in self.running_requests:
                            del self.running_requests[req.request_id]

                batch.requests = safe_requests

        return preempted

    def schedule(
        self,
        requests: list[RequestMetadata],
        instances: list[ExecutionInstance],
    ) -> list[SchedulingDecision]:
        """Schedule requests to instances with token-level preemption."""
        decisions = []

        # Step 0: Check for preemption opportunities
        preempted_requests = self._check_and_preempt(instances)

        # Add preempted requests back to scheduling queue
        all_requests = list(requests) + preempted_requests

        # Separate prefill and decoding instances
        prefill_instances = [
            i for i in instances if i.instance_type == ExecutionInstanceType.PREFILLING
        ]

        # Schedule prefill requests
        for request in all_requests:
            if not request.prefill_completed:
                decision = self._schedule_prefill_request(request, prefill_instances)
                if decision:
                    decisions.append(decision)
                    self.running_requests[request.request_id] = request

        return decisions

    def _schedule_prefill_request(
        self,
        request: RequestMetadata,
        prefill_instances: list[ExecutionInstance],
    ) -> SchedulingDecision | None:
        """Algorithm 1: Grouped Prefill-Phase Scheduling."""
        if not prefill_instances:
            return None

        # Step 1: Try to add to existing group with same model
        for instance in prefill_instances:
            job_queue = self.prefill_job_queues[instance.instance_id]
            for group in job_queue:
                if group.can_add(request):
                    group.requests.append(request)
                    return SchedulingDecision(
                        request_id=request.request_id,
                        target_instance_id=instance.instance_id,
                        parallelism_strategy=request.parallelism_hint
                        or ParallelismType.TENSOR_PARALLEL,
                        estimated_latency_ms=self._estimate_prefill_wait_time(instance) * 1000,
                        estimated_cost=0.0,
                    )

        # Step 2: Create new group and add to least loaded instance
        min_load = float("inf")
        best_instance = None

        for instance in prefill_instances:
            load = self._calculate_prefill_load(instance)
            if load < min_load:
                min_load = load
                best_instance = instance

        if best_instance:
            new_group = PrefillGroup(
                model_name=request.model_name or "default",
                requests=[request],
                max_size=self.max_group_size,
            )
            self.prefill_job_queues[best_instance.instance_id].append(new_group)

            return SchedulingDecision(
                request_id=request.request_id,
                target_instance_id=best_instance.instance_id,
                parallelism_strategy=request.parallelism_hint or ParallelismType.TENSOR_PARALLEL,
                estimated_latency_ms=self._estimate_prefill_wait_time(best_instance) * 1000,
                estimated_cost=0.0,
            )

        return None

    def _calculate_prefill_load(self, instance: ExecutionInstance) -> float:
        """Calculate total time to execute all groups in instance."""
        job_queue = self.prefill_job_queues[instance.instance_id]

        total_time = 0.0
        prev_model = None

        for group in job_queue:
            # Add auto-scaling time if model changes
            if prev_model and prev_model != group.model_name:
                overhead = self._get_scaling_overhead(
                    group.model_name,
                    instance.tensor_parallel_size,
                )
                total_time += overhead

            # Add execution time (batch size = 1 per paper)
            total_time += len(group.requests) * 1.0  # Assume 1s per request

            prev_model = group.model_name

        return total_time

    def _estimate_prefill_wait_time(self, instance: ExecutionInstance) -> float:
        """Estimate wait time for new request."""
        return self._calculate_prefill_load(instance)

    def get_next_prefill_request(self, instance_id: str) -> RequestMetadata | None:
        """Get next request to execute from prefill job queue (FIFO within groups)."""
        job_queue = self.prefill_job_queues[instance_id]

        if not job_queue:
            return None

        # Get from front group
        front_group = job_queue[0]
        if front_group.requests:
            request = front_group.requests.pop(0)

            # Remove empty group
            if not front_group.requests:
                job_queue.pop(0)

            return request

        return None

    def schedule_decoding_round(
        self,
        instance_id: str,
    ) -> list[tuple[DecodingBatch, float]]:
        """Algorithm 2: Batched Decoding-Phase Scheduling.

        Returns:
            List of (batch, time_quota) tuples
        """
        work_list = self.decoding_work_lists[instance_id]

        if not work_list:
            return []

        # Calculate time quotas for all batches
        n_values = [batch.n_value for batch in work_list]
        sum_inv_n = sum(1.0 / n for n in n_values)
        min_n = min(n_values)

        # Calculate α: α = max(c/(min_n * QMAX) + Σ(1/n_k), 0.5)
        alpha = max(
            self.estimated_scaling_overhead / (min_n * self.qmax) + sum_inv_n,
            self.min_alpha,
        )

        # Assign quota to each batch: q_i = (c/n_i) * (α - Σ(1/n_k))
        schedule = []
        for i, batch in enumerate(work_list):
            n_i = n_values[i]
            q_i = (self.estimated_scaling_overhead / n_i) * (alpha - sum_inv_n)

            # Ensure non-negative quota
            q_i = max(0.1, q_i)

            batch.time_quota = q_i
            batch.reset_quota()  # Reset remaining quota for new round
            schedule.append((batch, q_i))

        # Reorder work list to group batches with same model
        self._reorder_work_list_by_model(instance_id)

        return schedule

    def execute_batch_with_quota(
        self,
        batch: DecodingBatch,
        instance_id: str,
    ) -> int:
        """Execute a batch for its time quota, return number of tokens generated.

        This method should be called by the executor to run decoding steps
        until the time quota is exhausted.

        Returns:
            Number of tokens generated in this execution
        """
        tokens_generated = 0
        start_time = datetime.now()

        while batch.remaining_quota > 0 and batch.requests:
            # Simulate one decoding step for all requests in batch
            # Update token tracking for each request
            for req in batch.requests:
                req.tokens_generated += 1
                req.last_token_time = datetime.now()

                # Check if request is complete
                if req.max_tokens and req.tokens_generated >= req.max_tokens:
                    batch.requests.remove(req)
                    if req.request_id in self.running_requests:
                        del self.running_requests[req.request_id]

            tokens_generated += len(batch.requests)
            batch.tokens_executed += len(batch.requests)

            # Consume quota
            elapsed = (datetime.now() - start_time).total_seconds()
            batch.consume_quota(elapsed)

            # Check if quota exhausted
            if batch.remaining_quota <= 0:
                break

        batch.last_execution_time = datetime.now().timestamp()
        return tokens_generated

    def _reorder_work_list_by_model(self, instance_id: str):
        """Reorder work list to group batches with same model."""
        work_list = self.decoding_work_lists[instance_id]

        # Group by model
        model_batches = defaultdict(list)
        for batch in work_list:
            model_batches[batch.model_name].append(batch)

        # Flatten back to list
        reordered = []
        for model_name in sorted(model_batches.keys()):
            reordered.extend(model_batches[model_name])

        self.decoding_work_lists[instance_id] = reordered

    def add_to_decoding_batch(
        self,
        request: RequestMetadata,
        instance_id: str,
    ):
        """Add a prefilled request to decoding work list."""
        work_list = self.decoding_work_lists[instance_id]
        model_name = request.model_name or "default"

        # Try to find existing batch with same model
        for batch in work_list:
            if batch.model_name == model_name:
                batch.requests.append(request)
                return

        # Create new batch
        new_batch = DecodingBatch(
            model_name=model_name,
            requests=[request],
        )
        work_list.append(new_batch)

    def prioritize(
        self,
        requests: list[RequestMetadata],
    ) -> list[RequestMetadata]:
        """Prioritize requests (FIFO within groups for Aegaeon)."""
        return sorted(requests, key=lambda r: r.arrival_time)
