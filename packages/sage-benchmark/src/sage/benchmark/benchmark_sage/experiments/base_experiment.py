"""
Base experiment class for ICML benchmarks.

Provides common infrastructure for:
- Configuration management
- Workload generation
- Metrics collection
- Result reporting
"""

import json
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np

from sage.benchmark.benchmark_sage.experiments.common import RequestResult
from sage.benchmark.benchmark_sage.experiments.config import ExperimentConfig
from sage.benchmark.benchmark_sage.experiments.plotting import Plotter


@dataclass
class ExperimentResult:
    """Complete experiment results."""

    experiment_name: str
    experiment_section: str
    start_time: str
    end_time: str
    duration_s: float
    config: dict

    # Aggregate metrics
    total_requests: int
    successful_requests: int
    failed_requests: int
    throughput_rps: float

    # Latency metrics
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_mean_ms: float

    # SLO metrics
    slo_satisfaction_rate: float

    # Per-type metrics
    llm_metrics: dict = field(default_factory=dict)
    embedding_metrics: dict = field(default_factory=dict)

    # Raw data
    raw_results: list[dict] = field(default_factory=list)

    # Comparison data (for multi-baseline experiments)
    baseline_results: dict = field(default_factory=dict)


class BaseExperiment(ABC):
    """Base class for all ICML experiments."""

    def __init__(
        self,
        config: ExperimentConfig,
        output_dir: Path | str,
        verbose: bool = False,
    ):
        self.config = config
        self.output_dir = Path(output_dir)
        self.verbose = verbose

        # State
        self.results: list[RequestResult] = []
        self.start_time: float | None = None
        self.end_time: float | None = None

        # Random seed for reproducibility
        random.seed(config.workload.seed)
        np.random.seed(config.workload.seed)

    def validate(self) -> bool:
        """Validate configuration. Override in subclasses for specific validation."""
        if self.config.hardware.gpus < 1:
            raise ValueError("At least 1 GPU required")
        if self.config.workload.total_requests < 1:
            raise ValueError("total_requests must be positive")
        if not 0 <= self.config.workload.llm_ratio <= 1:
            raise ValueError("llm_ratio must be between 0 and 1")
        return True

    def setup(self) -> None:
        """Setup experiment environment."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log(f"Output directory: {self.output_dir}")

        # Save config
        config_path = self.output_dir / "config.json"
        with open(config_path, "w") as f:
            json.dump(self._config_to_dict(), f, indent=2)

        self._setup_impl()

    @abstractmethod
    def _setup_impl(self) -> None:
        """Implementation-specific setup. Override in subclasses."""
        pass

    def run(self) -> ExperimentResult:
        """Run the experiment."""
        self.log(f"Starting experiment: {self.config.name}")
        self.start_time = time.time()

        # Run warmup
        self.log(f"Running {self.config.workload.warmup_requests} warmup requests...")
        self._run_warmup()

        # Run main experiment
        self.log(f"Running {self.config.workload.total_requests} main requests...")
        self._run_impl()

        self.end_time = time.time()

        # Compute results
        result = self._compute_results()

        # Save results
        self._save_results(result)

        # Generate visualizations
        if self.config.output.generate_plots:
            self._generate_plots(result)

        return result

    @abstractmethod
    def _run_impl(self) -> None:
        """Implementation-specific run logic. Override in subclasses."""
        pass

    def _run_warmup(self) -> None:
        """Run warmup requests (not counted in results)."""
        # Default: run a fraction of requests as warmup
        # Subclasses should implement actual warmup
        pass

    def teardown(self) -> None:
        """Cleanup after experiment."""
        self._teardown_impl()
        self.log("Experiment teardown complete.")

    def _teardown_impl(self) -> None:
        """Implementation-specific teardown. Override in subclasses."""
        pass

    def _compute_results(self) -> ExperimentResult:
        """Compute aggregate metrics from raw results."""
        if not self.results:
            raise ValueError("No results to compute")

        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]

        latencies = [r.latency_ms for r in successful]

        duration = (self.end_time or time.time()) - (self.start_time or 0)

        # Separate by type
        llm_results = [r for r in successful if r.request_type == "llm"]
        embedding_results = [r for r in successful if r.request_type == "embedding"]

        # SLO calculation
        slo_met = sum(
            1
            for r in successful
            if (r.request_type == "llm" and r.latency_ms <= self.config.metrics.slo_chat_p99_ms)
            or (
                r.request_type == "embedding"
                and r.latency_ms <= self.config.metrics.slo_embedding_p99_ms
            )
        )

        return ExperimentResult(
            experiment_name=self.config.name,
            experiment_section=self.config.experiment_section,
            start_time=datetime.fromtimestamp(self.start_time).isoformat()
            if self.start_time
            else "",
            end_time=datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else "",
            duration_s=duration,
            config=self._config_to_dict(),
            total_requests=len(self.results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            throughput_rps=len(successful) / duration if duration > 0 else 0,
            latency_p50_ms=float(np.percentile(latencies, 50)) if latencies else 0,
            latency_p95_ms=float(np.percentile(latencies, 95)) if latencies else 0,
            latency_p99_ms=float(np.percentile(latencies, 99)) if latencies else 0,
            latency_mean_ms=float(np.mean(latencies)) if latencies else 0,
            slo_satisfaction_rate=slo_met / len(successful) if successful else 0,
            llm_metrics=self._compute_type_metrics(llm_results),
            embedding_metrics=self._compute_type_metrics(embedding_results),
            raw_results=[self._result_to_dict(r) for r in self.results]
            if self.config.output.save_raw_data
            else [],
        )

    def _compute_type_metrics(self, results: list[RequestResult]) -> dict:
        """Compute metrics for a specific request type."""
        if not results:
            return {}

        latencies = [r.latency_ms for r in results]
        return {
            "count": len(results),
            "latency_p50_ms": float(np.percentile(latencies, 50)),
            "latency_p95_ms": float(np.percentile(latencies, 95)),
            "latency_p99_ms": float(np.percentile(latencies, 99)),
            "latency_mean_ms": float(np.mean(latencies)),
            "tokens_in_total": sum(r.tokens_in for r in results),
            "tokens_out_total": sum(r.tokens_out for r in results),
        }

    def _save_results(self, result: ExperimentResult) -> None:
        """Save results to files."""
        # JSON results
        results_path = self.output_dir / "results.json"
        with open(results_path, "w") as f:
            json.dump(self._result_to_full_dict(result), f, indent=2)

        # Summary
        summary_path = self.output_dir / "summary.txt"
        with open(summary_path, "w") as f:
            f.write(self._generate_summary(result))

        # LaTeX table
        if self.config.output.export_latex:
            latex_path = self.output_dir / "results_table.tex"
            with open(latex_path, "w") as f:
                f.write(self._generate_latex_table(result))

        self.log(f"Results saved to {self.output_dir}")

    def _generate_plots(self, result: ExperimentResult) -> None:
        """Generate visualization plots."""
        try:
            plotter = Plotter()

            # 1. Latency Distribution (Histogram -> CDF is better for papers, but let's keep simple for now or use Plotter)
            # Using the new Plotter class

            # Prepare data for Plotter (it expects list of dicts for comparison, but here we have one result)
            # We wrap current result in a list
            result_dict = self._result_to_full_dict(result)
            result_dict["config_name"] = self.config.name  # Ensure name is present

            # Latency CDF
            plotter.plot_latency_cdf(
                [result_dict],
                self.output_dir / "latency_cdf.png",
                title=f"Latency CDF - {self.config.name}",
            )

            # Timeline (Waterfall)
            if result.raw_results:
                plotter.plot_timeline(result.raw_results, self.output_dir / "timeline.png")

        except Exception as e:
            self.log(f"Error generating plots: {e}")

    def _generate_summary(self, result: ExperimentResult) -> str:
        """Generate human-readable summary."""
        return f"""
