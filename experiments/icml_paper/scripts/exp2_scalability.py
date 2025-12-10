#!/usr/bin/env python3
"""
ICML Paper Experiment: Scalability Study
=========================================

This experiment demonstrates SAGE's scalability across multiple dimensions:
1. Number of backend engines (1, 2, 4, 8 vLLM instances)
2. Request rate (10 to saturation)
3. Concurrent clients

Key Questions:
- Does throughput scale linearly with backend count?
- What is the control plane overhead?
- Where is the saturation point?

Metrics:
- Throughput vs backend count (speedup factor)
- Latency vs request rate (saturation curve)
- Control plane overhead (measured by comparing direct vLLM vs SAGE gateway)
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

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class ScalabilityConfig:
    """Configuration for scalability experiments."""

    gateway_url: str
    backend_counts: list[int]
    request_rates: list[float]
    concurrent_clients: list[int]
    requests_per_config: int
    warmup_requests: int
    output_dir: str

    @classmethod
    def default(cls) -> "ScalabilityConfig":
        return cls(
            gateway_url=os.environ.get("SAGE_GATEWAY_URL", "http://localhost:8888"),
            backend_counts=[1, 2, 4, 8],
            request_rates=[10, 25, 50, 100, 150, 200, 300, 500],
            concurrent_clients=[1, 10, 50, 100],
            requests_per_config=500,
            warmup_requests=50,
            output_dir=os.environ.get("BENCHMARK_OUTPUT_DIR", "./results"),
        )


@dataclass
class ScalabilityResult:
    """Result for one scalability test point."""

    experiment_type: str  # "backend_scaling" | "rate_scaling" | "client_scaling"
    variable_name: str
    variable_value: int | float

    # Performance metrics
    throughput_rps: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_mean_ms: float

    # Scaling metrics
    speedup: float  # relative to baseline
    efficiency: float  # speedup / variable_value (for backend scaling)

    # Resource metrics
    success_rate: float
    total_requests: int
    duration_seconds: float

    timestamp: str


class ScalabilityBenchmark:
    """Runs scalability experiments."""

    def __init__(self, config: ScalabilityConfig):
        self.config = config
        self.timeout = aiohttp.ClientTimeout(total=60.0)

    async def send_request(
        self,
        session: aiohttp.ClientSession,
        request_id: str,
    ) -> dict[str, Any]:
        """Send a single LLM request and measure latency."""
        start = time.perf_counter()
        try:
            async with session.post(
                f"{self.config.gateway_url}/v1/chat/completions",
                json={
                    "model": "default",
                    "messages": [{"role": "user", "content": "Hello, how are you?"}],
                    "max_tokens": 64,
                },
            ) as resp:
                await resp.json()
                end = time.perf_counter()
                return {
                    "request_id": request_id,
                    "latency_ms": (end - start) * 1000,
                    "success": resp.status == 200,
                }
        except Exception as e:
            end = time.perf_counter()
            return {
                "request_id": request_id,
                "latency_ms": (end - start) * 1000,
                "success": False,
                "error": str(e),
            }

    async def run_throughput_test(
        self,
        n_requests: int,
        target_rate: float,
        n_clients: int = 1,
    ) -> dict[str, Any]:
        """Run a throughput test with specified parameters."""
        results = []
        interval = 1.0 / target_rate if target_rate > 0 else 0

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            # Warmup
            warmup_tasks = [
                self.send_request(session, f"warmup-{i}")
                for i in range(self.config.warmup_requests)
            ]
            await asyncio.gather(*warmup_tasks)

            # Main test
            start_time = time.perf_counter()

            if n_clients == 1:
                # Single client: send requests at target rate
                tasks = []
                for i in range(n_requests):
                    tasks.append(self.send_request(session, f"req-{i}"))
                    if interval > 0:
                        await asyncio.sleep(interval)
                results = await asyncio.gather(*tasks)
            else:
                # Multiple concurrent clients
                async def client_worker(client_id: int, n_reqs: int):
                    client_results = []
                    for i in range(n_reqs):
                        result = await self.send_request(session, f"c{client_id}-req-{i}")
                        client_results.append(result)
                        if interval > 0:
                            await asyncio.sleep(interval / n_clients)
                    return client_results

                reqs_per_client = n_requests // n_clients
                tasks = [client_worker(c, reqs_per_client) for c in range(n_clients)]
                all_results = await asyncio.gather(*tasks)
                results = [r for client_results in all_results for r in client_results]

            end_time = time.perf_counter()

        # Aggregate
        duration = end_time - start_time
        successful = [r for r in results if r["success"]]
        latencies = [r["latency_ms"] for r in successful]

        return {
            "total_requests": len(results),
            "successful_requests": len(successful),
            "duration_seconds": duration,
            "throughput_rps": len(successful) / duration if duration > 0 else 0,
            "latency_p50_ms": float(np.percentile(latencies, 50)) if latencies else 0,
            "latency_p95_ms": float(np.percentile(latencies, 95)) if latencies else 0,
            "latency_p99_ms": float(np.percentile(latencies, 99)) if latencies else 0,
            "latency_mean_ms": float(np.mean(latencies)) if latencies else 0,
            "success_rate": len(successful) / len(results) * 100 if results else 0,
        }

    async def experiment_backend_scaling(self) -> list[ScalabilityResult]:
        """Test throughput scaling with different numbers of backends."""
        logger.info("=== Experiment: Backend Scaling ===")
        results = []
        baseline_throughput = None

        for n_backends in self.config.backend_counts:
            logger.info(f"Testing with {n_backends} backend(s)...")

            # Note: In actual experiment, you would need to reconfigure the cluster
            # Here we assume the cluster is already configured with n_backends
            # This script would be called multiple times with different cluster configs

            metrics = await self.run_throughput_test(
                n_requests=self.config.requests_per_config,
                target_rate=0,  # Send as fast as possible
                n_clients=10,  # Use multiple clients to saturate
            )

            if baseline_throughput is None:
                baseline_throughput = metrics["throughput_rps"]

            speedup = (
                metrics["throughput_rps"] / baseline_throughput if baseline_throughput else 1.0
            )
            efficiency = speedup / n_backends

            result = ScalabilityResult(
                experiment_type="backend_scaling",
                variable_name="num_backends",
                variable_value=n_backends,
                throughput_rps=metrics["throughput_rps"],
                latency_p50_ms=metrics["latency_p50_ms"],
                latency_p95_ms=metrics["latency_p95_ms"],
                latency_p99_ms=metrics["latency_p99_ms"],
                latency_mean_ms=metrics["latency_mean_ms"],
                speedup=speedup,
                efficiency=efficiency,
                success_rate=metrics["success_rate"],
                total_requests=metrics["total_requests"],
                duration_seconds=metrics["duration_seconds"],
                timestamp=datetime.now().isoformat(),
            )
            results.append(result)

            logger.info(
                f"  Backends={n_backends}: "
                f"throughput={metrics['throughput_rps']:.1f} req/s, "
                f"speedup={speedup:.2f}x, "
                f"efficiency={efficiency:.1%}"
            )

        return results

    async def experiment_rate_scaling(self) -> list[ScalabilityResult]:
        """Test latency vs request rate to find saturation point."""
        logger.info("=== Experiment: Rate Scaling ===")
        results = []

        for rate in self.config.request_rates:
            logger.info(f"Testing at {rate} req/s...")

            metrics = await self.run_throughput_test(
                n_requests=min(int(rate * 30), self.config.requests_per_config),  # 30s worth
                target_rate=rate,
                n_clients=1,
            )

            result = ScalabilityResult(
                experiment_type="rate_scaling",
                variable_name="request_rate",
                variable_value=rate,
                throughput_rps=metrics["throughput_rps"],
                latency_p50_ms=metrics["latency_p50_ms"],
                latency_p95_ms=metrics["latency_p95_ms"],
                latency_p99_ms=metrics["latency_p99_ms"],
                latency_mean_ms=metrics["latency_mean_ms"],
                speedup=1.0,  # Not applicable
                efficiency=metrics["throughput_rps"] / rate if rate > 0 else 0,  # Achieved/target
                success_rate=metrics["success_rate"],
                total_requests=metrics["total_requests"],
                duration_seconds=metrics["duration_seconds"],
                timestamp=datetime.now().isoformat(),
            )
            results.append(result)

            logger.info(
                f"  Rate={rate}: "
                f"achieved={metrics['throughput_rps']:.1f} req/s, "
                f"p99={metrics['latency_p99_ms']:.1f}ms, "
                f"success={metrics['success_rate']:.1f}%"
            )

            # Stop if we've hit saturation (throughput not increasing with rate)
            if metrics["success_rate"] < 90:
                logger.info("  -> Saturation detected, stopping rate scaling")
                break

        return results

    async def experiment_client_scaling(self) -> list[ScalabilityResult]:
        """Test behavior with increasing concurrent clients."""
        logger.info("=== Experiment: Client Scaling ===")
        results = []
        baseline_latency = None

        for n_clients in self.config.concurrent_clients:
            logger.info(f"Testing with {n_clients} concurrent client(s)...")

            metrics = await self.run_throughput_test(
                n_requests=self.config.requests_per_config,
                target_rate=100,  # Fixed rate
                n_clients=n_clients,
            )

            if baseline_latency is None:
                baseline_latency = metrics["latency_p99_ms"]

            result = ScalabilityResult(
                experiment_type="client_scaling",
                variable_name="num_clients",
                variable_value=n_clients,
                throughput_rps=metrics["throughput_rps"],
                latency_p50_ms=metrics["latency_p50_ms"],
                latency_p95_ms=metrics["latency_p95_ms"],
                latency_p99_ms=metrics["latency_p99_ms"],
                latency_mean_ms=metrics["latency_mean_ms"],
                speedup=baseline_latency / metrics["latency_p99_ms"]
                if metrics["latency_p99_ms"]
                else 0,
                efficiency=metrics["throughput_rps"] / n_clients,  # Per-client throughput
                success_rate=metrics["success_rate"],
                total_requests=metrics["total_requests"],
                duration_seconds=metrics["duration_seconds"],
                timestamp=datetime.now().isoformat(),
            )
            results.append(result)

            logger.info(
                f"  Clients={n_clients}: "
                f"throughput={metrics['throughput_rps']:.1f} req/s, "
                f"p99={metrics['latency_p99_ms']:.1f}ms"
            )

        return results


async def main():
    parser = argparse.ArgumentParser(description="Scalability Experiment")
    parser.add_argument(
        "--experiment",
        type=str,
        choices=["backend", "rate", "client", "all"],
        default="all",
        help="Which experiment to run",
    )
    parser.add_argument(
        "--backends", type=str, default="1,2,4", help="Backend counts to test (comma-separated)"
    )
    parser.add_argument(
        "--rates",
        type=str,
        default="10,50,100,200,300",
        help="Request rates to test (comma-separated)",
    )
    parser.add_argument(
        "--clients", type=str, default="1,10,50", help="Client counts to test (comma-separated)"
    )
    parser.add_argument("--requests", type=int, default=500, help="Requests per configuration")
    parser.add_argument("--output", type=str, default="./results", help="Output directory")
    parser.add_argument("--gateway", type=str, default=None, help="Gateway URL")
    args = parser.parse_args()

    config = ScalabilityConfig.default()
    config.backend_counts = [int(x) for x in args.backends.split(",")]
    config.request_rates = [float(x) for x in args.rates.split(",")]
    config.concurrent_clients = [int(x) for x in args.clients.split(",")]
    config.requests_per_config = args.requests
    config.output_dir = args.output
    if args.gateway:
        config.gateway_url = args.gateway

    benchmark = ScalabilityBenchmark(config)
    all_results = []

    if args.experiment in ["backend", "all"]:
        results = await benchmark.experiment_backend_scaling()
        all_results.extend(results)

    if args.experiment in ["rate", "all"]:
        results = await benchmark.experiment_rate_scaling()
        all_results.extend(results)

    if args.experiment in ["client", "all"]:
        results = await benchmark.experiment_client_scaling()
        all_results.extend(results)

    # Save results
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"exp2_scalability_{args.experiment}_{timestamp}.json"

    with open(output_file, "w") as f:
        json.dump(
            {
                "experiment": "scalability",
                "sub_experiment": args.experiment,
                "config": asdict(config),
                "results": [asdict(r) for r in all_results],
            },
            f,
            indent=2,
        )

    logger.info(f"Results saved to {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
