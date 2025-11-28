# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Hybrid Benchmark HTTP Client Module
====================================

Provides async HTTP client for sending mixed LLM and Embedding requests
to the Control Plane and collecting response metrics.

This module handles:
- Async request sending to Control Plane
- Automatic dispatch to LLM or Embedding endpoints
- Streaming response processing for LLM TTFT/ITL metrics
- Batch embedding request handling
- Request timing and metrics recording
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..common.base_metrics import BaseRequestResult
from .config import RequestType

if TYPE_CHECKING:
    import aiohttp as aiohttp_type

    from .workload import HybridRequest

# Try to import aiohttp, provide helpful error if not available
AIOHTTP_AVAILABLE = False
try:
    import aiohttp

    AIOHTTP_AVAILABLE = True
except ImportError:
    aiohttp = None  # type: ignore[assignment]


@dataclass
class HybridRequestResult(BaseRequestResult):
    """Result of a single hybrid benchmark request (LLM or Embedding).

    Extends BaseRequestResult with fields for both LLM and Embedding metrics.

    Attributes:
        request_type: Type of request (llm_chat, llm_generate, embedding)

        # LLM-specific fields
        model_name: Target model name (for LLM)
        first_token_time: Time when first token received (epoch seconds)
        inter_token_latencies: List of inter-token latencies in ms
        output_token_count: Number of output tokens generated

        # Embedding-specific fields
        embedding_model: Embedding model name
        batch_size: Number of texts in the embedding batch
        embedding_dimensions: Dimension of the embedding vectors
        total_texts_embedded: Total number of texts successfully embedded
    """

    request_type: RequestType = RequestType.LLM_CHAT

    # LLM-specific fields
    model_name: str = ""
    first_token_time: float | None = None
    inter_token_latencies: list[float] = field(default_factory=list)
    output_token_count: int = 0

    # Embedding-specific fields
    embedding_model: str = ""
    batch_size: int = 1
    embedding_dimensions: int = 0
    total_texts_embedded: int = 0

    @property
    def is_llm_request(self) -> bool:
        """Check if this is an LLM request."""
        return self.request_type in (RequestType.LLM_CHAT, RequestType.LLM_GENERATE)

    @property
    def is_embedding_request(self) -> bool:
        """Check if this is an embedding request."""
        return self.request_type == RequestType.EMBEDDING

    @property
    def ttft_ms(self) -> float | None:
        """Time to first token in milliseconds (LLM only)."""
        if self.is_llm_request and self.send_time and self.first_token_time:
            return (self.first_token_time - self.send_time) * 1000
        return None

    @property
    def texts_per_second(self) -> float | None:
        """Texts embedded per second (Embedding only)."""
        if self.is_embedding_request and self.e2e_latency_ms:
            return self.total_texts_embedded / (self.e2e_latency_ms / 1000)
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        base = self.to_base_dict()
        base.update({
            "request_type": self.request_type.value,
        })

        if self.is_llm_request:
            base.update({
                "model_name": self.model_name,
                "first_token_time": self.first_token_time,
                "ttft_ms": self.ttft_ms,
                "inter_token_latencies": self.inter_token_latencies,
                "output_token_count": self.output_token_count,
            })
        elif self.is_embedding_request:
            base.update({
                "embedding_model": self.embedding_model,
                "batch_size": self.batch_size,
                "embedding_dimensions": self.embedding_dimensions,
                "total_texts_embedded": self.total_texts_embedded,
                "texts_per_second": self.texts_per_second,
            })

        return base


