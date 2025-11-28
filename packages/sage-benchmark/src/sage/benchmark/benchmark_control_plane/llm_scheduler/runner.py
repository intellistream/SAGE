# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
LLM Benchmark Runner Module
===========================

Orchestrates the LLM benchmark execution flow.

This module handles:
- Environment validation
- Policy switching
- Warmup execution
- Workload execution with timing control
- Results collection
- Auto-visualization of benchmark results
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .workload import LLMRequest

from ..common.gpu_monitor import GPUMetricsSummary, GPUMonitor
from .client import LLMBenchmarkClient, LLMRequestResult
from .config import LLMBenchmarkConfig
from .metrics import LLMMetricsCollector, LLMRequestMetrics
from .workload import LLMWorkloadGenerator

logger = logging.getLogger(__name__)


@dataclass
class LLMPolicyResult:
    """Results for a single policy LLM benchmark run.

    Attributes:
        policy: Policy name
        metrics: Aggregated metrics for this policy
        raw_results: List of individual request results
        control_plane_metrics: Metrics from Control Plane
        gpu_metrics: GPU metrics summary
        start_time: Run start time
        end_time: Run end time
    """

    policy: str
    metrics: LLMRequestMetrics
    raw_results: list[LLMRequestResult] = field(default_factory=list)
    control_plane_metrics: dict[str, Any] = field(default_factory=dict)
    gpu_metrics: GPUMetricsSummary | None = None
    start_time: float = 0.0
    end_time: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "policy": self.policy,
            "metrics": self.metrics.to_dict(),
            "raw_results": [r.to_dict() for r in self.raw_results],
            "control_plane_metrics": self.control_plane_metrics,
            "gpu_metrics": self.gpu_metrics.to_dict() if self.gpu_metrics else None,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


@dataclass
class LLMBenchmarkResult:
    """Complete LLM benchmark results across all policies.

    Attributes:
        config: Benchmark configuration used
        policy_results: Results for each policy
        best_throughput: Policy with best throughput
        best_slo_compliance: Policy with best SLO compliance
        best_p99_latency: Policy with best P99 latency
    """

    config: dict[str, Any]
    policy_results: dict[str, LLMPolicyResult] = field(default_factory=dict)
    best_throughput: str = ""
    best_slo_compliance: str = ""
    best_p99_latency: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "config": self.config,
            "policy_results": {
                name: result.to_dict() for name, result in self.policy_results.items()
            },
            "summary": {
                "best_throughput": self.best_throughput,
                "best_slo_compliance": self.best_slo_compliance,
                "best_p99_latency": self.best_p99_latency,
            },
        }


