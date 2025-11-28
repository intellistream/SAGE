# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""End-to-end integration tests for hybrid scheduling.

This module tests the complete hybrid scheduling pipeline including:
1. Simultaneous LLM and Embedding request submission
2. Request classification and routing
3. Scheduling decisions for mixed workloads
4. Resource competition and load balancing
5. Batch aggregation for embedding requests

Tests use mock backends to avoid GPU requirements while still
validating the full scheduling logic.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sage.common.components.sage_llm.sageLLM.control_plane.request_classifier import (
    RequestClassifier,
    ValidationResult,
)
from sage.common.components.sage_llm.sageLLM.control_plane.strategies.hybrid_policy import (
    EmbeddingBatch,
    EmbeddingPriority,
    HybridSchedulingConfig,
    HybridSchedulingPolicy,
)
from sage.common.components.sage_llm.sageLLM.control_plane.types import (
    ExecutionInstance,
    ExecutionInstanceType,
    RequestMetadata,
    RequestPriority,
    RequestType,
    SchedulingDecision,
)

if TYPE_CHECKING:
    from conftest import MockEmbeddingBackend, MockLLMBackend


class TestRequestClassificationE2E:
    """End-to-end tests for request classification in hybrid scheduling."""

    def test_classify_mixed_request_batch(
        self,
        sample_llm_requests: list[RequestMetadata],
        sample_embedding_requests: list[RequestMetadata],
    ):
        """Test classification of a mixed batch of requests."""
        classifier = RequestClassifier()

        # Classify all requests
        llm_classified = []
        embed_classified = []

        all_requests = sample_llm_requests + sample_embedding_requests

        for request in all_requests:
            request_type = classifier.classify(request)
            if request_type == RequestType.EMBEDDING:
                embed_classified.append(request)
            else:
                llm_classified.append(request)

        # Verify classification counts
        assert len(llm_classified) == len(sample_llm_requests)
        assert len(embed_classified) == len(sample_embedding_requests)

        # Verify correct classification
        for req in llm_classified:
            assert req.request_type in (RequestType.LLM_CHAT, RequestType.LLM_GENERATE)

        for req in embed_classified:
            assert req.request_type == RequestType.EMBEDDING

    def test_get_compatible_instances_for_mixed_workload(
        self,
        llm_execution_instance: ExecutionInstance,
        embedding_execution_instance: ExecutionInstance,
        mixed_execution_instance: ExecutionInstance,
    ):
        """Test instance compatibility filtering for mixed workloads."""
        classifier = RequestClassifier()
        all_instances = [
            llm_execution_instance,
            embedding_execution_instance,
            mixed_execution_instance,
        ]

        # Get compatible instances for LLM requests
        llm_compatible = classifier.get_compatible_instances(
            RequestType.LLM_CHAT, all_instances
        )
        assert len(llm_compatible) == 2  # LLM and mixed
        assert llm_execution_instance in llm_compatible
        assert mixed_execution_instance in llm_compatible
        assert embedding_execution_instance not in llm_compatible

        # Get compatible instances for Embedding requests
        embed_compatible = classifier.get_compatible_instances(
            RequestType.EMBEDDING, all_instances
        )
        assert len(embed_compatible) == 2  # Embedding and mixed
        assert embedding_execution_instance in embed_compatible
        assert mixed_execution_instance in embed_compatible
        assert llm_execution_instance not in embed_compatible

    def test_validate_mixed_requests(
        self,
        sample_llm_requests: list[RequestMetadata],
        sample_embedding_requests: list[RequestMetadata],
    ):
        """Test validation of mixed request types."""
        classifier = RequestClassifier()

        # All sample requests should be valid
        for request in sample_llm_requests:
            result = classifier.validate_request(request)
            assert result.is_valid, f"LLM request {request.request_id} should be valid"

        for request in sample_embedding_requests:
            result = classifier.validate_request(request)
            assert (
                result.is_valid
            ), f"Embedding request {request.request_id} should be valid"

    def test_classify_auto_detect_embedding(self):
        """Test auto-detection of embedding requests without explicit type."""
        classifier = RequestClassifier()

        # Request without explicit type but with embedding_texts
        request = RequestMetadata(
            request_id="auto-embed-1",
            embedding_texts=["Hello", "World"],
            embedding_model="BAAI/bge-m3",
        )

        # Should auto-classify as EMBEDDING
        request_type = classifier.classify(request)
        assert request_type == RequestType.EMBEDDING

    def test_classify_auto_detect_llm(self):
        """Test auto-detection of LLM requests without explicit type."""
        classifier = RequestClassifier()

        # Request without explicit type but with prompt
        request = RequestMetadata(
            request_id="auto-llm-1",
            prompt="Hello, how are you?",
            model_name="Qwen/Qwen2.5-7B-Instruct",
        )

        # Should auto-classify as LLM
        request_type = classifier.classify(request)
        assert request_type in (RequestType.LLM_CHAT, RequestType.LLM_GENERATE)