class HybridBenchmarkClient:
    """Async HTTP client for hybrid Control Plane benchmarking.

    This client sends both LLM and Embedding requests to the Control Plane's
    OpenAI-compatible API and collects detailed timing metrics.

    Endpoints:
    - LLM: /v1/chat/completions (chat) or /v1/completions (generate)
    - Embedding: /v1/embeddings
    """

    def __init__(
        self,
        control_plane_url: str,
        timeout_seconds: float = 60.0,
        enable_streaming: bool = True,
    ):
        """Initialize hybrid benchmark client.

        Args:
            control_plane_url: Base URL of the Control Plane service
            timeout_seconds: Request timeout in seconds
            enable_streaming: Whether to use streaming for LLM responses
        """
        if not AIOHTTP_AVAILABLE:
            raise RuntimeError(
                "aiohttp is required for HybridBenchmarkClient. "
                "Install it with: pip install aiohttp"
            )

        self.control_plane_url = control_plane_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.enable_streaming = enable_streaming
        self._session: aiohttp_type.ClientSession | None = None

    async def __aenter__(self) -> HybridBenchmarkClient:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def connect(self) -> None:
        """Create HTTP session."""
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)  # type: ignore[union-attr]
        self._session = aiohttp.ClientSession(timeout=timeout)  # type: ignore[union-attr]

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def health_check(self) -> bool:
        """Check if Control Plane is reachable.

        Returns:
            True if Control Plane is healthy
        """
        if not self._session:
            await self.connect()

        try:
            if self._session:
                async with self._session.get(f"{self.control_plane_url}/health") as resp:
                    return resp.status == 200
        except Exception:
            pass

        return False

    async def set_policy(self, policy: str) -> bool:
        """Set the scheduling policy on the Control Plane.

        Args:
            policy: Policy name to set

        Returns:
            True if policy was set successfully
        """
        if not self._session:
            await self.connect()

        try:
            if self._session:
                async with self._session.post(
                    f"{self.control_plane_url}/admin/set_policy",
                    json={"policy": policy},
                ) as resp:
                    return resp.status == 200
        except Exception:
            pass

        return False

    async def get_metrics(self) -> dict[str, Any]:
        """Get metrics from Control Plane.

        Returns:
            Metrics dictionary from Control Plane
        """
        if not self._session:
            await self.connect()

        try:
            if self._session:
                async with self._session.get(
                    f"{self.control_plane_url}/admin/metrics"
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception:
            pass

        return {}

    async def send_request(self, request: HybridRequest) -> HybridRequestResult:
        """Send a single request to the Control Plane.

        Automatically dispatches to LLM or Embedding endpoint based on
        request type.

        Args:
            request: HybridRequest object to send

        Returns:
            HybridRequestResult with timing metrics
        """
        if request.is_llm_request:
            return await self.send_llm_request(request)
        else:
            return await self.send_embedding_request(request)

    async def send_llm_request(self, request: HybridRequest) -> HybridRequestResult:
        """Send an LLM request to the Control Plane.

        Args:
            request: HybridRequest object (must be LLM type)

        Returns:
            HybridRequestResult with LLM timing metrics
        """
        result = HybridRequestResult(
            request_id=request.request_id,
            request_type=request.request_type,
            priority=request.priority,
            slo_deadline_ms=request.slo_deadline_ms,
            model_name=request.model_name,
            metadata=request.metadata,
        )

        if not self._session:
            await self.connect()

        # Determine endpoint
        if request.request_type == RequestType.LLM_CHAT:
            endpoint = f"{self.control_plane_url}/v1/chat/completions"
            payload = {
                "model": request.model_name,
                "messages": [{"role": "user", "content": request.prompt}],
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "stream": self.enable_streaming and request.stream,
            }
        else:
            # LLM_GENERATE
            endpoint = f"{self.control_plane_url}/v1/completions"
            payload = {
                "model": request.model_name,
                "prompt": request.prompt,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "stream": self.enable_streaming and request.stream,
            }

        headers = {
            "Content-Type": "application/json",
            "X-Request-ID": request.request_id,
            "X-Request-Priority": request.priority,
            "X-SLO-Deadline-Ms": str(request.slo_deadline_ms),
        }

        result.send_time = time.time()

        try:
            if not self._session:
                raise RuntimeError("Session not initialized")

            if self.enable_streaming and request.stream:
                result = await self._send_streaming_llm_request(
                    endpoint, payload, headers, result
                )
            else:
                result = await self._send_non_streaming_llm_request(
                    endpoint, payload, headers, result
                )

        except asyncio.TimeoutError:
            result.completion_time = time.time()
            result.success = False
            result.error = "Request timed out"

        except Exception as e:
            result.completion_time = time.time()
            result.success = False
            result.error = str(e)

        return result

    async def _send_streaming_llm_request(
        self,
        endpoint: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        result: HybridRequestResult,
    ) -> HybridRequestResult:
        """Send streaming LLM request and process response.

        Args:
            endpoint: API endpoint URL
            payload: Request payload
            headers: Request headers
            result: Result object to populate

        Returns:
            Updated HybridRequestResult
        """
        if not self._session:
            raise RuntimeError("Session not initialized")

        async with self._session.post(
            endpoint, json=payload, headers=headers
        ) as response:
            result.status_code = response.status

            if response.status != 200:
                result.success = False
                result.error = f"HTTP {response.status}: {await response.text()}"
                result.completion_time = time.time()
                return result

            # Process streaming response
            token_count = 0
            last_token_time = None

            async for line in response.content:
                line = line.decode("utf-8").strip()
                if not line or not line.startswith("data: "):
                    continue

                data_str = line[6:]  # Remove "data: " prefix
                if data_str == "[DONE]":
                    break

                try:
                    data = json.loads(data_str)
                    current_time = time.time()

                    # Record first token time
                    if result.first_token_time is None:
                        result.first_token_time = current_time

                    # Record inter-token latency
                    if last_token_time is not None:
                        itl = (current_time - last_token_time) * 1000
                        result.inter_token_latencies.append(itl)

                    last_token_time = current_time
                    token_count += 1

                except json.JSONDecodeError:
                    continue

            result.output_token_count = token_count
            result.completion_time = time.time()
            result.success = True

        return result

    async def _send_non_streaming_llm_request(
        self,
        endpoint: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        result: HybridRequestResult,
    ) -> HybridRequestResult:
        """Send non-streaming LLM request.

        Args:
            endpoint: API endpoint URL
            payload: Request payload
            headers: Request headers
            result: Result object to populate

        Returns:
            Updated HybridRequestResult
        """
        if not self._session:
            raise RuntimeError("Session not initialized")

        async with self._session.post(
            endpoint, json=payload, headers=headers
        ) as response:
            result.status_code = response.status
            result.completion_time = time.time()

            if response.status != 200:
                result.success = False
                result.error = f"HTTP {response.status}: {await response.text()}"
                return result

            data = await response.json()

            # Extract token count from response
            if "choices" in data and data["choices"]:
                choice = data["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    # Rough estimate: split by spaces
                    content = choice["message"]["content"]
                    result.output_token_count = len(content.split())
                elif "text" in choice:
                    result.output_token_count = len(choice["text"].split())

            # Usage info if available
            if "usage" in data:
                result.output_token_count = data["usage"].get(
                    "completion_tokens", result.output_token_count
                )

            result.success = True

        return result

    async def send_embedding_request(
        self, request: HybridRequest
    ) -> HybridRequestResult:
        """Send an embedding request to the Control Plane.

        Args:
            request: HybridRequest object (must be Embedding type)

        Returns:
            HybridRequestResult with embedding timing metrics
        """
        result = HybridRequestResult(
            request_id=request.request_id,
            request_type=RequestType.EMBEDDING,
            priority=request.priority,
            slo_deadline_ms=request.slo_deadline_ms,
            embedding_model=request.embedding_model,
            batch_size=request.batch_size,
            metadata=request.metadata,
        )

        if not self._session:
            await self.connect()

        endpoint = f"{self.control_plane_url}/v1/embeddings"

        payload = {
            "model": request.embedding_model,
            "input": request.texts if len(request.texts) > 1 else request.texts[0],
        }

        headers = {
            "Content-Type": "application/json",
            "X-Request-ID": request.request_id,
            "X-Request-Priority": request.priority,
            "X-SLO-Deadline-Ms": str(request.slo_deadline_ms),
        }

        result.send_time = time.time()

        try:
            if not self._session:
                raise RuntimeError("Session not initialized")

            async with self._session.post(
                endpoint, json=payload, headers=headers
            ) as response:
                result.status_code = response.status
                result.completion_time = time.time()

                if response.status != 200:
                    result.success = False
                    result.error = f"HTTP {response.status}: {await response.text()}"
                    return result

                data = await response.json()

                # Extract embedding info from response
                if "data" in data and data["data"]:
                    embeddings = data["data"]
                    result.total_texts_embedded = len(embeddings)

                    # Get embedding dimensions from first result
                    if embeddings and "embedding" in embeddings[0]:
                        result.embedding_dimensions = len(embeddings[0]["embedding"])

                # Usage info if available
                if "usage" in data:
                    result.total_texts_embedded = data["usage"].get(
                        "prompt_tokens", result.total_texts_embedded
                    )

                result.success = True

        except asyncio.TimeoutError:
            result.completion_time = time.time()
            result.success = False
            result.error = "Request timed out"

        except Exception as e:
            result.completion_time = time.time()
            result.success = False
            result.error = str(e)

        return result

    async def send_batch(
        self,
        requests: list[HybridRequest],
        concurrency: int = 50,
    ) -> list[HybridRequestResult]:
        """Send a batch of requests with concurrency control.

        Args:
            requests: List of HybridRequest objects
            concurrency: Maximum concurrent requests

        Returns:
            List of HybridRequestResult objects
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def send_with_semaphore(request: HybridRequest) -> HybridRequestResult:
            async with semaphore:
                return await self.send_request(request)

        tasks = [send_with_semaphore(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(
                    HybridRequestResult(
                        request_id=requests[i].request_id,
                        request_type=requests[i].request_type,
                        priority=requests[i].priority,
                        slo_deadline_ms=requests[i].slo_deadline_ms,
                        success=False,
                        error=str(result),
                    )
                )
            else:
                final_results.append(result)

        return final_results


# Re-export
__all__ = [
    "HybridBenchmarkClient",
    "HybridRequestResult",
]
