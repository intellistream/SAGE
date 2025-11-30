# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
SLO Compliance Experiment Module
================================

Measures SLO compliance rates across different scheduling policies.

This experiment:
1. Defines SLO targets for different request types and priorities
2. Measures compliance rates under various load conditions
3. Compares SLO-aware policies vs baseline policies
4. Generates SLO compliance charts and violation analysis
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

# Default load levels to test (request rates)
DEFAULT_LOAD_LEVELS = [50, 100, 200, 500]


class SLOComplianceExperiment(BaseExperiment):
    """Experiment to measure SLO compliance across policies.

    This experiment tests SLO compliance rates for different scheduling
    policies under various load conditions. It helps understand:
    - Which policies best meet SLO targets
    - How SLO compliance degrades under load
    - Violation patterns by request type and priority
    - Trade-offs between SLO compliance and throughput

    Example:
        exp = SLOComplianceExperiment(
            name="slo_compliance",
            control_plane_url="http://localhost:8000",
            load_levels=[50, 100, 200],
        )
        result = await exp.run_full()
    """

    def __init__(
        self,
        name: str,
        control_plane_url: str = "http://localhost:8000",
        load_levels: list[int] | None = None,
        num_requests: int = 500,
        llm_ratio: float = 0.5,
        policies: list[SchedulingPolicy] | None = None,
        arrival_pattern: ArrivalPattern = ArrivalPattern.POISSON,
        slo_config: HybridSLOConfig | None = None,
        output_dir: str | Path = "./.benchmarks",
        verbose: bool = True,
    ):
        """Initialize SLO compliance experiment.

        Args:
            name: Experiment name
            control_plane_url: URL of control plane service
            load_levels: List of request rates to test (default: [50, 100, 200, 500])
            num_requests: Number of requests per test
            llm_ratio: Ratio of LLM requests (0.0 to 1.0)
            policies: Scheduling policies to test (default: all)
            arrival_pattern: Request arrival pattern
            slo_config: SLO configuration (default: HybridSLOConfig defaults)
            output_dir: Directory for output files
            verbose: Whether to print progress messages
        """
        super().__init__(name=name, output_dir=output_dir, verbose=verbose)

        self.control_plane_url = control_plane_url
        self.load_levels = load_levels or DEFAULT_LOAD_LEVELS
        self.num_requests = num_requests
        self.llm_ratio = llm_ratio
        self.policies = policies or list(SchedulingPolicy)
        self.arrival_pattern = arrival_pattern
        self.slo_config = slo_config or HybridSLOConfig()

        self._runners: dict[int, HybridBenchmarkRunner] = {}

    @property
    def experiment_type(self) -> str:
        """Return experiment type identifier."""
        return "slo_compliance"

    def _get_parameters(self) -> dict[str, Any]:
        """Get experiment parameters for logging."""
        return {
            "control_plane_url": self.control_plane_url,
            "load_levels": self.load_levels,
            "num_requests": self.num_requests,
            "llm_ratio": self.llm_ratio,
            "policies": [p.value for p in self.policies],
            "arrival_pattern": self.arrival_pattern.value,
            "slo_config": self.slo_config.to_dict(),
        }

    def _prepare_impl(self) -> None:
        """Create benchmark runners for each load level."""
        for load in self.load_levels:
            config = HybridBenchmarkConfig(
                control_plane_url=self.control_plane_url,
                num_requests=self.num_requests,
                request_rate=load,
                llm_ratio=self.llm_ratio,
                embedding_ratio=1.0 - self.llm_ratio,
                policies=[p.value for p in self.policies],
                arrival_pattern=self.arrival_pattern,
                hybrid_slo_config=self.slo_config,
            )
            self._runners[load] = HybridBenchmarkRunner(config)
            self._log(f"   Prepared runner for load={load} req/s")

    async def _execute(self) -> list[dict[str, Any]]:
        """Execute SLO compliance experiment.

        Returns:
            List of results for each load level
        """
        results = []

        for load in self.load_levels:
            self._log(f"\n   📋 Testing SLO compliance at {load} req/s")

            runner = self._runners[load]
            result = await runner.run()

            # Extract SLO compliance data for each policy
            load_result = {
                "load_level": load,
                "num_requests": self.num_requests,
                "policies": {},
            }

            for policy_name, policy_result in result.policy_results.items():
                metrics = policy_result.metrics

                # Compute SLO compliance from raw results
                slo_stats = self._compute_slo_stats(
                    policy_result.raw_results,
                    metrics,
                )

                load_result["policies"][policy_name] = {
                    "overall_compliance": slo_stats["overall_compliance"],
                    "llm_compliance": slo_stats["llm_compliance"],
                    "embedding_compliance": slo_stats["embedding_compliance"],
                    "high_priority_compliance": slo_stats["high_priority_compliance"],
                    "normal_priority_compliance": slo_stats["normal_priority_compliance"],
                    "low_priority_compliance": slo_stats["low_priority_compliance"],
                    "violation_count": slo_stats["violation_count"],
                    "total_requests": slo_stats["total_requests"],
                    "avg_latency_ms": metrics.e2e_latency_avg_ms,
                    "p99_latency_ms": metrics.e2e_latency_p99_ms,
                }

                self._log(
                    f"      {policy_name}: compliance={slo_stats['overall_compliance']:.1%}, "
                    f"violations={slo_stats['violation_count']}/{slo_stats['total_requests']}"
                )

            results.append(load_result)

        return results

    def _compute_slo_stats(
        self,
        raw_results: list[Any],
        metrics: Any,
    ) -> dict[str, Any]:
        """Compute SLO compliance statistics from raw results.

        Args:
            raw_results: Raw results from benchmark run
            metrics: Aggregated metrics

        Returns:
            Dictionary of SLO compliance statistics
        """
        stats = {
            "overall_compliance": 0.0,
            "llm_compliance": 0.0,
            "embedding_compliance": 0.0,
            "high_priority_compliance": 0.0,
            "normal_priority_compliance": 0.0,
            "low_priority_compliance": 0.0,
            "violation_count": 0,
            "total_requests": 0,
        }

        # Counters for compliance calculation
        llm_met, llm_total = 0, 0
        emb_met, emb_total = 0, 0
        high_met, high_total = 0, 0
        normal_met, normal_total = 0, 0
        low_met, low_total = 0, 0

        for result in raw_results:
            # Handle both object and dict formats
            if hasattr(result, "latency_ms"):
                latency_ms = result.latency_ms
                request_type = getattr(result, "request_type", "llm_chat")
                priority = getattr(result, "priority", "NORMAL")
            elif isinstance(result, dict):
                latency_ms = result.get("latency_ms", 0)
                request_type = result.get("request_type", "llm_chat")
                priority = result.get("priority", "NORMAL")
            else:
                continue

            stats["total_requests"] += 1

            # Get SLO deadline for this request
            deadline = self.slo_config.get_deadline_for_request(priority, request_type)
            met_slo = latency_ms <= deadline

            if not met_slo:
                stats["violation_count"] += 1

            # Track by request type
            if "embedding" in str(request_type).lower():
                emb_total += 1
                if met_slo:
                    emb_met += 1
            else:
                llm_total += 1
                if met_slo:
                    llm_met += 1

            # Track by priority
            priority_upper = str(priority).upper()
            if priority_upper == "HIGH":
                high_total += 1
                if met_slo:
                    high_met += 1
            elif priority_upper == "LOW":
                low_total += 1
                if met_slo:
                    low_met += 1
            else:  # NORMAL
                normal_total += 1
                if met_slo:
                    normal_met += 1

        # Calculate compliance rates
        if stats["total_requests"] > 0:
            stats["overall_compliance"] = (
                stats["total_requests"] - stats["violation_count"]
            ) / stats["total_requests"]

        if llm_total > 0:
            stats["llm_compliance"] = llm_met / llm_total
        if emb_total > 0:
            stats["embedding_compliance"] = emb_met / emb_total
        if high_total > 0:
            stats["high_priority_compliance"] = high_met / high_total
        if normal_total > 0:
            stats["normal_priority_compliance"] = normal_met / normal_total
        if low_total > 0:
            stats["low_priority_compliance"] = low_met / low_total

        return stats

    def _compute_summary(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Compute SLO compliance summary statistics.

        Args:
            results: Raw results from _execute()

        Returns:
            Summary with SLO compliance comparison across policies
        """
        summary: dict[str, Any] = {
            "load_levels": self.load_levels,
            "slo_targets": self.slo_config.to_dict(),
            "policies": {},
            "best_policy_overall": None,
            "highest_compliance": 0.0,
        }

        # Aggregate per-policy statistics
        for policy in self.policies:
            policy_name = policy.value
            compliances = []
            violations_by_load = {}

            for result in results:
                load = result["load_level"]
                policy_data = result["policies"].get(policy_name, {})
                compliance = policy_data.get("overall_compliance", 0.0)
                compliances.append(compliance)
                violations_by_load[load] = policy_data.get("violation_count", 0)

            avg_compliance = sum(compliances) / len(compliances) if compliances else 0.0

            summary["policies"][policy_name] = {
                "avg_compliance": avg_compliance,
                "compliance_by_load": dict(zip(self.load_levels, compliances, strict=False)),
                "violations_by_load": violations_by_load,
                "min_compliance": min(compliances) if compliances else 0.0,
                "max_compliance": max(compliances) if compliances else 0.0,
            }

            # Track best policy
            if avg_compliance > summary["highest_compliance"]:
                summary["highest_compliance"] = avg_compliance
                summary["best_policy_overall"] = policy_name

        return summary

    def _visualize_impl(self) -> list[Path]:
        """Generate SLO compliance charts.

        Returns:
            List of paths to generated charts
        """
        charts = []

        if self._result is None or not self._result.results:
            return charts

        try:
            from ..visualization.charts import BenchmarkCharts

            chart_gen = BenchmarkCharts(output_dir=self.output_dir)

            # Generate SLO compliance comparison chart for each load level
            for result in self._result.results:
                load = result["load_level"]
                policy_metrics = {}

                for policy_name, policy_data in result["policies"].items():
                    policy_metrics[policy_name] = {
                        "slo": {
                            "compliance_rate": policy_data.get("overall_compliance", 0.0),
                            "by_priority": {
                                "high": policy_data.get("high_priority_compliance", 0.0),
                                "normal": policy_data.get("normal_priority_compliance", 0.0),
                                "low": policy_data.get("low_priority_compliance", 0.0),
                            },
                        }
                    }

                chart_path = chart_gen.plot_slo_compliance(
                    policy_metrics=policy_metrics,
                    title=f"SLO Compliance at {load} req/s",
                )
                if chart_path:
                    charts.append(chart_path)

            # Generate summary comparison chart using average compliance
            if self._result.summary.get("policies"):
                policy_metrics = {}
                for policy, data in self._result.summary["policies"].items():
                    policy_metrics[policy] = {
                        "slo": {"compliance_rate": data.get("avg_compliance", 0.0)}
                    }
                chart_path = chart_gen.plot_slo_compliance(
                    policy_metrics=policy_metrics,
                    title=f"Average SLO Compliance by Policy - {self.name}",
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
__all__ = ["SLOComplianceExperiment", "DEFAULT_LOAD_LEVELS"]
