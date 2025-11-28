# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Latency Experiment Module
=========================

Measures latency distribution under fixed load conditions.

This experiment:
1. Runs benchmarks at a fixed request rate
2. Collects detailed latency statistics (p50, p90, p95, p99, p999)
3. Analyzes latency distribution for each policy
4. Generates latency distribution charts and CDF plots
"""

from __future__ import annotations

import logging
import statistics
from pathlib import Path
from typing import Any

from ..common.base_config import ArrivalPattern, SchedulingPolicy
from ..hybrid_scheduler.config import HybridBenchmarkConfig
from ..hybrid_scheduler.runner import HybridBenchmarkRunner
from .base_experiment import BaseExperiment

logger = logging.getLogger(__name__)

# Default latency percentiles to compute
DEFAULT_PERCENTILES = [50, 90, 95, 99, 99.9]


class LatencyExperiment(BaseExperiment):
    """Experiment to measure latency distribution under fixed load.

    This experiment runs benchmarks at a fixed request rate and analyzes
    the latency distribution for each scheduling policy. It helps understand:
    - Latency percentiles (p50, p90, p95, p99, p999)
    - Latency variance and stability
    - Tail latency behavior
    - Policy comparison for latency-sensitive workloads

    Example:
        exp = LatencyExperiment(
            name="latency_analysis",
            control_plane_url="http://localhost:8000",
            request_rate=100,
            num_requests=1000,
        )
        result = await exp.run_full()
    """

    def __init__(
        self,
        name: str,
        control_plane_url: str = "http://localhost:8000",
        request_rate: int = 100,
        num_requests: int = 1000,
        llm_ratio: float = 0.5,
        policies: list[SchedulingPolicy] | None = None,
        arrival_pattern: ArrivalPattern = ArrivalPattern.POISSON,
        percentiles: list[float] | None = None,
        output_dir: str | Path = "./.benchmarks",
        verbose: bool = True,
    ):
        """Initialize latency experiment.

        Args:
            name: Experiment name
            control_plane_url: URL of control plane service
            request_rate: Fixed request rate for the test
            num_requests: Number of requests to send
            llm_ratio: Ratio of LLM requests (0.0 to 1.0)
            policies: Scheduling policies to test (default: all)
            arrival_pattern: Request arrival pattern
            percentiles: Percentiles to compute (default: [50, 90, 95, 99, 99.9])
            output_dir: Directory for output files
            verbose: Whether to print progress messages
        """
        super().__init__(name=name, output_dir=output_dir, verbose=verbose)

        self.control_plane_url = control_plane_url
        self.request_rate = request_rate
        self.num_requests = num_requests
        self.llm_ratio = llm_ratio
        self.policies = policies or list(SchedulingPolicy)
        self.arrival_pattern = arrival_pattern
        self.percentiles = percentiles or DEFAULT_PERCENTILES

        self._runner: HybridBenchmarkRunner | None = None

    @property
    def experiment_type(self) -> str:
        """Return experiment type identifier."""
        return "latency"

    def _get_parameters(self) -> dict[str, Any]:
        """Get experiment parameters for logging."""
        return {
            "control_plane_url": self.control_plane_url,
            "request_rate": self.request_rate,
            "num_requests": self.num_requests,
            "llm_ratio": self.llm_ratio,
            "policies": [p.value for p in self.policies],
            "arrival_pattern": self.arrival_pattern.value,
            "percentiles": self.percentiles,
        }

    def _prepare_impl(self) -> None:
        """Create benchmark runner."""
        config = HybridBenchmarkConfig(
            control_plane_url=self.control_plane_url,
            num_requests=self.num_requests,
            request_rate=self.request_rate,
            llm_ratio=self.llm_ratio,
            embedding_ratio=1.0 - self.llm_ratio,
            policies=[p.value for p in self.policies],
            arrival_pattern=self.arrival_pattern,
        )
        self._runner = HybridBenchmarkRunner(config)
        self._log(f"   Prepared runner for rate={self.request_rate} req/s")

    async def _execute(self) -> list[dict[str, Any]]:
        """Execute latency analysis experiment.

        Returns:
            List of latency results for each policy
        """
        if self._runner is None:
            raise RuntimeError("Runner not initialized")

        self._log(f"\n   📊 Running latency analysis at {self.request_rate} req/s")

        result = await self._runner.run()
        results = []

        for policy_name, policy_result in result.policy_results.items():
            metrics = policy_result.metrics

            # Collect raw latencies from results
            raw_latencies = self._extract_latencies(policy_result.raw_results)

            # Compute percentiles
            percentile_values = self._compute_percentiles(raw_latencies)

            policy_data = {
                "policy": policy_name,
                "request_rate": self.request_rate,
                "num_requests": self.num_requests,
                "latency_stats": {
                    "mean_ms": metrics.e2e_latency_avg_ms,
                    "min_ms": metrics.e2e_latency_min_ms,
                    "max_ms": metrics.e2e_latency_max_ms,
                    "p50_ms": metrics.e2e_latency_p50_ms,
                    "p90_ms": percentile_values.get("p90", 0.0),
                    "p95_ms": metrics.e2e_latency_p95_ms,
                    "p99_ms": metrics.e2e_latency_p99_ms,
                    "std_dev_ms": self._compute_std_dev(raw_latencies),
                },
                "percentiles": percentile_values,
                "raw_latencies": raw_latencies[:100],  # Store first 100 for distribution
                "success_rate": 1.0 - metrics.error_rate,
            }

            results.append(policy_data)

            self._log(
                f"      {policy_name}: mean={metrics.e2e_latency_avg_ms:.1f}ms, "
                f"p99={metrics.e2e_latency_p99_ms:.1f}ms, "
                f"stddev={policy_data['latency_stats']['std_dev_ms']:.1f}ms"
            )

        return results

    def _extract_latencies(self, raw_results: list[Any]) -> list[float]:
        """Extract latency values from raw benchmark results.

        Args:
            raw_results: Raw results from benchmark run

        Returns:
            List of latency values in milliseconds
        """
        latencies = []
        for result in raw_results:
            if hasattr(result, "latency_ms"):
                latencies.append(result.latency_ms)
            elif isinstance(result, dict) and "latency_ms" in result:
                latencies.append(result["latency_ms"])
        return latencies

    def _compute_percentiles(self, latencies: list[float]) -> dict[str, float]:
        """Compute latency percentiles.

        Args:
            latencies: List of latency values

        Returns:
            Dictionary mapping percentile names to values
        """
        if not latencies:
            return {f"p{p}": 0.0 for p in self.percentiles}

        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)

        percentile_values = {}
        for p in self.percentiles:
            idx = int((p / 100.0) * n)
            idx = min(idx, n - 1)
            percentile_values[f"p{p}"] = sorted_latencies[idx]

        return percentile_values

    def _compute_std_dev(self, latencies: list[float]) -> float:
        """Compute standard deviation of latencies.

        Args:
            latencies: List of latency values

        Returns:
            Standard deviation (0.0 if insufficient data)
        """
        if len(latencies) < 2:
            return 0.0
        return statistics.stdev(latencies)

    def _compute_summary(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Compute latency summary statistics.

        Args:
            results: Raw results from _execute()

        Returns:
            Summary with latency comparison across policies
        """
        summary: dict[str, Any] = {
            "request_rate": self.request_rate,
            "num_requests": self.num_requests,
            "policies": {},
            "best_policy_p50": None,
            "best_policy_p99": None,
            "lowest_p50": float("inf"),
            "lowest_p99": float("inf"),
        }

        for result in results:
            policy = result["policy"]
            stats = result["latency_stats"]

            summary["policies"][policy] = {
                "mean_ms": stats["mean_ms"],
                "p50_ms": stats["p50_ms"],
                "p99_ms": stats["p99_ms"],
                "std_dev_ms": stats["std_dev_ms"],
                "success_rate": result["success_rate"],
            }

            # Track best policies
            if stats["p50_ms"] < summary["lowest_p50"]:
                summary["lowest_p50"] = stats["p50_ms"]
                summary["best_policy_p50"] = policy

            if stats["p99_ms"] < summary["lowest_p99"]:
                summary["lowest_p99"] = stats["p99_ms"]
                summary["best_policy_p99"] = policy

        return summary

    def _visualize_impl(self) -> list[Path]:
        """Generate latency charts.

        Returns:
            List of paths to generated charts
        """
        charts = []

        if self._result is None or not self._result.results:
            return charts

        try:
            from ..visualization.charts import BenchmarkCharts

            chart_gen = BenchmarkCharts(output_dir=self.output_dir)

            # Prepare data for latency distribution chart
            # Format: {policy_name: [latency1, latency2, ...]}
            latency_data: dict[str, list[float]] = {}

            for result in self._result.results:
                policy = result["policy"]
                latencies = result.get("raw_latencies", [])
                if latencies:
                    latency_data[policy] = latencies

            # Generate latency distribution chart for each policy
            for policy_name, latencies in latency_data.items():
                if latencies:
                    chart_path = chart_gen.plot_latency_distribution(
                        latencies=latencies,
                        title=f"Latency Distribution - {policy_name}",
                    )
                    if chart_path:
                        charts.append(chart_path)

            # Generate percentile comparison chart
            policy_metrics: dict[str, dict[str, Any]] = {}
            for result in self._result.results:
                policy = result["policy"]
                stats = result.get("latency_stats", {})
                policy_metrics[policy] = {
                    "e2e_latency_ms": {
                        "p50": stats.get("p50_ms", 0),
                        "p95": stats.get("p95_ms", 0),
                        "p99": stats.get("p99_ms", 0),
                    }
                }

            if policy_metrics:
                chart_path = chart_gen.plot_latency_percentiles(
                    policy_metrics=policy_metrics,
                    title=f"Latency Percentiles - {self.name}",
                )
                if chart_path:
                    charts.append(chart_path)

            # Generate CDF plot
            if latency_data:
                chart_path = chart_gen.plot_latency_cdf(
                    policy_latencies=latency_data,
                    title=f"Latency CDF - {self.name}",
                )
                if chart_path:
                    charts.append(chart_path)

        except ImportError:
            self._log("   Warning: Could not import BenchmarkCharts for visualization")
        except Exception as e:
            self._log(f"   Warning: Visualization failed: {e}")
            logger.exception("Visualization error")

        return charts


# Re-export
__all__ = ["LatencyExperiment", "DEFAULT_PERCENTILES"]
