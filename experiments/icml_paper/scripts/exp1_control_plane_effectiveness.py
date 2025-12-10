#!/usr/bin/env python3
"""
ICML Paper Experiment: Control Plane Effectiveness
===================================================

This experiment demonstrates that SAGE's unified LLM+Embedding control plane
improves performance compared to separate services.

Experiment Design:
- Baseline 1: vLLM only (no embedding co-scheduling)
- Baseline 2: vLLM + separate embedding service (manual load balancing)
- SAGE: Unified control plane with HybridSchedulingPolicy

Metrics:
- p50, p95, p99 latency
- Throughput (requests/second)
- SLO satisfaction rate (p99 < 500ms target)

Workload:
- Mixed traffic: 70% LLM (chat), 30% Embedding
- Request rate: 10, 50, 100, 200 req/s
- Duration: 60 seconds per configuration
"""

import argparse
import asyncio
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class ExperimentConfig:
    """Configuration for a single experiment run."""

    name: str
    gateway_url: str
    request_rates: list[float]
    llm_ratio: float
    duration_seconds: int
    warmup_requests: int
    slo_target_ms: float
    output_dir: str

    @classmethod
    def default(cls) -> "ExperimentConfig":
        return cls(
            name="control_plane_effectiveness",
            gateway_url=os.environ.get("SAGE_GATEWAY_URL", "http://localhost:8888"),
            request_rates=[10, 50, 100, 200],
            llm_ratio=0.7,  # 70% LLM, 30% embedding
            duration_seconds=60,
            warmup_requests=20,
            slo_target_ms=500.0,
            output_dir=os.environ.get("BENCHMARK_OUTPUT_DIR", "./results"),
        )


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
    tokens_generated: int = 0


@dataclass
class ExperimentResult:
    """Aggregated results for one experiment configuration."""

    config_name: str
    policy: str
    request_rate: float
    total_requests: int
    successful_requests: int
    failed_requests: int

    # Latency metrics (ms)
    latency_p50: float
    latency_p95: float
    latency_p99: float
    latency_mean: float
    latency_std: float

    # Throughput
    throughput_rps: float

    # SLO compliance
    slo_target_ms: float
    slo_satisfaction_rate: float

    # By request type
    llm_latency_p99: float
    embedding_latency_p99: float

    # Timing
    duration_seconds: float
    timestamp: str