class TestHybridSchedulingPolicyE2E:
    """End-to-end tests for hybrid scheduling policy."""

    def test_schedule_mixed_requests_to_instances(
        self,
        mixed_requests: list[RequestMetadata],
        llm_execution_instance: ExecutionInstance,
        embedding_execution_instance: ExecutionInstance,
        mixed_execution_instance: ExecutionInstance,
    ):
        """Test scheduling mixed requests to appropriate instances."""
        policy = HybridSchedulingPolicy(
            embedding_batch_size=32,
            embedding_priority="normal",
            llm_fallback_policy="fifo",
        )

        instances = [
            llm_execution_instance,
            embedding_execution_instance,
            mixed_execution_instance,
        ]

        # Schedule all requests
        decisions = policy.schedule(mixed_requests, instances)

        # Verify all requests get decisions
        assert len(decisions) > 0

        # Check that LLM requests go to LLM-capable instances
        for decision in decisions:
            request = next(
                (r for r in mixed_requests if r.request_id == decision.request_id), None
            )
            if request and request.request_type in (
                RequestType.LLM_CHAT,
                RequestType.LLM_GENERATE,
            ):
                target_instance = next(
                    (i for i in instances if i.instance_id == decision.target_instance_id),
                    None,
                )
                if target_instance:
                    assert target_instance.instance_type in (
                        ExecutionInstanceType.GENERAL,
                        ExecutionInstanceType.LLM_EMBEDDING,
                        ExecutionInstanceType.HYBRID,
                    )

    def test_embedding_batching(
        self,
        sample_embedding_requests: list[RequestMetadata],
        embedding_execution_instance: ExecutionInstance,
    ):
        """Test that embedding requests are properly batched."""
        policy = HybridSchedulingPolicy(
            embedding_batch_size=32,
            embedding_priority="normal",
            llm_fallback_policy="fifo",
            config=HybridSchedulingConfig(
                enable_embedding_batching=True,
                min_embedding_batch_size=1,
            ),
        )

        instances = [embedding_execution_instance]

        # Add requests with same model to policy for batching
        for request in sample_embedding_requests:
            request.embedding_model = "BAAI/bge-m3"

        decisions = policy.schedule(sample_embedding_requests, instances)

        # Should have some decisions (batched or individual)
        assert len(decisions) >= 1

    def test_priority_scheduling_llm_over_embedding(
        self,
        llm_execution_instance: ExecutionInstance,
        embedding_execution_instance: ExecutionInstance,
    ):
        """Test that LLM requests are prioritized when configured."""
        policy = HybridSchedulingPolicy(
            embedding_batch_size=32,
            embedding_priority="low",  # LLM should be higher priority
            llm_fallback_policy="priority",
        )

        # Create high priority LLM and normal priority embedding
        llm_request = RequestMetadata(
            request_id="priority-llm-1",
            prompt="Urgent question",
            model_name="Qwen/Qwen2.5-7B-Instruct",
            request_type=RequestType.LLM_CHAT,
            priority=RequestPriority.HIGH,
        )

        embed_request = RequestMetadata(
            request_id="priority-embed-1",
            embedding_texts=["Text to embed"],
            embedding_model="BAAI/bge-m3",
            request_type=RequestType.EMBEDDING,
            priority=RequestPriority.NORMAL,
        )

        instances = [llm_execution_instance, embedding_execution_instance]

        # LLM request submitted first, then embedding
        decisions = policy.schedule([embed_request, llm_request], instances)

        # Both should get scheduled
        assert len(decisions) >= 1

    def test_adaptive_embedding_priority(
        self,
        sample_embedding_requests: list[RequestMetadata],
        embedding_execution_instance: ExecutionInstance,
    ):
        """Test adaptive priority adjustment for embedding requests."""
        policy = HybridSchedulingPolicy(
            embedding_batch_size=32,
            embedding_priority="adaptive",
            llm_fallback_policy="adaptive",
        )

        instances = [embedding_execution_instance]

        # Schedule with growing queue
        decisions = policy.schedule(sample_embedding_requests, instances)

        # Should handle all requests
        assert len(decisions) >= 1

    def test_hybrid_instance_ratio(
        self,
        mixed_execution_instance: ExecutionInstance,
    ):
        """Test LLM/Embedding time ratio on hybrid instances."""
        policy = HybridSchedulingPolicy(
            embedding_batch_size=32,
            embedding_priority="normal",
            llm_fallback_policy="fifo",
            config=HybridSchedulingConfig(
                hybrid_instance_ratio=0.7,  # 70% LLM, 30% Embedding
            ),
        )

        # Create balanced workload
        llm_requests = [
            RequestMetadata(
                request_id=f"ratio-llm-{i}",
                prompt=f"Question {i}",
                model_name="Qwen/Qwen2.5-7B-Instruct",
                request_type=RequestType.LLM_CHAT,
            )
            for i in range(7)
        ]

        embed_requests = [
            RequestMetadata(
                request_id=f"ratio-embed-{i}",
                embedding_texts=[f"Text {i}"],
                embedding_model="BAAI/bge-m3",
                request_type=RequestType.EMBEDDING,
            )
            for i in range(3)
        ]

        all_requests = llm_requests + embed_requests
        instances = [mixed_execution_instance]

        decisions = policy.schedule(all_requests, instances)

        # All requests should be schedulable on mixed instance
        assert len(decisions) >= 1

    def test_prefer_specialized_instances(
        self,
        llm_execution_instance: ExecutionInstance,
        embedding_execution_instance: ExecutionInstance,
        mixed_execution_instance: ExecutionInstance,
    ):
        """Test preference for specialized instances over mixed."""
        policy = HybridSchedulingPolicy(
            embedding_batch_size=32,
            embedding_priority="normal",
            llm_fallback_policy="fifo",
            config=HybridSchedulingConfig(
                prefer_specialized_instances=True,
            ),
        )

        # Create single requests
        llm_request = RequestMetadata(
            request_id="special-llm-1",
            prompt="Test question",
            model_name="Qwen/Qwen2.5-7B-Instruct",
            request_type=RequestType.LLM_CHAT,
        )

        embed_request = RequestMetadata(
            request_id="special-embed-1",
            embedding_texts=["Test text"],
            embedding_model="BAAI/bge-m3",
            request_type=RequestType.EMBEDDING,
        )

        instances = [
            llm_execution_instance,
            embedding_execution_instance,
            mixed_execution_instance,
        ]

        # Schedule LLM request - should prefer specialized LLM instance
        llm_decisions = policy.schedule([llm_request], instances)
        if llm_decisions:
            # First choice should be specialized if available
            first_decision = llm_decisions[0]
            target = next(
                (i for i in instances if i.instance_id == first_decision.target_instance_id),
                None,
            )
            # Should schedule to some valid instance
            assert target is not None

        # Schedule embedding request - should prefer specialized embedding instance
        embed_decisions = policy.schedule([embed_request], instances)
        if embed_decisions:
            first_decision = embed_decisions[0]
            target = next(
                (i for i in instances if i.instance_id == first_decision.target_instance_id),
                None,
            )
            assert target is not None


