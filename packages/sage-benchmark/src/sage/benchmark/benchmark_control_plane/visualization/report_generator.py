# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Benchmark Report Generator Module
==================================

Generates comprehensive HTML and Markdown reports from benchmark results.

This module provides:
- ReportGenerator: Main class for report generation
- HTML reports with embedded charts using Jinja2 templates
- Markdown reports for documentation and GitHub

Usage:
------
    from sage.benchmark.benchmark_control_plane.visualization import ReportGenerator

    generator = ReportGenerator(benchmark_result, charts_dir="./charts")
    generator.generate_html_report("./reports/benchmark_report.html")
    generator.generate_markdown_report("./reports/benchmark_report.md")
"""

from __future__ import annotations

import base64
import importlib.util
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..hybrid_scheduler.runner import HybridBenchmarkResult
    from ..llm_scheduler.runner import LLMBenchmarkResult

# Check Jinja2 availability using importlib.util.find_spec
JINJA2_AVAILABLE = importlib.util.find_spec("jinja2") is not None

logger = logging.getLogger(__name__)

# Template directory path
TEMPLATES_DIR = Path(__file__).parent / "templates"


class ReportGenerator:
    """Generates comprehensive benchmark reports in HTML and Markdown formats.

    This class uses Jinja2 templates for HTML reports and generates Markdown
    reports programmatically. Reports include:
    - Configuration summary
    - Performance metrics tables
    - Best performers summary
    - Embedded charts (for HTML)
    - Detailed per-policy breakdowns

    Example:
        result = await runner.run()
        charts = BenchmarkCharts(result.to_dict(), output_dir="./charts")
        chart_paths = charts.generate_all_charts()

        generator = ReportGenerator(result, charts_dir="./charts")
        generator.generate_html_report("./reports/report.html")
        generator.generate_markdown_report("./reports/report.md")
    """

    def __init__(
        self,
        result: LLMBenchmarkResult | HybridBenchmarkResult | dict[str, Any],
        charts_dir: str | Path | None = None,
        embed_charts: bool = True,
    ):
        """Initialize report generator.

        Args:
            result: Benchmark result object or dict
            charts_dir: Directory containing generated charts
            embed_charts: Whether to embed charts as base64 in HTML (default: True)
        """
        self.result = result
        self.charts_dir = Path(charts_dir) if charts_dir else None
        self.embed_charts = embed_charts
        self._jinja_env: Any = None

        if not JINJA2_AVAILABLE:
            logger.warning(
                "Jinja2 not available. HTML report generation will be disabled. "
                "Install with: pip install jinja2"
            )

    def _get_jinja_env(self) -> Any:
        """Get or create Jinja2 environment."""
        if self._jinja_env is None and JINJA2_AVAILABLE:
            # Import is guaranteed to succeed when JINJA2_AVAILABLE is True
            from jinja2 import Environment, FileSystemLoader, select_autoescape

            self._jinja_env = Environment(
                loader=FileSystemLoader(str(TEMPLATES_DIR)),
                autoescape=select_autoescape(["html", "xml"]),
            )
        return self._jinja_env

    def _get_result_dict(self) -> dict[str, Any]:
        """Convert result to dictionary if needed."""
        if isinstance(self.result, dict):
            return self.result
        if hasattr(self.result, "to_dict"):
            return self.result.to_dict()
        return {}

    def _is_hybrid_result(self) -> bool:
        """Check if result is from hybrid benchmark."""
        result_dict = self._get_result_dict()
        config = result_dict.get("config", {})
        return "llm_ratio" in config or "embedding_ratio" in config

    def _get_chart_paths(self) -> list[dict[str, str]]:
        """Get list of chart files with titles."""
        if not self.charts_dir or not self.charts_dir.exists():
            return []

        charts = []
        chart_titles = {
            "throughput_comparison": "Throughput Comparison",
            "throughput_vs_rate": "Throughput vs Request Rate",
            "latency_distribution": "Latency Distribution",
            "latency_percentiles": "Latency Percentiles",
            "latency_cdf": "Latency CDF",
            "slo_compliance": "SLO Compliance",
            "slo_by_priority": "SLO by Priority",
            "gpu_utilization": "GPU Utilization",
            "gpu_memory": "GPU Memory Usage",
            "mixed_ratio_impact": "Mixed Ratio Impact",
            "type_breakdown": "Request Type Breakdown",
            "embedding_batch_efficiency": "Embedding Batch Efficiency",
        }

        for ext in ["png", "svg", "pdf"]:
            for chart_file in self.charts_dir.glob(f"*.{ext}"):
                chart_name = chart_file.stem
                title = chart_titles.get(chart_name, chart_name.replace("_", " ").title())

                if self.embed_charts and ext in ["png", "svg"]:
                    # Read and encode as base64
                    with open(chart_file, "rb") as f:
                        data = base64.b64encode(f.read()).decode("utf-8")
                    mime = "image/png" if ext == "png" else "image/svg+xml"
                    path = f"data:{mime};base64,{data}"
                else:
                    path = str(chart_file)

                charts.append({"path": path, "title": title, "name": chart_name})

        return charts

    def _prepare_template_context(self) -> dict[str, Any]:
        """Prepare context data for template rendering."""
        result_dict = self._get_result_dict()
        config = result_dict.get("config", {})
        policy_results = result_dict.get("policy_results", {})
        summary = result_dict.get("summary", {})

        # Get best performers with values
        best_throughput = summary.get("best_throughput", "")
        best_slo = summary.get("best_slo_compliance", "")
        best_p99 = summary.get("best_p99_latency", "")

        best_throughput_value = 0
        best_slo_value = 0
        best_p99_value = 0

        if best_throughput and best_throughput in policy_results:
            metrics = policy_results[best_throughput].get("metrics", {})
            best_throughput_value = metrics.get("throughput", {}).get(
                "requests_per_second", 0
            )

        if best_slo and best_slo in policy_results:
            metrics = policy_results[best_slo].get("metrics", {})
            best_slo_value = metrics.get("slo", {}).get("compliance_rate", 0) * 100

        if best_p99 and best_p99 in policy_results:
            metrics = policy_results[best_p99].get("metrics", {})
            best_p99_value = metrics.get("e2e_latency_ms", {}).get("p99", 0)

        # Transform policy results for template
        transformed_results = {}
        for policy_name, policy_data in policy_results.items():
            metrics = policy_data.get("metrics", {})
            transformed_results[policy_name] = {
                "metrics": self._flatten_metrics(metrics),
                "gpu_metrics": policy_data.get("gpu_metrics"),
            }

        context = {
            "title": "Control Plane Benchmark Report",
            "subtitle": "Scheduling Policy Performance Analysis",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "benchmark_type": "Hybrid" if self._is_hybrid_result() else "LLM",
            "config": config,
            "policy_results": transformed_results,
            "charts": self._get_chart_paths(),
            "best_throughput": best_throughput,
            "best_throughput_value": f"{best_throughput_value:.1f}",
            "best_slo_compliance": best_slo,
            "best_slo_value": f"{best_slo_value:.1f}",
            "best_p99_latency": best_p99,
            "best_p99_value": f"{best_p99_value:.0f}",
            "is_hybrid": self._is_hybrid_result(),
        }

        # Add hybrid-specific data
        if self._is_hybrid_result():
            context["best_llm_throughput"] = summary.get("best_llm_throughput", "")
            context["best_embedding_throughput"] = summary.get(
                "best_embedding_throughput", ""
            )

        return context

    def _flatten_metrics(self, metrics: dict[str, Any]) -> dict[str, Any]:
        """Flatten nested metrics dict for template access."""
        flat = {}

        # Request counts
        counts = metrics.get("request_counts", {})
        flat["total_requests"] = counts.get("total", 0)
        flat["completed_requests"] = counts.get("completed", 0)
        flat["failed_requests"] = counts.get("failed", 0)
        flat["timeout_requests"] = counts.get("timeout", 0)

        # Throughput
        throughput = metrics.get("throughput", {})
        flat["throughput_rps"] = throughput.get("requests_per_second", 0)
        flat["token_throughput_tps"] = throughput.get("tokens_per_second", 0)
        flat["duration_seconds"] = throughput.get("duration_seconds", 0)

        # E2E Latency
        latency = metrics.get("e2e_latency_ms", {})
        flat["e2e_latency_avg_ms"] = latency.get("avg", 0)
        flat["e2e_latency_p50_ms"] = latency.get("p50", 0)
        flat["e2e_latency_p95_ms"] = latency.get("p95", 0)
        flat["e2e_latency_p99_ms"] = latency.get("p99", 0)
        flat["e2e_latency_min_ms"] = latency.get("min", 0)
        flat["e2e_latency_max_ms"] = latency.get("max", 0)

        # TTFT (for LLM)
        ttft = metrics.get("ttft_ms", {})
        flat["ttft_avg_ms"] = ttft.get("avg", 0)
        flat["ttft_p50_ms"] = ttft.get("p50", 0)
        flat["ttft_p95_ms"] = ttft.get("p95", 0)
        flat["ttft_p99_ms"] = ttft.get("p99", 0)

        # TBT (for LLM)
        tbt = metrics.get("tbt_ms", {})
        flat["tbt_avg_ms"] = tbt.get("avg", 0)
        flat["tbt_p95_ms"] = tbt.get("p95", 0)

        # SLO
        slo = metrics.get("slo", {})
        flat["slo_compliance_rate"] = slo.get("compliance_rate", 0)

        # Errors
        errors = metrics.get("errors", {})
        flat["error_rate"] = errors.get("error_rate", 0)
        flat["timeout_rate"] = errors.get("timeout_rate", 0)

        # LLM-specific (for hybrid)
        llm = metrics.get("llm", {})
        if llm:
            llm_throughput = llm.get("throughput", {})
            flat["llm_throughput_rps"] = llm_throughput.get("requests_per_second", 0)
            flat["llm_token_throughput_tps"] = llm_throughput.get("tokens_per_second", 0)
            llm_ttft = llm.get("ttft_ms", {})
            flat["llm_ttft_avg_ms"] = llm_ttft.get("avg", 0)
            flat["llm_ttft_p99_ms"] = llm_ttft.get("p99", 0)
            flat["llm_slo_compliance_rate"] = llm.get("slo_compliance_rate", 0)

        # Embedding-specific (for hybrid)
        embedding = metrics.get("embedding", {})
        if embedding:
            emb_throughput = embedding.get("throughput", {})
            flat["embedding_throughput_rps"] = emb_throughput.get("requests_per_second", 0)
            flat["embedding_throughput_texts_ps"] = emb_throughput.get(
                "texts_per_second", 0
            )
            batch = embedding.get("batch", {})
            flat["embedding_batch_efficiency"] = batch.get("efficiency", 0)
            flat["embedding_avg_batch_size"] = batch.get("avg_size", 0)
            flat["embedding_slo_compliance_rate"] = embedding.get("slo_compliance_rate", 0)

        return flat

    def generate_html_report(
        self,
        output_path: str | Path,
        template_name: str | None = None,
    ) -> Path:
        """Generate HTML report using Jinja2 template.

        Args:
            output_path: Path to save the HTML report
            template_name: Template file name (default: auto-select based on result type)

        Returns:
            Path to generated report

        Raises:
            RuntimeError: If Jinja2 is not available
        """
        if not JINJA2_AVAILABLE:
            raise RuntimeError(
                "Jinja2 is required for HTML report generation. "
                "Install with: pip install jinja2"
            )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Select template
        if template_name is None:
            template_name = "benchmark_report.html"

        env = self._get_jinja_env()
        template = env.get_template(template_name)

        # Render template
        context = self._prepare_template_context()
        html_content = template.render(**context)

        # Write output
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"Generated HTML report: {output_path}")
        return output_path

    def generate_markdown_report(
        self,
        output_path: str | Path,
    ) -> Path:
        """Generate Markdown report.

        Args:
            output_path: Path to save the Markdown report

        Returns:
            Path to generated report
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        result_dict = self._get_result_dict()
        config = result_dict.get("config", {})
        policy_results = result_dict.get("policy_results", {})
        summary = result_dict.get("summary", {})

        lines = []

        # Header
        lines.append("# SAGE Control Plane Benchmark Report")
        lines.append("")
        benchmark_type = "Hybrid" if self._is_hybrid_result() else "LLM"
        lines.append(f"**Benchmark Type:** {benchmark_type}")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Summary section
        lines.append("## Summary")
        lines.append("")
        if summary.get("best_throughput"):
            lines.append(f"- **Best Throughput:** {summary['best_throughput']}")
        if summary.get("best_slo_compliance"):
            lines.append(f"- **Best SLO Compliance:** {summary['best_slo_compliance']}")
        if summary.get("best_p99_latency"):
            lines.append(f"- **Best P99 Latency:** {summary['best_p99_latency']}")
        if self._is_hybrid_result():
            if summary.get("best_llm_throughput"):
                lines.append(f"- **Best LLM Throughput:** {summary['best_llm_throughput']}")
            if summary.get("best_embedding_throughput"):
                lines.append(
                    f"- **Best Embedding Throughput:** {summary['best_embedding_throughput']}"
                )
        lines.append("")

        # Configuration section
        lines.append("## Configuration")
        lines.append("")
        lines.append("| Parameter | Value |")
        lines.append("|-----------|-------|")
        lines.append(f"| Control Plane URL | {config.get('control_plane_url', 'N/A')} |")
        lines.append(f"| Total Requests | {config.get('num_requests', 'N/A')} |")
        lines.append(f"| Request Rate | {config.get('request_rate', 'N/A')} req/s |")
        lines.append(f"| Arrival Pattern | {config.get('arrival_pattern', 'N/A')} |")
        policies = config.get("policies", [])
        lines.append(f"| Policies | {', '.join(policies) if policies else 'N/A'} |")
        if self._is_hybrid_result():
            lines.append(f"| LLM Ratio | {config.get('llm_ratio', 'N/A')} |")
            lines.append(f"| Embedding Ratio | {config.get('embedding_ratio', 'N/A')} |")
        lines.append("")

        # Comparison table
        lines.append("## Policy Comparison")
        lines.append("")

        if self._is_hybrid_result():
            lines.append(
                "| Policy | Throughput | LLM Throughput | Embed Throughput | "
                "Avg Latency | P99 Latency | SLO Rate | Error Rate |"
            )
            lines.append("|--------|------------|----------------|------------------|"
                         "------------|-------------|----------|------------|")
        else:
            lines.append(
                "| Policy | Throughput | Avg Latency | P99 Latency | "
                "Avg TTFT | SLO Rate | Error Rate |"
            )
            lines.append("|--------|------------|-------------|-------------|"
                         "----------|----------|------------|")

        for policy_name, policy_data in policy_results.items():
            metrics = self._flatten_metrics(policy_data.get("metrics", {}))

            throughput = f"{metrics['throughput_rps']:.1f} req/s"
            avg_latency = f"{metrics['e2e_latency_avg_ms']:.0f} ms"
            p99_latency = f"{metrics['e2e_latency_p99_ms']:.0f} ms"
            slo_rate = f"{metrics['slo_compliance_rate'] * 100:.1f}%"
            error_rate = f"{metrics['error_rate'] * 100:.1f}%"

            if self._is_hybrid_result():
                llm_tp = f"{metrics.get('llm_throughput_rps', 0):.1f} req/s"
                emb_tp = f"{metrics.get('embedding_throughput_rps', 0):.1f} req/s"
                lines.append(
                    f"| {policy_name} | {throughput} | {llm_tp} | {emb_tp} | "
                    f"{avg_latency} | {p99_latency} | {slo_rate} | {error_rate} |"
                )
            else:
                ttft = f"{metrics.get('ttft_avg_ms', 0):.0f} ms"
                lines.append(
                    f"| {policy_name} | {throughput} | {avg_latency} | {p99_latency} | "
                    f"{ttft} | {slo_rate} | {error_rate} |"
                )

        lines.append("")

        # Detailed results per policy
        lines.append("## Detailed Results")
        lines.append("")

        for policy_name, policy_data in policy_results.items():
            metrics = self._flatten_metrics(policy_data.get("metrics", {}))

            lines.append(f"### {policy_name}")
            lines.append("")

            lines.append("#### Throughput")
            lines.append("")
            lines.append(f"- Request Throughput: {metrics['throughput_rps']:.1f} req/s")
            lines.append(f"- Token Throughput: {metrics['token_throughput_tps']:.1f} tokens/s")
            lines.append(f"- Duration: {metrics['duration_seconds']:.1f} seconds")
            lines.append("")

            lines.append("#### Latency")
            lines.append("")
            lines.append(f"- E2E Average: {metrics['e2e_latency_avg_ms']:.0f} ms")
            lines.append(f"- E2E P50: {metrics['e2e_latency_p50_ms']:.0f} ms")
            lines.append(f"- E2E P95: {metrics['e2e_latency_p95_ms']:.0f} ms")
            lines.append(f"- E2E P99: {metrics['e2e_latency_p99_ms']:.0f} ms")
            if not self._is_hybrid_result():
                lines.append(f"- TTFT Average: {metrics['ttft_avg_ms']:.0f} ms")
                lines.append(f"- TBT Average: {metrics['tbt_avg_ms']:.1f} ms")
            lines.append("")

            lines.append("#### Request Statistics")
            lines.append("")
            lines.append(f"- Total: {metrics['total_requests']}")
            lines.append(f"- Completed: {metrics['completed_requests']}")
            lines.append(f"- Failed: {metrics['failed_requests']}")
            lines.append(f"- Timeouts: {metrics['timeout_requests']}")
            lines.append(f"- SLO Compliance: {metrics['slo_compliance_rate'] * 100:.1f}%")
            lines.append(f"- Error Rate: {metrics['error_rate'] * 100:.1f}%")
            lines.append("")

            # Hybrid-specific sections
            if self._is_hybrid_result():
                lines.append("#### LLM Performance")
                lines.append("")
                lines.append(
                    f"- Throughput: {metrics.get('llm_throughput_rps', 0):.1f} req/s"
                )
                lines.append(
                    f"- Token Throughput: {metrics.get('llm_token_throughput_tps', 0):.1f} tokens/s"
                )
                lines.append(f"- TTFT Average: {metrics.get('llm_ttft_avg_ms', 0):.0f} ms")
                lines.append(
                    f"- SLO Compliance: {metrics.get('llm_slo_compliance_rate', 0) * 100:.1f}%"
                )
                lines.append("")

                lines.append("#### Embedding Performance")
                lines.append("")
                lines.append(
                    f"- Throughput: {metrics.get('embedding_throughput_rps', 0):.1f} req/s"
                )
                lines.append(
                    f"- Texts/s: {metrics.get('embedding_throughput_texts_ps', 0):.1f}"
                )
                lines.append(
                    f"- Batch Efficiency: {metrics.get('embedding_batch_efficiency', 0) * 100:.1f}%"
                )
                lines.append(
                    f"- Avg Batch Size: {metrics.get('embedding_avg_batch_size', 0):.1f}"
                )
                lines.append(
                    f"- SLO Compliance: {metrics.get('embedding_slo_compliance_rate', 0) * 100:.1f}%"
                )
                lines.append("")

            # GPU metrics
            gpu_metrics = policy_data.get("gpu_metrics")
            if gpu_metrics:
                lines.append("#### GPU Metrics")
                lines.append("")
                util = gpu_metrics.get("utilization", {})
                mem = gpu_metrics.get("memory", {})
                lines.append(f"- Utilization Average: {util.get('avg', 0):.1f}%")
                lines.append(f"- Utilization Max: {util.get('max', 0):.1f}%")
                lines.append(f"- Memory Used Average: {mem.get('used_avg_mb', 0):.0f} MB")
                lines.append(f"- Memory Used Max: {mem.get('used_max_mb', 0):.0f} MB")
                lines.append("")

        # Charts section
        charts = self._get_chart_paths()
        if charts and not self.embed_charts:
            lines.append("## Charts")
            lines.append("")
            for chart in charts:
                lines.append(f"### {chart['title']}")
                lines.append("")
                lines.append(f"![{chart['title']}]({chart['path']})")
                lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append("*Generated by SAGE Benchmark Framework*")

        # Write output
        content = "\n".join(lines)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Generated Markdown report: {output_path}")
        return output_path

    def generate_comparison_html_report(
        self,
        output_path: str | Path,
    ) -> Path:
        """Generate HTML comparison report for multiple policies.

        Args:
            output_path: Path to save the HTML report

        Returns:
            Path to generated report

        Raises:
            RuntimeError: If Jinja2 is not available
        """
        if not JINJA2_AVAILABLE:
            raise RuntimeError(
                "Jinja2 is required for HTML report generation. "
                "Install with: pip install jinja2"
            )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        env = self._get_jinja_env()
        template = env.get_template("comparison_report.html")

        context = self._prepare_template_context()
        html_content = template.render(**context)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"Generated comparison HTML report: {output_path}")
        return output_path

    def generate_full_report(
        self,
        output_dir: str | Path,
        report_name: str = "benchmark",
        include_html: bool = True,
        include_markdown: bool = True,
        include_comparison: bool = True,
    ) -> dict[str, Path]:
        """Generate all report formats.

        Args:
            output_dir: Directory to save reports
            report_name: Base name for report files
            include_html: Generate HTML report
            include_markdown: Generate Markdown report
            include_comparison: Generate comparison HTML report

        Returns:
            Dictionary mapping report type to output path
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        reports: dict[str, Path] = {}

        if include_html:
            try:
                html_path = output_dir / f"{report_name}.html"
                reports["html"] = self.generate_html_report(html_path)
            except RuntimeError as e:
                logger.warning(f"HTML report generation failed: {e}")

        if include_markdown:
            md_path = output_dir / f"{report_name}.md"
            reports["markdown"] = self.generate_markdown_report(md_path)

        if include_comparison:
            try:
                comparison_path = output_dir / f"{report_name}_comparison.html"
                reports["comparison"] = self.generate_comparison_html_report(comparison_path)
            except RuntimeError as e:
                logger.warning(f"Comparison report generation failed: {e}")

        return reports
