# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Hybrid scheduling strategy for mixed LLM and Embedding workloads.

This module implements the HybridSchedulingPolicy, which enables unified
scheduling of both LLM (chat/generation) and Embedding requests within
a shared resource pool. The policy supports:

1. Request type classification and grouping
2. Embedding request batching for improved throughput
3. Type-isolated scheduling to appropriate instances
4. Dynamic load balancing between LLM and Embedding workloads
5. Fallback to configurable LLM scheduling strategies

Example:
    >>> from control_plane.strategies.hybrid_policy import HybridSchedulingPolicy
    >>> from control_plane.types import RequestMetadata, ExecutionInstance, RequestType
    >>>
    >>> policy = HybridSchedulingPolicy(
    ...     embedding_batch_size=32,
    ...     embedding_priority="normal",
    ...     llm_fallback_policy="adaptive",
    ... )
    >>>
    >>> requests = [...]  # Mixed LLM and Embedding requests
    >>> instances = [...]  # Mixed instance types
    >>> decisions = policy.schedule(requests, instances)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from ..request_classifier import RequestClassifier
from ..types import (
    ExecutionInstance,
    ExecutionInstanceType,
    ParallelismType,
    RequestMetadata,
    RequestType,
    SchedulingDecision,
)
from .adaptive import AdaptivePolicy
from .base import SchedulingPolicy
from .fifo import FIFOPolicy
from .priority import PriorityPolicy
from .slo_aware import SLOAwarePolicy

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class EmbeddingPriority(Enum):
    """Priority level for embedding requests relative to LLM requests.

    Attributes:
        HIGH: Embedding requests are processed before LLM requests.
            Use when embedding latency is critical (e.g., real-time search).
        NORMAL: Embedding and LLM requests are treated equally.
            Requests are scheduled based on arrival time and priority.
        LOW: LLM requests are prioritized over embedding requests.
            Use when LLM response time is more critical.
        ADAPTIVE: Priority is adjusted based on queue depths and load.
            Embedding priority increases when embedding queue grows.
    """

    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    ADAPTIVE = "adaptive"


@dataclass
class HybridSchedulingConfig:
    """Configuration for HybridSchedulingPolicy.

    Attributes:
        embedding_batch_size: Target batch size for embedding requests.
            Larger batches improve throughput but increase latency.
            Default is 32.
        embedding_priority: Priority level for embedding requests.
            Can be "high", "normal", "low", or "adaptive".
            Default is "normal".
        llm_fallback_policy: Name of the policy to use for LLM scheduling.
            Can be "fifo", "priority", "slo_aware", "adaptive".
            Default is "adaptive".
        hybrid_instance_ratio: Target ratio of LLM to Embedding time
            for mixed (LLM_EMBEDDING) instances. 0.7 means 70% LLM, 30% Embedding.
            Default is 0.7.
        enable_embedding_batching: Whether to batch embedding requests.
            Default is True.
        max_embedding_wait_ms: Maximum time to wait for batching embeddings.
            Default is 50ms.
        min_embedding_batch_size: Minimum batch size before scheduling.
            Default is 1 (no minimum).
        prefer_specialized_instances: Whether to prefer specialized instances
            (EMBEDDING for embeddings, LLM-only for LLM) over mixed instances.
            Default is True.
    """

    embedding_batch_size: int = 32
    embedding_priority: str = "normal"
    llm_fallback_policy: str = "adaptive"
    hybrid_instance_ratio: float = 0.7
    enable_embedding_batching: bool = True
    max_embedding_wait_ms: float = 50.0
    min_embedding_batch_size: int = 1
    prefer_specialized_instances: bool = True


@dataclass
class EmbeddingBatch:
    """A batch of embedding requests grouped for efficient processing.

    Attributes:
        requests: List of embedding requests in this batch.
        model: The embedding model name (all requests in batch use same model).
        total_texts: Total number of texts across all requests.
        created_at: Timestamp when batch was created.
        batch_id: Unique identifier for this batch.
    """

    requests: list[RequestMetadata] = field(default_factory=list)
    model: str | None = None
    total_texts: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    batch_id: str = ""

    def add_request(self, request: RequestMetadata) -> bool:
        """Add a request to this batch if compatible.

        Args:
            request: The embedding request to add.

        Returns:
            True if request was added, False if incompatible.
        """
        # Get model from request
        request_model = request.embedding_model or request.model_name

        # First request sets the model
        if not self.requests:
            self.model = request_model
            self.requests.append(request)
            self.total_texts += len(request.embedding_texts or [])
            return True

        # Check model compatibility
        if request_model != self.model:
            return False

        self.requests.append(request)
        self.total_texts += len(request.embedding_texts or [])
        return True

    @property
    def size(self) -> int:
        """Number of requests in this batch."""
        return len(self.requests)


