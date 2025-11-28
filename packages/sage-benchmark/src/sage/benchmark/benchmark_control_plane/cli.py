# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""
Command Line Interface for Control Plane Benchmark
===================================================

Provides CLI commands for running and comparing scheduling policy benchmarks.

Usage:
    # LLM-only benchmark
    sage-cp-bench run --mode llm --policy fifo --requests 100 --rate 10

    # Hybrid (LLM + Embedding) benchmark
    sage-cp-bench run --mode hybrid --policy hybrid_slo --llm-ratio 0.7 --requests 100

    # Compare policies
    sage-cp-bench compare --mode hybrid --policies fifo,priority,hybrid_slo

    # Run predefined experiment
    sage-cp-bench experiment --name throughput --mode llm

    # Generate visualizations from results
    sage-cp-bench visualize --input results.json --output ./charts

    # Load config from YAML
    sage-cp-bench run --config benchmark_config.yaml
"""

from __future__ import annotations

import asyncio
import json
import logging
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    import typer as typer_module

# Try to import typer, provide helpful error if not available
try:
    import typer
    from typer import Argument, Option

    TYPER_AVAILABLE = True
except ImportError:
    TYPER_AVAILABLE = False

    # Provide stub types for type checking when typer is not installed
    class _TyperStub:
        """Stub for typer module when not installed."""

        class Typer:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            def command(self, *args: Any, **kwargs: Any) -> Callable[..., Any]:
                def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
                    return f

                return decorator

        @staticmethod
        def echo(*args: Any, **kwargs: Any) -> None:
            pass

        class Exit(SystemExit):
            pass

    def _option_stub(*args: Any, **kwargs: Any) -> Any:
        return None

    def _argument_stub(*args: Any, **kwargs: Any) -> Any:
        return None

    typer = _TyperStub()  # type: ignore[assignment]
    Option = _option_stub  # type: ignore[misc, assignment]
    Argument = _argument_stub  # type: ignore[misc, assignment]

# Try to import PyYAML for config loading
try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:

    class _YamlStub:
        """Stub for yaml module when not installed."""

        @staticmethod
        def safe_load(f: Any) -> dict[str, Any]:
            return {}

        @staticmethod
        def dump(data: Any, f: Any, **kwargs: Any) -> None:
            pass

    yaml = _YamlStub()  # type: ignore[assignment]
    YAML_AVAILABLE = False

from .config import BenchmarkConfig
from .reporter import BenchmarkReporter
from .runner import BenchmarkRunner

logger = logging.getLogger(__name__)


class BenchmarkMode(str, Enum):
    """Benchmark mode."""

    LLM = "llm"
    HYBRID = "hybrid"


def load_config_file(config_path: Path) -> dict[str, Any]:
    """Load configuration from JSON or YAML file.

    Args:
        config_path: Path to config file

    Returns:
        Configuration dictionary

    Raises:
        ValueError: If file format is not supported
    """
    if not config_path.exists():
        raise ValueError(f"Config file not found: {config_path}")

    suffix = config_path.suffix.lower()

    if suffix == ".json":
        with open(config_path) as f:
            return json.load(f)
    elif suffix in (".yaml", ".yml"):
        if not YAML_AVAILABLE:
            raise ValueError(
                "PyYAML is required to load YAML config files. "
                "Install with: pip install pyyaml"
            )
        with open(config_path) as f:
            return yaml.safe_load(f)
    else:
        raise ValueError(f"Unsupported config file format: {suffix}")


def create_app() -> Any:
    """Create the CLI application.

    Returns:
        Typer application
    """
    if not TYPER_AVAILABLE:
        raise RuntimeError("typer is required for CLI. Install it with: pip install typer")

    app = typer.Typer(
        name="sage-cp-bench",
        help="🚀 sageLLM Control Plane Scheduling Policy Benchmark",
        add_completion=False,
    )

    # ========================================================================
    # run command - Run benchmark for a single policy
    # ========================================================================
    @app.command("run")
    def run_benchmark(
        mode: BenchmarkMode = Option(
            BenchmarkMode.LLM,
            "--mode",
            "-m",
            help="Benchmark mode: llm (LLM only) or hybrid (LLM + Embedding)",
        ),
        control_plane: str = Option(
            "http://localhost:8080",
            "--control-plane",
            "-c",
            help="Control Plane URL",
        ),
        policy: str = Option(
            "fifo",
            "--policy",
            "-p",
            help="Scheduling policy to benchmark",
        ),
        requests: int = Option(
            100,
            "--requests",
            "-n",
            help="Number of requests to send",
        ),
        rate: float = Option(
            10.0,
            "--rate",
            "-r",
            help="Request rate (requests/second)",
        ),
        llm_ratio: float = Option(
            0.7,
            "--llm-ratio",
            help="LLM request ratio for hybrid mode (0.0-1.0)",
        ),
        output: str = Option(
            "./benchmark_results",
            "--output",
            "-o",
            help="Output directory for results",
        ),
        warmup: int = Option(
            10,
            "--warmup",
            "-w",
            help="Number of warmup requests",
        ),
        timeout: float = Option(
            60.0,
            "--timeout",
            "-t",
            help="Request timeout in seconds",
        ),
        no_streaming: bool = Option(
            False,
            "--no-streaming",
            help="Disable streaming responses",
        ),
        no_visualize: bool = Option(
            False,
            "--no-visualize",
            help="Disable automatic visualization generation",
        ),
        config: str = Option(
            None,
            "--config",
            help="Load configuration from JSON/YAML file",
        ),
        quiet: bool = Option(
            False,
            "--quiet",
            "-q",
            help="Suppress progress output",
        ),
    ) -> None:
        """Run benchmark for a single scheduling policy.

        Examples:
            # LLM-only benchmark
            sage-cp-bench run --mode llm --policy fifo --requests 100

            # Hybrid benchmark with 70% LLM, 30% Embedding
            sage-cp-bench run --mode hybrid --policy hybrid_slo --llm-ratio 0.7

            # Load from config file
            sage-cp-bench run --config benchmark.yaml
        """
        # Load config from file if provided
        config_data: dict[str, Any] = {}
        if config:
            try:
                config_data = load_config_file(Path(config))
                if not quiet:
                    typer.echo(f"📄 Loaded config from: {config}")
            except ValueError as e:
                typer.echo(f"❌ {e}", err=True)
                raise typer.Exit(1)

        output_path = Path(output)

        if mode == BenchmarkMode.LLM:
            _run_llm_benchmark(
                control_plane=config_data.get("control_plane_url", control_plane),
                policy=config_data.get("policy", policy),
                requests=config_data.get("num_requests", requests),
                rate=config_data.get("request_rate", rate),
                output_path=output_path,
                warmup=config_data.get("warmup_requests", warmup),
                timeout=config_data.get("timeout_seconds", timeout),
                enable_streaming=not config_data.get("no_streaming", no_streaming),
                auto_visualize=not config_data.get("no_visualize", no_visualize),
                quiet=quiet,
            )
        else:
            _run_hybrid_benchmark(
                control_plane=config_data.get("control_plane_url", control_plane),
                policy=config_data.get("policy", policy),
                requests=config_data.get("num_requests", requests),
                rate=config_data.get("request_rate", rate),
                llm_ratio=config_data.get("llm_ratio", llm_ratio),
                output_path=output_path,
                warmup=config_data.get("warmup_requests", warmup),
                timeout=config_data.get("timeout_seconds", timeout),
                enable_streaming=not config_data.get("no_streaming", no_streaming),
                auto_visualize=not config_data.get("no_visualize", no_visualize),
                quiet=quiet,
            )

    def _run_llm_benchmark(
        control_plane: str,
        policy: str,
        requests: int,
        rate: float,
        output_path: Path,
        warmup: int,
        timeout: float,
        enable_streaming: bool,
        auto_visualize: bool,
        quiet: bool,
    ) -> None:
        """Run LLM-only benchmark."""
        from .llm_scheduler import (
            LLMBenchmarkConfig,
            LLMBenchmarkReporter,
            LLMBenchmarkRunner,
        )

        cfg = LLMBenchmarkConfig(
            control_plane_url=control_plane,
            policies=[policy],
            num_requests=requests,
            request_rate=rate,
            warmup_requests=warmup,
            timeout_seconds=timeout,
            enable_streaming=enable_streaming,
            auto_visualize=auto_visualize,
        )

        errors = cfg.validate()
        if errors:
            typer.echo(f"❌ Configuration errors: {errors}", err=True)
            raise typer.Exit(1)

        if not quiet:
            typer.echo(f"\n🚀 Running LLM benchmark for policy: {policy}")
            typer.echo(f"   Control Plane: {control_plane}")
            typer.echo(f"   Requests: {requests} @ {rate} req/s")

        runner = LLMBenchmarkRunner(cfg, verbose=not quiet, output_dir=output_path)
        result = asyncio.run(runner.run(auto_visualize=auto_visualize))

        reporter = LLMBenchmarkReporter(result)
        reporter.print_summary()

        output_path.mkdir(parents=True, exist_ok=True)
        reporter.save_json(output_path / "llm_benchmark_results.json")
        reporter.save_csv(output_path / "llm_benchmark_results.csv")

        if not quiet:
            typer.echo(f"\n📁 Results saved to: {output_path}")

    def _run_hybrid_benchmark(
        control_plane: str,
        policy: str,
        requests: int,
        rate: float,
        llm_ratio: float,
        output_path: Path,
        warmup: int,
        timeout: float,
        enable_streaming: bool,
        auto_visualize: bool,
        quiet: bool,
    ) -> None:
        """Run hybrid (LLM + Embedding) benchmark."""
        from .hybrid_scheduler import (
            HybridBenchmarkConfig,
            HybridBenchmarkReporter,
            HybridBenchmarkRunner,
        )

        embedding_ratio = 1.0 - llm_ratio

        cfg = HybridBenchmarkConfig(
            control_plane_url=control_plane,
            policies=[policy],
            num_requests=requests,
            request_rate=rate,
            llm_ratio=llm_ratio,
            embedding_ratio=embedding_ratio,
            warmup_requests=warmup,
            timeout_seconds=timeout,
            enable_streaming=enable_streaming,
            auto_visualize=auto_visualize,
        )

        errors = cfg.validate()
        if errors:
            typer.echo(f"❌ Configuration errors: {errors}", err=True)
            raise typer.Exit(1)

        if not quiet:
            typer.echo(f"\n🚀 Running Hybrid benchmark for policy: {policy}")
            typer.echo(f"   Control Plane: {control_plane}")
            typer.echo(f"   Requests: {requests} @ {rate} req/s")
            typer.echo(f"   LLM Ratio: {llm_ratio:.0%}, Embedding Ratio: {embedding_ratio:.0%}")

        runner = HybridBenchmarkRunner(cfg, verbose=not quiet, output_dir=output_path)
        result = asyncio.run(runner.run(auto_visualize=auto_visualize))

        reporter = HybridBenchmarkReporter(result)
        reporter.print_summary()

        output_path.mkdir(parents=True, exist_ok=True)
        reporter.save_json(output_path / "hybrid_benchmark_results.json")
        reporter.save_csv(output_path / "hybrid_benchmark_results.csv")

        if not quiet:
            typer.echo(f"\n📁 Results saved to: {output_path}")

    # ========================================================================
    # compare command - Compare multiple policies
    # ========================================================================
    @app.command("compare")
    def compare_policies(
        mode: BenchmarkMode = Option(
            BenchmarkMode.LLM,
            "--mode",
            "-m",
            help="Benchmark mode: llm or hybrid",
        ),
        control_plane: str = Option(
            "http://localhost:8080",
            "--control-plane",
            "-c",
            help="Control Plane URL",
        ),
        policies: str = Option(
            "fifo,priority,slo_aware",
            "--policies",
            "-p",
            help="Comma-separated list of policies to compare",
        ),
        requests: int = Option(
            100,
            "--requests",
            "-n",
            help="Number of requests per policy",
        ),
        rate: float = Option(
            10.0,
            "--rate",
            "-r",
            help="Request rate (requests/second)",
        ),
        llm_ratio: float = Option(
            0.7,
            "--llm-ratio",
            help="LLM request ratio for hybrid mode (0.0-1.0)",
        ),
        output: str = Option(
            "./benchmark_results",
            "--output",
            "-o",
            help="Output directory for results",
        ),
        warmup: int = Option(
            10,
            "--warmup",
            "-w",
            help="Number of warmup requests",
        ),
        timeout: float = Option(
            60.0,
            "--timeout",
            "-t",
            help="Request timeout in seconds",
        ),
        no_visualize: bool = Option(
            False,
            "--no-visualize",
            help="Disable automatic visualization generation",
        ),
        config: str = Option(
            None,
            "--config",
            help="Load configuration from JSON/YAML file",
        ),
        quiet: bool = Option(
            False,
            "--quiet",
            "-q",
            help="Suppress progress output",
        ),
    ) -> None:
        """Compare multiple scheduling policies.

        Examples:
            # Compare LLM policies
            sage-cp-bench compare --mode llm --policies fifo,priority,slo_aware

            # Compare hybrid policies
            sage-cp-bench compare --mode hybrid --policies fifo,hybrid_slo --llm-ratio 0.7
        """
        config_data: dict[str, Any] = {}
        if config:
            try:
                config_data = load_config_file(Path(config))
                if not quiet:
                    typer.echo(f"📄 Loaded config from: {config}")
            except ValueError as e:
                typer.echo(f"❌ {e}", err=True)
                raise typer.Exit(1)

        policy_list = [p.strip() for p in policies.split(",")]
        output_path = Path(output)

        if mode == BenchmarkMode.LLM:
            _compare_llm_policies(
                control_plane=config_data.get("control_plane_url", control_plane),
                policy_list=config_data.get("policies", policy_list),
                requests=config_data.get("num_requests", requests),
                rate=config_data.get("request_rate", rate),
                output_path=output_path,
                warmup=config_data.get("warmup_requests", warmup),
                timeout=config_data.get("timeout_seconds", timeout),
                auto_visualize=not config_data.get("no_visualize", no_visualize),
                quiet=quiet,
            )
        else:
            _compare_hybrid_policies(
                control_plane=config_data.get("control_plane_url", control_plane),
                policy_list=config_data.get("policies", policy_list),
                requests=config_data.get("num_requests", requests),
                rate=config_data.get("request_rate", rate),
                llm_ratio=config_data.get("llm_ratio", llm_ratio),
                output_path=output_path,
                warmup=config_data.get("warmup_requests", warmup),
                timeout=config_data.get("timeout_seconds", timeout),
                auto_visualize=not config_data.get("no_visualize", no_visualize),
                quiet=quiet,
            )

    def _compare_llm_policies(
        control_plane: str,
        policy_list: list[str],
        requests: int,
        rate: float,
        output_path: Path,
        warmup: int,
        timeout: float,
        auto_visualize: bool,
        quiet: bool,
    ) -> None:
        """Compare LLM policies."""
        from .llm_scheduler import (
            LLMBenchmarkConfig,
            LLMBenchmarkReporter,
            LLMBenchmarkRunner,
        )

        cfg = LLMBenchmarkConfig(
            control_plane_url=control_plane,
            policies=policy_list,
            num_requests=requests,
            request_rate=rate,
            warmup_requests=warmup,
            timeout_seconds=timeout,
            auto_visualize=auto_visualize,
        )

        errors = cfg.validate()
        if errors:
            typer.echo(f"❌ Configuration errors: {errors}", err=True)
            raise typer.Exit(1)

        if not quiet:
            typer.echo(f"\n🔄 Comparing LLM policies: {', '.join(policy_list)}")
            typer.echo(f"   Control Plane: {control_plane}")
            typer.echo(f"   Requests per policy: {requests} @ {rate} req/s")

        runner = LLMBenchmarkRunner(cfg, verbose=not quiet, output_dir=output_path)
        result = asyncio.run(runner.run(auto_visualize=auto_visualize))

        reporter = LLMBenchmarkReporter(result)
        reporter.print_summary()

        output_path.mkdir(parents=True, exist_ok=True)
        reporter.save_json(output_path / "llm_comparison_results.json")
        reporter.save_csv(output_path / "llm_comparison_results.csv")

        if not quiet:
            typer.echo(f"\n📁 Results saved to: {output_path}")

    def _compare_hybrid_policies(
        control_plane: str,
        policy_list: list[str],
        requests: int,
        rate: float,
        llm_ratio: float,
        output_path: Path,
        warmup: int,
        timeout: float,
        auto_visualize: bool,
        quiet: bool,
    ) -> None:
        """Compare hybrid policies."""
        from .hybrid_scheduler import (
            HybridBenchmarkConfig,
            HybridBenchmarkReporter,
            HybridBenchmarkRunner,
        )

        embedding_ratio = 1.0 - llm_ratio

        cfg = HybridBenchmarkConfig(
            control_plane_url=control_plane,
            policies=policy_list,
            num_requests=requests,
            request_rate=rate,
            llm_ratio=llm_ratio,
            embedding_ratio=embedding_ratio,
            warmup_requests=warmup,
            timeout_seconds=timeout,
            auto_visualize=auto_visualize,
        )

        errors = cfg.validate()
        if errors:
            typer.echo(f"❌ Configuration errors: {errors}", err=True)
            raise typer.Exit(1)

        if not quiet:
            typer.echo(f"\n🔄 Comparing Hybrid policies: {', '.join(policy_list)}")
            typer.echo(f"   Control Plane: {control_plane}")
            typer.echo(f"   Requests per policy: {requests} @ {rate} req/s")
            typer.echo(f"   LLM Ratio: {llm_ratio:.0%}")

        runner = HybridBenchmarkRunner(cfg, verbose=not quiet, output_dir=output_path)
        result = asyncio.run(runner.run(auto_visualize=auto_visualize))

        reporter = HybridBenchmarkReporter(result)
        reporter.print_summary()

        output_path.mkdir(parents=True, exist_ok=True)
        reporter.save_json(output_path / "hybrid_comparison_results.json")
        reporter.save_csv(output_path / "hybrid_comparison_results.csv")

        if not quiet:
            typer.echo(f"\n📁 Results saved to: {output_path}")

    # ========================================================================
    # sweep command - Rate sweep for a policy
    # ========================================================================
    @app.command("sweep")
    def rate_sweep(
        mode: BenchmarkMode = Option(
            BenchmarkMode.LLM,
            "--mode",
            "-m",
            help="Benchmark mode: llm or hybrid",
        ),
        control_plane: str = Option(
            "http://localhost:8080",
            "--control-plane",
            "-c",
            help="Control Plane URL",
        ),
        policy: str = Option(
            "fifo",
            "--policy",
            "-p",
            help="Policy to benchmark",
        ),
        requests: int = Option(
            100,
            "--requests",
            "-n",
            help="Number of requests per rate",
        ),
        rates: str = Option(
            "10,50,100,200",
            "--rates",
            "-r",
            help="Comma-separated list of request rates to test",
        ),
        llm_ratio: float = Option(
            0.7,
            "--llm-ratio",
            help="LLM request ratio for hybrid mode",
        ),
        output: str = Option(
            "./benchmark_results",
            "--output",
            "-o",
            help="Output directory for results",
        ),
        quiet: bool = Option(
            False,
            "--quiet",
            "-q",
            help="Suppress progress output",
        ),
    ) -> None:
        """Sweep across multiple request rates for a single policy.

        Examples:
            sage-cp-bench sweep --mode llm --policy fifo --rates 10,50,100,200
            sage-cp-bench sweep --mode hybrid --policy hybrid_slo --rates 10,50,100
        """
        rate_list = [float(r.strip()) for r in rates.split(",")]
        output_path = Path(output)

        if mode == BenchmarkMode.LLM:
            _sweep_llm_rates(
                control_plane=control_plane,
                policy=policy,
                requests=requests,
                rate_list=rate_list,
                output_path=output_path,
                quiet=quiet,
            )
        else:
            _sweep_hybrid_rates(
                control_plane=control_plane,
                policy=policy,
                requests=requests,
                rate_list=rate_list,
                llm_ratio=llm_ratio,
                output_path=output_path,
                quiet=quiet,
            )

    def _sweep_llm_rates(
        control_plane: str,
        policy: str,
        requests: int,
        rate_list: list[float],
        output_path: Path,
        quiet: bool,
    ) -> None:
        """Sweep LLM rates."""
        from .llm_scheduler import LLMBenchmarkConfig, LLMBenchmarkRunner

        cfg = LLMBenchmarkConfig(
            control_plane_url=control_plane,
            policies=[policy],
            num_requests=requests,
        )

        if not quiet:
            typer.echo(f"\n📊 Rate sweep for LLM policy: {policy}")
            typer.echo(f"   Rates: {', '.join(str(r) for r in rate_list)} req/s")

        runner = LLMBenchmarkRunner(cfg, verbose=not quiet)
        results = asyncio.run(runner.run_rate_sweep(policy, rate_list))

        _print_rate_sweep_table(results)
        _save_rate_sweep_results(results, policy, output_path, "llm", quiet)

    def _sweep_hybrid_rates(
        control_plane: str,
        policy: str,
        requests: int,
        rate_list: list[float],
        llm_ratio: float,
        output_path: Path,
        quiet: bool,
    ) -> None:
        """Sweep hybrid rates."""
        from .hybrid_scheduler import HybridBenchmarkConfig, HybridBenchmarkRunner

        cfg = HybridBenchmarkConfig(
            control_plane_url=control_plane,
            policies=[policy],
            num_requests=requests,
            llm_ratio=llm_ratio,
            embedding_ratio=1.0 - llm_ratio,
        )

        if not quiet:
            typer.echo(f"\n📊 Rate sweep for Hybrid policy: {policy}")
            typer.echo(f"   Rates: {', '.join(str(r) for r in rate_list)} req/s")
            typer.echo(f"   LLM Ratio: {llm_ratio:.0%}")

        runner = HybridBenchmarkRunner(cfg, verbose=not quiet)
        results = asyncio.run(runner.run_rate_sweep(policy, rate_list))

        _print_rate_sweep_table_hybrid(results)
        _save_rate_sweep_results(results, policy, output_path, "hybrid", quiet)

    def _print_rate_sweep_table(results: dict) -> None:
        """Print rate sweep results table for LLM."""
        typer.echo("\n" + "=" * 70)
        typer.echo("                      Rate Sweep Results")
        typer.echo("=" * 70)

        headers = ["Rate", "Throughput", "P99 E2E", "SLO Rate", "Errors"]
        header_line = "| " + " | ".join(f"{h:^12}" for h in headers) + " |"
        typer.echo(header_line)
        typer.echo("|" + "|".join("-" * 14 for _ in headers) + "|")

        for rate_val, policy_result in results.items():
            m = policy_result.metrics
            row = [
                f"{rate_val} req/s",
                f"{m.throughput_rps:.1f} req/s",
                f"{m.e2e_latency_p99_ms:.0f} ms",
                f"{m.slo_compliance_rate:.1%}",
                f"{m.error_rate:.1%}",
            ]
            row_line = "| " + " | ".join(f"{v:^12}" for v in row) + " |"
            typer.echo(row_line)

    def _print_rate_sweep_table_hybrid(results: dict) -> None:
        """Print rate sweep results table for hybrid."""
        typer.echo("\n" + "=" * 90)
        typer.echo("                           Hybrid Rate Sweep Results")
        typer.echo("=" * 90)

        headers = ["Rate", "Throughput", "LLM RPS", "Embed RPS", "P99 E2E", "SLO Rate"]
        header_line = "| " + " | ".join(f"{h:^12}" for h in headers) + " |"
        typer.echo(header_line)
        typer.echo("|" + "|".join("-" * 14 for _ in headers) + "|")

        for rate_val, policy_result in results.items():
            m = policy_result.metrics
            row = [
                f"{rate_val} req/s",
                f"{m.throughput_rps:.1f} req/s",
                f"{m.llm_throughput_rps:.1f} req/s",
                f"{m.embedding_throughput_rps:.1f} req/s",
                f"{m.e2e_latency_p99_ms:.0f} ms",
                f"{m.slo_compliance_rate:.1%}",
            ]
            row_line = "| " + " | ".join(f"{v:^12}" for v in row) + " |"
            typer.echo(row_line)

    def _save_rate_sweep_results(
        results: dict, policy: str, output_path: Path, mode_str: str, quiet: bool
    ) -> None:
        """Save rate sweep results to file."""
        output_path.mkdir(parents=True, exist_ok=True)
        sweep_results = {str(rate): result.to_dict() for rate, result in results.items()}
        sweep_file = output_path / f"rate_sweep_{mode_str}_{policy}.json"
        with open(sweep_file, "w") as f:
            json.dump(sweep_results, f, indent=2)

        if not quiet:
            typer.echo(f"\n📁 Results saved to: {sweep_file}")

    # ========================================================================
    # experiment command - Run predefined experiments
    # ========================================================================
    @app.command("experiment")
    def run_experiment(
        name: str = Option(
            ...,
            "--name",
            "-e",
            help="Experiment name: throughput, latency, slo, mixed_ratio",
        ),
        control_plane: str = Option(
            "http://localhost:8080",
            "--control-plane",
            "-c",
            help="Control Plane URL",
        ),
        num_requests: int = Option(
            500,
            "--requests",
            "-n",
            help="Number of requests per test",
        ),
        request_rate: int = Option(
            100,
            "--rate",
            "-r",
            help="Request rate (for latency/mixed_ratio experiments)",
        ),
        llm_ratio: float = Option(
            0.5,
            "--llm-ratio",
            help="Ratio of LLM requests (0.0 to 1.0)",
        ),
        policies: str = Option(
            "fifo,priority,slo_aware",
            "--policies",
            "-p",
            help="Comma-separated list of policies to test",
        ),
        output: str = Option(
            "./experiment_results",
            "--output",
            "-o",
            help="Output directory",
        ),
        no_visualize: bool = Option(
            False,
            "--no-visualize",
            help="Skip generating visualizations",
        ),
        quiet: bool = Option(
            False,
            "--quiet",
            "-q",
            help="Suppress progress output",
        ),
    ) -> None:
        """Run a predefined benchmark experiment.

        Available experiments:
        - throughput: Sweep request rates to find max throughput
        - latency: Analyze latency distribution under fixed load
        - slo: Compare SLO compliance across policies and load levels
        - mixed_ratio: Test different LLM/Embedding ratios

        Examples:
            sage-cp-bench experiment --name throughput --policies fifo,priority
            sage-cp-bench experiment --name latency --rate 100 --requests 1000
            sage-cp-bench experiment --name slo --policies fifo,slo_aware
            sage-cp-bench experiment --name mixed_ratio --rate 100
        """
        # Import experiment classes
        from .common.base_config import SchedulingPolicy
        from .experiments import (
            LatencyExperiment,
            MixedRatioExperiment,
            SLOComplianceExperiment,
            ThroughputExperiment,
        )

        # Parse policies
        policy_list: list[SchedulingPolicy] = []
        for p in policies.split(","):
            p = p.strip().lower()
            try:
                policy_list.append(SchedulingPolicy(p))
            except ValueError:
                typer.echo(
                    f"❌ Unknown policy: {p}\n"
                    f"   Available: {', '.join([sp.value for sp in SchedulingPolicy])}",
                    err=True,
                )
                raise typer.Exit(1)

        output_path = Path(output)
        verbose = not quiet

        # Map experiment names to classes and create appropriate experiment
        if name == "throughput":
            experiment = ThroughputExperiment(
                name=f"throughput_{name}",
                control_plane_url=control_plane,
                num_requests=num_requests,
                llm_ratio=llm_ratio,
                policies=policy_list,
                output_dir=output_path,
                verbose=verbose,
            )
        elif name == "latency":
            experiment = LatencyExperiment(
                name=f"latency_{name}",
                control_plane_url=control_plane,
                request_rate=request_rate,
                num_requests=num_requests,
                llm_ratio=llm_ratio,
                policies=policy_list,
                output_dir=output_path,
                verbose=verbose,
            )
        elif name == "slo":
            experiment = SLOComplianceExperiment(
                name=f"slo_{name}",
                control_plane_url=control_plane,
                num_requests=num_requests,
                llm_ratio=llm_ratio,
                policies=policy_list,
                output_dir=output_path,
                verbose=verbose,
            )
        elif name == "mixed_ratio":
            experiment = MixedRatioExperiment(
                name=f"mixed_ratio_{name}",
                control_plane_url=control_plane,
                request_rate=request_rate,
                num_requests=num_requests,
                policies=policy_list,
                output_dir=output_path,
                verbose=verbose,
            )
        else:
            typer.echo(
                f"❌ Unknown experiment: {name}\n"
                "   Available: throughput, latency, slo, mixed_ratio",
                err=True,
            )
            raise typer.Exit(1)

        if not quiet:
            typer.echo(f"\n🧪 Running experiment: {name}")
            typer.echo(f"   Policies: {', '.join(p.value for p in policy_list)}")
            typer.echo(f"   Output: {output_path}")

        # Run experiment with full lifecycle
        if no_visualize:
            result = asyncio.run(experiment.run())
        else:
            result = asyncio.run(experiment.run_full())

        if result.success:
            typer.echo(f"\n✅ Experiment completed successfully")
            typer.echo(f"   Duration: {result.duration_seconds:.1f}s")
            typer.echo(f"   Results saved to: {output_path}")

            # Show summary
            if result.summary:
                typer.echo("\n📊 Summary:")
                if "best_policy" in result.summary:
                    typer.echo(f"   Best policy: {result.summary['best_policy']}")
                if "max_throughput" in result.summary:
                    typer.echo(
                        f"   Max throughput: {result.summary['max_throughput']:.1f} req/s"
                    )
                if "overall_compliance" in result.summary:
                    typer.echo(
                        f"   Overall SLO compliance: {result.summary['overall_compliance']:.1%}"
                    )

            # Show generated charts
            if result.charts and not quiet:
                typer.echo("\n📈 Generated charts:")
                for chart_path in result.charts:
                    typer.echo(f"   - {chart_path.name}")
        else:
            typer.echo(f"\n❌ Experiment failed: {result.error}", err=True)
            raise typer.Exit(1)

    # ========================================================================
    # visualize command - Generate visualizations from results
    # ========================================================================
    @app.command("visualize")
    def generate_visualizations(
        input_file: str = Option(
            ...,
            "--input",
            "-i",
            help="Path to benchmark results JSON file",
        ),
        output: str = Option(
            "./visualizations",
            "--output",
            "-o",
            help="Output directory for charts and reports",
        ),
        format_type: str = Option(
            "all",
            "--format",
            "-f",
            help="Output format: charts, html, markdown, all",
        ),
        quiet: bool = Option(
            False,
            "--quiet",
            "-q",
            help="Suppress progress output",
        ),
    ) -> None:
        """Generate visualizations from benchmark results.

        Examples:
            sage-cp-bench visualize --input results.json --output ./charts
            sage-cp-bench visualize --input results.json --format html
        """
        input_path = Path(input_file)
        output_path = Path(output)

        if not input_path.exists():
            typer.echo(f"❌ Input file not found: {input_path}", err=True)
            raise typer.Exit(1)

        # Load results
        with open(input_path) as f:
            results = json.load(f)

        if not quiet:
            typer.echo(f"\n📊 Generating visualizations from: {input_path}")

        output_path.mkdir(parents=True, exist_ok=True)

        generated_files: list[str] = []

        # Generate charts
        if format_type in ("charts", "all"):
            try:
                from .visualization import BenchmarkCharts

                if not quiet:
                    typer.echo("   📈 Generating charts...")

                # Extract policy metrics if available
                policy_results = results.get("policy_results", {})
                policy_metrics = {}
                for policy_name, policy_data in policy_results.items():
                    policy_metrics[policy_name] = policy_data.get("metrics", {})

                charts = BenchmarkCharts(output_dir=output_path)
                chart_paths = charts.generate_all_charts(policy_metrics=policy_metrics)

                for path in chart_paths:
                    generated_files.append(str(path))
                    if not quiet:
                        typer.echo(f"      - {path.name}")

            except ImportError as e:
                typer.echo(f"   ⚠️  Charts skipped (missing dependencies): {e}")

        # Generate HTML report
        if format_type in ("html", "all"):
            try:
                from .visualization import ReportGenerator

                if not quiet:
                    typer.echo("   📄 Generating HTML report...")

                report_gen = ReportGenerator(result=results, charts_dir=output_path)
                html_path = report_gen.generate_html_report(
                    output_path / "benchmark_report.html"
                )
                generated_files.append(str(html_path))

                if not quiet:
                    typer.echo(f"      - {html_path.name}")

            except ImportError as e:
                typer.echo(f"   ⚠️  HTML report skipped (missing dependencies): {e}")
            except RuntimeError as e:
                typer.echo(f"   ⚠️  HTML report skipped: {e}")

        # Generate Markdown report
        if format_type in ("markdown", "md", "all"):
            try:
                from .visualization import ReportGenerator

                if not quiet:
                    typer.echo("   📝 Generating Markdown report...")

                report_gen = ReportGenerator(result=results, charts_dir=output_path)
                md_path = report_gen.generate_markdown_report(
                    output_path / "benchmark_report.md"
                )
                generated_files.append(str(md_path))

                if not quiet:
                    typer.echo(f"      - {md_path.name}")

            except ImportError as e:
                typer.echo(f"   ⚠️  Markdown report skipped (missing dependencies): {e}")

        if not quiet:
            typer.echo(f"\n✅ Generated {len(generated_files)} files in: {output_path}")

    # ========================================================================
    # config command - Show/save example configuration
    # ========================================================================
    @app.command("config")
    def show_config(
        mode: BenchmarkMode = Option(
            BenchmarkMode.LLM,
            "--mode",
            "-m",
            help="Configuration mode: llm or hybrid",
        ),
        output: str = Option(
            None,
            "--output",
            "-o",
            help="Save example config to file (JSON or YAML)",
        ),
    ) -> None:
        """Show or save example configuration.

        Examples:
            sage-cp-bench config --mode llm
            sage-cp-bench config --mode hybrid --output config.yaml
        """
        if mode == BenchmarkMode.LLM:
            from .llm_scheduler import LLMBenchmarkConfig

            cfg = LLMBenchmarkConfig()
        else:
            from .hybrid_scheduler import HybridBenchmarkConfig

            cfg = HybridBenchmarkConfig()

        config_dict = cfg.to_dict()

        if output:
            output_path = Path(output)
            suffix = output_path.suffix.lower()

            if suffix in (".yaml", ".yml"):
                if not YAML_AVAILABLE:
                    typer.echo(
                        "❌ PyYAML required for YAML output. Install with: pip install pyyaml",
                        err=True,
                    )
                    raise typer.Exit(1)
                with open(output_path, "w") as f:
                    yaml.dump(config_dict, f, default_flow_style=False)
            else:
                with open(output_path, "w") as f:
                    json.dump(config_dict, f, indent=2)

            typer.echo(f"✅ Example config saved to: {output_path}")
        else:
            typer.echo(f"Example {mode.value.upper()} configuration:")
            typer.echo(json.dumps(config_dict, indent=2))

    # ========================================================================
    # validate command - Validate configuration file
    # ========================================================================
    @app.command("validate")
    def validate_config(
        config_file: str = Argument(
            ...,
            help="Path to configuration file (JSON or YAML)",
        ),
        mode: BenchmarkMode = Option(
            BenchmarkMode.LLM,
            "--mode",
            "-m",
            help="Configuration mode to validate as",
        ),
    ) -> None:
        """Validate a configuration file.

        Examples:
            sage-cp-bench validate config.json --mode llm
            sage-cp-bench validate config.yaml --mode hybrid
        """
        config_path = Path(config_file)

        try:
            config_data = load_config_file(config_path)
        except ValueError as e:
            typer.echo(f"❌ {e}", err=True)
            raise typer.Exit(1)

        if mode == BenchmarkMode.LLM:
            from .llm_scheduler import LLMBenchmarkConfig

            cfg = LLMBenchmarkConfig.from_dict(config_data)
        else:
            from .hybrid_scheduler import HybridBenchmarkConfig

            cfg = HybridBenchmarkConfig.from_dict(config_data)

        errors = cfg.validate()

        if errors:
            typer.echo("❌ Configuration errors:")
            for error in errors:
                typer.echo(f"   - {error}")
            raise typer.Exit(1)
        else:
            typer.echo(f"✅ Configuration is valid for {mode.value.upper()} mode.")

    return app


# Create the app instance
try:
    app = create_app() if TYPER_AVAILABLE else None
except Exception:
    app = None


def main() -> None:
    """Main entry point for CLI."""
    if not TYPER_AVAILABLE or app is None:
        print("Error: typer is required for CLI. Install it with: pip install typer")
        return

    app()


if __name__ == "__main__":
    main()
