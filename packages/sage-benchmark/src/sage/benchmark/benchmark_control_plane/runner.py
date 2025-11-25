"""
Benchmark Runner Module
=======================

Orchestrates the benchmark execution flow.

This module handles:
- Environment validation
- Policy switching
- Warmup execution
- Workload execution with timing control
- Results collection
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .workload import Request

from .client import BenchmarkClient, RequestResult
from .config import BenchmarkConfig
from .metrics import MetricsCollector, RequestMetrics
from .workload import WorkloadGenerator


@dataclass
class PolicyResult:
    """Results for a single policy benchmark run.

    Attributes:
        policy: Policy name
        metrics: Aggregated metrics for this policy
        raw_results: List of individual request results
        control_plane_metrics: Metrics from Control Plane
        start_time: Run start time
        end_time: Run end time
    """

    policy: str
    metrics: RequestMetrics
    raw_results: list[RequestResult] = field(default_factory=list)
    control_plane_metrics: dict[str, Any] = field(default_factory=dict)
    start_time: float = 0.0
    end_time: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "policy": self.policy,
            "metrics": self.metrics.to_dict(),
            "raw_results": [r.to_dict() for r in self.raw_results],
            "control_plane_metrics": self.control_plane_metrics,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


@dataclass
class BenchmarkResult:
    """Complete benchmark results across all policies.

    Attributes:
        config: Benchmark configuration used
        policy_results: Results for each policy
        best_throughput: Policy with best throughput
        best_slo_compliance: Policy with best SLO compliance
        best_p99_latency: Policy with best P99 latency
    """

    config: dict[str, Any]
    policy_results: dict[str, PolicyResult] = field(default_factory=dict)
    best_throughput: str = ""
    best_slo_compliance: str = ""
    best_p99_latency: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "config": self.config,
            "policy_results": {
                name: result.to_dict()
                for name, result in self.policy_results.items()
            },
            "summary": {
                "best_throughput": self.best_throughput,
                "best_slo_compliance": self.best_slo_compliance,
                "best_p99_latency": self.best_p99_latency,
            },
        }


class BenchmarkRunner:
    """Orchestrates benchmark execution.

    This class manages the complete benchmark flow:
    1. Validate environment (Control Plane reachability)
    2. For each policy:
       a. Switch Control Plane to policy
       b. Run warmup requests
       c. Execute workload with timing control
       d. Collect metrics
    3. Generate comparison results
    """

    def __init__(
        self,
        config: BenchmarkConfig,
        verbose: bool = True,
    ):
        """Initialize benchmark runner.

        Args:
            config: Benchmark configuration
            verbose: Whether to print progress messages
        """
        self.config = config
        self.verbose = verbose
        self.workload_generator = WorkloadGenerator(config)

    def _log(self, message: str) -> None:
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    async def run(self) -> BenchmarkResult:
        """Run the complete benchmark.

        Returns:
            BenchmarkResult with results for all policies
        """
        # Validate configuration
        errors = self.config.validate()
        if errors:
            raise ValueError(f"Invalid configuration: {errors}")

        result = BenchmarkResult(config=self.config.to_dict())

        # Generate workload once (same workload for all policies)
        self._log("\n📝 Generating workload...")
        workload = self.workload_generator.generate()
        self._log(f"   Generated {len(workload)} requests")

        async with BenchmarkClient(
            self.config.control_plane_url,
            timeout_seconds=self.config.timeout_seconds,
            enable_streaming=self.config.enable_streaming,
        ) as client:
            # Check Control Plane health
            self._log("\n🔍 Checking Control Plane health...")
            is_healthy = await client.health_check()
            if not is_healthy:
                self._log("   ⚠️  Control Plane health check failed, proceeding anyway...")

            # Run benchmark for each policy
            for policy in self.config.policies:
                self._log(f"\n{'=' * 60}")
                self._log(f"🚀 Benchmarking policy: {policy}")
                self._log(f"{'=' * 60}")

                policy_result = await self._run_policy(client, policy, workload)
                result.policy_results[policy] = policy_result

                self._log(f"   ✅ Completed: {policy_result.metrics.completed_requests} requests")
                self._log(f"   📊 Throughput: {policy_result.metrics.throughput_rps:.2f} req/s")
                self._log(
                    f"   📈 SLO Compliance: {policy_result.metrics.slo_compliance_rate:.1%}"
                )

        # Determine best performers
        result = self._determine_best_performers(result)

        return result

    async def run_single_policy(self, policy: str) -> PolicyResult:
        """Run benchmark for a single policy.

        Args:
            policy: Policy name to benchmark

        Returns:
            PolicyResult for the specified policy
        """
        workload = self.workload_generator.generate()

        async with BenchmarkClient(
            self.config.control_plane_url,
            timeout_seconds=self.config.timeout_seconds,
            enable_streaming=self.config.enable_streaming,
        ) as client:
            return await self._run_policy(client, policy, workload)

    async def run_rate_sweep(
        self,
        policy: str,
        rates: list[float],
    ) -> dict[float, PolicyResult]:
        """Run benchmark across multiple request rates.

        Args:
            policy: Policy to benchmark
            rates: List of request rates to test

        Returns:
            Dictionary mapping rate to PolicyResult
        """
        results = {}

        async with BenchmarkClient(
            self.config.control_plane_url,
            timeout_seconds=self.config.timeout_seconds,
            enable_streaming=self.config.enable_streaming,
        ) as client:
            for rate in rates:
                self._log(f"\n🔄 Testing rate: {rate} req/s")

                # Update config for this rate
                original_rate = self.config.request_rate
                self.config.request_rate = rate

                # Generate new workload with updated rate
                workload = self.workload_generator.generate()

                policy_result = await self._run_policy(client, policy, workload)
                results[rate] = policy_result

                # Restore original rate
                self.config.request_rate = original_rate

        return results

    async def _run_policy(
        self,
        client: BenchmarkClient,
        policy: str,
        workload: list[Request],
    ) -> PolicyResult:
        """Run benchmark for a single policy.

        Args:
            client: Benchmark client
            policy: Policy name
            workload: List of requests to send

        Returns:
            PolicyResult for this policy
        """
        result = PolicyResult(policy=policy)

        # Try to switch policy
        self._log(f"   🔧 Switching to policy: {policy}")
        policy_switched = await client.set_policy(policy)
        if not policy_switched:
            self._log("   ⚠️  Policy switch failed or not supported, continuing...")

        # Run warmup
        if self.config.warmup_requests > 0:
            self._log(f"   🔥 Running warmup ({self.config.warmup_requests} requests)...")
            warmup_workload = workload[: self.config.warmup_requests]
            await self._execute_workload(client, warmup_workload)

        # Run main workload
        main_workload = workload[self.config.warmup_requests:]
        self._log(f"   ▶️  Running main workload ({len(main_workload)} requests)...")

        result.start_time = time.time()
        raw_results = await self._execute_workload(client, main_workload)
        result.end_time = time.time()

        result.raw_results = raw_results

        # Collect Control Plane metrics
        result.control_plane_metrics = await client.get_metrics()

        # Compute aggregated metrics
        collector = MetricsCollector()
        collector.set_time_range(result.start_time, result.end_time)
        collector.add_results(raw_results)
        result.metrics = collector.compute_metrics()

        return result

    async def _execute_workload(
        self,
        client: BenchmarkClient,
        workload: list[Request],
    ) -> list[RequestResult]:
        """Execute workload with timing control.

        Args:
            client: Benchmark client
            workload: List of requests to send

        Returns:
            List of RequestResults
        """
        if not workload:
            return []

        results: list[RequestResult] = []
        start_time = time.time()

        # Create tasks for all requests
        tasks: list[asyncio.Task] = []
        semaphore = asyncio.Semaphore(self.config.concurrent_requests)

        async def send_request_at_time(request: Request) -> RequestResult:
            """Send request at scheduled time."""
            async with semaphore:
                # Wait until scheduled time
                elapsed = time.time() - start_time
                wait_time = request.scheduled_arrival_time - elapsed
                if wait_time > 0:
                    await asyncio.sleep(wait_time)

                return await client.send_request(request)

        # Schedule all requests
        for request in workload:
            task = asyncio.create_task(send_request_at_time(request))
            tasks.append(task)

        # Wait for all to complete
        results = await asyncio.gather(*tasks)

        return list(results)

    def _determine_best_performers(self, result: BenchmarkResult) -> BenchmarkResult:
        """Determine best performing policies.

        Args:
            result: BenchmarkResult to update

        Returns:
            Updated BenchmarkResult
        """
        if not result.policy_results:
            return result

        # Best throughput
        best_throughput_policy = max(
            result.policy_results.items(),
            key=lambda x: x[1].metrics.throughput_rps,
        )
        result.best_throughput = best_throughput_policy[0]

        # Best SLO compliance
        best_slo_policy = max(
            result.policy_results.items(),
            key=lambda x: x[1].metrics.slo_compliance_rate,
        )
        result.best_slo_compliance = best_slo_policy[0]

        # Best P99 latency (lowest is best)
        policies_with_latency = [
            (name, p) for name, p in result.policy_results.items()
            if p.metrics.e2e_latency_p99_ms > 0
        ]
        if policies_with_latency:
            best_p99_policy = min(
                policies_with_latency,
                key=lambda x: x[1].metrics.e2e_latency_p99_ms,
            )
            result.best_p99_latency = best_p99_policy[0]

        return result
