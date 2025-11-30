# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Hybrid Benchmark Reporter Module
=================================

Generates reports from hybrid (LLM + Embedding) benchmark results.

This module provides:
- Terminal table output with mixed workload details
- JSON report generation
- CSV export for further analysis
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .runner import HybridBenchmarkResult


class HybridBenchmarkReporter:
    """Generates hybrid benchmark reports in various formats.

    Supports:
    - Rich terminal output with tables for LLM and Embedding metrics
    - JSON files for programmatic access
    - CSV files for spreadsheet analysis

    Example:
        result = await runner.run()
        reporter = HybridBenchmarkReporter(result)
        reporter.print_summary()
        reporter.save_json("results/benchmark.json")
        reporter.save_csv("results/benchmark.csv")
    """

    def __init__(self, result: HybridBenchmarkResult):
        """Initialize reporter.

        Args:
            result: HybridBenchmarkResult to report on
        """
        self.result = result

    def print_summary(self) -> None:
        """Print comprehensive summary to terminal."""
        print("\n" + "=" * 80)
        print("          sageLLM Hybrid Scheduling Policy Benchmark Report")
        print("=" * 80)

        # Print config summary
        config = self.result.config
        print(
            f"Config: {config.get('num_requests', 'N/A')} requests "
            f"@ {config.get('request_rate', 'N/A')} req/s"
        )
        print(
            f"Mix Ratio: LLM={config.get('llm_ratio', 0):.0%}, "
            f"Embedding={config.get('embedding_ratio', 0):.0%}"
        )
        llm_models = list(config.get("llm_model_distribution", {}).keys())
        print(f"LLM Models: {', '.join(llm_models) if llm_models else 'N/A'}")
        print(f"Embedding Model: {config.get('embedding_model', 'N/A')}")
        print("-" * 80)
        print()

        # Print overall metrics table
        self._print_overall_table()

        # Print LLM-specific metrics table
        self._print_llm_table()

        # Print Embedding-specific metrics table
        self._print_embedding_table()

        # Print GPU metrics if available
        self._print_gpu_table()

        # Print best performers
        self._print_best_performers()

    def _print_overall_table(self) -> None:
        """Print overall metrics table."""
        print("📊 Overall Performance")
        print("-" * 80)

        headers = [
            "Policy",
            "Throughput",
            "Avg E2E",
            "P99 E2E",
            "SLO Rate",
            "Error Rate",
        ]
        header_line = "| " + " | ".join(f"{h:^12}" for h in headers) + " |"
        separator = "|" + "|".join("-" * 14 for _ in headers) + "|"

        print(header_line)
        print(separator)

        for policy_name, policy_result in self.result.policy_results.items():
            m = policy_result.metrics
            row = [
                policy_name[:12],
                f"{m.throughput_rps:.1f} req/s",
                f"{m.e2e_latency_avg_ms:.0f} ms",
                f"{m.e2e_latency_p99_ms:.0f} ms",
                f"{m.slo_compliance_rate:.1%}",
                f"{m.error_rate:.1%}",
            ]
            row_line = "| " + " | ".join(f"{v:^12}" for v in row) + " |"
            print(row_line)

        print()

    def _print_llm_table(self) -> None:
        """Print LLM-specific metrics table."""
        print("🤖 LLM Performance")
        print("-" * 80)

        headers = [
            "Policy",
            "Throughput",
            "Token/s",
            "TTFT Avg",
            "TTFT P99",
            "E2E P99",
            "SLO Rate",
        ]
        header_line = "| " + " | ".join(f"{h:^10}" for h in headers) + " |"
        separator = "|" + "|".join("-" * 12 for _ in headers) + "|"

        print(header_line)
        print(separator)

        for policy_name, policy_result in self.result.policy_results.items():
            m = policy_result.metrics
            row = [
                policy_name[:10],
                f"{m.llm_throughput_rps:.1f}",
                f"{m.llm_token_throughput_tps:.0f}",
                f"{m.llm_ttft_avg_ms:.0f} ms",
                f"{m.llm_ttft_p99_ms:.0f} ms",
                f"{m.llm_e2e_latency_p99_ms:.0f} ms",
                f"{m.llm_slo_compliance_rate:.1%}",
            ]
            row_line = "| " + " | ".join(f"{v:^10}" for v in row) + " |"
            print(row_line)

        print()

    def _print_embedding_table(self) -> None:
        """Print Embedding-specific metrics table."""
        print("📝 Embedding Performance")
        print("-" * 80)

        headers = [
            "Policy",
            "Throughput",
            "Texts/s",
            "Batch Eff",
            "Avg Batch",
            "E2E P99",
            "SLO Rate",
        ]
        header_line = "| " + " | ".join(f"{h:^10}" for h in headers) + " |"
        separator = "|" + "|".join("-" * 12 for _ in headers) + "|"

        print(header_line)
        print(separator)

        for policy_name, policy_result in self.result.policy_results.items():
            m = policy_result.metrics
            row = [
                policy_name[:10],
                f"{m.embedding_throughput_rps:.1f}",
                f"{m.embedding_throughput_texts_ps:.0f}",
                f"{m.embedding_batch_efficiency:.1%}",
                f"{m.embedding_avg_batch_size:.1f}",
                f"{m.embedding_e2e_latency_p99_ms:.0f} ms",
                f"{m.embedding_slo_compliance_rate:.1%}",
            ]
            row_line = "| " + " | ".join(f"{v:^10}" for v in row) + " |"
            print(row_line)

        print()

    def _print_gpu_table(self) -> None:
        """Print GPU metrics table if available."""
        # Check if any policy has GPU metrics
        has_gpu_metrics = any(
            pr.gpu_metrics is not None for pr in self.result.policy_results.values()
        )
        if not has_gpu_metrics:
            return

        print("🎮 GPU Resource Usage")
        print("-" * 80)

        headers = [
            "Policy",
            "Util Avg",
            "Util Max",
            "Mem Avg",
            "Mem Max",
            "Temp Avg",
            "Power Avg",
        ]
        header_line = "| " + " | ".join(f"{h:^10}" for h in headers) + " |"
        separator = "|" + "|".join("-" * 12 for _ in headers) + "|"

        print(header_line)
        print(separator)

        for policy_name, policy_result in self.result.policy_results.items():
            gpu = policy_result.gpu_metrics
            if gpu:
                row = [
                    policy_name[:10],
                    f"{gpu.utilization_avg:.1f}%",
                    f"{gpu.utilization_max:.1f}%",
                    f"{gpu.memory_used_avg_mb:.0f}MB",
                    f"{gpu.memory_used_max_mb:.0f}MB",
                    f"{gpu.temperature_avg_celsius:.1f}C",
                    f"{gpu.power_avg_watts:.0f}W",
                ]
            else:
                row = [policy_name[:10]] + ["N/A"] * 6
            row_line = "| " + " | ".join(f"{v:^10}" for v in row) + " |"
            print(row_line)

        print()

    def _print_best_performers(self) -> None:
        """Print best performers summary."""
        print("🏆 Best Performers")
        print("-" * 80)

        if self.result.best_throughput:
            best_tp = self.result.policy_results[self.result.best_throughput]
            print(
                f"  Best Overall Throughput: {self.result.best_throughput} "
                f"({best_tp.metrics.throughput_rps:.1f} req/s)"
            )

        if self.result.best_llm_throughput:
            best_llm = self.result.policy_results[self.result.best_llm_throughput]
            print(
                f"  Best LLM Throughput: {self.result.best_llm_throughput} "
                f"({best_llm.metrics.llm_throughput_rps:.1f} req/s)"
            )

        if self.result.best_embedding_throughput:
            best_embed = self.result.policy_results[self.result.best_embedding_throughput]
            print(
                f"  Best Embedding Throughput: {self.result.best_embedding_throughput} "
                f"({best_embed.metrics.embedding_throughput_rps:.1f} req/s)"
            )

        if self.result.best_slo_compliance:
            best_slo = self.result.policy_results[self.result.best_slo_compliance]
            print(
                f"  Best SLO Compliance: {self.result.best_slo_compliance} "
                f"({best_slo.metrics.slo_compliance_rate:.1%})"
            )

        if self.result.best_p99_latency:
            best_p99 = self.result.policy_results[self.result.best_p99_latency]
            print(
                f"  Best P99 Latency: {self.result.best_p99_latency} "
                f"({best_p99.metrics.e2e_latency_p99_ms:.0f} ms)"
            )

        print()

    def save_json(self, output_path: Path | str) -> Path:
        """Save full results as JSON.

        Args:
            output_path: Path to save JSON file

        Returns:
            Path where file was saved
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        report: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "version": "1.0",
            "benchmark_type": "hybrid",
            **self.result.to_dict(),
        }

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        return output_path

    def save_csv(self, output_path: Path | str) -> Path:
        """Save summary as CSV.

        Args:
            output_path: Path to save CSV file

        Returns:
            Path where file was saved
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        headers = [
            # Basic info
            "policy",
            # Overall metrics
            "throughput_rps",
            "e2e_latency_avg_ms",
            "e2e_latency_p50_ms",
            "e2e_latency_p95_ms",
            "e2e_latency_p99_ms",
            "slo_compliance_rate",
            "error_rate",
            "timeout_rate",
            "total_requests",
            "completed_requests",
            # LLM metrics
            "llm_total_requests",
            "llm_completed_requests",
            "llm_throughput_rps",
            "llm_token_throughput_tps",
            "llm_ttft_avg_ms",
            "llm_ttft_p50_ms",
            "llm_ttft_p95_ms",
            "llm_ttft_p99_ms",
            "llm_tbt_avg_ms",
            "llm_e2e_latency_avg_ms",
            "llm_e2e_latency_p99_ms",
            "llm_slo_compliance_rate",
            # Embedding metrics
            "embedding_total_requests",
            "embedding_completed_requests",
            "embedding_throughput_rps",
            "embedding_throughput_texts_ps",
            "embedding_batch_efficiency",
            "embedding_avg_batch_size",
            "embedding_e2e_latency_avg_ms",
            "embedding_e2e_latency_p99_ms",
            "embedding_slo_compliance_rate",
            # Mix ratios
            "llm_ratio_actual",
            "embedding_ratio_actual",
            # GPU metrics
            "gpu_utilization_avg",
            "gpu_utilization_max",
            "gpu_memory_avg_mb",
            "gpu_memory_max_mb",
        ]

        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)

            for policy_name, policy_result in self.result.policy_results.items():
                m = policy_result.metrics
                gpu = policy_result.gpu_metrics

                row = [
                    # Basic info
                    policy_name,
                    # Overall metrics
                    m.throughput_rps,
                    m.e2e_latency_avg_ms,
                    m.e2e_latency_p50_ms,
                    m.e2e_latency_p95_ms,
                    m.e2e_latency_p99_ms,
                    m.slo_compliance_rate,
                    m.error_rate,
                    m.timeout_rate,
                    m.total_requests,
                    m.completed_requests,
                    # LLM metrics
                    m.llm_total_requests,
                    m.llm_completed_requests,
                    m.llm_throughput_rps,
                    m.llm_token_throughput_tps,
                    m.llm_ttft_avg_ms,
                    m.llm_ttft_p50_ms,
                    m.llm_ttft_p95_ms,
                    m.llm_ttft_p99_ms,
                    m.llm_tbt_avg_ms,
                    m.llm_e2e_latency_avg_ms,
                    m.llm_e2e_latency_p99_ms,
                    m.llm_slo_compliance_rate,
                    # Embedding metrics
                    m.embedding_total_requests,
                    m.embedding_completed_requests,
                    m.embedding_throughput_rps,
                    m.embedding_throughput_texts_ps,
                    m.embedding_batch_efficiency,
                    m.embedding_avg_batch_size,
                    m.embedding_e2e_latency_avg_ms,
                    m.embedding_e2e_latency_p99_ms,
                    m.embedding_slo_compliance_rate,
                    # Mix ratios
                    m.llm_ratio_actual,
                    m.embedding_ratio_actual,
                    # GPU metrics
                    gpu.utilization_avg if gpu else "",
                    gpu.utilization_max if gpu else "",
                    gpu.memory_used_avg_mb if gpu else "",
                    gpu.memory_used_max_mb if gpu else "",
                ]
                writer.writerow(row)

        return output_path

    def save_detailed_csv(self, output_path: Path | str) -> Path:
        """Save detailed per-request results as CSV.

        This includes all raw request results for detailed analysis.

        Args:
            output_path: Path to save CSV file

        Returns:
            Path where file was saved
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        headers = [
            "policy",
            "request_id",
            "request_type",
            "priority",
            "slo_deadline_ms",
            "send_time",
            "completion_time",
            "e2e_latency_ms",
            "success",
            "met_slo",
            "error",
            # LLM-specific
            "model_name",
            "ttft_ms",
            "output_token_count",
            # Embedding-specific
            "embedding_model",
            "batch_size",
            "total_texts_embedded",
            "texts_per_second",
        ]

        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)

            for policy_name, policy_result in self.result.policy_results.items():
                for r in policy_result.raw_results:
                    row = [
                        policy_name,
                        r.request_id,
                        r.request_type.value,
                        r.priority,
                        r.slo_deadline_ms,
                        r.send_time,
                        r.completion_time,
                        r.e2e_latency_ms,
                        r.success,
                        r.met_slo,
                        r.error or "",
                        # LLM-specific
                        r.model_name if r.is_llm_request else "",
                        r.ttft_ms if r.is_llm_request else "",
                        r.output_token_count if r.is_llm_request else "",
                        # Embedding-specific
                        r.embedding_model if r.is_embedding_request else "",
                        r.batch_size if r.is_embedding_request else "",
                        r.total_texts_embedded if r.is_embedding_request else "",
                        r.texts_per_second if r.is_embedding_request else "",
                    ]
                    writer.writerow(row)

        return output_path

    def get_comparison_table(self) -> dict[str, dict[str, Any]]:
        """Get a comparison table of all policies.

        Returns:
            Dictionary with policy names as keys and metric dictionaries as values
        """
        comparison: dict[str, dict[str, Any]] = {}

        for policy_name, policy_result in self.result.policy_results.items():
            m = policy_result.metrics
            gpu = policy_result.gpu_metrics

            comparison[policy_name] = {
                "overall": {
                    "throughput_rps": m.throughput_rps,
                    "e2e_latency_p99_ms": m.e2e_latency_p99_ms,
                    "slo_compliance_rate": m.slo_compliance_rate,
                    "error_rate": m.error_rate,
                },
                "llm": {
                    "throughput_rps": m.llm_throughput_rps,
                    "token_throughput_tps": m.llm_token_throughput_tps,
                    "ttft_avg_ms": m.llm_ttft_avg_ms,
                    "slo_compliance_rate": m.llm_slo_compliance_rate,
                },
                "embedding": {
                    "throughput_rps": m.embedding_throughput_rps,
                    "texts_per_second": m.embedding_throughput_texts_ps,
                    "batch_efficiency": m.embedding_batch_efficiency,
                    "slo_compliance_rate": m.embedding_slo_compliance_rate,
                },
                "gpu": {
                    "utilization_avg": gpu.utilization_avg if gpu else None,
                    "memory_used_avg_mb": gpu.memory_used_avg_mb if gpu else None,
                },
            }

        return comparison
