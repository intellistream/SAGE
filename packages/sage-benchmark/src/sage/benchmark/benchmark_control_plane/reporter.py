"""
Benchmark Reporter Module
=========================

Generates reports from benchmark results.

This module provides:
- Terminal table output
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
    from .runner import BenchmarkResult, PolicyResult


class BenchmarkReporter:
    """Generates benchmark reports in various formats.

    Supports:
    - Rich terminal output with tables
    - JSON files for programmatic access
    - CSV files for spreadsheet analysis
    """

    def __init__(self, result: BenchmarkResult):
        """Initialize reporter.

        Args:
            result: BenchmarkResult to report on
        """
        self.result = result

    def print_summary(self) -> None:
        """Print summary to terminal."""
        print("\n" + "=" * 70)
        print("          sageLLM Scheduling Policy Benchmark Report")
        print("=" * 70)

        # Print config summary
        config = self.result.config
        print(f"Config: {config.get('num_requests', 'N/A')} requests "
              f"@ {config.get('request_rate', 'N/A')} req/s")
        models = list(config.get('model_distribution', {}).keys())
        print(f"Models: {', '.join(models)}")
        print("-" * 70)
        print()

        # Print table header
        headers = [
            "Policy",
            "Throughput",
            "Avg E2E",
            "P99 E2E",
            "Avg TTFT",
            "SLO Rate",
            "Errors",
        ]
        header_line = "| " + " | ".join(f"{h:^10}" for h in headers) + " |"
        separator = "|" + "|".join("-" * 12 for _ in headers) + "|"

        print(header_line)
        print(separator)

        # Print data rows
        for policy_name, policy_result in self.result.policy_results.items():
            m = policy_result.metrics
            row = [
                policy_name[:10],
                f"{m.throughput_rps:.1f} req/s",
                f"{m.e2e_latency_avg_ms:.0f} ms",
                f"{m.e2e_latency_p99_ms:.0f} ms",
                f"{m.ttft_avg_ms:.0f} ms",
                f"{m.slo_compliance_rate:.1%}",
                f"{m.error_rate:.1%}",
            ]
            row_line = "| " + " | ".join(f"{v:^10}" for v in row) + " |"
            print(row_line)

        print()

        # Print best performers
        if self.result.best_throughput:
            best_tp = self.result.policy_results[self.result.best_throughput]
            print(f"Best Throughput: {self.result.best_throughput} "
                  f"({best_tp.metrics.throughput_rps:.1f} req/s)")

        if self.result.best_slo_compliance:
            best_slo = self.result.policy_results[self.result.best_slo_compliance]
            print(f"Best SLO Compliance: {self.result.best_slo_compliance} "
                  f"({best_slo.metrics.slo_compliance_rate:.1%})")

        if self.result.best_p99_latency:
            best_p99 = self.result.policy_results[self.result.best_p99_latency]
            print(f"Best P99 Latency: {self.result.best_p99_latency} "
                  f"({best_p99.metrics.e2e_latency_p99_ms:.0f} ms)")

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

        report = {
            "timestamp": datetime.now().isoformat(),
            "version": "1.0",
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
            "policy",
            "throughput_rps",
            "e2e_latency_avg_ms",
            "e2e_latency_p50_ms",
            "e2e_latency_p95_ms",
            "e2e_latency_p99_ms",
            "ttft_avg_ms",
            "ttft_p50_ms",
            "ttft_p95_ms",
            "ttft_p99_ms",
            "tbt_avg_ms",
            "tbt_p95_ms",
            "slo_compliance_rate",
            "error_rate",
            "timeout_rate",
            "total_requests",
            "completed_requests",
            "failed_requests",
        ]

        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)

            for policy_name, policy_result in self.result.policy_results.items():
                m = policy_result.metrics
                row = [
                    policy_name,
                    m.throughput_rps,
                    m.e2e_latency_avg_ms,
                    m.e2e_latency_p50_ms,
                    m.e2e_latency_p95_ms,
                    m.e2e_latency_p99_ms,
                    m.ttft_avg_ms,
                    m.ttft_p50_ms,
                    m.ttft_p95_ms,
                    m.ttft_p99_ms,
                    m.tbt_avg_ms,
                    m.tbt_p95_ms,
                    m.slo_compliance_rate,
                    m.error_rate,
                    m.timeout_rate,
                    m.total_requests,
                    m.completed_requests,
                    m.failed_requests,
                ]
                writer.writerow(row)

        return output_path

    def save_all(self, output_dir: Path | str) -> dict[str, Path]:
        """Save all report formats.

        Args:
            output_dir: Directory to save reports

        Returns:
            Dictionary mapping format to file path
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        paths = {
            "json": self.save_json(output_dir / f"report_{timestamp}.json"),
            "csv": self.save_csv(output_dir / f"summary_{timestamp}.csv"),
        }

        return paths

    def generate_detailed_report(self) -> str:
        """Generate a detailed text report.

        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("             SAGE Control Plane Benchmark Detailed Report")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.now().isoformat()}")
        lines.append("")

        # Configuration section
        lines.append("-" * 80)
        lines.append("CONFIGURATION")
        lines.append("-" * 80)
        config = self.result.config
        lines.append(f"  Control Plane URL: {config.get('control_plane_url', 'N/A')}")
        lines.append(f"  Policies Tested: {', '.join(config.get('policies', []))}")
        lines.append(f"  Total Requests: {config.get('num_requests', 'N/A')}")
        lines.append(f"  Request Rate: {config.get('request_rate', 'N/A')} req/s")
        lines.append(f"  Arrival Pattern: {config.get('arrival_pattern', 'N/A')}")
        lines.append(f"  Warmup Requests: {config.get('warmup_requests', 'N/A')}")
        lines.append(f"  Timeout: {config.get('timeout_seconds', 'N/A')} seconds")
        lines.append("")

        # Per-policy sections
        for policy_name, policy_result in self.result.policy_results.items():
            lines.append("-" * 80)
            lines.append(f"POLICY: {policy_name.upper()}")
            lines.append("-" * 80)

            m = policy_result.metrics
            lines.append("")
            lines.append("  Request Statistics:")
            lines.append(f"    Total: {m.total_requests}")
            lines.append(f"    Completed: {m.completed_requests}")
            lines.append(f"    Failed: {m.failed_requests}")
            lines.append(f"    Timeouts: {m.timeout_requests}")
            lines.append("")

            lines.append("  Throughput:")
            lines.append(f"    Duration: {m.duration_seconds:.2f} seconds")
            lines.append(f"    Request Throughput: {m.throughput_rps:.2f} req/s")
            lines.append(f"    Token Throughput: {m.token_throughput_tps:.2f} token/s")
            lines.append("")

            lines.append("  End-to-End Latency:")
            lines.append(f"    Average: {m.e2e_latency_avg_ms:.2f} ms")
            lines.append(f"    P50: {m.e2e_latency_p50_ms:.2f} ms")
            lines.append(f"    P95: {m.e2e_latency_p95_ms:.2f} ms")
            lines.append(f"    P99: {m.e2e_latency_p99_ms:.2f} ms")
            lines.append(f"    Min: {m.e2e_latency_min_ms:.2f} ms")
            lines.append(f"    Max: {m.e2e_latency_max_ms:.2f} ms")
            lines.append("")

            lines.append("  Time to First Token (TTFT):")
            lines.append(f"    Average: {m.ttft_avg_ms:.2f} ms")
            lines.append(f"    P50: {m.ttft_p50_ms:.2f} ms")
            lines.append(f"    P95: {m.ttft_p95_ms:.2f} ms")
            lines.append(f"    P99: {m.ttft_p99_ms:.2f} ms")
            lines.append("")

            lines.append("  Time Between Tokens (TBT):")
            lines.append(f"    Average: {m.tbt_avg_ms:.2f} ms")
            lines.append(f"    P95: {m.tbt_p95_ms:.2f} ms")
            lines.append("")

            lines.append("  SLO Compliance:")
            lines.append(f"    Overall: {m.slo_compliance_rate:.1%}")
            for priority, rate in m.slo_by_priority.items():
                lines.append(f"    {priority}: {rate:.1%}")
            lines.append("")

            lines.append("  Error Rates:")
            lines.append(f"    Error Rate: {m.error_rate:.1%}")
            lines.append(f"    Timeout Rate: {m.timeout_rate:.1%}")
            lines.append("")

        # Summary section
        lines.append("=" * 80)
        lines.append("SUMMARY")
        lines.append("=" * 80)
        if self.result.best_throughput:
            lines.append(f"  Best Throughput: {self.result.best_throughput}")
        if self.result.best_slo_compliance:
            lines.append(f"  Best SLO Compliance: {self.result.best_slo_compliance}")
        if self.result.best_p99_latency:
            lines.append(f"  Best P99 Latency: {self.result.best_p99_latency}")
        lines.append("=" * 80)

        return "\n".join(lines)


def format_policy_result(policy_result: PolicyResult) -> dict[str, Any]:
    """Format a policy result for display.

    Args:
        policy_result: PolicyResult to format

    Returns:
        Formatted dictionary
    """
    m = policy_result.metrics
    return {
        "policy": policy_result.policy,
        "throughput": f"{m.throughput_rps:.1f} req/s",
        "latency": {
            "avg": f"{m.e2e_latency_avg_ms:.0f} ms",
            "p95": f"{m.e2e_latency_p95_ms:.0f} ms",
            "p99": f"{m.e2e_latency_p99_ms:.0f} ms",
        },
        "slo_compliance": f"{m.slo_compliance_rate:.1%}",
        "errors": f"{m.error_rate:.1%}",
    }
