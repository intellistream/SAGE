# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Embedding executor for executing embedding requests on OpenAI-compatible endpoints.

This module provides the EmbeddingExecutor class that handles embedding requests
by calling OpenAI-compatible /v1/embeddings endpoints. It supports batch processing,
error handling with retry logic, and performance metrics collection.

Supported backends:
- OpenAI-compatible embedding servers (e.g., embedding_server.py in sage_embedding)
- vLLM instances with embedding support
- TEI (Text Embeddings Inference) servers

Example:
    >>> executor = EmbeddingExecutor(timeout=60, max_retries=3)
    >>> await executor.initialize()
    >>> result = await executor.execute_embedding(
    ...     texts=["Hello world", "How are you?"],
    ...     model="BAAI/bge-m3",
    ...     host="localhost",
    ...     port=8090,
    ... )
    >>> print(result.embeddings)  # List of embedding vectors
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result of an embedding request.

    This dataclass contains the output of an embedding operation,
    including the embedding vectors, model information, usage statistics,
    and performance metrics.

    Attributes:
        request_id: Unique identifier for this embedding request.
        embeddings: List of embedding vectors, where each vector is a list of floats.
            The length of the outer list matches the number of input texts.
        model: Name of the model used for embedding.
        usage: Token usage statistics from the embedding server.
            Typically contains 'prompt_tokens' and 'total_tokens'.
        latency_ms: Total time taken for the embedding request in milliseconds.
        created_at: Timestamp when the result was created.
        success: Whether the embedding request succeeded.
        error_message: Error message if the request failed, None otherwise.
        metadata: Additional metadata from the embedding response.

    Example:
        >>> result = EmbeddingResult(
        ...     request_id="emb-123",
        ...     embeddings=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
        ...     model="BAAI/bge-m3",
        ...     usage={"prompt_tokens": 10, "total_tokens": 10},
        ...     latency_ms=50.5,
        ... )
        >>> len(result.embeddings)
        2
    """

    request_id: str
    embeddings: list[list[float]]
    model: str
    usage: dict[str, int]
    latency_ms: float
    created_at: datetime = field(default_factory=datetime.now)
    success: bool = True
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def embedding_count(self) -> int:
        """Get the number of embeddings in the result."""
        return len(self.embeddings)

    @property
    def embedding_dimension(self) -> int | None:
        """Get the dimension of the embedding vectors.

        Returns:
            The dimension of the first embedding vector, or None if no embeddings.
        """
        if self.embeddings and len(self.embeddings) > 0:
            return len(self.embeddings[0])
        return None


class EmbeddingExecutorError(Exception):
    """Base exception for EmbeddingExecutor errors."""

    pass


class EmbeddingInstanceUnavailableError(EmbeddingExecutorError):
    """Raised when the embedding instance is unavailable or unhealthy."""

    def __init__(self, host: str, port: int, message: str | None = None):
        self.host = host
        self.port = port
        self.message = message or f"Embedding instance at {host}:{port} is unavailable"
        super().__init__(self.message)


class EmbeddingTimeoutError(EmbeddingExecutorError):
    """Raised when an embedding request times out."""

    def __init__(self, host: str, port: int, timeout_seconds: float):
        self.host = host
        self.port = port
        self.timeout_seconds = timeout_seconds
        super().__init__(f"Embedding request to {host}:{port} timed out after {timeout_seconds}s")


class EmbeddingRequestError(EmbeddingExecutorError):
    """Raised when an embedding request fails with an error response."""

    def __init__(self, host: str, port: int, status_code: int, error_detail: str):
        self.host = host
        self.port = port
        self.status_code = status_code
        self.error_detail = error_detail
        super().__init__(
            f"Embedding request to {host}:{port} failed with status {status_code}: {error_detail}"
        )


@dataclass
class EmbeddingMetrics:
    """Performance metrics for embedding operations.

    Attributes:
        total_requests: Total number of embedding requests made.
        successful_requests: Number of successful requests.
        failed_requests: Number of failed requests.
        total_texts_embedded: Total number of texts embedded across all requests.
        total_latency_ms: Cumulative latency across all requests.
        avg_latency_ms: Average latency per request.
        avg_texts_per_request: Average number of texts per request.
        retries_total: Total number of retry attempts.
    """

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_texts_embedded: int = 0
    total_latency_ms: float = 0.0
    retries_total: int = 0

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency per request."""
        if self.successful_requests == 0:
            return 0.0
        return self.total_latency_ms / self.successful_requests

    @property
    def avg_texts_per_request(self) -> float:
        """Calculate average number of texts per request."""
        if self.successful_requests == 0:
            return 0.0
        return self.total_texts_embedded / self.successful_requests

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0 to 1.0)."""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests


class EmbeddingExecutor:
    """Executor for embedding requests via OpenAI-compatible HTTP API.

    This class handles the execution of embedding requests by calling
    OpenAI-compatible /v1/embeddings endpoints. It provides:

    - Batch processing of multiple texts
    - Configurable timeout and retry logic
    - Performance metrics collection
    - Health checking of embedding instances

    The executor is designed to work with various embedding backends:
    - Custom embedding servers (embedding_server.py)
    - vLLM instances with embedding capabilities
    - TEI (Text Embeddings Inference) servers
    - Any OpenAI-compatible embedding API

    Attributes:
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retry attempts for failed requests.
        retry_delay: Initial delay between retries in seconds (uses exponential backoff).
        metrics: Performance metrics for this executor.

    Example:
        >>> executor = EmbeddingExecutor(timeout=60, max_retries=3)
        >>> await executor.initialize()
        >>>
        >>> # Execute a single embedding request
        >>> result = await executor.execute_embedding(
        ...     texts=["Hello world"],
        ...     model="BAAI/bge-m3",
        ...     host="localhost",
        ...     port=8090,
        ... )
        >>>
        >>> # Execute with batching
        >>> result = await executor.execute_embedding_batch(
        ...     texts=["text1", "text2", ..., "text100"],
        ...     model="BAAI/bge-m3",
        ...     host="localhost",
        ...     port=8090,
        ...     batch_size=32,
        ... )
        >>>
        >>> await executor.cleanup()
    """

    def __init__(
        self,
        timeout: int = 300,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """Initialize the EmbeddingExecutor.

        Args:
            timeout: Request timeout in seconds. Default is 300 (5 minutes).
            max_retries: Maximum number of retry attempts. Default is 3.
            retry_delay: Initial delay between retries in seconds. Default is 1.0.
                Uses exponential backoff: delay * (2 ** retry_number).
        """
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.http_session: aiohttp.ClientSession | None = None
        self.metrics = EmbeddingMetrics()
        self._initialized = False

        logger.info(
            "EmbeddingExecutor created with timeout=%ds, max_retries=%d",
            timeout,
            max_retries,
        )

    async def initialize(self) -> None:
        """Initialize the HTTP session.

        Must be called before executing any embedding requests.
        Safe to call multiple times - will only initialize once.
        """
        if not self._initialized:
            self.http_session = aiohttp.ClientSession(timeout=self.timeout)
            self._initialized = True
            logger.info("EmbeddingExecutor HTTP session initialized")

    async def cleanup(self) -> None:
        """Cleanup resources and close HTTP session.

        Should be called when the executor is no longer needed.
        Safe to call multiple times.
        """
        if self.http_session:
            await self.http_session.close()
            self.http_session = None
            self._initialized = False
            logger.info("EmbeddingExecutor HTTP session closed")

    async def execute_embedding(
        self,
        texts: list[str],
        model: str,
        host: str,
        port: int,
        request_id: str | None = None,
        encoding_format: str = "float",
    ) -> EmbeddingResult:
        """Execute an embedding request on the specified endpoint.

        Args:
            texts: List of texts to embed.
            model: Name of the embedding model to use.
            host: Hostname of the embedding server.
            port: Port of the embedding server.
            request_id: Optional unique identifier for the request.
                If not provided, a UUID will be generated.
            encoding_format: Encoding format for embeddings. Default is "float".

        Returns:
            EmbeddingResult containing the embedding vectors and metadata.

        Raises:
            EmbeddingInstanceUnavailableError: If the instance is unavailable.
            EmbeddingTimeoutError: If the request times out after all retries.
            EmbeddingRequestError: If the server returns an error response.
            EmbeddingExecutorError: For other execution errors.

        Example:
            >>> result = await executor.execute_embedding(
            ...     texts=["Hello", "World"],
            ...     model="BAAI/bge-m3",
            ...     host="localhost",
            ...     port=8090,
            ... )
            >>> print(len(result.embeddings))  # 2
        """
        if not self._initialized:
            await self.initialize()

        if not self.http_session:
            raise EmbeddingExecutorError("HTTP session not initialized")

        request_id = request_id or str(uuid.uuid4())
        self.metrics.total_requests += 1

        url = f"http://{host}:{port}/v1/embeddings"
        payload = {
            "input": texts,
            "model": model,
            "encoding_format": encoding_format,
        }

        logger.info(
            "Executing embedding request %s: %d texts on %s:%d (model=%s)",
            request_id,
            len(texts),
            host,
            port,
            model,
        )

        start_time = time.perf_counter()
        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                result = await self._execute_http_request(
                    url=url,
                    payload=payload,
                    request_id=request_id,
                    host=host,
                    port=port,
                    model=model,
                    texts=texts,
                    start_time=start_time,
                )
                return result

            except (TimeoutError, aiohttp.ClientError) as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2**attempt)
                    self.metrics.retries_total += 1
                    logger.warning(
                        "Embedding request %s failed (attempt %d/%d), retrying in %.1fs: %s",
                        request_id,
                        attempt + 1,
                        self.max_retries + 1,
                        delay,
                        str(e),
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Embedding request %s failed after %d attempts: %s",
                        request_id,
                        self.max_retries + 1,
                        str(e),
                    )

            except EmbeddingRequestError:
                # Server returned an error response (4xx, 5xx) - don't retry
                self.metrics.failed_requests += 1
                raise

        # All retries exhausted
        self.metrics.failed_requests += 1

        if isinstance(last_exception, TimeoutError):
            raise EmbeddingTimeoutError(host, port, self.timeout.total or 300)
        elif isinstance(last_exception, aiohttp.ClientConnectorError):
            raise EmbeddingInstanceUnavailableError(host, port, str(last_exception))
        else:
            raise EmbeddingExecutorError(
                f"Embedding request failed after {self.max_retries + 1} attempts: {last_exception}"
            )

    async def _execute_http_request(
        self,
        url: str,
        payload: dict[str, Any],
        request_id: str,
        host: str,
        port: int,
        model: str,
        texts: list[str],
        start_time: float,
    ) -> EmbeddingResult:
        """Execute the actual HTTP request to the embedding endpoint.

        Args:
            url: Full URL of the embedding endpoint.
            payload: Request payload.
            request_id: Unique request identifier.
            host: Server hostname.
            port: Server port.
            model: Model name.
            texts: List of texts being embedded.
            start_time: Request start timestamp (perf_counter).

        Returns:
            EmbeddingResult with the embedding vectors.

        Raises:
            aiohttp.ClientError: On connection errors.
            asyncio.TimeoutError: On timeout.
            EmbeddingRequestError: On error response from server.
        """
        if not self.http_session:
            raise EmbeddingExecutorError("HTTP session not initialized")

        async with self.http_session.post(url, json=payload) as response:
            latency_ms = (time.perf_counter() - start_time) * 1000

            if response.status == 200:
                result_data = await response.json()
                embeddings = self._parse_embeddings_response(result_data)
                usage = result_data.get("usage", {"prompt_tokens": 0, "total_tokens": 0})
                response_model = result_data.get("model", model)

                # Update metrics
                self.metrics.successful_requests += 1
                self.metrics.total_texts_embedded += len(texts)
                self.metrics.total_latency_ms += latency_ms

                logger.info(
                    "Embedding request %s completed in %.2fms (%d texts, %d tokens)",
                    request_id,
                    latency_ms,
                    len(texts),
                    usage.get("total_tokens", 0),
                )

                return EmbeddingResult(
                    request_id=request_id,
                    embeddings=embeddings,
                    model=response_model,
                    usage=usage,
                    latency_ms=latency_ms,
                    success=True,
                    metadata={
                        "host": host,
                        "port": port,
                        "text_count": len(texts),
                    },
                )
            else:
                error_text = await response.text()
                logger.error(
                    "Embedding request %s failed with status %d: %s",
                    request_id,
                    response.status,
                    error_text,
                )
                raise EmbeddingRequestError(host, port, response.status, error_text)

    def _parse_embeddings_response(self, response_data: dict[str, Any]) -> list[list[float]]:
        """Parse embeddings from OpenAI-compatible response format.

        The OpenAI API returns embeddings in the format:
        {
            "object": "list",
            "data": [
                {"object": "embedding", "embedding": [...], "index": 0},
                {"object": "embedding", "embedding": [...], "index": 1},
                ...
            ],
            "model": "...",
            "usage": {...}
        }

        Args:
            response_data: Response data from the embedding API.

        Returns:
            List of embedding vectors, ordered by index.
        """
        data = response_data.get("data", [])

        # Sort by index to ensure correct ordering
        sorted_data = sorted(data, key=lambda x: x.get("index", 0))

        embeddings = [item.get("embedding", []) for item in sorted_data]
        return embeddings

    async def execute_embedding_batch(
        self,
        texts: list[str],
        model: str,
        host: str,
        port: int,
        batch_size: int = 32,
        request_id_prefix: str | None = None,
    ) -> EmbeddingResult:
        """Execute embedding with automatic batching for large text lists.

        For large numbers of texts, this method splits them into batches
        and executes them sequentially to avoid overwhelming the server.
        Results are combined into a single EmbeddingResult.

        Args:
            texts: List of texts to embed.
            model: Name of the embedding model to use.
            host: Hostname of the embedding server.
            port: Port of the embedding server.
            batch_size: Maximum number of texts per batch. Default is 32.
            request_id_prefix: Optional prefix for batch request IDs.

        Returns:
            EmbeddingResult containing all embedding vectors in order.

        Raises:
            Same exceptions as execute_embedding.

        Example:
            >>> # Embed 1000 texts in batches of 32
            >>> result = await executor.execute_embedding_batch(
            ...     texts=large_text_list,
            ...     model="BAAI/bge-m3",
            ...     host="localhost",
            ...     port=8090,
            ...     batch_size=32,
            ... )
        """
        if len(texts) <= batch_size:
            # No need to batch, execute directly
            return await self.execute_embedding(
                texts=texts,
                model=model,
                host=host,
                port=port,
                request_id=request_id_prefix,
            )

        request_id_prefix = request_id_prefix or str(uuid.uuid4())[:8]
        all_embeddings: list[list[float]] = []
        total_usage: dict[str, int] = {"prompt_tokens": 0, "total_tokens": 0}
        start_time = time.perf_counter()

        num_batches = (len(texts) + batch_size - 1) // batch_size
        logger.info(
            "Executing batch embedding: %d texts in %d batches (batch_size=%d)",
            len(texts),
            num_batches,
            batch_size,
        )

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_num = i // batch_size + 1
            batch_request_id = f"{request_id_prefix}-batch{batch_num}"

            result = await self.execute_embedding(
                texts=batch_texts,
                model=model,
                host=host,
                port=port,
                request_id=batch_request_id,
            )

            all_embeddings.extend(result.embeddings)
            total_usage["prompt_tokens"] += result.usage.get("prompt_tokens", 0)
            total_usage["total_tokens"] += result.usage.get("total_tokens", 0)

        total_latency_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "Batch embedding completed: %d texts in %.2fms (%.2f texts/s)",
            len(texts),
            total_latency_ms,
            len(texts) / (total_latency_ms / 1000) if total_latency_ms > 0 else 0,
        )

        return EmbeddingResult(
            request_id=request_id_prefix,
            embeddings=all_embeddings,
            model=model,
            usage=total_usage,
            latency_ms=total_latency_ms,
            success=True,
            metadata={
                "host": host,
                "port": port,
                "text_count": len(texts),
                "batch_count": num_batches,
                "batch_size": batch_size,
            },
        )

    async def health_check(self, host: str, port: int) -> bool:
        """Check health of an embedding endpoint.

        Attempts to reach the health endpoint or root endpoint of the server.
        Updates metrics based on the result.

        Args:
            host: Hostname of the embedding server.
            port: Port of the embedding server.

        Returns:
            True if the endpoint is healthy, False otherwise.
        """
        if not self._initialized:
            await self.initialize()

        if not self.http_session:
            return False

        # Try multiple health endpoints (different servers may use different paths)
        health_endpoints = [
            f"http://{host}:{port}/health",
            f"http://{host}:{port}/",
            f"http://{host}:{port}/v1/models",
        ]

        timeout = aiohttp.ClientTimeout(total=5)

        for url in health_endpoints:
            try:
                async with self.http_session.get(url, timeout=timeout) as response:
                    if response.status == 200:
                        logger.debug(
                            "Health check passed for %s:%d (endpoint: %s)", host, port, url
                        )
                        return True
            except (TimeoutError, aiohttp.ClientError):
                continue

        logger.warning("Health check failed for %s:%d", host, port)
        return False

    def get_metrics(self) -> EmbeddingMetrics:
        """Get current performance metrics.

        Returns:
            EmbeddingMetrics with current statistics.
        """
        return self.metrics

    def reset_metrics(self) -> None:
        """Reset all performance metrics to zero."""
        self.metrics = EmbeddingMetrics()
        logger.info("EmbeddingExecutor metrics reset")

    async def __aenter__(self) -> EmbeddingExecutor:
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.cleanup()
