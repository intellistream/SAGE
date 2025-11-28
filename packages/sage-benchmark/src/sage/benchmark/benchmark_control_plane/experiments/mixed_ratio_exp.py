# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Mixed Ratio Experiment Module
=============================

Measures performance impact of different LLM/Embedding request ratios.

This experiment:
1. Sweeps LLM ratios: [0%, 25%, 50%, 75%, 100%]
2. Measures throughput, latency, and SLO compliance at each ratio
3. Identifies optimal ratio for hybrid scheduling
4. Generates ratio sweep charts and analysis
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ..common.base_config import ArrivalPattern, SchedulingPolicy
from ..hybrid_scheduler.config import HybridBenchmarkConfig, HybridSLOConfig
from ..hybrid_scheduler.runner import HybridBenchmarkRunner
from .base_experiment import BaseExperiment

logger = logging.getLogger(__name__)

# Default LLM ratios to sweep (0%, 25%, 50%, 75%, 100%)
DEFAULT_LLM_RATIOS = [0.0, 0.25, 0.5, 0.75, 1.0]


class MixedRatioExperiment(BaseExperiment):
    """Experiment to measure impact of LLM/Embedding ratio on performance.

    This experiment sweeps through different ratios of LLM to Embedding
    requests and measures performance metrics for each configuration.
    It helps understand:
    - How workload mix affects throughput
    - Latency characteristics at different ratios
    - Optimal ratio for hybrid scheduling policies
    - Policy effectiveness for different workload mixes

    Example:
        exp = MixedRatioExperiment(
            name="mixed_ratio_sweep",
            control_plane_url="http://localhost:8000",
            llm_ratios=[0.0, 0.25, 0.5, 0.75, 1.0],
        )
        result = await exp.run_full()
    """

    def __init__(
        self,
        name: str,
        control_plane_url: str = "http://localhost:8000",
        llm_ratios: list[float] | None = None,
        request_rate: int = 100,
        num_requests: int = 500,
        policies: list[SchedulingPolicy] | None = None,
        arrival_pattern: ArrivalPattern = ArrivalPattern.POISSON,
        slo_config: HybridSLOConfig | None = None,
        output_dir: str | Path = "./.benchmarks",
        verbose: bool = True,
    ):
        """Initialize mixed ratio experiment.

        Args:
            name: Experiment name
            control_plane_url: URL of control plane service
            llm_ratios: List of LLM ratios to sweep (default: [0.0, 0.25, 0.5, 0.75, 1.0])
            request_rate: Fixed request rate for tests
            num_requests: Number of requests per test
            policies: Scheduling policies to test (default: all)
            arrival_pattern: Request arrival pattern
            slo_config: SLO configuration
            output_dir: Directory for output files
            verbose: Whether to print progress messages
        """
        super().__init__(name=name, output_dir=output_dir, verbose=verbose)

        self.control_plane_url = control_plane_url
        self.llm_ratios = llm_ratios or DEFAULT_LLM_RATIOS
        self.request_rate = request_rate
        self.num_requests = num_requests
        self.policies = policies or list(SchedulingPolicy)
        self.arrival_pattern = arrival_pattern
        self.slo_config = slo_config or HybridSLOConfig()

        self._runners: dict[float, HybridBenchmarkRunner] = {}

    @property
    def experiment_type(self) -> str:
        """Return experiment type identifier."""
        return "mixed_ratio"

    def _get_parameters(self) -> dict[str, Any]:
        """Get experiment parameters for logging."""
        return {
            "control_plane_url": self.control_plane_url,
            "llm_ratios": self.llm_ratios,
            "request_rate": self.request_rate,
            "num_requests": self.num_requests,
            "policies": [p.value for p in self.policies],
            "arrival_pattern": self.arrival_pattern.value,
            "slo_config": self.slo_config.to_dict(),
        }

    def _prepare_impl(self) -> None:
        """Create benchmark runners for each LLM ratio."""
        for ratio in self.llm_ratios:
            config = HybridBenchmarkConfig(
                control_plane_url=self.control_plane_url,
                num_requests=self.num_requests,
                request_rate=self.request_rate,
                llm_ratio=ratio,
                embedding_ratio=1.0 - ratio,
                policies=[p.value for p in self.policies],
                arrival_pattern=self.arrival_pattern,
                hybrid_slo_config=self.slo_config,
            )
            self._runners[ratio] = HybridBenchmarkRunner(config)
            self._log(f"   Prepared runner for LLM ratio={ratio:.0%}")

    async def _execute(self) -> list[dict[str, Any]]:
        """Execute mixed ratio sweep experiment.

        Returns:
            List of results for each LLM ratio
        """
        results = []

        for ratio in self.llm_ratios:
            emb_ratio = 1.0 - ratio
            self._log(
                f"\n   🔄 Testing ratio: LLM={ratio:.0%}, Embedding={emb_ratio:.0%}"
            )

            runner = self._runners[ratio]
            result = await runner.run()

            # Extract metrics for each policy at this ratio
            ratio_result = {
                "llm_ratio": ratio,
                "embedding_ratio": emb_ratio,
                "request_rate": self.request_rate,
                "num_requests": self.num_requests,
                "policies": {},
            }

            for policy_name, policy_result in result.policy_results.items():
                metrics = policy_result.metrics

                # Compute separate stats for LLM and Embedding requests
                llm_stats, emb_stats = self._compute_type_stats(
                    policy_result.raw_results
                )

                ratio_result["policies"][policy_name] = {
                    "throughput": metrics.throughput_rps,
                    "avg_latency_ms": metrics.e2e_latency_avg_ms,
                    "p50_latency_ms": metrics.e2e_latency_p50_ms,
                    "p99_latency_ms": metrics.e2e_latency_p99_ms,
                    "success_rate": 1.0 - metrics.error_rate,
                    "slo_compliance": self._compute_slo_compliance(
                        policy_result.raw_results
                    ),
                    "llm_stats": llm_stats,
                    "embedding_stats": emb_stats,
                }

                self._log(
                    f"      {policy_name}: throughput={metrics.throughput_rps:.1f}, "
                    f"p99={metrics.e2e_latency_p99_ms:.1f}ms"
                )

            results.append(ratio_result)

        return results

    def _compute_type_stats(
        self, raw_results: list[Any]
    ) -> tuple[dict[str, float], dict[str, float]]:
        """Compute separate statistics for LLM and Embedding requests.

        Args:
            raw_results: Raw results from benchmark run

        Returns:
            Tuple of (llm_stats, embedding_stats) dictionaries
        """
        llm_latencies = []
        emb_latencies = []

        for result in raw_results:
            if hasattr(result, "latency_ms"):
                latency = result.latency_ms
                request_type = getattr(result, "request_type", "llm_chat")
            elif isinstance(result, dict):
                latency = result.get("latency_ms", 0)
                request_type = result.get("request_type", "llm_chat")
            else:
                continue

            if "embedding" in str(request_type).lower():
                emb_latencies.append(latency)
            else:
                llm_latencies.append(latency)

        def compute_stats(latencies: list[float]) -> dict[str, float]:
            if not latencies:
                return {
                    "count": 0,
                    "avg_latency_ms": 0.0,
                    "p50_latency_ms": 0.0,
                    "p99_latency_ms": 0.0,
                }

            sorted_lat = sorted(latencies)
            n = len(sorted_lat)

            return {
                "count": n,
                "avg_latency_ms": sum(latencies) / n,
                "p50_latency_ms": sorted_lat[int(n * 0.5)],
                "p99_latency_ms": sorted_lat[min(int(n * 0.99), n - 1)],
            }

        return compute_stats(llm_latencies), compute_stats(emb_latencies)

    def _compute_slo_compliance(self, raw_results: list[Any]) -> float:
        """Compute overall SLO compliance rate.

        Args:
            raw_results: Raw results from benchmark run

        Returns:
            SLO compliance rate (0.0 to 1.0)
        """
        met_count = 0
        total_count = 0

        for result in raw_results:
            if hasattr(result, "latency_ms"):
                latency = result.latency_ms
                request_type = getattr(result, "request_type", "llm_chat")
                priority = getattr(result, "priority", "NORMAL")
            elif isinstance(result, dict):
                latency = result.get("latency_ms", 0)
                request_type = result.get("request_type", "llm_chat")
                priority = result.get("priority", "NORMAL")
            else:
                continue

            total_count += 1
            deadline = self.slo_config.get_deadline_for_request(priority, request_type)

            if latency <= deadline:
                met_count += 1

        return met_count / total_count if total_count > 0 else 0.0

    def _compute_summary(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Compute mixed ratio summary statistics.

        Args:
            results: Raw results from _execute()

        Returns:
            Summary with optimal ratios and policy comparisons
        """
        summary: dict[str, Any] = {
            "llm_ratios": self.llm_ratios,
            "request_rate": self.request_rate,
            "policies": {},
            "optimal_ratio_by_policy": {},
            "best_overall_config": None,
            "best_throughput": 0.0,
        }

        # Aggregate per-policy statistics
        for policy in self.policies:
            policy_name = policy.value
            throughputs = []
            compliances = []
            optimal_ratio = 0.0
            max_throughput = 0.0

            for result in results:
                ratio = result["llm_ratio"]
                policy_data = result["policies"].get(policy_name, {})
                throughput = policy_data.get("throughput", 0.0)
                compliance = policy_data.get("slo_compliance", 0.0)

                throughputs.append(throughput)
                compliances.append(compliance)

                if throughput > max_throughput:
                    max_throughput = throughput
                    optimal_ratio = ratio

            summary["policies"][policy_name] = {
                "throughputs_by_ratio": dict(
                    zip(self.llm_ratios, throughputs, strict=False)
                ),
                "compliances_by_ratio": dict(
                    zip(self.llm_ratios, compliances, strict=False)
                ),
                "max_throughput": max_throughput,
                "optimal_ratio": optimal_ratio,
                "avg_compliance": (
                    sum(compliances) / len(compliances) if compliances else 0.0
                ),
            }

            summary["optimal_ratio_by_policy"][policy_name] = optimal_ratio

            # Track global best
            if max_throughput > summary["best_throughput"]:
                summary["best_throughput"] = max_throughput
                summary["best_overall_config"] = {
                    "policy": policy_name,
                    "llm_ratio": optimal_ratio,
                    "throughput": max_throughput,
                }

        return summary

    def _visualize_impl(self) -> list[Path]:
        """Generate mixed ratio charts.

        Returns:
            List of paths to generated charts
        """
        charts = []

        if self._result is None or not self._result.results:
            return charts

        try:
            from ..visualization.charts import BenchmarkCharts

            chart_gen = BenchmarkCharts(output_dir=self.output_dir)

            # Generate mixed ratio impact chart for each policy
            for policy in self.policies:
                policy_name = policy.value
                ratio_results = []

                for result in self._result.results:
                    policy_metrics = result["policies"].get(policy_name, {})
                    ratio_results.append({
                        "llm_ratio": result["llm_ratio"],
                        "throughput_rps": policy_metrics.get("throughput", 0.0),
                        "slo_compliance_rate": policy_metrics.get("slo_compliance", 0.0),
                    })

                chart_path = chart_gen.plot_mixed_ratio_impact(
                    ratio_results=ratio_results,
                    title=f"Performance vs LLM Ratio - {policy_name}",
                )
                if chart_path:
                    charts.append(chart_path)

            # Generate throughput comparison at 50% ratio (typical hybrid workload)
            mid_ratio_result = None
            for result in self._result.results:
                if abs(result["llm_ratio"] - 0.5) < 0.1:
                    mid_ratio_result = result
                    break

            if mid_ratio_result:
                policy_metrics = {}
                for policy_name, policy_data in mid_ratio_result["policies"].items():
                    policy_metrics[policy_name] = {
                        "throughput": {
                            "requests_per_second": policy_data.get("throughput", 0.0)
                        }
                    }

                chart_path = chart_gen.plot_throughput_comparison(
                    policy_metrics=policy_metrics,
                    title=f"Throughput at 50% LLM Ratio - {self.name}",
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
__all__ = ["MixedRatioExperiment", "DEFAULT_LLM_RATIOS"]
