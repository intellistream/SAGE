"""
Command Line Interface for Control Plane Benchmark
===================================================

Provides CLI commands for running and comparing scheduling policy benchmarks.

Usage:
    sage-bench run --control-plane http://localhost:8080 --policy aegaeon
    sage-bench compare --policies fifo,priority,slo_aware,aegaeon
    sage-bench sweep --policy aegaeon --rates 50,100,200
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Try to import typer, provide helpful error if not available
try:
    import typer
    from typer import Argument, Option

    TYPER_AVAILABLE = True
except ImportError:
    TYPER_AVAILABLE = False
    typer = None  # type: ignore[assignment]

from .config import BenchmarkConfig
from .reporter import BenchmarkReporter
from .runner import BenchmarkRunner


def create_app() -> typer.Typer:
    """Create the CLI application.

    Returns:
        Typer application
    """
    if not TYPER_AVAILABLE:
        raise RuntimeError(
            "typer is required for CLI. Install it with: pip install typer"
        )

    app = typer.Typer(
        name="sage-bench",
        help="🚀 sageLLM Control Plane Scheduling Policy Benchmark",
        add_completion=False,
    )

    @app.command("run")
    def run_benchmark(
        control_plane: str = Option(
            "http://localhost:8080",
            "--control-plane", "-c",
            help="Control Plane URL",
        ),
        policy: str = Option(
            "fifo",
            "--policy", "-p",
            help="Scheduling policy to benchmark",
        ),
        requests: int = Option(
            100,
            "--requests", "-n",
            help="Number of requests to send",
        ),
        rate: float = Option(
            10.0,
            "--rate", "-r",
            help="Request rate (requests/second)",
        ),
        output: str = Option(
            "./benchmark_results",
            "--output", "-o",
            help="Output directory for results",
        ),
        warmup: int = Option(
            10,
            "--warmup", "-w",
            help="Number of warmup requests",
        ),
        timeout: float = Option(
            60.0,
            "--timeout", "-t",
            help="Request timeout in seconds",
        ),
        no_streaming: bool = Option(
            False,
            "--no-streaming",
            help="Disable streaming responses",
        ),
        quiet: bool = Option(
            False,
            "--quiet", "-q",
            help="Suppress progress output",
        ),
    ) -> None:
        """Run benchmark for a single scheduling policy."""
        config = BenchmarkConfig(
            control_plane_url=control_plane,
            policies=[policy],
            num_requests=requests,
            request_rate=rate,
            output_dir=Path(output),
            warmup_requests=warmup,
            timeout_seconds=timeout,
            enable_streaming=not no_streaming,
        )

        # Validate config
        errors = config.validate()
        if errors:
            typer.echo(f"❌ Configuration errors: {errors}", err=True)
            raise typer.Exit(1)

        if not quiet:
            typer.echo(f"\n🚀 Running benchmark for policy: {policy}")
            typer.echo(f"   Control Plane: {control_plane}")
            typer.echo(f"   Requests: {requests} @ {rate} req/s")

        runner = BenchmarkRunner(config, verbose=not quiet)
        result = asyncio.run(runner.run())

        # Generate report
        reporter = BenchmarkReporter(result)
        reporter.print_summary()

        # Save results
        paths = reporter.save_all(Path(output))
        if not quiet:
            typer.echo(f"\n📁 Results saved to:")
            for fmt, path in paths.items():
                typer.echo(f"   {fmt}: {path}")

    @app.command("compare")
    def compare_policies(
        control_plane: str = Option(
            "http://localhost:8080",
            "--control-plane", "-c",
            help="Control Plane URL",
        ),
        policies: str = Option(
            "fifo,priority,slo_aware",
            "--policies", "-p",
            help="Comma-separated list of policies to compare",
        ),
        requests: int = Option(
            100,
            "--requests", "-n",
            help="Number of requests per policy",
        ),
        rate: float = Option(
            10.0,
            "--rate", "-r",
            help="Request rate (requests/second)",
        ),
        output: str = Option(
            "./benchmark_results",
            "--output", "-o",
            help="Output directory for results",
        ),
        warmup: int = Option(
            10,
            "--warmup", "-w",
            help="Number of warmup requests",
        ),
        timeout: float = Option(
            60.0,
            "--timeout", "-t",
            help="Request timeout in seconds",
        ),
        quiet: bool = Option(
            False,
            "--quiet", "-q",
            help="Suppress progress output",
        ),
    ) -> None:
        """Compare multiple scheduling policies."""
        policy_list = [p.strip() for p in policies.split(",")]

        config = BenchmarkConfig(
            control_plane_url=control_plane,
            policies=policy_list,
            num_requests=requests,
            request_rate=rate,
            output_dir=Path(output),
            warmup_requests=warmup,
            timeout_seconds=timeout,
        )

        # Validate config
        errors = config.validate()
        if errors:
            typer.echo(f"❌ Configuration errors: {errors}", err=True)
            raise typer.Exit(1)

        if not quiet:
            typer.echo(f"\n🔄 Comparing policies: {', '.join(policy_list)}")
            typer.echo(f"   Control Plane: {control_plane}")
            typer.echo(f"   Requests per policy: {requests} @ {rate} req/s")

        runner = BenchmarkRunner(config, verbose=not quiet)
        result = asyncio.run(runner.run())

        # Generate report
        reporter = BenchmarkReporter(result)
        reporter.print_summary()

        # Save results
        paths = reporter.save_all(Path(output))
        if not quiet:
            typer.echo(f"\n📁 Results saved to:")
            for fmt, path in paths.items():
                typer.echo(f"   {fmt}: {path}")

    @app.command("sweep")
    def rate_sweep(
        control_plane: str = Option(
            "http://localhost:8080",
            "--control-plane", "-c",
            help="Control Plane URL",
        ),
        policy: str = Option(
            "fifo",
            "--policy", "-p",
            help="Policy to benchmark",
        ),
        requests: int = Option(
            100,
            "--requests", "-n",
            help="Number of requests per rate",
        ),
        rates: str = Option(
            "10,50,100,200",
            "--rates", "-r",
            help="Comma-separated list of request rates to test",
        ),
        output: str = Option(
            "./benchmark_results",
            "--output", "-o",
            help="Output directory for results",
        ),
        quiet: bool = Option(
            False,
            "--quiet", "-q",
            help="Suppress progress output",
        ),
    ) -> None:
        """Sweep across multiple request rates for a single policy."""
        rate_list = [float(r.strip()) for r in rates.split(",")]

        config = BenchmarkConfig(
            control_plane_url=control_plane,
            policies=[policy],
            num_requests=requests,
            output_dir=Path(output),
        )

        if not quiet:
            typer.echo(f"\n📊 Rate sweep for policy: {policy}")
            typer.echo(f"   Rates: {', '.join(str(r) for r in rate_list)} req/s")

        runner = BenchmarkRunner(config, verbose=not quiet)
        results = asyncio.run(runner.run_rate_sweep(policy, rate_list))

        # Print summary table
        typer.echo("\n" + "=" * 60)
        typer.echo("                  Rate Sweep Results")
        typer.echo("=" * 60)

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

        # Save results
        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)

        sweep_results = {
            str(rate): result.to_dict()
            for rate, result in results.items()
        }
        sweep_file = output_path / f"rate_sweep_{policy}.json"
        with open(sweep_file, "w") as f:
            json.dump(sweep_results, f, indent=2)

        if not quiet:
            typer.echo(f"\n📁 Results saved to: {sweep_file}")

    @app.command("config")
    def show_config(
        output: str = Option(
            None,
            "--output", "-o",
            help="Save example config to file",
        ),
    ) -> None:
        """Show example configuration."""
        config = BenchmarkConfig()
        config_dict = config.to_dict()

        if output:
            output_path = Path(output)
            with open(output_path, "w") as f:
                json.dump(config_dict, f, indent=2)
            typer.echo(f"✅ Example config saved to: {output_path}")
        else:
            typer.echo("Example configuration:")
            typer.echo(json.dumps(config_dict, indent=2))

    @app.command("validate")
    def validate_config(
        config_file: str = Argument(
            ...,
            help="Path to configuration file",
        ),
    ) -> None:
        """Validate a configuration file."""
        config_path = Path(config_file)

        if not config_path.exists():
            typer.echo(f"❌ Config file not found: {config_path}", err=True)
            raise typer.Exit(1)

        with open(config_path) as f:
            config_data = json.load(f)

        config = BenchmarkConfig.from_dict(config_data)
        errors = config.validate()

        if errors:
            typer.echo("❌ Configuration errors:")
            for error in errors:
                typer.echo(f"   - {error}")
            raise typer.Exit(1)
        else:
            typer.echo("✅ Configuration is valid!")

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
