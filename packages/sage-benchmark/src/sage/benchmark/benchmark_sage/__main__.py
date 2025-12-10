"""CLI entry point for running SAGE system-level benchmark experiments.

This module supersedes the legacy ``benchmark_icml`` entry point. It exposes
experiments that were originally designed for section 5.x of a paper draft,
under a more general "benchmark_sage" namespace.

Usage examples:

    python -m sage.benchmark.benchmark_sage --experiment 5.1
    python -m sage.benchmark.benchmark_sage --all
    python -m sage.benchmark.benchmark_sage --experiment 5.2 --config config/exp_5_2.yaml

"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SAGE system benchmark suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run Section 5.1 experiment
    python -m sage.benchmark.benchmark_sage --experiment 5.1

    # Run all experiments
    python -m sage.benchmark.benchmark_sage --all

    # Run with custom config
    python -m sage.benchmark.benchmark_sage --experiment 5.2 --config my_config.yaml

    # Dry run (validate only)
    python -m sage.benchmark.benchmark_sage --experiment 5.1 --dry-run
        """,
    )

    parser.add_argument(
        "--experiment",
        "-e",
        type=str,
        choices=["5.1", "5.2", "5.3"],
        help="Experiment section to run (5.1, 5.2, or 5.3)",
    )
    parser.add_argument("--all", "-a", action="store_true", help="Run all experiments")
    parser.add_argument("--config", "-c", type=str, help="Path to custom config file (YAML)")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="results",
        help="Output directory for results (default: results)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate config without running")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--quick",
        "-q",
        action="store_true",
        help="Run quick version with reduced samples",
    )

    args = parser.parse_args()

    if not args.experiment and not args.all:
        parser.print_help()
        return 1

    # Import here to avoid slow startup for --help
    from sage.benchmark.benchmark_sage.config.config_loader import ConfigLoader
    from sage.benchmark.benchmark_sage.experiments.exp_5_1_control_plane import (
        ControlPlaneExperiment,
    )
    from sage.benchmark.benchmark_sage.experiments.exp_5_2_scheduling import (
        SchedulingPolicyExperiment,
    )
    from sage.benchmark.benchmark_sage.experiments.exp_5_3_e2e import EndToEndExperiment

    experiment_map = {
        "5.1": ControlPlaneExperiment,
        "5.2": SchedulingPolicyExperiment,
        "5.3": EndToEndExperiment,
    }

    if args.all:
        experiments_to_run = ["5.1", "5.2", "5.3"]
    else:
        experiments_to_run = [args.experiment]

    config_loader = ConfigLoader()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, dict] = {}

    for exp_section in experiments_to_run:
        print(f"\n{'=' * 60}")
        print(f"Running Experiment Section {exp_section}")
        print(f"{'=' * 60}\n")

        if args.config:
            config = config_loader.load(args.config)
        else:
            default_config = (
                Path(__file__).parent / "config" / f"exp_{exp_section.replace('.', '_')}.yaml"
            )
            if default_config.exists():
                config = config_loader.load(str(default_config))
            else:
                config = config_loader.get_default_config(exp_section)

        if args.quick:
            config = config_loader.apply_quick_mode(config)

        exp_class = experiment_map[exp_section]
        experiment = exp_class(
            config=config,
            output_dir=output_dir / f"exp_{exp_section.replace('.', '_')}",
            verbose=args.verbose,
        )

        if args.dry_run:
            print(f"[DRY RUN] Validating config for experiment {exp_section}...")
            experiment.validate()
            print("[DRY RUN] Config validation passed.")
            continue

        try:
            experiment.setup()
            result = experiment.run()
            experiment.teardown()
            results[exp_section] = result
            print(f"\nExperiment {exp_section} completed. Results saved to {experiment.output_dir}")
        except Exception as exc:  # noqa: BLE001
            print(f"Error running experiment {exp_section}: {exc}")
            if args.verbose:
                import traceback

                traceback.print_exc()
            results[exp_section] = {"error": str(exc)}

    if not args.dry_run:
        print(f"\n{'=' * 60}")
        print("Experiment Summary")
        print(f"{'=' * 60}")
        for exp_section, result in results.items():
            if "error" in result:
                print(f"  {exp_section}: FAILED - {result['error']}")
            else:
                print(f"  {exp_section}: COMPLETED")
        print(f"\nResults saved to: {output_dir.absolute()}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
