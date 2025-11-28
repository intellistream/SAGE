# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Throughput Experiment Module
============================

Measures maximum throughput across different request rates and scheduling policies.

This experiment:
1. Sweeps request rates: [50, 100, 200, 500, 1000] requests/second
2. Measures throughput for each scheduling policy
3. Identifies optimal request rate for each policy
4. Generates throughput vs request rate charts
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ..common.base_config import ArrivalPattern, SchedulingPolicy
from ..hybrid_scheduler.config import HybridBenchmarkConfig
from ..hybrid_scheduler.runner import HybridBenchmarkRunner
from .base_experiment import BaseExperiment

logger = logging.getLogger(__name__)

# Default request rates to sweep
DEFAULT_REQUEST_RATES = [50, 100, 200, 500, 1000]


class ThroughputExperiment(BaseExperiment):
    """Experiment to measure maximum throughput across request rates.

    This experiment sweeps through multiple request rates and measures
    the throughput achieved by each scheduling policy. It helps identify:
    - Maximum sustainable throughput for each policy
    - Optimal request rate for production deployment
    - Policy performance comparison at different loads

    Example:
        exp = ThroughputExperiment(
            name="throughput_sweep",
            control_plane_url="http://localhost:8000",
            request_rates=[50, 100, 200, 500],
        )
        result = await exp.run_full()
    """

    def __init__(
        self,
        name: str,
        control_plane_url: str = "http://localhost:8000",
        request_rates: list[int] | None = None,
        num_requests: int = 500,
        llm_ratio: float = 0.5,
        policies: list[SchedulingPolicy] | None = None,
        arrival_pattern: ArrivalPattern = ArrivalPattern.POISSON,
        output_dir: str | Path = "./.benchmarks",
        verbose: bool = True,
    ):
        """Initialize throughput experiment.

        Args:
            name: Experiment name
            control_plane_url: URL of control plane service
            request_rates: List of request rates to sweep (default: [50, 100, 200, 500, 1000])
            num_requests: Number of requests per test
            llm_ratio: Ratio of LLM requests (0.0 to 1.0)
            policies: Scheduling policies to test (default: all)
            arrival_pattern: Request arrival pattern
            output_dir: Directory for output files
            verbose: Whether to print progress messages
        """
        super().__init__(name=name, output_dir=output_dir, verbose=verbose)

        self.control_plane_url = control_plane_url
        self.request_rates = request_rates or DEFAULT_REQUEST_RATES
        self.num_requests = num_requests
        self.llm_ratio = llm_ratio
        self.policies = policies or list(SchedulingPolicy)
        self.arrival_pattern = arrival_pattern

        # Runner will be created in prepare()
        self._runners: dict[int, HybridBenchmarkRunner] = {}

    @property
    def experiment_type(self) -> str:
        """Return experiment type identifier."""
        return "throughput"

    def _get_parameters(self) -> dict[str, Any]:
        """Get experiment parameters for logging."""
        return {
            "control_plane_url": self.control_plane_url,
            "request_rates": self.request_rates,
            "num_requests": self.num_requests,
            "llm_ratio": self.llm_ratio,
            "policies": [p.value for p in self.policies],
            "arrival_pattern": self.arrival_pattern.value,
        }

    def _prepare_impl(self) -> None:
        """Create benchmark runners for each request rate."""
        for rate in self.request_rates:
            config = HybridBenchmarkConfig(
                control_plane_url=self.control_plane_url,
                num_requests=self.num_requests,
                request_rate=rate,
                llm_ratio=self.llm_ratio,
                embedding_ratio=1.0 - self.llm_ratio,
                policies=[p.value for p in self.policies],
                arrival_pattern=self.arrival_pattern,
            )
            self._runners[rate] = HybridBenchmarkRunner(config)
            self._log(f"   Prepared runner for rate={rate} req/s")

    async def _execute(self) -> list[dict[str, Any]]:
        """Execute throughput sweep experiment.

        Returns:
            List of results for each request rate
        """
        results = []

        for rate in self.request_rates:
            self._log(f"\n   📈 Testing request rate: {rate} req/s")

            runner = self._runners[rate]
            result = await runner.run()

            # Extract throughput data for each policy
            rate_result = {
                "request_rate": rate,
                "num_requests": self.num_requests,
                "policies": {},
            }

            for policy_name, policy_result in result.policy_results.items():
                metrics = policy_result.metrics

                rate_result["policies"][policy_name] = {
                    "throughput": metrics.throughput_rps,
                    "avg_latency_ms": metrics.e2e_latency_avg_ms,
                    "p99_latency_ms": metrics.e2e_latency_p99_ms,
                    "success_rate": 1.0 - metrics.error_rate,
                    "error_count": metrics.failed_requests,
                }

                self._log(
                    f"      {policy_name}: {metrics.throughput_rps:.1f} req/s, "
                    f"p99={metrics.e2e_latency_p99_ms:.1f}ms"
                )

            results.append(rate_result)

        return results

    def _compute_summary(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Compute throughput summary statistics.

        Args:
            results: Raw results from _execute()

        Returns:
            Summary with max throughput and optimal rates per policy
        """
        summary: dict[str, Any] = {
            "policies": {},
            "best_policy": None,
            "max_throughput": 0.0,
        }

        # Aggregate per-policy statistics
        for policy in self.policies:
            policy_name = policy.value
            throughputs = []
            optimal_rate = 0
            max_throughput = 0.0

            for result in results:
                rate = result["request_rate"]
                policy_data = result["policies"].get(policy_name, {})
                throughput = policy_data.get("throughput", 0.0)
                throughputs.append(throughput)

                if throughput > max_throughput:
                    max_throughput = throughput
                    optimal_rate = rate

            summary["policies"][policy_name] = {
                "max_throughput": max_throughput,
                "optimal_rate": optimal_rate,
                "throughputs_by_rate": dict(
                    zip(self.request_rates, throughputs, strict=False)
                ),
            }

            # Track global best
            if max_throughput > summary["max_throughput"]:
                summary["max_throughput"] = max_throughput
                summary["best_policy"] = policy_name

        return summary

    def _visualize_impl(self) -> list[Path]:
        """Generate throughput charts.

        Returns:
            List of paths to generated charts
        """
        charts = []

        if self._result is None or not self._result.results:
            return charts

        try:
            from ..visualization.charts import BenchmarkCharts

            chart_gen = BenchmarkCharts(output_dir=self.output_dir)

            # Prepare data for throughput vs request rate chart
            # Format: {policy_name: [(rate, throughput), ...]}
            throughput_data: dict[str, list[tuple[float, float]]] = {}

            for policy in self.policies:
                policy_name = policy.value
                throughput_data[policy_name] = []

                for result in self._result.results:
                    rate = float(result["request_rate"])
                    throughput = result["policies"].get(policy_name, {}).get(
                        "throughput", 0.0
                    )
                    throughput_data[policy_name].append((rate, throughput))

            # Generate throughput chart for each policy
            for policy_name, rate_results in throughput_data.items():
                chart_path = chart_gen.plot_throughput_vs_rate(
                    rate_results=rate_results,
                    title=f"Throughput vs Rate - {policy_name}",
                )
                if chart_path:
                    charts.append(chart_path)

            # Generate policy comparison bar chart
            if self._result.summary.get("policies"):
                # Convert summary to policy_metrics format
                policy_metrics = {}
                for policy, data in self._result.summary["policies"].items():
                    policy_metrics[policy] = {
                        "throughput": {
                            "requests_per_second": data["max_throughput"]
                        }
                    }
                chart_path = chart_gen.plot_throughput_comparison(
                    policy_metrics=policy_metrics,
                    title=f"Max Throughput by Policy - {self.name}",
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
__all__ = ["ThroughputExperiment", "DEFAULT_REQUEST_RATES"]
