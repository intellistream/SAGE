# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Unit tests for EmbeddingExecutor.

Tests the EmbeddingExecutor class that handles embedding requests
via OpenAI-compatible HTTP API.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip(
    "sage.llm.sageLLM.control_plane.executors.embedding_executor",
    reason="sage-llm-core package not available; skip embedding executor tests.",
)

from sage.llm.sageLLM.control_plane.executors.embedding_executor import (
    EmbeddingExecutor,
    EmbeddingInstanceUnavailableError,
    EmbeddingMetrics,
    EmbeddingRequestError,
    EmbeddingResult,
    EmbeddingTimeoutError,
)


class TestEmbeddingResult:
    """Tests for EmbeddingResult dataclass."""

    def test_embedding_result_basic_creation(self):
        """Test creating a basic EmbeddingResult."""
        result = EmbeddingResult(
            request_id="test-123",
            embeddings=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            model="BAAI/bge-m3",
            usage={"prompt_tokens": 10, "total_tokens": 10},
            latency_ms=50.5,
        )

        assert result.request_id == "test-123"
        assert len(result.embeddings) == 2
        assert result.model == "BAAI/bge-m3"
        assert result.usage["total_tokens"] == 10
        assert result.latency_ms == 50.5
        assert result.success is True
        assert result.error_message is None

    def test_embedding_result_embedding_count(self):
        """Test embedding_count property."""
        result = EmbeddingResult(
            request_id="test",
            embeddings=[[0.1], [0.2], [0.3]],
            model="test-model",
            usage={},
            latency_ms=10.0,
        )

        assert result.embedding_count == 3

    def test_embedding_result_embedding_dimension(self):
        """Test embedding_dimension property."""
        result = EmbeddingResult(
            request_id="test",
            embeddings=[[0.1, 0.2, 0.3, 0.4, 0.5]],
            model="test-model",
            usage={},
            latency_ms=10.0,
        )

        assert result.embedding_dimension == 5

    def test_embedding_result_empty_embeddings(self):
        """Test embedding_dimension with empty embeddings."""
        result = EmbeddingResult(
            request_id="test",
            embeddings=[],
            model="test-model",
            usage={},
            latency_ms=10.0,
        )

        assert result.embedding_count == 0
        assert result.embedding_dimension is None

    def test_embedding_result_with_error(self):
        """Test creating an EmbeddingResult with error."""
        result = EmbeddingResult(
            request_id="test-error",
            embeddings=[],
            model="test-model",
            usage={},
            latency_ms=100.0,
            success=False,
            error_message="Connection failed",
        )

        assert result.success is False
        assert result.error_message == "Connection failed"


class TestEmbeddingMetrics:
    """Tests for EmbeddingMetrics dataclass."""

    def test_metrics_default_values(self):
        """Test default values for metrics."""
        metrics = EmbeddingMetrics()

        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.total_texts_embedded == 0
        assert metrics.total_latency_ms == 0.0
        assert metrics.retries_total == 0

    def test_metrics_avg_latency_no_requests(self):
        """Test avg_latency_ms with no successful requests."""
        metrics = EmbeddingMetrics()

        assert metrics.avg_latency_ms == 0.0

    def test_metrics_avg_latency_with_requests(self):
        """Test avg_latency_ms calculation."""
        metrics = EmbeddingMetrics(
            successful_requests=10,
            total_latency_ms=500.0,
        )

        assert metrics.avg_latency_ms == 50.0

    def test_metrics_avg_texts_per_request(self):
        """Test avg_texts_per_request calculation."""
        metrics = EmbeddingMetrics(
            successful_requests=5,
            total_texts_embedded=50,
        )

        assert metrics.avg_texts_per_request == 10.0

    def test_metrics_success_rate(self):
        """Test success_rate calculation."""
        metrics = EmbeddingMetrics(
            total_requests=100,
            successful_requests=95,
            failed_requests=5,
        )

        assert metrics.success_rate == 0.95

    def test_metrics_success_rate_no_requests(self):
        """Test success_rate with no requests."""
        metrics = EmbeddingMetrics()

        assert metrics.success_rate == 1.0


class TestEmbeddingExceptions:
    """Tests for custom exception classes."""

    def test_embedding_instance_unavailable_error(self):
        """Test EmbeddingInstanceUnavailableError."""
        error = EmbeddingInstanceUnavailableError("localhost", 8090)

        assert error.host == "localhost"
        assert error.port == 8090
        assert "localhost:8090" in str(error)
        assert "unavailable" in str(error)

    def test_embedding_instance_unavailable_error_with_message(self):
        """Test EmbeddingInstanceUnavailableError with custom message."""
        error = EmbeddingInstanceUnavailableError("localhost", 8090, "Custom error message")

        assert error.message == "Custom error message"

    def test_embedding_timeout_error(self):
        """Test EmbeddingTimeoutError."""
        error = EmbeddingTimeoutError("localhost", 8090, 30.0)

        assert error.host == "localhost"
        assert error.port == 8090
        assert error.timeout_seconds == 30.0
        assert "timed out" in str(error)

    def test_embedding_request_error(self):
        """Test EmbeddingRequestError."""
        error = EmbeddingRequestError("localhost", 8090, 500, "Internal Server Error")

        assert error.host == "localhost"
        assert error.port == 8090
        assert error.status_code == 500
        assert error.error_detail == "Internal Server Error"
        assert "500" in str(error)