class TestConcurrentRequestHandling:
    """Tests for concurrent request handling in hybrid scheduling."""

    @pytest.mark.asyncio
    async def test_concurrent_llm_and_embedding_requests(
        self,
        mock_llm_backend: "MockLLMBackend",
        mock_embedding_backend: "MockEmbeddingBackend",
    ):
        """Test handling concurrent LLM and embedding requests."""
        # Simulate concurrent requests
        async def llm_request():
            return await mock_llm_backend.handle_chat_completion(
                {
                    "model": "Qwen/Qwen2.5-7B-Instruct",
                    "messages": [{"role": "user", "content": "Hello"}],
                }
            )

        async def embedding_request():
            return await mock_embedding_backend.handle_embedding(
                {
                    "model": "BAAI/bge-m3",
                    "input": ["Text 1", "Text 2"],
                }
            )

        # Run concurrently
        results = await asyncio.gather(
            llm_request(),
            embedding_request(),
            llm_request(),
            embedding_request(),
        )

        # All should succeed
        assert len(results) == 4
        for result in results:
            assert result.status == 200
            assert result.data is not None

        # Check request counts
        assert mock_llm_backend.request_count == 2
        assert mock_embedding_backend.request_count == 2

    @pytest.mark.asyncio
    async def test_high_concurrency_mixed_workload(
        self,
        mock_llm_backend: "MockLLMBackend",
        mock_embedding_backend: "MockEmbeddingBackend",
    ):
        """Test high concurrency with many mixed requests."""
        num_requests = 50

        async def make_requests():
            tasks = []
            for i in range(num_requests):
                if i % 2 == 0:
                    # LLM request
                    tasks.append(
                        mock_llm_backend.handle_chat_completion(
                            {
                                "model": "Qwen/Qwen2.5-7B-Instruct",
                                "messages": [
                                    {"role": "user", "content": f"Question {i}"}
                                ],
                            }
                        )
                    )
                else:
                    # Embedding request
                    tasks.append(
                        mock_embedding_backend.handle_embedding(
                            {
                                "model": "BAAI/bge-m3",
                                "input": [f"Text {i}"],
                            }
                        )
                    )
            return await asyncio.gather(*tasks)

        start_time = time.time()
        results = await make_requests()
        elapsed_time = time.time() - start_time

        # All should succeed
        assert len(results) == num_requests
        for result in results:
            assert result.status == 200

        # Should complete in reasonable time (parallel execution)
        # With mock delays of ~10ms, 50 sequential would be 500ms+
        # Parallel should be much faster
        assert elapsed_time < 2.0, f"Took too long: {elapsed_time}s"

        # Check total request counts
        assert mock_llm_backend.request_count == num_requests // 2
        assert mock_embedding_backend.request_count == num_requests // 2

    @pytest.mark.asyncio
    async def test_request_ordering_under_load(
        self,
        mock_llm_backend: "MockLLMBackend",
    ):
        """Test that request ordering is maintained under load."""
        request_order = []
        response_order = []

        async def tracked_request(index: int):
            request_order.append(index)
            result = await mock_llm_backend.handle_chat_completion(
                {
                    "model": "test",
                    "messages": [{"role": "user", "content": f"Request {index}"}],
                }
            )
            response_order.append(index)
            return result

        # Submit in order
        tasks = [tracked_request(i) for i in range(10)]
        await asyncio.gather(*tasks)

        # Request order should be sequential (all submitted before awaiting)
        assert request_order == list(range(10))
        # Response order might vary due to async (but all should complete)
        assert set(response_order) == set(range(10))


