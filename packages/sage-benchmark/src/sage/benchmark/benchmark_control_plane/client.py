"""
Benchmark HTTP Client Module
=============================

Provides async HTTP client for sending requests to the Control Plane and
collecting response metrics.

This module handles:
- Async request sending to Control Plane
- Streaming response processing for TTFT/ITL metrics
- Request timing and metrics recording
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .workload import Request

# Try to import aiohttp, provide helpful error if not available
try:
    import aiohttp

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


@dataclass
class RequestResult:
    """Result of a single benchmark request.

    Attributes:
        request_id: Unique request identifier
        model_name: Target model name
        priority: Request priority
        slo_deadline_ms: SLO deadline in milliseconds

        send_time: Time when request was sent (epoch seconds)
        first_token_time: Time when first token received (epoch seconds)
        completion_time: Time when request completed (epoch seconds)

        inter_token_latencies: List of inter-token latencies in ms
        output_token_count: Number of output tokens generated

        success: Whether the request succeeded
        error: Error message if request failed
        status_code: HTTP status code

        metadata: Additional metadata from the request
    """

    request_id: str
    model_name: str
    priority: str
    slo_deadline_ms: int

    send_time: float = 0.0
    first_token_time: float | None = None
    completion_time: float | None = None

    inter_token_latencies: list[float] = field(default_factory=list)
    output_token_count: int = 0

    success: bool = False
    error: str | None = None
    status_code: int | None = None

    metadata: dict = field(default_factory=dict)

    @property
    def e2e_latency_ms(self) -> float | None:
        """End-to-end latency in milliseconds."""
        if self.send_time is not None and self.completion_time is not None:
            return (self.completion_time - self.send_time) * 1000
        return None

    @property
    def ttft_ms(self) -> float | None:
        """Time to first token in milliseconds."""
        if self.send_time is not None and self.first_token_time is not None:
            return (self.first_token_time - self.send_time) * 1000
        return None

    @property
    def met_slo(self) -> bool:
        """Whether the request met its SLO deadline."""
        e2e = self.e2e_latency_ms
        if e2e is None:
            return False
        return e2e <= self.slo_deadline_ms

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "request_id": self.request_id,
            "model_name": self.model_name,
            "priority": self.priority,
            "slo_deadline_ms": self.slo_deadline_ms,
            "send_time": self.send_time,
            "first_token_time": self.first_token_time,
            "completion_time": self.completion_time,
            "e2e_latency_ms": self.e2e_latency_ms,
            "ttft_ms": self.ttft_ms,
            "inter_token_latencies": self.inter_token_latencies,
            "output_token_count": self.output_token_count,
            "success": self.success,
            "error": self.error,
            "status_code": self.status_code,
            "met_slo": self.met_slo,
            "metadata": self.metadata,
        }


class BenchmarkClient:
    """Async HTTP client for Control Plane benchmarking.

    This client sends requests to the Control Plane's OpenAI-compatible API
    and collects detailed timing metrics including TTFT and inter-token latencies.
    """

    def __init__(
        self,
        control_plane_url: str,
        timeout_seconds: float = 60.0,
        enable_streaming: bool = True,
    ):
        """Initialize benchmark client.

        Args:
            control_plane_url: Base URL of the Control Plane service
            timeout_seconds: Request timeout in seconds
            enable_streaming: Whether to use streaming responses
        """
        if not AIOHTTP_AVAILABLE:
            raise RuntimeError(
                "aiohttp is required for BenchmarkClient. Install it with: pip install aiohttp"
            )

        self.control_plane_url = control_plane_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.enable_streaming = enable_streaming
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> BenchmarkClient:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def connect(self) -> None:
        """Create HTTP session."""
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        self._session = aiohttp.ClientSession(timeout=timeout)

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
                async with self._session.get(f"{self.control_plane_url}/health") as response:
                    return response.status == 200
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
                ) as response:
                    return response.status == 200
        except aiohttp.ClientError:
            # Network errors are expected when Control Plane is unavailable
            pass
        except TimeoutError:
            # Timeout errors are expected in some scenarios
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
                async with self._session.get(f"{self.control_plane_url}/admin/metrics") as response:
                    if response.status == 200:
                        return await response.json()
        except aiohttp.ClientError:
            # Network errors are expected when Control Plane is unavailable
            pass
        except TimeoutError:
            # Timeout errors are expected in some scenarios
            pass

        return {}

    async def send_request(self, request: Request) -> RequestResult:
        """Send a single request to the Control Plane.

        Args:
            request: Request object to send

        Returns:
            RequestResult with timing metrics
        """
        result = RequestResult(
            request_id=request.request_id,
            model_name=request.model_name,
            priority=request.priority,
            slo_deadline_ms=request.slo_deadline_ms,
            metadata=request.metadata,
        )

        if not self._session:
            await self.connect()

        # Prepare request payload (OpenAI-compatible format)
        payload = {
            "model": request.model_name,
            "messages": [{"role": "user", "content": request.prompt}],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": self.enable_streaming,
        }

        # Custom headers for metadata
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

            if self.enable_streaming:
                result = await self._send_streaming_request(payload, headers, result)
            else:
                result = await self._send_non_streaming_request(payload, headers, result)

        except TimeoutError:
            result.completion_time = time.time()
            result.success = False
            result.error = "Request timed out"

        except Exception as e:
            result.completion_time = time.time()
            result.success = False
            result.error = str(e)

        return result

    async def _send_streaming_request(
        self,
        payload: dict[str, Any],
        headers: dict[str, str],
        result: RequestResult,
    ) -> RequestResult:
        """Send request with streaming response handling.

        Processes Server-Sent Events (SSE) format responses from the Control Plane.
        Each SSE event is expected to be a JSON object containing token data.

        Args:
            payload: Request payload
            headers: Request headers
            result: RequestResult to update

        Returns:
            Updated RequestResult
        """
        if not self._session:
            raise RuntimeError("Session not initialized")

        url = f"{self.control_plane_url}/v1/chat/completions"

        async with self._session.post(url, json=payload, headers=headers) as response:
            result.status_code = response.status

            if response.status != 200:
                result.success = False
                result.error = f"HTTP {response.status}: {await response.text()}"
                result.completion_time = time.time()
                return result

            last_token_time: float | None = None
            token_count = 0

            # Process SSE stream
            # SSE format: "data: <json>\n\n" or "data: [DONE]\n\n"
            async for line in response.content:
                try:
                    line_str = line.decode("utf-8").strip()
                except UnicodeDecodeError:
                    continue

                # Skip empty lines and SSE comments
                if not line_str or line_str.startswith(":"):
                    continue

                if line_str.startswith("data: "):
                    data = line_str[6:]

                    # End of stream marker
                    if data == "[DONE]":
                        break

                    # Try to parse JSON data to extract token info
                    # Even if parsing fails, we count the event as a token
                    try:
                        import json

                        event_data = json.loads(data)
                        # Check if this event contains actual content
                        choices = event_data.get("choices", [])
                        if choices and choices[0].get("delta", {}).get("content"):
                            current_time = time.time()

                            # Record first token time
                            if result.first_token_time is None:
                                result.first_token_time = current_time

                            # Calculate inter-token latency
                            if last_token_time is not None:
                                itl = (current_time - last_token_time) * 1000
                                result.inter_token_latencies.append(itl)

                            last_token_time = current_time
                            token_count += 1
                    except (json.JSONDecodeError, KeyError, TypeError):
                        # If JSON parsing fails, still record timing for the event
                        current_time = time.time()
                        if result.first_token_time is None:
                            result.first_token_time = current_time
                        if last_token_time is not None:
                            itl = (current_time - last_token_time) * 1000
                            result.inter_token_latencies.append(itl)
                        last_token_time = current_time
                        token_count += 1

            result.output_token_count = token_count
            result.completion_time = time.time()
            result.success = True

        return result

    async def _send_non_streaming_request(
        self,
        payload: dict[str, Any],
        headers: dict[str, str],
        result: RequestResult,
    ) -> RequestResult:
        """Send request without streaming.

        Args:
            payload: Request payload
            headers: Request headers
            result: RequestResult to update

        Returns:
            Updated RequestResult
        """
        if not self._session:
            raise RuntimeError("Session not initialized")

        url = f"{self.control_plane_url}/v1/chat/completions"
        payload["stream"] = False

        async with self._session.post(url, json=payload, headers=headers) as response:
            result.status_code = response.status

            if response.status != 200:
                result.success = False
                result.error = f"HTTP {response.status}: {await response.text()}"
                result.completion_time = time.time()
                return result

            data = await response.json()
            result.completion_time = time.time()
            result.first_token_time = result.completion_time  # No TTFT for non-streaming

            # Extract token count from response
            if "usage" in data:
                result.output_token_count = data["usage"].get("completion_tokens", 0)

            result.success = True

        return result

    async def send_batch(
        self,
        requests: list[Request],
        max_concurrent: int = 50,
    ) -> list[RequestResult]:
        """Send a batch of requests with concurrency control.

        Args:
            requests: List of requests to send
            max_concurrent: Maximum concurrent requests

        Returns:
            List of RequestResults
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def send_with_semaphore(request: Request) -> RequestResult:
            async with semaphore:
                return await self.send_request(request)

        tasks = [send_with_semaphore(req) for req in requests]
        return await asyncio.gather(*tasks)
