from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


class Plotter:
    """
    Utility class for generating publication-quality plots for SAGE experiments.
    """

    def __init__(self, style: str = "seaborn-v0_8-paper"):
        try:
            plt.style.use(style)
        except Exception:
            pass  # Fallback to default

        # Set common font sizes
        plt.rcParams.update(
            {
                "font.size": 12,
                "axes.labelsize": 14,
                "axes.titlesize": 16,
                "xtick.labelsize": 12,
                "ytick.labelsize": 12,
                "legend.fontsize": 12,
                "figure.titlesize": 18,
            }
        )

    def plot_latency_cdf(
        self, results: list[dict[str, Any]], output_path: Path, title: str = "Latency CDF"
    ):
        """Plot Cumulative Distribution Function of latencies."""
        plt.figure(figsize=(8, 5))

        for res in results:
            latencies = np.sort([r["latency_ms"] for r in res["raw_results"] if r["success"]])
            y = np.arange(1, len(latencies) + 1) / len(latencies)
            plt.plot(latencies, y, label=res.get("config_name", "Experiment"), linewidth=2)

        plt.xlabel("Latency (ms)")
        plt.ylabel("CDF")
        plt.title(title)
        plt.grid(True, linestyle="--", alpha=0.7)
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()

    def plot_throughput_vs_latency(self, results: list[dict[str, Any]], output_path: Path):
        """Plot Throughput vs Latency curve."""
        plt.figure(figsize=(8, 5))

        throughputs = [r["throughput_rps"] for r in results]
        p99_latencies = [r["latency_p99_ms"] for r in results]
        labels = [r.get("config_name", "") for r in results]

        plt.plot(throughputs, p99_latencies, "o-", linewidth=2, markersize=8)

        for i, txt in enumerate(labels):
            plt.annotate(
                txt, (throughputs[i], p99_latencies[i]), xytext=(5, 5), textcoords="offset points"
            )

        plt.xlabel("Throughput (req/s)")
        plt.ylabel("p99 Latency (ms)")
        plt.title("Throughput vs Latency")
        plt.grid(True, linestyle="--", alpha=0.7)
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()

    def plot_scalability_bar(self, results: list[dict[str, Any]], output_path: Path):
        """Plot scalability bar chart."""
        plt.figure(figsize=(10, 6))

        configs = [str(r["config"]["hardware"].get("gpus", "")) + " GPUs" for r in results]
        throughputs = [r["throughput_rps"] for r in results]

        bars = plt.bar(configs, throughputs, color="skyblue", edgecolor="black")

        # Add value labels
        for bar in bars:
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{height:.1f}",
                ha="center",
                va="bottom",
            )

        plt.xlabel("Configuration")
        plt.ylabel("Throughput (req/s)")
        plt.title("System Scalability")
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()

    def plot_timeline(self, raw_results: list[dict[str, Any]], output_path: Path):
        """Plot request timeline (waterfall chart)."""
        plt.figure(figsize=(12, 6))

        # Sort by start time
        sorted_results = sorted(raw_results, key=lambda x: x["start_time"])
        # Take a slice if too many
        if len(sorted_results) > 100:
            sorted_results = sorted_results[:100]

        start_time_base = sorted_results[0]["start_time"]

        for i, req in enumerate(sorted_results):
            start = req["start_time"] - start_time_base
            duration = req["latency_ms"] / 1000.0
            color = "blue" if req["request_type"] == "llm" else "green"
            plt.barh(i, duration, left=start, color=color, alpha=0.6, edgecolor="none")

        plt.xlabel("Time (s)")
        plt.ylabel("Request ID")
        plt.title("Request Timeline (First 100)")
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