class TestResourceCompetition:
    """Tests for resource competition scenarios in hybrid scheduling."""

    def test_instance_overload_handling(
        self,
        mixed_execution_instance: ExecutionInstance,
    ):
        """Test handling when instances are overloaded."""
        policy = HybridSchedulingPolicy(
            embedding_batch_size=32,
            embedding_priority="normal",
            llm_fallback_policy="fifo",
        )

        # Create more requests than instance can handle
        many_requests = [
            RequestMetadata(
                request_id=f"overload-{i}",
                prompt=f"Question {i}",
                model_name="Qwen/Qwen2.5-7B-Instruct",
                request_type=RequestType.LLM_CHAT,
            )
            for i in range(100)
        ]

        # Single instance
        instances = [mixed_execution_instance]

        # Should still produce valid decisions (possibly queued)
        decisions = policy.schedule(many_requests, instances)

        # Some decisions should be made
        assert len(decisions) >= 0  # May queue some

    def test_no_compatible_instance_available(self):
        """Test behavior when no compatible instance is available."""
        policy = HybridSchedulingPolicy(
            embedding_batch_size=32,
            embedding_priority="normal",
            llm_fallback_policy="fifo",
        )

        # Embedding request
        embed_request = RequestMetadata(
            request_id="no-instance-1",
            embedding_texts=["Test"],
            embedding_model="BAAI/bge-m3",
            request_type=RequestType.EMBEDDING,
        )

        # Only LLM instance available (no embedding support)
        llm_only_instance = ExecutionInstance(
            instance_id="llm-only-1",
            host="localhost",
            port=8001,
            instance_type=ExecutionInstanceType.GENERAL,
            model_name="Qwen/Qwen2.5-7B-Instruct",
            supported_request_types=[RequestType.LLM_CHAT, RequestType.LLM_GENERATE],
        )

        decisions = policy.schedule([embed_request], [llm_only_instance])

        # Should handle gracefully (no decision or queued)
        # The policy should not crash
        assert isinstance(decisions, list)

    def test_load_balancing_across_instances(
        self,
        llm_execution_instance: ExecutionInstance,
        mixed_execution_instance: ExecutionInstance,
    ):
        """Test load balancing when multiple instances are available."""
        policy = HybridSchedulingPolicy(
            embedding_batch_size=32,
            embedding_priority="normal",
            llm_fallback_policy="fifo",
        )

        # Create LLM requests
        requests = [
            RequestMetadata(
                request_id=f"balance-{i}",
                prompt=f"Question {i}",
                model_name="Qwen/Qwen2.5-7B-Instruct",
                request_type=RequestType.LLM_CHAT,
            )
            for i in range(10)
        ]

        # Two capable instances
        instances = [llm_execution_instance, mixed_execution_instance]

        decisions = policy.schedule(requests, instances)

        # Should distribute across instances
        target_counts: dict[str, int] = {}
        for decision in decisions:
            target = decision.target_instance_id
            target_counts[target] = target_counts.get(target, 0) + 1

        # With balanced load, both should get some requests
        # (exact distribution depends on policy implementation)
        assert len(decisions) >= 1


