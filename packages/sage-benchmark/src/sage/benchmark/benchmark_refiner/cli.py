#!/usr/bin/env python3
"""
Refiner Benchmark CLI
=====================

Command-line interface for running Refiner algorithm benchmarks.

Usage:
    # Quick comparison of algorithms
    sage-refiner-bench compare --algorithms baseline,longrefiner,reform --samples 100

    # Run from config file
    sage-refiner-bench run --config experiment.yaml

    # Budget sweep
    sage-refiner-bench sweep --algorithm longrefiner --budgets 512,1024,2048,4096

    # Head analysis for REFORM
    sage-refiner-bench heads --model llama-3.1-8b --dataset nq --samples 100
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="sage-refiner-bench",
        description="🚀 SAGE Refiner Algorithm Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick algorithm comparison
  %(prog)s compare --algorithms baseline,longrefiner,reform,provence --samples 50

  # Run from YAML config
  %(prog)s run --config my_experiment.yaml

  # Sweep different budgets
  %(prog)s sweep --algorithm longrefiner --budgets 512,1024,2048,4096

  # Generate example config
  %(prog)s config --output experiment.yaml

  # Run head analysis (for REFORM)
  %(prog)s heads --model /path/to/model --dataset nq --samples 100
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ========================================================================
    # compare command
    # ========================================================================
    compare_parser = subparsers.add_parser(
        "compare",
        help="Compare multiple Refiner algorithms",
    )
    compare_parser.add_argument(
        "--algorithms", "-a",
        type=str,
        default="baseline,longrefiner,reform,provence",
        help="Comma-separated list of algorithms to compare",
    )
    compare_parser.add_argument(
        "--samples", "-n",
        type=int,
        default=50,
        help="Number of samples to evaluate",
    )
    compare_parser.add_argument(
        "--budget", "-b",
        type=int,
        default=2048,
        help="Token budget for compression",
    )
    compare_parser.add_argument(
        "--dataset", "-d",
        type=str,
        default="nq",
        help="Dataset to use (nq, hotpotqa, triviaqa, squad)",
    )
    compare_parser.add_argument(
        "--output", "-o",
        type=str,
        default="./.benchmarks/refiner",
        help="Output directory",
    )
    compare_parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress output",
    )

    # ========================================================================
    # run command
    # ========================================================================
    run_parser = subparsers.add_parser(
        "run",
        help="Run experiment from config file",
    )
    run_parser.add_argument(
        "--config", "-c",
        type=str,
        required=True,
        help="Path to YAML config file",
    )
    run_parser.add_argument(
        "--type", "-t",
        type=str,
        default="comparison",
        choices=["comparison", "quality", "latency", "compression"],
        help="Experiment type",
    )
    run_parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress output",
    )

    # ========================================================================
    # sweep command
    # ========================================================================
    sweep_parser = subparsers.add_parser(
        "sweep",
        help="Sweep across different budgets for an algorithm",
    )
    sweep_parser.add_argument(
        "--algorithm", "-a",
        type=str,
        required=True,
        help="Algorithm to sweep",
    )
    sweep_parser.add_argument(
        "--budgets", "-b",
        type=str,
        default="512,1024,2048,4096",
        help="Comma-separated list of budgets to test",
    )
    sweep_parser.add_argument(
        "--samples", "-n",
        type=int,
        default=50,
        help="Number of samples per budget",
    )
    sweep_parser.add_argument(
        "--output", "-o",
        type=str,
        default="./.benchmarks/refiner",
        help="Output directory",
    )
    sweep_parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress output",
    )

    # ========================================================================
    # config command
    # ========================================================================
    config_parser = subparsers.add_parser(
        "config",
        help="Generate example configuration file",
    )
    config_parser.add_argument(
        "--output", "-o",
        type=str,
        default="refiner_experiment.yaml",
        help="Output file path",
    )

    # ========================================================================
    # heads command
    # ========================================================================
    heads_parser = subparsers.add_parser(
        "heads",
        help="Run attention head analysis (for REFORM)",
    )
    heads_parser.add_argument(
        "--config", "-c",
        type=str,
        help="Path to head analysis config file",
    )
    heads_parser.add_argument(
        "--model", "-m",
        type=str,
        help="Model name or path",
    )
    heads_parser.add_argument(
        "--dataset", "-d",
        type=str,
        default="nq",
        help="Dataset to use",
    )
    heads_parser.add_argument(
        "--samples", "-n",
        type=int,
        default=100,
        help="Number of samples",
    )
    heads_parser.add_argument(
        "--output", "-o",
        type=str,
        default="./.benchmarks/head_analysis",
        help="Output directory",
    )
    heads_parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        help="Device to use (cuda, cpu)",
    )
    heads_parser.add_argument(
        "--top-k",
        type=int,
        default=20,
        help="Number of top heads to report",
    )

    return parser


def cmd_compare(args: argparse.Namespace) -> int:
    """Run algorithm comparison."""
    from sage.benchmark.benchmark_refiner.experiments.runner import (
        RefinerExperimentRunner,
    )

    algorithms = [a.strip() for a in args.algorithms.split(",")]

    print(f"\n🚀 Comparing Refiner algorithms: {', '.join(algorithms)}")
    print(f"   Samples: {args.samples}")
    print(f"   Budget: {args.budget}")
    print(f"   Dataset: {args.dataset}")
    print(f"   Output: {args.output}")

    runner = RefinerExperimentRunner(verbose=not args.quiet)
    result = runner.quick_compare(
        algorithms=algorithms,
        max_samples=args.samples,
        budget=args.budget,
        dataset=args.dataset,
        output_dir=args.output,
    )

    if result.success:
        runner.print_comparison_table(result)
        print(f"\n✅ Results saved to: {args.output}")
        return 0
    else:
        print(f"\n❌ Experiment failed: {result.error}")
        return 1


def cmd_run(args: argparse.Namespace) -> int:
    """Run experiment from config."""
    from sage.benchmark.benchmark_refiner.experiments.runner import (
        RefinerExperimentRunner,
    )

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return 1

    print(f"\n📄 Loading config from: {config_path}")

    runner = RefinerExperimentRunner(verbose=not args.quiet)
    result = runner.run_from_config(str(config_path), args.type)

    if result.success:
        runner.print_comparison_table(result)
        return 0
    else:
        print(f"\n❌ Experiment failed: {result.error}")
        return 1


def cmd_sweep(args: argparse.Namespace) -> int:
    """Run budget sweep."""
    from sage.benchmark.benchmark_refiner.experiments.runner import (
        RefinerExperimentRunner,
    )

    budgets = [int(b.strip()) for b in args.budgets.split(",")]

    print(f"\n📊 Sweeping budgets for algorithm: {args.algorithm}")
    print(f"   Budgets: {budgets}")
    print(f"   Samples: {args.samples}")

    runner = RefinerExperimentRunner(verbose=not args.quiet)
    results = runner.compare_budgets(
        algorithm=args.algorithm,
        budgets=budgets,
        max_samples=args.samples,
        output_dir=args.output,
    )

    # Print summary table
    print("\n" + "=" * 60)
    print("                   Budget Sweep Results")
    print("=" * 60)
    print(f"| {'Budget':^10} | {'F1 Score':^12} | {'Compression':^12} |")
    print("|" + "-" * 12 + "|" + "-" * 14 + "|" + "-" * 14 + "|")

    for budget, result in results.items():
        if result.algorithm_metrics:
            metrics = list(result.algorithm_metrics.values())[0]
            print(f"| {budget:^10} | {metrics.avg_f1:^12.4f} | {metrics.avg_compression_rate:^12.2f}x |")

    print("=" * 60)
    print(f"\n✅ Results saved to: {args.output}")

    return 0


def cmd_config(args: argparse.Namespace) -> int:
    """Generate example config."""
    from sage.benchmark.benchmark_refiner.experiments.base_experiment import (
        RefinerExperimentConfig,
    )

    config = RefinerExperimentConfig(
        name="example_experiment",
        description="Example Refiner benchmark experiment",
        algorithms=["baseline", "longrefiner", "reform", "provence"],
        max_samples=100,
        budget=2048,
    )

    output_path = Path(args.output)
    config.save_yaml(str(output_path))

    print(f"✅ Example config saved to: {output_path}")
    return 0


def cmd_heads(args: argparse.Namespace) -> int:
    """Run head analysis."""
    import subprocess

    # 使用已有的 find_heads.py 脚本
    cmd = [
        sys.executable,
        "-m", "sage.benchmark.benchmark_refiner.analysis.find_heads",
    ]

    if args.config:
        cmd.extend(["--config", args.config])
    else:
        # 需要配置文件，生成临时配置
        import tempfile

        import yaml

        if not args.model:
            print("❌ Either --config or --model must be specified")
            return 1

        config = {
            "model": args.model,
            "dataset": args.dataset,
            "num_samples": args.samples,
            "device": args.device,
            "dtype": "bfloat16",
            "top_k": args.top_k,
            "output_dir": args.output,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            temp_config = f.name

        cmd.extend(["--config", temp_config])

    print("\n🔍 Running head analysis...")
    result = subprocess.run(cmd)
    return result.returncode


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    commands: dict[str, Any] = {
        "compare": cmd_compare,
        "run": cmd_run,
        "sweep": cmd_sweep,
        "config": cmd_config,
        "heads": cmd_heads,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