class TestEmbeddingExecutor:
    """Tests for EmbeddingExecutor class."""

    @pytest.fixture
    def executor(self):
        """Create an EmbeddingExecutor instance for testing."""
        return EmbeddingExecutor(timeout=30, max_retries=2, retry_delay=0.1)

    @pytest.fixture
    def mock_openai_response(self):
        """Create a mock OpenAI-compatible embedding response."""
        return {
            "object": "list",
            "data": [
                {"object": "embedding", "embedding": [0.1, 0.2, 0.3], "index": 0},
                {"object": "embedding", "embedding": [0.4, 0.5, 0.6], "index": 1},
            ],
            "model": "BAAI/bge-m3",
            "usage": {"prompt_tokens": 10, "total_tokens": 10},
        }

    def test_executor_initialization(self, executor):
        """Test executor initialization."""
        assert executor.max_retries == 2
        assert executor.retry_delay == 0.1
        assert executor.http_session is None
        assert executor._initialized is False

    @pytest.mark.asyncio
    async def test_executor_initialize(self, executor):
        """Test executor initialize method."""
        await executor.initialize()

        assert executor._initialized is True
        assert executor.http_session is not None

        await executor.cleanup()

    @pytest.mark.asyncio
    async def test_executor_cleanup(self, executor):
        """Test executor cleanup method."""
        await executor.initialize()
        await executor.cleanup()

        assert executor._initialized is False
        assert executor.http_session is None

    @pytest.mark.asyncio
    async def test_executor_context_manager(self):
        """Test executor async context manager."""
        async with EmbeddingExecutor(timeout=30) as executor:
            assert executor._initialized is True

        assert executor._initialized is False

    @pytest.mark.asyncio
    async def test_execute_embedding_success(self, executor, mock_openai_response):
        """Test successful embedding execution."""
        await executor.initialize()

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_openai_response)

        with patch.object(
            executor.http_session,
            "post",
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock()
            ),
        ):
            result = await executor.execute_embedding(
                texts=["Hello", "World"],
                model="BAAI/bge-m3",
                host="localhost",
                port=8090,
            )

            assert result.success is True
            assert len(result.embeddings) == 2
            assert result.model == "BAAI/bge-m3"
            assert result.usage["total_tokens"] == 10
            assert executor.metrics.successful_requests == 1
            assert executor.metrics.total_texts_embedded == 2

        await executor.cleanup()

    @pytest.mark.asyncio
    async def test_execute_embedding_error_response(self, executor):
        """Test embedding execution with error response."""
        await executor.initialize()

        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")

        # Create a proper async context manager mock
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        with patch.object(executor.http_session, "post", return_value=mock_cm):
            with pytest.raises(EmbeddingRequestError) as exc_info:
                await executor.execute_embedding(
                    texts=["Hello"],
                    model="BAAI/bge-m3",
                    host="localhost",
                    port=8090,
                )

            assert exc_info.value.status_code == 500
            assert executor.metrics.failed_requests == 1

        await executor.cleanup()

    @pytest.mark.asyncio
    async def test_execute_embedding_with_retry(self, executor, mock_openai_response):
        """Test embedding execution with retry on failure."""
        await executor.initialize()

        mock_response_success = AsyncMock()
        mock_response_success.status = 200
        mock_response_success.json = AsyncMock(return_value=mock_openai_response)

        call_count = 0

        def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError()
            # Return a proper async context manager for success case
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_response_success)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            return mock_cm

        with patch.object(executor.http_session, "post", side_effect=mock_post):
            result = await executor.execute_embedding(
                texts=["Hello"],
                model="BAAI/bge-m3",
                host="localhost",
                port=8090,
            )

            assert result.success is True
            assert executor.metrics.retries_total == 1

        await executor.cleanup()

    @pytest.mark.asyncio
    async def test_execute_embedding_all_retries_exhausted(self, executor):
        """Test embedding execution when all retries are exhausted."""
        await executor.initialize()

        with patch.object(executor.http_session, "post", side_effect=TimeoutError()):
            with pytest.raises(EmbeddingTimeoutError):
                await executor.execute_embedding(
                    texts=["Hello"],
                    model="BAAI/bge-m3",
                    host="localhost",
                    port=8090,
                )

            # Should have retried max_retries times
            assert executor.metrics.retries_total == executor.max_retries

        await executor.cleanup()

    @pytest.mark.asyncio
    async def test_execute_embedding_batch_small_input(self, executor, mock_openai_response):
        """Test batch embedding with small input (no actual batching needed)."""
        await executor.initialize()

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_openai_response)

        with patch.object(
            executor.http_session,
            "post",
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock()
            ),
        ):
            result = await executor.execute_embedding_batch(
                texts=["Hello", "World"],
                model="BAAI/bge-m3",
                host="localhost",
                port=8090,
                batch_size=32,
            )

            assert result.success is True
            assert len(result.embeddings) == 2

        await executor.cleanup()

    @pytest.mark.asyncio
    async def test_execute_embedding_batch_large_input(self, executor):
        """Test batch embedding with large input (actual batching)."""
        await executor.initialize()

        def create_mock_response(num_embeddings):
            return {
                "object": "list",
                "data": [
                    {"object": "embedding", "embedding": [0.1 * i], "index": i}
                    for i in range(num_embeddings)
                ],
                "model": "BAAI/bge-m3",
                "usage": {"prompt_tokens": num_embeddings, "total_tokens": num_embeddings},
            }

        call_count = 0
        batch_sizes = []

        def mock_post(*args, **kwargs):
            nonlocal call_count, batch_sizes
            call_count += 1
            json_data = kwargs.get("json", {})
            input_texts = json_data.get("input", [])
            batch_sizes.append(len(input_texts))

            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=create_mock_response(len(input_texts)))

            # Return a proper async context manager
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            return mock_cm

        with patch.object(executor.http_session, "post", side_effect=mock_post):
            texts = [f"text_{i}" for i in range(100)]
            result = await executor.execute_embedding_batch(
                texts=texts,
                model="BAAI/bge-m3",
                host="localhost",
                port=8090,
                batch_size=32,
            )

            assert result.success is True
            assert len(result.embeddings) == 100
            assert call_count == 4  # 100 texts / 32 batch_size = 4 batches (32+32+32+4)
            assert batch_sizes == [32, 32, 32, 4]
            assert result.metadata["batch_count"] == 4

        await executor.cleanup()

    @pytest.mark.asyncio
    async def test_health_check_success(self, executor):
        """Test successful health check."""
        await executor.initialize()

        mock_response = AsyncMock()
        mock_response.status = 200

        with patch.object(
            executor.http_session,
            "get",
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock()
            ),
        ):
            is_healthy = await executor.health_check("localhost", 8090)

            assert is_healthy is True

        await executor.cleanup()

    @pytest.mark.asyncio
    async def test_health_check_failure(self, executor):
        """Test failed health check."""
        await executor.initialize()

        with patch.object(executor.http_session, "get", side_effect=TimeoutError()):
            is_healthy = await executor.health_check("localhost", 8090)

            assert is_healthy is False

        await executor.cleanup()

    def test_parse_embeddings_response(self, executor):
        """Test parsing OpenAI-compatible response."""
        response_data = {
            "object": "list",
            "data": [
                {"object": "embedding", "embedding": [0.1, 0.2], "index": 1},
                {"object": "embedding", "embedding": [0.3, 0.4], "index": 0},
            ],
            "model": "test",
            "usage": {},
        }

        embeddings = executor._parse_embeddings_response(response_data)

        # Should be sorted by index
        assert embeddings == [[0.3, 0.4], [0.1, 0.2]]

    def test_reset_metrics(self, executor):
        """Test resetting metrics."""
        executor.metrics.total_requests = 100
        executor.metrics.successful_requests = 95
        executor.metrics.failed_requests = 5

        executor.reset_metrics()

        assert executor.metrics.total_requests == 0
        assert executor.metrics.successful_requests == 0
        assert executor.metrics.failed_requests == 0

    def test_get_metrics(self, executor):
        """Test getting metrics."""
        executor.metrics.total_requests = 50

        metrics = executor.get_metrics()

        assert metrics.total_requests == 50
        assert metrics is executor.metrics


class TestEmbeddingExecutorIntegration:
    """Integration-style tests for EmbeddingExecutor (using mocks)."""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling multiple concurrent embedding requests."""
        executor = EmbeddingExecutor(timeout=30, max_retries=1, retry_delay=0.01)
        await executor.initialize()

        mock_response_data = {
            "object": "list",
            "data": [{"object": "embedding", "embedding": [0.1], "index": 0}],
            "model": "test",
            "usage": {"prompt_tokens": 1, "total_tokens": 1},
        }

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)

        with patch.object(
            executor.http_session,
            "post",
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock()
            ),
        ):
            # Execute 10 concurrent requests
            tasks = [
                executor.execute_embedding(
                    texts=["text"],
                    model="test",
                    host="localhost",
                    port=8090,
                    request_id=f"req-{i}",
                )
                for i in range(10)
            ]

            results = await asyncio.gather(*tasks)

            assert len(results) == 10
            assert all(r.success for r in results)
            assert executor.metrics.total_requests == 10
            assert executor.metrics.successful_requests == 10

        await executor.cleanup()
