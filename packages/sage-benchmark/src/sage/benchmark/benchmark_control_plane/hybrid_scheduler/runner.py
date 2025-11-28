# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Hybrid Benchmark Runner Module
==============================

Orchestrates hybrid (LLM + Embedding) benchmark execution flow.

This module handles:
- Environment validation
- Policy switching
- Warmup execution
- Mixed workload execution with timing control
- GPU resource monitoring
- Results collection
- Auto-visualization of benchmark results
"""

from __future__ import annotations

import asyncio
import copy
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..common.gpu_monitor import GPUMetricsSummary, GPUMonitor

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .workload import HybridRequest

from .client import HybridBenchmarkClient, HybridRequestResult
from .config import HybridBenchmarkConfig
from .metrics import HybridMetricsCollector, HybridRequestMetrics
from .workload import HybridWorkloadGenerator


@dataclass
class HybridPolicyResult:
    """Results for a single policy benchmark run in hybrid mode.

    Attributes:
        policy: Policy name
        metrics: Aggregated hybrid metrics for this policy
        raw_results: List of individual request results
        control_plane_metrics: Metrics from Control Plane
        gpu_metrics: GPU resource usage metrics
        start_time: Run start time
        end_time: Run end time
    """

    policy: str
    metrics: HybridRequestMetrics
    raw_results: list[HybridRequestResult] = field(default_factory=list)
    control_plane_metrics: dict[str, Any] = field(default_factory=dict)
    gpu_metrics: GPUMetricsSummary | None = None
    start_time: float = 0.0
    end_time: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "policy": self.policy,
            "metrics": self.metrics.to_dict(),
            "raw_results": [r.to_dict() for r in self.raw_results],
            "control_plane_metrics": self.control_plane_metrics,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }
        if self.gpu_metrics:
            result["gpu_metrics"] = self.gpu_metrics.to_dict()
        return result


@dataclass
class HybridBenchmarkResult:
    """Complete hybrid benchmark results across all policies.

    Attributes:
        config: Benchmark configuration used
        policy_results: Results for each policy
        best_throughput: Policy with best overall throughput
        best_llm_throughput: Policy with best LLM throughput
        best_embedding_throughput: Policy with best Embedding throughput
        best_slo_compliance: Policy with best SLO compliance
        best_p99_latency: Policy with best P99 latency
    """

    config: dict[str, Any]
    policy_results: dict[str, HybridPolicyResult] = field(default_factory=dict)
    best_throughput: str = ""
    best_llm_throughput: str = ""
    best_embedding_throughput: str = ""
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
                "best_llm_throughput": self.best_llm_throughput,
                "best_embedding_throughput": self.best_embedding_throughput,
                "best_slo_compliance": self.best_slo_compliance,
                "best_p99_latency": self.best_p99_latency,
            },
        }


class HybridBenchmarkRunner:
    """Orchestrates hybrid (LLM + Embedding) benchmark execution.

    This class manages the complete benchmark flow for mixed workloads:
    1. Validate environment (Control Plane reachability)
    2. For each policy:
       a. Switch Control Plane to policy
       b. Run warmup requests (both LLM and Embedding)
       c. Start GPU monitoring
       d. Execute mixed workload with timing control
       e. Stop GPU monitoring and collect metrics
       f. Collect request metrics
    3. Generate comparison results

    Example:
        config = HybridBenchmarkConfig(
            control_plane_url="http://localhost:8000",
            num_requests=1000,
            llm_ratio=0.7,
            embedding_ratio=0.3,
            policies=["fifo", "priority", "hybrid_slo"],
        )
        runner = HybridBenchmarkRunner(config)
        result = await runner.run()
    """

    def __init__(
        self,
        config: HybridBenchmarkConfig,
        verbose: bool = True,
        enable_gpu_monitoring: bool = True,
        gpu_monitor_interval: float = 0.5,
        output_dir: str | Path | None = None,
    ):
        """Initialize hybrid benchmark runner.

        Args:
            config: Hybrid benchmark configuration
            verbose: Whether to print progress messages
            enable_gpu_monitoring: Whether to monitor GPU resources
            gpu_monitor_interval: GPU sampling interval in seconds
            output_dir: Directory for output files (charts, reports)
        """
        self.config = config
        self.verbose = verbose
        self.enable_gpu_monitoring = enable_gpu_monitoring
        self.gpu_monitor_interval = gpu_monitor_interval
        self.output_dir = Path(output_dir) if output_dir else Path(".benchmarks")
        self.workload_generator = HybridWorkloadGenerator(config)

    def _log(self, message: str) -> None:
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    async def run(self, auto_visualize: bool | None = None) -> HybridBenchmarkResult:
        """Run the complete hybrid benchmark.

        Args:
            auto_visualize: Override config.auto_visualize setting

        Returns:
            HybridBenchmarkResult with results for all policies
        """
        # Validate configuration
        errors = self.config.validate()
        if errors:
            raise ValueError(f"Invalid configuration: {errors}")

        result = HybridBenchmarkResult(config=self.config.to_dict())

        # Generate workload once (same workload for all policies)
        self._log("\n📝 Generating hybrid workload...")
        workload = self.workload_generator.generate()

        # Count request types
        llm_count = sum(1 for r in workload if r.is_llm_request)
        embed_count = sum(1 for r in workload if r.is_embedding_request)
        self._log(f"   Generated {len(workload)} requests (LLM: {llm_count}, Embedding: {embed_count})")

        async with HybridBenchmarkClient(
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
                self._log(f"   📊 Overall Throughput: {policy_result.metrics.throughput_rps:.2f} req/s")
                self._log(f"   🤖 LLM Throughput: {policy_result.metrics.llm_throughput_rps:.2f} req/s")
                self._log(f"   📝 Embedding Throughput: {policy_result.metrics.embedding_throughput_rps:.2f} req/s")
                self._log(f"   📈 SLO Compliance: {policy_result.metrics.slo_compliance_rate:.1%}")

                if policy_result.gpu_metrics:
                    self._log(f"   🎮 GPU Utilization: {policy_result.gpu_metrics.utilization_avg:.1f}%")

        # Determine best performers
        result = self._determine_best_performers(result)

        # Auto visualization
        should_visualize = (
            auto_visualize if auto_visualize is not None else self.config.auto_visualize
        )
        if should_visualize:
            self._generate_visualizations(result)

        return result

    def _generate_visualizations(self, result: HybridBenchmarkResult) -> None:
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
                report_name="hybrid_benchmark",
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

    async def run_single_policy(self, policy: str) -> HybridPolicyResult:
        """Run benchmark for a single policy.

        Args:
            policy: Policy name to benchmark

        Returns:
            HybridPolicyResult for the specified policy
        """
        workload = self.workload_generator.generate()

        async with HybridBenchmarkClient(
            self.config.control_plane_url,
            timeout_seconds=self.config.timeout_seconds,
            enable_streaming=self.config.enable_streaming,
        ) as client:
            return await self._run_policy(client, policy, workload)

    async def run_rate_sweep(
        self,
        policy: str,
        rates: list[float],
    ) -> dict[float, HybridPolicyResult]:
        """Run benchmark across multiple request rates.

        Args:
            policy: Policy to benchmark
            rates: List of request rates to test

        Returns:
            Dictionary mapping rate to HybridPolicyResult
        """
        results: dict[float, HybridPolicyResult] = {}

        async with HybridBenchmarkClient(
            self.config.control_plane_url,
            timeout_seconds=self.config.timeout_seconds,
            enable_streaming=self.config.enable_streaming,
        ) as client:
            for rate in rates:
                self._log(f"\n🔄 Testing rate: {rate} req/s")

                # Create a deep copy of config to avoid side effects
                rate_config = copy.deepcopy(self.config)
                rate_config.request_rate = rate

                # Create a new workload generator with the modified config
                rate_workload_generator = HybridWorkloadGenerator(rate_config)
                workload = rate_workload_generator.generate()

                policy_result = await self._run_policy(client, policy, workload)
                results[rate] = policy_result

        return results

    async def run_ratio_sweep(
        self,
        policy: str,
        llm_ratios: list[float],
    ) -> dict[float, HybridPolicyResult]:
        """Run benchmark across multiple LLM/Embedding ratios.

        Args:
            policy: Policy to benchmark
            llm_ratios: List of LLM ratios to test (embedding_ratio = 1 - llm_ratio)

        Returns:
            Dictionary mapping LLM ratio to HybridPolicyResult
        """
        results: dict[float, HybridPolicyResult] = {}

        async with HybridBenchmarkClient(
            self.config.control_plane_url,
            timeout_seconds=self.config.timeout_seconds,
            enable_streaming=self.config.enable_streaming,
        ) as client:
            for llm_ratio in llm_ratios:
                embedding_ratio = 1.0 - llm_ratio
                self._log(f"\n🔄 Testing ratio: LLM={llm_ratio:.0%}, Embedding={embedding_ratio:.0%}")

                # Create a deep copy of config to avoid side effects
                ratio_config = copy.deepcopy(self.config)
                ratio_config.llm_ratio = llm_ratio
                ratio_config.embedding_ratio = embedding_ratio

                # Create a new workload generator with the modified config
                ratio_workload_generator = HybridWorkloadGenerator(ratio_config)
                workload = ratio_workload_generator.generate()

                policy_result = await self._run_policy(client, policy, workload)
                results[llm_ratio] = policy_result

        return results

    async def _run_policy(
        self,
        client: HybridBenchmarkClient,
        policy: str,
        workload: list[HybridRequest],
    ) -> HybridPolicyResult:
        """Run benchmark for a single policy.

        Args:
            client: Hybrid benchmark client
            policy: Policy name
            workload: List of hybrid requests to send

        Returns:
            HybridPolicyResult for this policy
        """
        result = HybridPolicyResult(
            policy=policy,
            metrics=HybridRequestMetrics(),
        )

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

        # Start GPU monitoring
        gpu_monitor: GPUMonitor | None = None
        if self.enable_gpu_monitoring:
            gpu_monitor = GPUMonitor()
            gpu_monitor.start_monitoring(interval_seconds=self.gpu_monitor_interval)
            self._log("   🎮 GPU monitoring started")

        # Run main workload
        main_workload = workload[self.config.warmup_requests :]
        self._log(f"   ▶️  Running main workload ({len(main_workload)} requests)...")

        result.start_time = time.time()
        raw_results = await self._execute_workload(client, main_workload)
        result.end_time = time.time()

        result.raw_results = raw_results

        # Stop GPU monitoring and get summary
        if gpu_monitor:
            gpu_monitor.stop_monitoring()
            result.gpu_metrics = gpu_monitor.get_summary()
            self._log("   🎮 GPU monitoring stopped")

        # Collect Control Plane metrics
        result.control_plane_metrics = await client.get_metrics()

        # Compute aggregated metrics
        collector = HybridMetricsCollector()
        collector.set_time_range(result.start_time, result.end_time)
        collector.add_results(raw_results)
        result.metrics = collector.compute_metrics()

        return result

    async def _execute_workload(
        self,
        client: HybridBenchmarkClient,
        workload: list[HybridRequest],
    ) -> list[HybridRequestResult]:
        """Execute workload with timing control.

        Args:
            client: Hybrid benchmark client
            workload: List of hybrid requests to send

        Returns:
            List of HybridRequestResults
        """
        if not workload:
            return []

        results: list[HybridRequestResult] = []
        start_time = time.time()

        # Create tasks for all requests
        tasks: list[asyncio.Task[HybridRequestResult]] = []
        semaphore = asyncio.Semaphore(self.config.concurrent_requests)

        async def send_request_at_time(request: HybridRequest) -> HybridRequestResult:
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
        completed = await asyncio.gather(*tasks)
        results = list(completed)

        return results

    def _determine_best_performers(
        self, result: HybridBenchmarkResult
    ) -> HybridBenchmarkResult:
        """Determine best performing policies.

        Args:
            result: HybridBenchmarkResult to update

        Returns:
            Updated HybridBenchmarkResult
        """
        if not result.policy_results:
            return result

        # Best overall throughput
        best_throughput_policy = max(
            result.policy_results.items(),
            key=lambda x: x[1].metrics.throughput_rps,
        )
        result.best_throughput = best_throughput_policy[0]

        # Best LLM throughput
        best_llm_policy = max(
            result.policy_results.items(),
            key=lambda x: x[1].metrics.llm_throughput_rps,
        )
        result.best_llm_throughput = best_llm_policy[0]

        # Best Embedding throughput
        best_embedding_policy = max(
            result.policy_results.items(),
            key=lambda x: x[1].metrics.embedding_throughput_rps,
        )
        result.best_embedding_throughput = best_embedding_policy[0]

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
