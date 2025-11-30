# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Visualization Module for Control Plane Benchmark
=================================================

This module provides visualization tools for benchmark results, including:
- BenchmarkCharts: Various performance charts (throughput, latency, SLO, GPU)
- ReportGenerator: HTML/Markdown report generation

Usage:
------
    from sage.benchmark.benchmark_control_plane.visualization import (
        BenchmarkCharts,
        ReportGenerator,
    )

    # Generate charts from metrics
    charts = BenchmarkCharts(output_dir="./charts")
    chart_paths = charts.generate_all_charts(benchmark_result)

    # Generate reports
    report_gen = ReportGenerator(output_dir="./reports")
    report_gen.generate_full_report(benchmark_result, report_name="benchmark")

    # Generate specific charts
    charts.plot_throughput_comparison(policy_metrics)
    charts.plot_latency_distribution(latencies)
    charts.plot_slo_compliance(policy_metrics)
    charts.plot_gpu_utilization(gpu_metrics)

    # For hybrid workloads
    charts.plot_mixed_ratio_impact(ratio_results)
    charts.plot_type_breakdown(metrics)
"""

from .charts import CHART_STYLE, COLORS, POLICY_COLORS, BenchmarkCharts
from .report_generator import ReportGenerator

__all__ = [
    # Charts (Task 4A)
    "BenchmarkCharts",
    "CHART_STYLE",
    "COLORS",
    "POLICY_COLORS",
    # ReportGenerator (Task 4B)
    "ReportGenerator",
]