class BenchmarkClient:
    """Client for sending benchmark requests to SAGE gateway."""

    def __init__(self, gateway_url: str, timeout: float = 60.0):
        self.gateway_url = gateway_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()

    async def send_llm_request(self, request_id: str, prompt: str) -> RequestResult:
        """Send a chat completion request."""
        start_time = time.perf_counter()
        try:
            async with self._session.post(
                f"{self.gateway_url}/v1/chat/completions",
                json={
                    "model": "default",
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
                    tokens = data.get("usage", {}).get("completion_tokens", 0)
                    return RequestResult(
                        request_id=request_id,
                        request_type="llm",
                        start_time=start_time,
                        end_time=end_time,
                        latency_ms=latency_ms,
                        success=True,
                        tokens_generated=tokens,
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

    async def send_embedding_request(self, request_id: str, texts: list[str]) -> RequestResult:
        """Send an embedding request."""
        start_time = time.perf_counter()
        try:
            async with self._session.post(
                f"{self.gateway_url}/v1/embeddings",
                json={
                    "model": "default",
                    "input": texts,
                },
                headers={"Content-Type": "application/json"},
            ) as resp:
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000

                if resp.status == 200:
                    return RequestResult(
                        request_id=request_id,
                        request_type="embedding",
                        start_time=start_time,
                        end_time=end_time,
                        latency_ms=latency_ms,
                        success=True,
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

    # Sample prompts for LLM requests
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

    # Sample texts for embedding requests
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
            # Random subset of texts for embedding
            n_texts = self.rng.integers(1, 4)
            texts = list(self.rng.choice(self.TEXTS, size=n_texts, replace=False))
            return ("embedding", {"texts": texts})


async def run_experiment(
    config: ExperimentConfig,
    policy: str,
    request_rate: float,
) -> ExperimentResult:
    """Run a single experiment configuration."""
    logger.info(f"Running experiment: policy={policy}, rate={request_rate} req/s")

    workload = WorkloadGenerator(llm_ratio=config.llm_ratio)
    results: list[RequestResult] = []

    async with BenchmarkClient(config.gateway_url) as client:
        # Warmup
        logger.info(f"Warmup: {config.warmup_requests} requests")
        warmup_tasks = []
        for i in range(config.warmup_requests):
            req_type, params = workload.generate_request(f"warmup-{i}")
            if req_type == "llm":
                warmup_tasks.append(client.send_llm_request(f"warmup-{i}", params["prompt"]))
            else:
                warmup_tasks.append(client.send_embedding_request(f"warmup-{i}", params["texts"]))
        await asyncio.gather(*warmup_tasks)

        # Main experiment
        logger.info(f"Starting main experiment: {config.duration_seconds}s at {request_rate} req/s")
        start_time = time.perf_counter()
        request_id = 0
        interval = 1.0 / request_rate

        tasks = []
        while time.perf_counter() - start_time < config.duration_seconds:
            req_type, params = workload.generate_request(f"req-{request_id}")
            if req_type == "llm":
                tasks.append(client.send_llm_request(f"req-{request_id}", params["prompt"]))
            else:
                tasks.append(client.send_embedding_request(f"req-{request_id}", params["texts"]))

            request_id += 1
            await asyncio.sleep(interval)

        # Wait for all pending requests
        logger.info(f"Waiting for {len(tasks)} pending requests...")
        results = await asyncio.gather(*tasks)

    end_time = time.perf_counter()
    actual_duration = end_time - start_time

    # Aggregate results
    return aggregate_results(
        results=results,
        config_name=config.name,
        policy=policy,
        request_rate=request_rate,
        slo_target_ms=config.slo_target_ms,
        duration=actual_duration,
    )


def aggregate_results(
    results: list[RequestResult],
    config_name: str,
    policy: str,
    request_rate: float,
    slo_target_ms: float,
    duration: float,
) -> ExperimentResult:
    """Aggregate individual request results into experiment metrics."""
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    if not successful:
        logger.warning("No successful requests!")
        return ExperimentResult(
            config_name=config_name,
            policy=policy,
            request_rate=request_rate,
            total_requests=len(results),
            successful_requests=0,
            failed_requests=len(failed),
            latency_p50=0,
            latency_p95=0,
            latency_p99=0,
            latency_mean=0,
            latency_std=0,
            throughput_rps=0,
            slo_target_ms=slo_target_ms,
            slo_satisfaction_rate=0,
            llm_latency_p99=0,
            embedding_latency_p99=0,
            duration_seconds=duration,
            timestamp=datetime.now().isoformat(),
        )

    latencies = [r.latency_ms for r in successful]
    llm_latencies = [r.latency_ms for r in successful if r.request_type == "llm"]
    embedding_latencies = [r.latency_ms for r in successful if r.request_type == "embedding"]

    slo_satisfied = sum(1 for lat in latencies if lat <= slo_target_ms)

    return ExperimentResult(
        config_name=config_name,
        policy=policy,
        request_rate=request_rate,
        total_requests=len(results),
        successful_requests=len(successful),
        failed_requests=len(failed),
        latency_p50=float(np.percentile(latencies, 50)),
        latency_p95=float(np.percentile(latencies, 95)),
        latency_p99=float(np.percentile(latencies, 99)),
        latency_mean=float(np.mean(latencies)),
        latency_std=float(np.std(latencies)),
        throughput_rps=len(successful) / duration,
        slo_target_ms=slo_target_ms,
        slo_satisfaction_rate=slo_satisfied / len(successful) * 100,
        llm_latency_p99=float(np.percentile(llm_latencies, 99)) if llm_latencies else 0,
        embedding_latency_p99=float(np.percentile(embedding_latencies, 99))
        if embedding_latencies
        else 0,
        duration_seconds=duration,
        timestamp=datetime.now().isoformat(),
    )


async def main():
    parser = argparse.ArgumentParser(description="Control Plane Effectiveness Experiment")
    parser.add_argument("--policy", type=str, default="hybrid", help="Scheduling policy to test")
    parser.add_argument(
        "--rates", type=str, default="10,50,100,200", help="Comma-separated request rates"
    )
    parser.add_argument("--duration", type=int, default=60, help="Duration per rate in seconds")
    parser.add_argument("--output", type=str, default="./results", help="Output directory")
    parser.add_argument("--gateway", type=str, default=None, help="Gateway URL (default: from env)")
    args = parser.parse_args()

    config = ExperimentConfig.default()
    config.request_rates = [float(r) for r in args.rates.split(",")]
    config.duration_seconds = args.duration
    config.output_dir = args.output
    if args.gateway:
        config.gateway_url = args.gateway

    # Run experiments
    all_results = []
    for rate in config.request_rates:
        result = await run_experiment(config, args.policy, rate)
        all_results.append(result)

        # Print summary
        logger.info(
            f"Rate {rate} req/s: "
            f"p99={result.latency_p99:.1f}ms, "
            f"throughput={result.throughput_rps:.1f} req/s, "
            f"SLO={result.slo_satisfaction_rate:.1f}%"
        )

    # Save results
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"exp1_control_plane_{args.policy}_{timestamp}.json"

    with open(output_file, "w") as f:
        json.dump(
            {
                "experiment": "control_plane_effectiveness",
                "policy": args.policy,
                "config": asdict(config),
                "results": [asdict(r) for r in all_results],
            },
            f,
            indent=2,
        )

    logger.info(f"Results saved to {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
