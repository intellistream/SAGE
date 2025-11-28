# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project
# pyright: reportOptionalMemberAccess=false
# pyright: reportArgumentType=false

"""
Benchmark Charts Module
========================

Generates various performance charts for Control Plane benchmark results.

This module provides:
- BenchmarkCharts: Main class for chart generation
- Throughput charts: comparison, vs rate
- Latency charts: distribution, percentiles, CDF
- SLO charts: compliance rates, by priority
- GPU charts: utilization, memory
- Mixed workload charts: ratio impact, type breakdown, batch efficiency

Usage:
------
    from sage.benchmark.benchmark_control_plane.visualization import BenchmarkCharts

    charts = BenchmarkCharts(metrics, output_dir="./charts")
    chart_paths = charts.generate_all_charts()
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

# Try to import matplotlib
MATPLOTLIB_AVAILABLE = False
try:
    import matplotlib

    matplotlib.use("Agg")  # Use non-interactive backend
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    plt = None  # type: ignore[assignment]
    Figure = None  # type: ignore[assignment, misc]

# Try to import numpy
try:
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:
    np = None  # type: ignore[assignment]
    NUMPY_AVAILABLE = False

if TYPE_CHECKING:
    from ..common.base_metrics import BaseRequestMetrics
    from ..hybrid_scheduler.metrics import HybridRequestMetrics
    from ..llm_scheduler.metrics import LLMRequestMetrics

logger = logging.getLogger(__name__)

# Chart style configuration
CHART_STYLE = {
    "figure.figsize": (10, 6),
    "figure.dpi": 100,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
}

# Color palette for consistent styling
COLORS = {
    "primary": "#2563eb",
    "secondary": "#64748b",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "llm": "#3b82f6",
    "embedding": "#8b5cf6",
    "high": "#ef4444",
    "normal": "#f59e0b",
    "low": "#22c55e",
}

# Policy colors for comparison charts
POLICY_COLORS = [
    "#2563eb",  # Blue
    "#dc2626",  # Red
    "#16a34a",  # Green
    "#9333ea",  # Purple
    "#ea580c",  # Orange
    "#0891b2",  # Cyan
    "#c026d3",  # Fuchsia
    "#65a30d",  # Lime
]


class BenchmarkCharts:
    """Generates benchmark performance charts.

    This class creates various visualizations from benchmark metrics,
    including throughput comparisons, latency distributions, SLO compliance,
    and GPU utilization charts.

    Attributes:
        metrics: Benchmark metrics object (LLMRequestMetrics or HybridRequestMetrics)
        output_dir: Directory to save generated charts
        format: Image format for saving (png, svg, pdf)
    """

    def __init__(
        self,
        metrics: BaseRequestMetrics | dict[str, Any] | None = None,
        output_dir: str | Path = "./charts",
        format: str = "png",
    ):
        """Initialize charts generator.

        Args:
            metrics: Benchmark metrics object or dict
            output_dir: Directory to save generated charts
            format: Image format (png, svg, pdf)
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.warning(
                "matplotlib not available. Chart generation will be disabled. "
                "Install with: pip install matplotlib"
            )

        self.metrics = metrics
        self.output_dir = Path(output_dir)
        self.format = format
        self._generated_charts: list[Path] = []

        # Apply chart style
        if MATPLOTLIB_AVAILABLE:
            plt.rcParams.update(CHART_STYLE)

    def _ensure_output_dir(self) -> None:
        """Create output directory if it doesn't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _save_figure(self, fig: Any, name: str) -> Path:
        """Save figure to file.

        Args:
            fig: Matplotlib figure
            name: Chart name (without extension)

        Returns:
            Path to saved chart file
        """
        self._ensure_output_dir()
        path = self.output_dir / f"{name}.{self.format}"
        fig.savefig(path, bbox_inches="tight", facecolor="white", edgecolor="none")
        plt.close(fig)
        self._generated_charts.append(path)
        logger.info(f"Saved chart: {path}")
        return path

    def _get_metrics_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary if needed."""
        if self.metrics is None:
            return {}
        if isinstance(self.metrics, dict):
            return self.metrics
        to_dict_method = getattr(self.metrics, "to_dict", None)
        if callable(to_dict_method):
            result = to_dict_method()
            if isinstance(result, dict):
                return result
        return {}

    # ========================================================================
    # Throughput Charts
    # ========================================================================

    def plot_throughput_comparison(
        self,
        policy_metrics: dict[str, dict[str, Any]] | None = None,
        title: str = "Throughput Comparison by Policy",
    ) -> Path | None:
        """Generate bar chart comparing throughput across policies.

        Args:
            policy_metrics: Dict mapping policy names to metrics dicts
            title: Chart title

        Returns:
            Path to saved chart, or None if generation failed
        """
        if not MATPLOTLIB_AVAILABLE:
            return None

        if policy_metrics is None:
            # Use single metrics for single policy
            metrics_dict = self._get_metrics_dict()
            if not metrics_dict:
                return None
            policy_metrics = {"current": metrics_dict}

        fig, ax = plt.subplots(figsize=(10, 6))

        policies = list(policy_metrics.keys())
        throughputs = []

        for policy_name in policies:
            m = policy_metrics[policy_name]
            if isinstance(m, dict):
                tp = m.get("throughput", {}).get("requests_per_second", 0)
            else:
                tp = getattr(m, "throughput_rps", 0)
            throughputs.append(tp)

        colors = [POLICY_COLORS[i % len(POLICY_COLORS)] for i in range(len(policies))]
        bars = ax.bar(policies, throughputs, color=colors, edgecolor="white", linewidth=1)

        # Add value labels on bars
        for bar, value in zip(bars, throughputs):
            height = bar.get_height()
            ax.annotate(
                f"{value:.1f}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontweight="bold",
            )

        ax.set_xlabel("Policy")
        ax.set_ylabel("Throughput (requests/second)")
        ax.set_title(title)
        ax.set_ylim(bottom=0)

        return self._save_figure(fig, "throughput_comparison")

    def plot_throughput_vs_rate(
        self,
        rate_results: list[tuple[float, float]] | None = None,
        title: str = "Throughput vs Request Rate",
    ) -> Path | None:
        """Generate line chart showing throughput at different request rates.

        Args:
            rate_results: List of (request_rate, achieved_throughput) tuples
            title: Chart title

        Returns:
            Path to saved chart, or None if generation failed
        """
        if not MATPLOTLIB_AVAILABLE or not NUMPY_AVAILABLE:
            return None

        if rate_results is None or len(rate_results) == 0:
            return None

        fig, ax = plt.subplots(figsize=(10, 6))

        rates = [r[0] for r in rate_results]
        throughputs = [r[1] for r in rate_results]

        # Plot achieved throughput
        ax.plot(
            rates,
            throughputs,
            marker="o",
            linewidth=2,
            markersize=8,
            color=COLORS["primary"],
            label="Achieved Throughput",
        )

        # Plot ideal throughput line (y=x)
        max_rate = max(rates) * 1.1
        ax.plot(
            [0, max_rate],
            [0, max_rate],
            linestyle="--",
            color=COLORS["secondary"],
            alpha=0.7,
            label="Ideal (y=x)",
        )

        ax.set_xlabel("Request Rate (requests/second)")
        ax.set_ylabel("Achieved Throughput (requests/second)")
        ax.set_title(title)
        ax.legend()
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)

        return self._save_figure(fig, "throughput_vs_rate")

    # ========================================================================
    # Latency Charts
    # ========================================================================

    def plot_latency_distribution(
        self,
        latencies: list[float] | None = None,
        title: str = "Latency Distribution",
        bins: int = 50,
    ) -> Path | None:
        """Generate histogram of latency distribution.

        Args:
            latencies: List of latency values in ms
            title: Chart title
            bins: Number of histogram bins

        Returns:
            Path to saved chart, or None if generation failed
        """
        if not MATPLOTLIB_AVAILABLE or not NUMPY_AVAILABLE:
            return None

        if latencies is None:
            # Try to get from metrics
            metrics_dict = self._get_metrics_dict()
            if "latency_samples" in metrics_dict:
                latencies = metrics_dict["latency_samples"]
            else:
                return None

        if not latencies:
            return None

        fig, ax = plt.subplots(figsize=(10, 6))

        ax.hist(
            latencies,
            bins=bins,
            color=COLORS["primary"],
            edgecolor="white",
            alpha=0.8,
        )

        # Add percentile lines
        p50 = np.percentile(latencies, 50)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)

        ax.axvline(p50, color=COLORS["success"], linestyle="--", linewidth=2, label=f"P50: {p50:.1f}ms")
        ax.axvline(p95, color=COLORS["warning"], linestyle="--", linewidth=2, label=f"P95: {p95:.1f}ms")
        ax.axvline(p99, color=COLORS["error"], linestyle="--", linewidth=2, label=f"P99: {p99:.1f}ms")

        ax.set_xlabel("Latency (ms)")
        ax.set_ylabel("Count")
        ax.set_title(title)
        ax.legend()

        return self._save_figure(fig, "latency_distribution")

    def plot_latency_percentiles(
        self,
        policy_metrics: dict[str, dict[str, Any]] | None = None,
        title: str = "Latency Percentiles by Policy",
    ) -> Path | None:
        """Generate grouped bar chart comparing latency percentiles.

        Args:
            policy_metrics: Dict mapping policy names to metrics dicts
            title: Chart title

        Returns:
            Path to saved chart, or None if generation failed
        """
        if not MATPLOTLIB_AVAILABLE or not NUMPY_AVAILABLE:
            return None

        if policy_metrics is None:
            metrics_dict = self._get_metrics_dict()
            if not metrics_dict:
                return None
            policy_metrics = {"current": metrics_dict}

        fig, ax = plt.subplots(figsize=(12, 6))

        policies = list(policy_metrics.keys())
        percentiles = ["p50", "p95", "p99"]
        x = np.arange(len(policies))
        width = 0.25

        for i, pct in enumerate(percentiles):
            values = []
            for policy_name in policies:
                m = policy_metrics[policy_name]
                if isinstance(m, dict):
                    lat = m.get("e2e_latency_ms", {})
                    val = lat.get(pct, 0)
                else:
                    val = getattr(m, f"e2e_latency_{pct}_ms", 0)
                values.append(val)

            color = [COLORS["success"], COLORS["warning"], COLORS["error"]][i]
            bars = ax.bar(x + i * width, values, width, label=pct.upper(), color=color)

            # Add value labels
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax.annotate(
                    f"{value:.0f}",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

        ax.set_xlabel("Policy")
        ax.set_ylabel("Latency (ms)")
        ax.set_title(title)
        ax.set_xticks(x + width)
        ax.set_xticklabels(policies)
        ax.legend()
        ax.set_ylim(bottom=0)

        return self._save_figure(fig, "latency_percentiles")

    def plot_latency_cdf(
        self,
        latencies: list[float] | None = None,
        policy_latencies: dict[str, list[float]] | None = None,
        title: str = "Latency CDF",
    ) -> Path | None:
        """Generate cumulative distribution function (CDF) chart.

        Args:
            latencies: List of latency values for single policy
            policy_latencies: Dict mapping policy names to latency lists
            title: Chart title

        Returns:
            Path to saved chart, or None if generation failed
        """
        if not MATPLOTLIB_AVAILABLE or not NUMPY_AVAILABLE:
            return None

        fig, ax = plt.subplots(figsize=(10, 6))

        if policy_latencies is None and latencies is not None:
            policy_latencies = {"current": latencies}

        if policy_latencies is None:
            return None

        for i, (policy_name, lats) in enumerate(policy_latencies.items()):
            if not lats:
                continue
            sorted_data = np.sort(lats)
            cdf = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
            color = POLICY_COLORS[i % len(POLICY_COLORS)]
            ax.plot(sorted_data, cdf, linewidth=2, color=color, label=policy_name)

        # Add percentile reference lines
        ax.axhline(0.50, color=COLORS["secondary"], linestyle=":", alpha=0.5, label="P50")
        ax.axhline(0.95, color=COLORS["secondary"], linestyle=":", alpha=0.5, label="P95")
        ax.axhline(0.99, color=COLORS["secondary"], linestyle=":", alpha=0.5, label="P99")

        ax.set_xlabel("Latency (ms)")
        ax.set_ylabel("CDF")
        ax.set_title(title)
        ax.legend()
        ax.set_xlim(left=0)
        ax.set_ylim(0, 1.05)

        return self._save_figure(fig, "latency_cdf")

    # ========================================================================
    # SLO Charts
    # ========================================================================

    def plot_slo_compliance(
        self,
        policy_metrics: dict[str, dict[str, Any]] | None = None,
        title: str = "SLO Compliance Rate by Policy",
    ) -> Path | None:
        """Generate bar chart showing SLO compliance rates.

        Args:
            policy_metrics: Dict mapping policy names to metrics dicts
            title: Chart title

        Returns:
            Path to saved chart, or None if generation failed
        """
        if not MATPLOTLIB_AVAILABLE:
            return None

        if policy_metrics is None:
            metrics_dict = self._get_metrics_dict()
            if not metrics_dict:
                return None
            policy_metrics = {"current": metrics_dict}

        fig, ax = plt.subplots(figsize=(10, 6))

        policies = list(policy_metrics.keys())
        compliance_rates = []

        for policy_name in policies:
            m = policy_metrics[policy_name]
            if isinstance(m, dict):
                rate = m.get("slo", {}).get("compliance_rate", 0)
            else:
                rate = getattr(m, "slo_compliance_rate", 0)
            compliance_rates.append(rate * 100)  # Convert to percentage

        # Color bars based on compliance rate
        colors = []
        for rate in compliance_rates:
            if rate >= 95:
                colors.append(COLORS["success"])
            elif rate >= 80:
                colors.append(COLORS["warning"])
            else:
                colors.append(COLORS["error"])

        bars = ax.bar(policies, compliance_rates, color=colors, edgecolor="white", linewidth=1)

        # Add value labels
        for bar, value in zip(bars, compliance_rates):
            height = bar.get_height()
            ax.annotate(
                f"{value:.1f}%",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontweight="bold",
            )

        # Add target line
        ax.axhline(95, color=COLORS["secondary"], linestyle="--", alpha=0.7, label="95% Target")

        ax.set_xlabel("Policy")
        ax.set_ylabel("SLO Compliance Rate (%)")
        ax.set_title(title)
        ax.set_ylim(0, 105)
        ax.legend()

        return self._save_figure(fig, "slo_compliance")

    def plot_slo_by_priority(
        self,
        metrics: dict[str, Any] | None = None,
        title: str = "SLO Compliance by Priority",
    ) -> Path | None:
        """Generate bar chart showing SLO compliance by priority level.

        Args:
            metrics: Metrics dict with slo_by_priority
            title: Chart title

        Returns:
            Path to saved chart, or None if generation failed
        """
        if not MATPLOTLIB_AVAILABLE:
            return None

        if metrics is None:
            metrics = self._get_metrics_dict()

        if not metrics:
            return None

        slo_by_priority = metrics.get("slo", {}).get("by_priority", {})
        if not slo_by_priority:
            # Try direct attribute
            slo_by_priority = getattr(self.metrics, "slo_by_priority", None)
            if not slo_by_priority:
                return None

        if not slo_by_priority:
            return None

        fig, ax = plt.subplots(figsize=(10, 6))

        priorities = list(slo_by_priority.keys())
        rates = [slo_by_priority[p] * 100 for p in priorities]

        # Color by priority
        colors = [COLORS.get(p, COLORS["secondary"]) for p in priorities]

        bars = ax.bar(priorities, rates, color=colors, edgecolor="white", linewidth=1)

        # Add value labels
        for bar, value in zip(bars, rates):
            height = bar.get_height()
            ax.annotate(
                f"{value:.1f}%",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontweight="bold",
            )

        ax.set_xlabel("Priority Level")
        ax.set_ylabel("SLO Compliance Rate (%)")
        ax.set_title(title)
        ax.set_ylim(0, 105)

        return self._save_figure(fig, "slo_by_priority")

    # ========================================================================
    # GPU Resource Charts
    # ========================================================================

    def plot_gpu_utilization(
        self,
        gpu_metrics: list[dict[str, Any]] | None = None,
        title: str = "GPU Utilization Over Time",
    ) -> Path | None:
        """Generate line chart showing GPU utilization over time.

        Args:
            gpu_metrics: List of GPU metric snapshots with timestamps
            title: Chart title

        Returns:
            Path to saved chart, or None if generation failed
        """
        if not MATPLOTLIB_AVAILABLE or not NUMPY_AVAILABLE:
            return None

        if gpu_metrics is None or len(gpu_metrics) == 0:
            return None

        fig, ax = plt.subplots(figsize=(12, 6))

        timestamps = [m.get("timestamp", i) for i, m in enumerate(gpu_metrics)]
        # Normalize timestamps to start from 0
        if timestamps and isinstance(timestamps[0], (int, float)):
            t0 = timestamps[0]
            timestamps = [t - t0 for t in timestamps]

        utilizations = [m.get("gpu_utilization_percent", 0) for m in gpu_metrics]

        ax.plot(
            timestamps,
            utilizations,
            linewidth=2,
            color=COLORS["primary"],
            label="GPU Utilization",
        )

        # Add average line
        avg_util = np.mean(utilizations)
        ax.axhline(avg_util, color=COLORS["secondary"], linestyle="--", label=f"Avg: {avg_util:.1f}%")

        ax.fill_between(timestamps, utilizations, alpha=0.3, color=COLORS["primary"])

        ax.set_xlabel("Time (seconds)")
        ax.set_ylabel("GPU Utilization (%)")
        ax.set_title(title)
        ax.legend()
        ax.set_ylim(0, 105)

        return self._save_figure(fig, "gpu_utilization")

    def plot_gpu_memory(
        self,
        gpu_metrics: list[dict[str, Any]] | None = None,
        title: str = "GPU Memory Usage Over Time",
    ) -> Path | None:
        """Generate line chart showing GPU memory usage over time.

        Args:
            gpu_metrics: List of GPU metric snapshots with timestamps
            title: Chart title

        Returns:
            Path to saved chart, or None if generation failed
        """
        if not MATPLOTLIB_AVAILABLE or not NUMPY_AVAILABLE:
            return None

        if gpu_metrics is None or len(gpu_metrics) == 0:
            return None

        fig, ax = plt.subplots(figsize=(12, 6))

        timestamps = [m.get("timestamp", i) for i, m in enumerate(gpu_metrics)]
        if timestamps and isinstance(timestamps[0], (int, float)):
            t0 = timestamps[0]
            timestamps = [t - t0 for t in timestamps]

        # Get memory in GB
        memory_used = [m.get("memory_used_gb", 0) for m in gpu_metrics]
        memory_total = gpu_metrics[0].get("memory_total_gb", 0) if gpu_metrics else 0

        ax.plot(
            timestamps,
            memory_used,
            linewidth=2,
            color=COLORS["llm"],
            label="Memory Used",
        )

        if memory_total > 0:
            ax.axhline(
                memory_total,
                color=COLORS["error"],
                linestyle="--",
                label=f"Total: {memory_total:.1f} GB",
            )

        ax.fill_between(timestamps, memory_used, alpha=0.3, color=COLORS["llm"])

        ax.set_xlabel("Time (seconds)")
        ax.set_ylabel("Memory (GB)")
        ax.set_title(title)
        ax.legend()
        ax.set_ylim(bottom=0)

        return self._save_figure(fig, "gpu_memory")

    # ========================================================================
    # Mixed Workload Charts (Hybrid-specific)
    # ========================================================================

    def plot_mixed_ratio_impact(
        self,
        ratio_results: list[dict[str, Any]] | None = None,
        title: str = "Performance vs LLM/Embedding Ratio",
    ) -> Path | None:
        """Generate chart showing performance impact of LLM/Embedding ratio.

        Args:
            ratio_results: List of results at different ratios, each with
                          'llm_ratio', 'throughput_rps', 'slo_compliance_rate'
            title: Chart title

        Returns:
            Path to saved chart, or None if generation failed
        """
        if not MATPLOTLIB_AVAILABLE or not NUMPY_AVAILABLE:
            return None

        if ratio_results is None or len(ratio_results) == 0:
            return None

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        llm_ratios = [r.get("llm_ratio", 0) * 100 for r in ratio_results]
        throughputs = [r.get("throughput_rps", 0) for r in ratio_results]
        slo_rates = [r.get("slo_compliance_rate", 0) * 100 for r in ratio_results]

        # Throughput chart
        ax1.plot(
            llm_ratios,
            throughputs,
            marker="o",
            linewidth=2,
            markersize=8,
            color=COLORS["primary"],
        )
        ax1.set_xlabel("LLM Ratio (%)")
        ax1.set_ylabel("Throughput (requests/second)")
        ax1.set_title("Throughput vs LLM Ratio")
        ax1.set_xlim(0, 100)
        ax1.set_ylim(bottom=0)

        # SLO compliance chart
        ax2.plot(
            llm_ratios,
            slo_rates,
            marker="s",
            linewidth=2,
            markersize=8,
            color=COLORS["success"],
        )
        ax2.axhline(95, color=COLORS["secondary"], linestyle="--", alpha=0.7, label="95% Target")
        ax2.set_xlabel("LLM Ratio (%)")
        ax2.set_ylabel("SLO Compliance (%)")
        ax2.set_title("SLO Compliance vs LLM Ratio")
        ax2.set_xlim(0, 100)
        ax2.set_ylim(0, 105)
        ax2.legend()

        fig.suptitle(title, fontsize=14, fontweight="bold")
        plt.tight_layout()

        return self._save_figure(fig, "mixed_ratio_impact")

    def plot_embedding_batch_efficiency(
        self,
        batch_results: list[dict[str, Any]] | None = None,
        title: str = "Embedding Batch Efficiency",
    ) -> Path | None:
        """Generate chart showing embedding batch efficiency.

        Args:
            batch_results: List of results at different batch sizes, each with
                          'batch_size', 'throughput_texts_ps', 'latency_avg_ms'
            title: Chart title

        Returns:
            Path to saved chart, or None if generation failed
        """
        if not MATPLOTLIB_AVAILABLE or not NUMPY_AVAILABLE:
            return None

        if batch_results is None or len(batch_results) == 0:
            return None

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        batch_sizes = [r.get("batch_size", 0) for r in batch_results]
        throughputs = [r.get("throughput_texts_ps", 0) for r in batch_results]
        latencies = [r.get("latency_avg_ms", 0) for r in batch_results]

        # Throughput vs batch size
        ax1.bar(
            [str(b) for b in batch_sizes],
            throughputs,
            color=COLORS["embedding"],
            edgecolor="white",
        )
        ax1.set_xlabel("Batch Size")
        ax1.set_ylabel("Throughput (texts/second)")
        ax1.set_title("Throughput vs Batch Size")
        ax1.set_ylim(bottom=0)

        # Latency vs batch size
        ax2.plot(
            batch_sizes,
            latencies,
            marker="o",
            linewidth=2,
            markersize=8,
            color=COLORS["warning"],
        )
        ax2.set_xlabel("Batch Size")
        ax2.set_ylabel("Average Latency (ms)")
        ax2.set_title("Latency vs Batch Size")
        ax2.set_ylim(bottom=0)

        fig.suptitle(title, fontsize=14, fontweight="bold")
        plt.tight_layout()

        return self._save_figure(fig, "embedding_batch_efficiency")

    def plot_type_breakdown(
        self,
        metrics: dict[str, Any] | None = None,
        title: str = "Request Type Breakdown",
    ) -> Path | None:
        """Generate pie chart showing LLM vs Embedding request breakdown.

        Args:
            metrics: Metrics dict with LLM and Embedding counts
            title: Chart title

        Returns:
            Path to saved chart, or None if generation failed
        """
        if not MATPLOTLIB_AVAILABLE:
            return None

        if metrics is None:
            metrics = self._get_metrics_dict()

        if not metrics:
            return None

        # Extract counts
        llm_count = 0
        embed_count = 0

        if "llm" in metrics:
            llm_count = metrics["llm"].get("request_counts", {}).get("total", 0)
        if "embedding" in metrics:
            embed_count = metrics["embedding"].get("request_counts", {}).get("total", 0)

        # Try alternative structure
        if llm_count == 0 and embed_count == 0:
            llm_count = getattr(self.metrics, "llm_total_requests", 0)
            embed_count = getattr(self.metrics, "embedding_total_requests", 0)

        if llm_count == 0 and embed_count == 0:
            return None

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Pie chart for request counts
        sizes = [llm_count, embed_count]
        labels = [f"LLM ({llm_count})", f"Embedding ({embed_count})"]
        colors = [COLORS["llm"], COLORS["embedding"]]
        explode = (0.02, 0.02)

        ax1.pie(
            sizes,
            explode=explode,
            labels=labels,
            colors=colors,
            autopct="%1.1f%%",
            startangle=90,
            textprops={"fontsize": 11},
        )
        ax1.set_title("Request Distribution")

        # Bar chart for throughput comparison
        llm_throughput = 0
        embed_throughput = 0

        if "llm" in metrics:
            llm_throughput = metrics["llm"].get("throughput", {}).get("requests_per_second", 0)
        if "embedding" in metrics:
            embed_throughput = metrics["embedding"].get("throughput", {}).get("requests_per_second", 0)

        llm_throughput = getattr(self.metrics, "llm_throughput_rps", llm_throughput)
        embed_throughput = getattr(self.metrics, "embedding_throughput_rps", embed_throughput)

        bars = ax2.bar(
            ["LLM", "Embedding"],
            [llm_throughput, embed_throughput],
            color=[COLORS["llm"], COLORS["embedding"]],
            edgecolor="white",
        )

        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax2.annotate(
                f"{height:.1f}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontweight="bold",
            )

        ax2.set_ylabel("Throughput (requests/second)")
        ax2.set_title("Throughput by Type")
        ax2.set_ylim(bottom=0)

        fig.suptitle(title, fontsize=14, fontweight="bold")
        plt.tight_layout()

        return self._save_figure(fig, "type_breakdown")

    def plot_llm_vs_embedding_latency(
        self,
        metrics: dict[str, Any] | None = None,
        title: str = "Latency Comparison: LLM vs Embedding",
    ) -> Path | None:
        """Generate grouped bar chart comparing LLM and Embedding latencies.

        Args:
            metrics: Metrics dict with LLM and Embedding latency data
            title: Chart title

        Returns:
            Path to saved chart, or None if generation failed
        """
        if not MATPLOTLIB_AVAILABLE or not NUMPY_AVAILABLE:
            return None

        if metrics is None:
            metrics = self._get_metrics_dict()

        if not metrics:
            return None

        fig, ax = plt.subplots(figsize=(10, 6))

        # Extract latency data
        llm_latencies = {}
        embed_latencies = {}

        if "llm" in metrics:
            llm_lat = metrics["llm"].get("e2e_latency_ms", {})
            llm_latencies = {"avg": llm_lat.get("avg", 0), "p99": llm_lat.get("p99", 0)}

        if "embedding" in metrics:
            embed_lat = metrics["embedding"].get("e2e_latency_ms", {})
            embed_latencies = {"avg": embed_lat.get("avg", 0), "p99": embed_lat.get("p99", 0)}

        if not llm_latencies.get("avg") and not embed_latencies.get("avg"):
            return None

        x = np.arange(2)
        width = 0.35

        llm_values = [llm_latencies.get("avg", 0), llm_latencies.get("p99", 0)]
        embed_values = [embed_latencies.get("avg", 0), embed_latencies.get("p99", 0)]

        bars1 = ax.bar(x - width / 2, llm_values, width, label="LLM", color=COLORS["llm"])
        bars2 = ax.bar(x + width / 2, embed_values, width, label="Embedding", color=COLORS["embedding"])

        # Add value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.annotate(
                    f"{height:.0f}",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

        ax.set_xlabel("Metric")
        ax.set_ylabel("Latency (ms)")
        ax.set_title(title)
        ax.set_xticks(x)
        ax.set_xticklabels(["Average", "P99"])
        ax.legend()
        ax.set_ylim(bottom=0)

        return self._save_figure(fig, "llm_vs_embedding_latency")

    # ========================================================================
    # Generate All Charts
    # ========================================================================

    def generate_all_charts(
        self,
        policy_metrics: dict[str, dict[str, Any]] | None = None,
        latencies: list[float] | None = None,
        gpu_metrics: list[dict[str, Any]] | None = None,
        rate_results: list[tuple[float, float]] | None = None,
        ratio_results: list[dict[str, Any]] | None = None,
        batch_results: list[dict[str, Any]] | None = None,
    ) -> list[Path]:
        """Generate all applicable charts based on available data.

        Args:
            policy_metrics: Dict mapping policy names to metrics dicts
            latencies: List of latency values for distribution charts
            gpu_metrics: List of GPU metric snapshots
            rate_results: List of (rate, throughput) tuples
            ratio_results: List of results at different LLM/Embedding ratios
            batch_results: List of results at different batch sizes

        Returns:
            List of paths to generated charts
        """
        self._generated_charts = []

        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib not available, skipping chart generation")
            return []

        metrics_dict = self._get_metrics_dict()

        # Throughput charts
        self.plot_throughput_comparison(policy_metrics)
        if rate_results:
            self.plot_throughput_vs_rate(rate_results)

        # Latency charts
        if latencies:
            self.plot_latency_distribution(latencies)
            self.plot_latency_cdf(latencies)
        self.plot_latency_percentiles(policy_metrics)

        # SLO charts
        self.plot_slo_compliance(policy_metrics)
        self.plot_slo_by_priority(metrics_dict)

        # GPU charts
        if gpu_metrics:
            self.plot_gpu_utilization(gpu_metrics)
            self.plot_gpu_memory(gpu_metrics)

        # Mixed workload charts (if applicable)
        if ratio_results:
            self.plot_mixed_ratio_impact(ratio_results)
        if batch_results:
            self.plot_embedding_batch_efficiency(batch_results)

        # Type breakdown (for hybrid metrics)
        if "llm" in metrics_dict or "embedding" in metrics_dict:
            self.plot_type_breakdown(metrics_dict)
            self.plot_llm_vs_embedding_latency(metrics_dict)

        logger.info(f"Generated {len(self._generated_charts)} charts in {self.output_dir}")
        return self._generated_charts

    def get_generated_charts(self) -> list[Path]:
        """Get list of all generated chart paths.

        Returns:
            List of paths to generated charts
        """
        return self._generated_charts.copy()


# Re-export
__all__ = [
    "BenchmarkCharts",
    "CHART_STYLE",
    "COLORS",
    "POLICY_COLORS",
]