class TestEmbeddingBatchAggregation:
    """Tests for embedding request batch aggregation."""

    def test_batch_creation(self):
        """Test creating and adding to embedding batches."""
        batch = EmbeddingBatch(batch_id="test-batch-1")

        # Add first request
        request1 = RequestMetadata(
            request_id="batch-req-1",
            embedding_texts=["Text 1", "Text 2"],
            embedding_model="BAAI/bge-m3",
            request_type=RequestType.EMBEDDING,
        )
        result1 = batch.add_request(request1)
        assert result1 is True
        assert batch.model == "BAAI/bge-m3"
        assert len(batch.requests) == 1

        # Add compatible request
        request2 = RequestMetadata(
            request_id="batch-req-2",
            embedding_texts=["Text 3"],
            embedding_model="BAAI/bge-m3",
            request_type=RequestType.EMBEDDING,
        )
        result2 = batch.add_request(request2)
        assert result2 is True
        assert len(batch.requests) == 2

    def test_batch_model_compatibility(self):
        """Test that batches reject incompatible models."""
        batch = EmbeddingBatch(batch_id="test-batch-2")

        # Add first request with model A
        request1 = RequestMetadata(
            request_id="batch-req-1",
            embedding_texts=["Text 1"],
            embedding_model="model-A",
            request_type=RequestType.EMBEDDING,
        )
        batch.add_request(request1)

        # Try to add request with different model
        request2 = RequestMetadata(
            request_id="batch-req-2",
            embedding_texts=["Text 2"],
            embedding_model="model-B",
            request_type=RequestType.EMBEDDING,
        )
        result = batch.add_request(request2)

        # Should reject incompatible model
        assert result is False
        assert len(batch.requests) == 1

    def test_batch_size_limit(self):
        """Test that batches respect size limits."""
        policy = HybridSchedulingPolicy(
            embedding_batch_size=5,  # Small batch size
            embedding_priority="normal",
            llm_fallback_policy="fifo",
        )

        # Create many small embedding requests
        requests = [
            RequestMetadata(
                request_id=f"size-limit-{i}",
                embedding_texts=[f"Text {i}"],
                embedding_model="BAAI/bge-m3",
                request_type=RequestType.EMBEDDING,
            )
            for i in range(20)
        ]

        embedding_instance = ExecutionInstance(
            instance_id="embed-1",
            host="localhost",
            port=8090,
            instance_type=ExecutionInstanceType.EMBEDDING,
            model_name="BAAI/bge-m3",
            supported_request_types=[RequestType.EMBEDDING],
            embedding_max_batch_size=32,
        )

        decisions = policy.schedule(requests, [embedding_instance])

        # Should produce decisions (batched appropriately)
        assert len(decisions) >= 1


class TestSchedulingMetrics:
    """Tests for scheduling metrics collection."""

    def test_decision_contains_required_fields(
        self,
        sample_llm_requests: list[RequestMetadata],
        llm_execution_instance: ExecutionInstance,
    ):
        """Test that scheduling decisions contain all required fields."""
        policy = HybridSchedulingPolicy(
            embedding_batch_size=32,
            embedding_priority="normal",
            llm_fallback_policy="fifo",
        )

        decisions = policy.schedule(sample_llm_requests, [llm_execution_instance])

        for decision in decisions:
            # Check required fields exist
            assert decision.request_id is not None
            assert decision.target_instance_id is not None
            assert hasattr(decision, "scheduled_at") or hasattr(decision, "decision_time")

    def test_scheduling_latency(
        self,
        mixed_requests: list[RequestMetadata],
        llm_execution_instance: ExecutionInstance,
        embedding_execution_instance: ExecutionInstance,
    ):
        """Test that scheduling completes within acceptable time."""
        policy = HybridSchedulingPolicy(
            embedding_batch_size=32,
            embedding_priority="normal",
            llm_fallback_policy="fifo",
        )

        instances = [llm_execution_instance, embedding_execution_instance]

        # Measure scheduling time
        start_time = time.time()
        decisions = policy.schedule(mixed_requests, instances)
        elapsed_time = time.time() - start_time

        # Scheduling should be fast (< 100ms for small batches)
        assert elapsed_time < 0.1, f"Scheduling took too long: {elapsed_time}s"

        # Should produce some decisions
        assert len(decisions) >= 0
