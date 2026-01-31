import time
from dataclasses import dataclass, field
from typing import Any, Optional

import aiohttp
import numpy as np


@dataclass
class RequestResult:
    """Result of a single request."""

    request_id: str
    request_type: str  # "llm" or "embedding"
    start_time: float
    end_time: float
    latency_ms: float
    success: bool
    error: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    metadata: dict = field(default_factory=dict)


class BenchmarkClient:
    """Client for sending benchmark requests to SAGE gateway."""

    def __init__(self, gateway_url: str, timeout: float = 60.0):
        self.gateway_url = gateway_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()

    async def send_llm_request(
        self, request_id: str, prompt: str, model: str = "default"
    ) -> RequestResult:
        """Send a chat completion request."""
        if not self._session:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        start_time = time.perf_counter()
        try:
            async with self._session.post(
                f"{self.gateway_url}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 128,
                    "temperature": 0.7,
                },
                headers={"Content-Type": "application/json"},
            ) as resp:
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000

                if resp.status == 200:
                    data = await resp.json()
                    tokens_out = data.get("usage", {}).get("completion_tokens", 0)
                    tokens_in = data.get("usage", {}).get("prompt_tokens", 0)
                    return RequestResult(
                        request_id=request_id,
                        request_type="llm",
                        start_time=start_time,
                        end_time=end_time,
                        latency_ms=latency_ms,
                        success=True,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                    )
                else:
                    error_text = await resp.text()
                    return RequestResult(
                        request_id=request_id,
                        request_type="llm",
                        start_time=start_time,
                        end_time=end_time,
                        latency_ms=latency_ms,
                        success=False,
                        error=f"HTTP {resp.status}: {error_text[:200]}",
                    )
        except Exception as e:
            end_time = time.perf_counter()
            return RequestResult(
                request_id=request_id,
                request_type="llm",
                start_time=start_time,
                end_time=end_time,
                latency_ms=(end_time - start_time) * 1000,
                success=False,
                error=str(e),
            )

    async def send_embedding_request(
        self, request_id: str, texts: list[str], model: str = "default"
    ) -> RequestResult:
        """Send an embedding request."""
        if not self._session:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        start_time = time.perf_counter()
        try:
            async with self._session.post(
                f"{self.gateway_url}/v1/embeddings",
                json={
                    "model": model,
                    "input": texts,
                },
                headers={"Content-Type": "application/json"},
            ) as resp:
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000

                if resp.status == 200:
                    data = await resp.json()
                    usage = data.get("usage", {})
                    tokens_in = usage.get("prompt_tokens", 0) or usage.get("total_tokens", 0)
                    return RequestResult(
                        request_id=request_id,
                        request_type="embedding",
                        start_time=start_time,
                        end_time=end_time,
                        latency_ms=latency_ms,
                        success=True,
                        tokens_in=tokens_in,
                    )
                else:
                    error_text = await resp.text()
                    return RequestResult(
                        request_id=request_id,
                        request_type="embedding",
                        start_time=start_time,
                        end_time=end_time,
                        latency_ms=latency_ms,
                        success=False,
                        error=f"HTTP {resp.status}: {error_text[:200]}",
                    )
        except Exception as e:
            end_time = time.perf_counter()
            return RequestResult(
                request_id=request_id,
                request_type="embedding",
                start_time=start_time,
                end_time=end_time,
                latency_ms=(end_time - start_time) * 1000,
                success=False,
                error=str(e),
            )


class WorkloadGenerator:
    """Generates mixed LLM+Embedding workload."""

    PROMPTS = [
        "Explain the concept of machine learning in simple terms.",
        "What are the main differences between Python and Java?",
        "Write a short poem about artificial intelligence.",
        "Summarize the key points of deep learning.",
        "What is the capital of France and its population?",
        "Describe the process of photosynthesis.",
        "What are the benefits of regular exercise?",
        "Explain how a neural network works.",
    ]

    TEXTS = [
        "Machine learning is a subset of artificial intelligence.",
        "Deep learning uses neural networks with many layers.",
        "Natural language processing enables computers to understand text.",
        "Computer vision allows machines to interpret images.",
        "Reinforcement learning involves learning through trial and error.",
    ]

    def __init__(self, llm_ratio: float = 0.7, seed: int = 42):
        self.llm_ratio = llm_ratio
        self.rng = np.random.default_rng(seed)

    def generate_request(self, request_id: str) -> tuple[str, dict[str, Any]]:
        """Generate a random request (LLM or embedding)."""
        if self.rng.random() < self.llm_ratio:
            prompt = self.rng.choice(self.PROMPTS)
            return ("llm", {"prompt": prompt})
        else:
            n_texts = self.rng.integers(1, 4)
            texts = list(self.rng.choice(self.TEXTS, size=n_texts, replace=False))
            return ("embedding", {"texts": texts})

    def generate_arrival_times(
        self, n_requests: int, rate: float, pattern: str = "poisson"
    ) -> list[float]:
        """Generate request arrival times."""
        if pattern == "constant":
            interval = 1.0 / rate
            return [i * interval for i in range(n_requests)]
        elif pattern == "poisson":
            intervals = np.random.exponential(1.0 / rate, n_requests)
            return list(np.cumsum(intervals))
        elif pattern == "bursty":
            times = []
            t = 0
            while len(times) < n_requests:
                for _ in range(min(10, n_requests - len(times))):
                    t += np.random.exponential(0.1)
                    times.append(t)
                for _ in range(min(50, n_requests - len(times))):
                    t += np.random.exponential(0.005)
                    times.append(t)
            return times[:n_requests]
        else:
            raise ValueError(f"Unknown arrival pattern: {pattern}")