class LLMBenchmarkRunner:
    """Orchestrates LLM benchmark execution.

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
        config: LLMBenchmarkConfig,
        verbose: bool = True,
        enable_gpu_monitoring: bool = True,
        output_dir: str | Path | None = None,
    ):
        """Initialize benchmark runner.

        Args:
            config: Benchmark configuration
            verbose: Whether to print progress messages
            enable_gpu_monitoring: Whether to collect GPU metrics
            output_dir: Directory for output files (charts, reports)
        """
        self.config = config
        self.verbose = verbose
        self.enable_gpu_monitoring = enable_gpu_monitoring
        self.output_dir = Path(output_dir) if output_dir else Path(".benchmarks")
        self.workload_generator = LLMWorkloadGenerator(config)

    def _log(self, message: str) -> None:
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    async def run(self, auto_visualize: bool | None = None) -> LLMBenchmarkResult:
        """Run the complete benchmark.

        Args:
            auto_visualize: Override config.auto_visualize setting

        Returns:
            LLMBenchmarkResult with results for all policies
        """
        # Validate configuration
        errors = self.config.validate()
        if errors:
            raise ValueError(f"Invalid configuration: {errors}")

        result = LLMBenchmarkResult(config=self.config.to_dict())

        # Generate workload once (same workload for all policies)
        self._log("\n Generating workload...")
        workload = self.workload_generator.generate()
        self._log(f"   Generated {len(workload)} requests")

        async with LLMBenchmarkClient(
            self.config.control_plane_url,
            timeout_seconds=self.config.timeout_seconds,
            enable_streaming=self.config.enable_streaming,
        ) as client:
            # Check Control Plane health
            self._log("\n Checking Control Plane health...")
            is_healthy = await client.health_check()
            if not is_healthy:
                self._log("   Control Plane health check failed, proceeding anyway...")

            # Run benchmark for each policy
            for policy in self.config.policies:
                self._log(f"\n{'=' * 60}")
                self._log(f" Benchmarking policy: {policy}")
                self._log(f"{'=' * 60}")

                policy_result = await self._run_policy(client, policy, workload)
                result.policy_results[policy] = policy_result

                self._log(f"   Completed: {policy_result.metrics.completed_requests} requests")
                self._log(f"   Throughput: {policy_result.metrics.throughput_rps:.2f} req/s")
                self._log(f"   SLO Compliance: {policy_result.metrics.slo_compliance_rate:.1%}")

        # Determine best performers
        result = self._determine_best_performers(result)

        # Auto visualization
        should_visualize = auto_visualize if auto_visualize is not None else self.config.auto_visualize
        if should_visualize:
            self._generate_visualizations(result)

        return result

    def _generate_visualizations(self, result: LLMBenchmarkResult) -> None:
        """Generate charts and reports for benchmark results.

        Args:
            result: Benchmark results to visualize
        """
        try:
            from ..visualization import BenchmarkCharts, ReportGenerator

            self._log("\n📊 Generating visualizations...")

            # Ensure output directory exists
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Convert result to dict format for visualization
            result_dict = result.to_dict()

            # Extract policy metrics for charts
            policy_metrics = {}
            for policy_name, policy_result in result.policy_results.items():
                policy_metrics[policy_name] = policy_result.metrics.to_dict()

            # Generate charts
            self._log("   📈 Generating charts...")
            charts = BenchmarkCharts(output_dir=self.output_dir)
            chart_paths = charts.generate_all_charts(policy_metrics=policy_metrics)
            for path in chart_paths:
                self._log(f"      - {path.name}")

            # Generate reports
            self._log("   📝 Generating reports...")
            report_gen = ReportGenerator(result=result_dict, charts_dir=self.output_dir)
            report_paths = report_gen.generate_full_report(
                output_dir=self.output_dir,
                report_name="llm_benchmark",
            )
            for report_type, path in report_paths.items():
                self._log(f"      - {report_type}: {path}")

            self._log(f"   ✅ Visualizations saved to: {self.output_dir}")

        except ImportError as e:
            logger.warning(f"Visualization dependencies not available: {e}")
            self._log("   ⚠️  Visualization skipped (missing dependencies)")
        except Exception as e:
            logger.warning(f"Visualization failed: {e}")
            self._log(f"   ⚠️  Visualization failed: {e}")

    async def run_single_policy(self, policy: str) -> LLMPolicyResult:
        """Run benchmark for a single policy.

        Args:
            policy: Policy name to benchmark

        Returns:
            LLMPolicyResult for the specified policy
        """
        workload = self.workload_generator.generate()

        async with LLMBenchmarkClient(
            self.config.control_plane_url,
            timeout_seconds=self.config.timeout_seconds,
            enable_streaming=self.config.enable_streaming,
        ) as client:
            return await self._run_policy(client, policy, workload)

    async def run_rate_sweep(
        self,
        policy: str,
        rates: list[float],
    ) -> dict[float, LLMPolicyResult]:
        """Run benchmark across multiple request rates.

        Args:
            policy: Policy to benchmark
            rates: List of request rates to test

        Returns:
            Dictionary mapping rate to LLMPolicyResult
        """
        import copy

        results = {}

        async with LLMBenchmarkClient(
            self.config.control_plane_url,
            timeout_seconds=self.config.timeout_seconds,
            enable_streaming=self.config.enable_streaming,
        ) as client:
            for rate in rates:
                self._log(f"\n Testing rate: {rate} req/s")

                # Create a deep copy of config to avoid side effects
                rate_config = copy.deepcopy(self.config)
                rate_config.request_rate = rate

                # Create a new workload generator with the modified config
                rate_workload_generator = LLMWorkloadGenerator(rate_config)
                workload = rate_workload_generator.generate()

                policy_result = await self._run_policy(client, policy, workload)
                results[rate] = policy_result

        return results

    async def _run_policy(
        self,
        client: LLMBenchmarkClient,
        policy: str,
        workload: list[LLMRequest],
    ) -> LLMPolicyResult:
        """Run benchmark for a single policy.

        Args:
            client: Benchmark client
            policy: Policy name
            workload: List of requests to send

        Returns:
            LLMPolicyResult for this policy
        """
        result = LLMPolicyResult(policy=policy, metrics=LLMRequestMetrics())

        # Try to switch policy
        self._log(f"   Switching to policy: {policy}")
        policy_switched = await client.set_policy(policy)
        if not policy_switched:
            self._log("   Policy switch failed or not supported, continuing...")

        # Run warmup
        if self.config.warmup_requests > 0:
            self._log(f"   Running warmup ({self.config.warmup_requests} requests)...")
            warmup_workload = workload[: self.config.warmup_requests]
            await self._execute_workload(client, warmup_workload)

        # Start GPU monitoring
        gpu_monitor = None
        if self.enable_gpu_monitoring:
            gpu_monitor = GPUMonitor()
            gpu_monitor.start_monitoring(interval_seconds=0.5)

        # Run main workload
        main_workload = workload[self.config.warmup_requests:]
        self._log(f"   Running main workload ({len(main_workload)} requests)...")

        result.start_time = time.time()
        raw_results = await self._execute_workload(client, main_workload)
        result.end_time = time.time()

        # Stop GPU monitoring
        if gpu_monitor:
            gpu_monitor.stop_monitoring()
            result.gpu_metrics = gpu_monitor.get_summary()

        result.raw_results = raw_results

        # Collect Control Plane metrics
        result.control_plane_metrics = await client.get_metrics()

        # Compute aggregated metrics
        collector = LLMMetricsCollector()
        collector.set_time_range(result.start_time, result.end_time)
        collector.add_results(raw_results)
        result.metrics = collector.compute_metrics()

        return result

    async def _execute_workload(
        self,
        client: LLMBenchmarkClient,
        workload: list[LLMRequest],
    ) -> list[LLMRequestResult]:
        """Execute workload with timing control.

        Args:
            client: Benchmark client
            workload: List of requests to send

        Returns:
            List of LLMRequestResults
        """
        if not workload:
            return []

        results: list[LLMRequestResult] = []
        start_time = time.time()

        # Create tasks for all requests
        tasks: list[asyncio.Task] = []
        semaphore = asyncio.Semaphore(self.config.concurrent_requests)

        async def send_request_at_time(request: LLMRequest) -> LLMRequestResult:
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

    def _determine_best_performers(self, result: LLMBenchmarkResult) -> LLMBenchmarkResult:
        """Determine best performing policies.

        Args:
            result: LLMBenchmarkResult to update

        Returns:
            Updated LLMBenchmarkResult
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
            (name, p)
            for name, p in result.policy_results.items()
            if p.metrics.e2e_latency_p99_ms > 0
        ]
        if policies_with_latency:
            best_p99_policy = min(
                policies_with_latency,
                key=lambda x: x[1].metrics.e2e_latency_p99_ms,
            )
            result.best_p99_latency = best_p99_policy[0]

        return result


# Backward compatibility aliases
PolicyResult = LLMPolicyResult
BenchmarkResult = LLMBenchmarkResult
BenchmarkRunner = LLMBenchmarkRunner

__all__ = [
    "LLMPolicyResult",
    "LLMBenchmarkResult",
    "LLMBenchmarkRunner",
    # Backward compatibility
    "PolicyResult",
    "BenchmarkResult",
    "BenchmarkRunner",
]