class HybridSchedulingPolicy(SchedulingPolicy):
    """Hybrid scheduling policy for mixed LLM and Embedding workloads.

    This policy implements unified scheduling for LLM (chat/generation) and
    Embedding requests, enabling efficient resource utilization across
    heterogeneous execution instances.

    Key features:
    1. **Request Classification**: Automatically classifies requests by type
       using RequestClassifier.
    2. **Type-Isolated Scheduling**: Routes requests to compatible instances
       (EMBEDDING requests to EMBEDDING/LLM_EMBEDDING instances, etc.).
    3. **Embedding Batching**: Groups embedding requests by model for
       improved throughput.
    4. **Load Balancing**: Balances load across mixed instances to maximize
       GPU utilization.
    5. **Fallback Strategies**: Uses configurable LLM scheduling strategies
       (FIFO, Priority, SLO-Aware, Adaptive) for LLM requests.

    Scheduling Algorithm:
    1. Classify all requests by type (LLM_CHAT, LLM_GENERATE, EMBEDDING)
    2. Group embedding requests into batches by model
    3. Schedule embedding batches:
       - Prefer EMBEDDING instances (specialized)
       - Fall back to LLM_EMBEDDING instances if needed
    4. Schedule LLM requests using fallback policy:
       - Exclude EMBEDDING-only instances
       - Consider load on mixed instances
    5. Apply priority adjustments based on embedding_priority setting

    Example:
        >>> policy = HybridSchedulingPolicy()
        >>> decisions = policy.schedule(requests, instances)
        >>> for d in decisions:
        ...     print(f"{d.request_id} -> {d.target_instance_id}")
    """

    def __init__(
        self,
        embedding_batch_size: int = 32,
        embedding_priority: str = "normal",
        llm_fallback_policy: str = "adaptive",
        hybrid_instance_ratio: float = 0.7,
        config: HybridSchedulingConfig | None = None,
    ) -> None:
        """Initialize the hybrid scheduling policy.

        Args:
            embedding_batch_size: Target batch size for embedding requests.
            embedding_priority: Priority for embeddings ("high", "normal",
                "low", "adaptive").
            llm_fallback_policy: LLM scheduling policy name ("fifo",
                "priority", "slo_aware", "adaptive").
            hybrid_instance_ratio: Target LLM/Embedding ratio for mixed
                instances (0.0-1.0).
            config: Full configuration object. If provided, overrides
                individual parameters.
        """
        super().__init__("Hybrid")

        # Use config if provided, otherwise build from parameters
        if config is not None:
            self.config = config
        else:
            self.config = HybridSchedulingConfig(
                embedding_batch_size=embedding_batch_size,
                embedding_priority=embedding_priority,
                llm_fallback_policy=llm_fallback_policy,
                hybrid_instance_ratio=hybrid_instance_ratio,
            )

        # Initialize components
        self.classifier = RequestClassifier()
        self._init_llm_fallback_policy()

        # Parse embedding priority
        self.embedding_priority = self._parse_embedding_priority(self.config.embedding_priority)

        # Metrics tracking
        self._embedding_scheduled_count = 0
        self._llm_scheduled_count = 0
        self._batch_count = 0

        logger.info(
            "HybridSchedulingPolicy initialized: "
            "embedding_batch_size=%d, embedding_priority=%s, "
            "llm_fallback=%s, hybrid_ratio=%.2f",
            self.config.embedding_batch_size,
            self.config.embedding_priority,
            self.config.llm_fallback_policy,
            self.config.hybrid_instance_ratio,
        )

    def _init_llm_fallback_policy(self) -> None:
        """Initialize the LLM fallback scheduling policy."""
        policy_name = self.config.llm_fallback_policy.lower()

        if policy_name == "fifo":
            self.llm_policy: SchedulingPolicy = FIFOPolicy()
        elif policy_name == "priority":
            self.llm_policy = PriorityPolicy()
        elif policy_name == "slo_aware":
            self.llm_policy = SLOAwarePolicy()
        elif policy_name == "adaptive":
            self.llm_policy = AdaptivePolicy()
        else:
            logger.warning(
                "Unknown LLM fallback policy '%s', using Adaptive",
                policy_name,
            )
            self.llm_policy = AdaptivePolicy()

    def _parse_embedding_priority(self, priority_str: str) -> EmbeddingPriority:
        """Parse embedding priority from string.

        Args:
            priority_str: Priority string ("high", "normal", "low", "adaptive").

        Returns:
            EmbeddingPriority enum value.
        """
        priority_map = {
            "high": EmbeddingPriority.HIGH,
            "normal": EmbeddingPriority.NORMAL,
            "low": EmbeddingPriority.LOW,
            "adaptive": EmbeddingPriority.ADAPTIVE,
        }
        return priority_map.get(priority_str.lower(), EmbeddingPriority.NORMAL)

    def schedule(
        self,
        requests: list[RequestMetadata],
        instances: list[ExecutionInstance],
    ) -> list[SchedulingDecision]:
        """Schedule mixed LLM and Embedding requests to appropriate instances.

        This method implements the core hybrid scheduling algorithm:
        1. Classify and group requests by type
        2. Batch embedding requests by model
        3. Schedule embedding batches to embedding-capable instances
        4. Schedule LLM requests using fallback policy
        5. Apply priority adjustments

        Args:
            requests: List of pending requests (mixed LLM and Embedding).
            instances: List of available execution instances.

        Returns:
            List of scheduling decisions mapping requests to instances.
        """
        if not requests or not instances:
            return []

        decisions: list[SchedulingDecision] = []

        # Step 1: Classify and group requests by type
        llm_requests, embedding_requests = self._group_requests_by_type(requests)

        logger.debug(
            "Grouped requests: %d LLM, %d Embedding",
            len(llm_requests),
            len(embedding_requests),
        )

        # Step 2: Determine scheduling order based on priority
        if self.embedding_priority == EmbeddingPriority.HIGH:
            # Schedule embeddings first
            decisions.extend(self._schedule_embedding_requests(embedding_requests, instances))
            decisions.extend(self._schedule_llm_requests(llm_requests, instances, decisions))
        elif self.embedding_priority == EmbeddingPriority.LOW:
            # Schedule LLM first
            decisions.extend(self._schedule_llm_requests(llm_requests, instances, []))
            decisions.extend(self._schedule_embedding_requests(embedding_requests, instances))
        elif self.embedding_priority == EmbeddingPriority.ADAPTIVE:
            # Adaptive: check queue depths
            decisions.extend(self._schedule_adaptive(llm_requests, embedding_requests, instances))
        else:
            # Normal: interleave based on arrival time
            decisions.extend(
                self._schedule_interleaved(llm_requests, embedding_requests, instances)
            )

        return decisions

    def _group_requests_by_type(
        self,
        requests: list[RequestMetadata],
    ) -> tuple[list[RequestMetadata], list[RequestMetadata]]:
        """Group requests by type (LLM vs Embedding).

        Args:
            requests: List of all requests.

        Returns:
            Tuple of (llm_requests, embedding_requests).
        """
        llm_requests: list[RequestMetadata] = []
        embedding_requests: list[RequestMetadata] = []

        for request in requests:
            request_type = self.classifier.classify(request)
            if request_type == RequestType.EMBEDDING:
                embedding_requests.append(request)
            else:
                llm_requests.append(request)

        return llm_requests, embedding_requests

    def _schedule_embedding_requests(
        self,
        requests: list[RequestMetadata],
        instances: list[ExecutionInstance],
    ) -> list[SchedulingDecision]:
        """Schedule embedding requests to compatible instances.

        Implements batching and instance selection for embedding requests:
        1. Group requests into batches by model
        2. For each batch, find compatible instances
        3. Prefer EMBEDDING instances, fall back to LLM_EMBEDDING

        Args:
            requests: List of embedding requests to schedule.
            instances: List of all execution instances.

        Returns:
            List of scheduling decisions for embedding requests.
        """
        if not requests:
            return []

        decisions: list[SchedulingDecision] = []

        # Get embedding-capable instances
        embedding_instances = self.classifier.get_compatible_instances(
            RequestType.EMBEDDING,
            instances,
            prefer_specialized=self.config.prefer_specialized_instances,
        )

        if not embedding_instances:
            logger.warning(
                "No embedding-capable instances available for %d requests",
                len(requests),
            )
            return []

        # Group requests into batches by model
        batches = self._create_embedding_batches(requests)

        logger.debug(
            "Created %d embedding batches from %d requests",
            len(batches),
            len(requests),
        )

        # Schedule each batch
        for batch in batches:
            batch_decisions = self._schedule_embedding_batch(batch, embedding_instances)
            decisions.extend(batch_decisions)

        self._embedding_scheduled_count += len(decisions)
        self._batch_count += len(batches)

        return decisions

    def _create_embedding_batches(
        self,
        requests: list[RequestMetadata],
    ) -> list[EmbeddingBatch]:
        """Create batches from embedding requests.

        Groups requests by model and respects batch size limits.

        Args:
            requests: List of embedding requests.

        Returns:
            List of EmbeddingBatch objects.
        """
        if not self.config.enable_embedding_batching:
            # No batching: each request is its own batch
            batches = []
            for i, req in enumerate(requests):
                batch = EmbeddingBatch(batch_id=f"batch-{i}")
                batch.add_request(req)
                batches.append(batch)
            return batches

        # Group by model
        model_batches: dict[str, list[EmbeddingBatch]] = {}
        batch_counter = 0

        for request in requests:
            model = request.embedding_model or request.model_name or "default"

            if model not in model_batches:
                model_batches[model] = []

            # Try to add to existing batch
            added = False
            for batch in model_batches[model]:
                # Check if batch has room
                new_texts = len(request.embedding_texts or [])
                if batch.total_texts + new_texts <= self.config.embedding_batch_size:
                    batch.add_request(request)
                    added = True
                    break

            # Create new batch if needed
            if not added:
                batch = EmbeddingBatch(batch_id=f"batch-{batch_counter}")
                batch_counter += 1
                batch.add_request(request)
                model_batches[model].append(batch)

        # Flatten batches
        all_batches = []
        for batches in model_batches.values():
            all_batches.extend(batches)

        return all_batches

    def _schedule_embedding_batch(
        self,
        batch: EmbeddingBatch,
        instances: list[ExecutionInstance],
    ) -> list[SchedulingDecision]:
        """Schedule a single embedding batch to an instance.

        Args:
            batch: The embedding batch to schedule.
            instances: List of embedding-capable instances.

        Returns:
            List of scheduling decisions (one per request in batch).
        """
        decisions: list[SchedulingDecision] = []

        # Find best instance for this batch
        available = [i for i in instances if i.can_accept_embedding_request()]

        if not available:
            logger.warning(
                "No available instances for embedding batch %s (%d requests)",
                batch.batch_id,
                batch.size,
            )
            return []

        # Prefer instances with matching model loaded
        target = self._select_embedding_instance(available, batch.model)

        # Create decision for each request in batch
        for request in batch.requests:
            decision = SchedulingDecision(
                request_id=request.request_id,
                target_instance_id=target.instance_id,
                parallelism_strategy=ParallelismType.DATA_PARALLEL,
                tensor_parallel_size=1,
                pipeline_parallel_size=1,
                estimated_latency_ms=self._estimate_embedding_latency(batch.total_texts, target),
                estimated_cost=0.0,
                reason=f"Hybrid: embedding batch {batch.batch_id}",
                metadata={
                    "batch_id": batch.batch_id,
                    "batch_size": batch.size,
                    "total_texts": batch.total_texts,
                    "request_type": "embedding",
                },
            )
            decisions.append(decision)

        return decisions

    def _select_embedding_instance(
        self,
        instances: list[ExecutionInstance],
        model: str | None,
    ) -> ExecutionInstance:
        """Select the best instance for an embedding batch.

        Selection criteria:
        1. Prefer instances with matching model already loaded
        2. Prefer pure EMBEDDING instances over LLM_EMBEDDING
        3. Prefer instances with lower embedding load
        4. Prefer instances with more available capacity

        Args:
            instances: List of available embedding instances.
            model: Target embedding model name.

        Returns:
            Selected ExecutionInstance.
        """

        def score_instance(instance: ExecutionInstance) -> tuple[int, int, float, float]:
            """Score instance (lower is better).

            Returns tuple for sorting:
            (model_match, type_preference, embedding_load, general_load)
            """
            # Model match: 0 if matches, 1 if not
            model_match = 0 if (model and instance.embedding_model_loaded == model) else 1

            # Type preference: 0 for EMBEDDING, 1 for LLM_EMBEDDING
            type_pref = 0 if (instance.instance_type == ExecutionInstanceType.EMBEDDING) else 1

            # Embedding load ratio
            embedding_load = (
                instance.embedding_active_requests / instance.embedding_max_batch_size
                if instance.embedding_max_batch_size > 0
                else 1.0
            )

            # General load
            general_load = instance.current_load

            return (model_match, type_pref, embedding_load, general_load)

        return min(instances, key=score_instance)

    def _estimate_embedding_latency(
        self,
        num_texts: int,
        instance: ExecutionInstance,
    ) -> float:
        """Estimate embedding latency for a batch.

        Simple estimation: base latency + per-text overhead.

        Args:
            num_texts: Number of texts to embed.
            instance: Target instance.

        Returns:
            Estimated latency in milliseconds.
        """
        # Base latency (network overhead, etc.)
        base_latency = 5.0

        # Per-text processing time (varies by model/hardware)
        per_text_latency = 0.5

        # Account for current load
        load_factor = 1.0 + instance.current_load

        return (base_latency + num_texts * per_text_latency) * load_factor

    def _schedule_llm_requests(
        self,
        requests: list[RequestMetadata],
        instances: list[ExecutionInstance],
        existing_decisions: list[SchedulingDecision],
    ) -> list[SchedulingDecision]:
        """Schedule LLM requests using the fallback policy.

        Filters instances to exclude EMBEDDING-only instances and
        delegates to the configured LLM scheduling policy.

        Args:
            requests: List of LLM requests to schedule.
            instances: List of all execution instances.
            existing_decisions: Already-made scheduling decisions
                (for load consideration).

        Returns:
            List of scheduling decisions for LLM requests.
        """
        if not requests:
            return []

        # Get LLM-capable instances
        llm_instances = self.classifier.get_compatible_instances(
            RequestType.LLM_CHAT,  # LLM_CHAT and LLM_GENERATE have same instance requirements
            instances,
            prefer_specialized=self.config.prefer_specialized_instances,
        )

        if not llm_instances:
            logger.warning(
                "No LLM-capable instances available for %d requests",
                len(requests),
            )
            return []

        # Account for load from embedding scheduling on mixed instances
        adjusted_instances = self._adjust_instance_load_for_embeddings(
            llm_instances, existing_decisions
        )

        # Delegate to fallback policy
        decisions = self.llm_policy.schedule(requests, adjusted_instances)

        # Add hybrid metadata
        for decision in decisions:
            decision.metadata["request_type"] = "llm"
            decision.metadata["hybrid_policy"] = True
            decision.metadata["llm_fallback"] = self.config.llm_fallback_policy

        self._llm_scheduled_count += len(decisions)

        return decisions

    def _adjust_instance_load_for_embeddings(
        self,
        instances: list[ExecutionInstance],
        embedding_decisions: list[SchedulingDecision],
    ) -> list[ExecutionInstance]:
        """Adjust instance load estimates based on embedding scheduling.

        For mixed (LLM_EMBEDDING) instances, accounts for load from
        recently scheduled embedding requests.

        Args:
            instances: LLM-capable instances.
            embedding_decisions: Decisions made for embedding requests.

        Returns:
            List of instances (may have adjusted load estimates).
        """
        if not embedding_decisions:
            return instances

        # Count embedding decisions per instance
        embedding_counts: dict[str, int] = {}
        for decision in embedding_decisions:
            instance_id = decision.target_instance_id
            embedding_counts[instance_id] = embedding_counts.get(instance_id, 0) + 1

        # For simplicity, we don't modify the instances in place
        # The load is already tracked via embedding_active_requests
        # This method is a hook for future enhancements

        return instances

    def _schedule_adaptive(
        self,
        llm_requests: list[RequestMetadata],
        embedding_requests: list[RequestMetadata],
        instances: list[ExecutionInstance],
    ) -> list[SchedulingDecision]:
        """Schedule with adaptive priority based on queue depths.

        When embedding queue is much longer, prioritize embeddings.
        When LLM queue is much longer, prioritize LLM.

        Args:
            llm_requests: List of LLM requests.
            embedding_requests: List of embedding requests.
            instances: List of execution instances.

        Returns:
            List of scheduling decisions.
        """
        decisions: list[SchedulingDecision] = []

        # Calculate queue ratio
        total = len(llm_requests) + len(embedding_requests)
        if total == 0:
            return []

        embedding_ratio = len(embedding_requests) / total

        # Adaptive threshold: if embedding > 40%, prioritize embeddings
        if embedding_ratio > 0.4:
            logger.debug(
                "Adaptive: prioritizing embeddings (ratio=%.2f)",
                embedding_ratio,
            )
            decisions.extend(self._schedule_embedding_requests(embedding_requests, instances))
            decisions.extend(self._schedule_llm_requests(llm_requests, instances, decisions))
        else:
            logger.debug(
                "Adaptive: prioritizing LLM (embedding ratio=%.2f)",
                embedding_ratio,
            )
            decisions.extend(self._schedule_llm_requests(llm_requests, instances, []))
            decisions.extend(self._schedule_embedding_requests(embedding_requests, instances))

        return decisions

    def _schedule_interleaved(
        self,
        llm_requests: list[RequestMetadata],
        embedding_requests: list[RequestMetadata],
        instances: list[ExecutionInstance],
    ) -> list[SchedulingDecision]:
        """Schedule requests in interleaved order by arrival time.

        Mixes LLM and embedding scheduling based on request arrival order.

        Args:
            llm_requests: List of LLM requests.
            embedding_requests: List of embedding requests.
            instances: List of execution instances.

        Returns:
            List of scheduling decisions.
        """
        # Combine and sort by arrival time
        all_requests = llm_requests + embedding_requests
        sorted_requests = sorted(all_requests, key=lambda r: r.arrival_time)

        # Re-split while maintaining order
        ordered_llm: list[RequestMetadata] = []
        ordered_embedding: list[RequestMetadata] = []

        for request in sorted_requests:
            if self.classifier.classify(request) == RequestType.EMBEDDING:
                ordered_embedding.append(request)
            else:
                ordered_llm.append(request)

        # Schedule both types
        decisions: list[SchedulingDecision] = []
        decisions.extend(self._schedule_embedding_requests(ordered_embedding, instances))
        decisions.extend(self._schedule_llm_requests(ordered_llm, instances, decisions))

        # Sort final decisions by original arrival time
        request_order = {r.request_id: i for i, r in enumerate(sorted_requests)}
        decisions.sort(key=lambda d: request_order.get(d.request_id, float("inf")))

        return decisions

    def prioritize(self, requests: list[RequestMetadata]) -> list[RequestMetadata]:
        """Prioritize requests for scheduling.

        Uses a hybrid prioritization that considers:
        1. Request priority level (CRITICAL > HIGH > NORMAL > LOW > BACKGROUND)
        2. Request type based on embedding_priority setting
        3. Arrival time (FIFO within same priority)

        Args:
            requests: List of requests to prioritize.

        Returns:
            Sorted list of requests by priority.
        """

        def priority_key(request: RequestMetadata) -> tuple[int, int, datetime]:
            """Generate sort key for request.

            Returns:
                Tuple of (type_priority, request_priority, arrival_time).
            """
            # Type priority based on embedding_priority setting
            is_embedding = self.classifier.classify(request) == RequestType.EMBEDDING

            if self.embedding_priority == EmbeddingPriority.HIGH:
                type_prio = 0 if is_embedding else 1
            elif self.embedding_priority == EmbeddingPriority.LOW:
                type_prio = 1 if is_embedding else 0
            else:
                type_prio = 0  # Equal priority

            return (type_prio, request.priority.value, request.arrival_time)

        return sorted(requests, key=priority_key)

    def get_metrics(self) -> dict[str, int | float]:
        """Get scheduling metrics.

        Returns:
            Dictionary of metric name to value.
        """
        return {
            "embedding_scheduled_count": self._embedding_scheduled_count,
            "llm_scheduled_count": self._llm_scheduled_count,
            "batch_count": self._batch_count,
            "total_scheduled": (self._embedding_scheduled_count + self._llm_scheduled_count),
        }

    def reset_metrics(self) -> None:
        """Reset scheduling metrics."""
        self._embedding_scheduled_count = 0
        self._llm_scheduled_count = 0
        self._batch_count = 0