Experiment Summary: {result.experiment_name}
{"=" * 60}
Section: {result.experiment_section}
Duration: {result.duration_s:.1f}s
Start: {result.start_time}
End: {result.end_time}

Requests:
  Total: {result.total_requests}
  Successful: {result.successful_requests}
  Failed: {result.failed_requests}
  Throughput: {result.throughput_rps:.2f} req/s

Latency:
  p50: {result.latency_p50_ms:.1f}ms
  p95: {result.latency_p95_ms:.1f}ms
  p99: {result.latency_p99_ms:.1f}ms
  Mean: {result.latency_mean_ms:.1f}ms

SLO Satisfaction: {result.slo_satisfaction_rate * 100:.1f}%

LLM Metrics:
  Count: {result.llm_metrics.get("count", 0)}
  p99 Latency: {result.llm_metrics.get("latency_p99_ms", 0):.1f}ms

Embedding Metrics:
  Count: {result.embedding_metrics.get("count", 0)}
  p99 Latency: {result.embedding_metrics.get("latency_p99_ms", 0):.1f}ms
"""

    def _generate_latex_table(self, result: ExperimentResult) -> str:
        """Generate LaTeX table for paper."""
        return f"""
\\begin{{table}}[htbp]
\\centering
\\caption{{Results for {result.experiment_name}}}
\\label{{tab:{result.experiment_name.replace("_", "-")}}}
\\begin{{tabular}}{{lc}}
\\toprule
Metric & Value \\\\
\\midrule
Total Requests & {result.total_requests} \\\\
Throughput (req/s) & {result.throughput_rps:.2f} \\\\
Latency p50 (ms) & {result.latency_p50_ms:.1f} \\\\
Latency p95 (ms) & {result.latency_p95_ms:.1f} \\\\
Latency p99 (ms) & {result.latency_p99_ms:.1f} \\\\
SLO Satisfaction & {result.slo_satisfaction_rate * 100:.1f}\\% \\\\
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""

    def log(self, message: str) -> None:
        """Log message if verbose mode is enabled."""
        if self.verbose:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] {message}")

    def _config_to_dict(self) -> dict:
        """Convert config to dictionary."""
        return {
            "name": self.config.name,
            "description": self.config.description,
            "section": self.config.experiment_section,
            "hardware": {
                "gpus": self.config.hardware.gpus,
                "gpu_type": self.config.hardware.gpu_type,
            },
            "models": {
                "llm": self.config.llm_model.name,
                "embedding": self.config.embedding_model.name,
            },
            "workload": {
                "total_requests": self.config.workload.total_requests,
                "llm_ratio": self.config.workload.llm_ratio,
                "request_rate": self.config.workload.request_rate,
            },
        }

    def _result_to_dict(self, r: RequestResult) -> dict:
        """Convert RequestResult to dictionary."""
        return {
            "request_id": r.request_id,
            "request_type": r.request_type,
            "start_time": r.start_time,
            "end_time": r.end_time,
            "latency_ms": r.latency_ms,
            "success": r.success,
            "error": r.error,
            "tokens_in": r.tokens_in,
            "tokens_out": r.tokens_out,
        }

    def _result_to_full_dict(self, result: ExperimentResult) -> dict:
        """Convert ExperimentResult to full dictionary."""
        return {
            "experiment_name": result.experiment_name,
            "experiment_section": result.experiment_section,
            "start_time": result.start_time,
            "end_time": result.end_time,
            "duration_s": result.duration_s,
            "config": result.config,
            "total_requests": result.total_requests,
            "successful_requests": result.successful_requests,
            "failed_requests": result.failed_requests,
            "throughput_rps": result.throughput_rps,
            "latency_p50_ms": result.latency_p50_ms,
            "latency_p95_ms": result.latency_p95_ms,
            "latency_p99_ms": result.latency_p99_ms,
            "latency_mean_ms": result.latency_mean_ms,
            "slo_satisfaction_rate": result.slo_satisfaction_rate,
            "llm_metrics": result.llm_metrics,
            "embedding_metrics": result.embedding_metrics,
            "raw_results": result.raw_results,
            "baseline_results": result.baseline_results,
        }
