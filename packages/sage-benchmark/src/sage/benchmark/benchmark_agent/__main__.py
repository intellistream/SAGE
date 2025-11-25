"""
CLI entry point for running agent benchmark experiments.

Usage:
    python -m sage.benchmark.benchmark_agent --config config/tool_selection_exp.yaml
    python -m sage.benchmark.benchmark_agent --config config/planning_exp.yaml
    python -m sage.benchmark.benchmark_agent --config config/timing_detection_exp.yaml
"""

import argparse
import sys
from pathlib import Path

from sage.benchmark.benchmark_agent.config.config_loader import ConfigLoader
from sage.benchmark.benchmark_agent.experiments import (
    PlanningExperiment,
    TimingDetectionExperiment,
    ToolSelectionExperiment,
)


def create_experiment(config):
    """
    Create appropriate experiment instance based on config type.

    Args:
        config: Experiment configuration

    Returns:
        Experiment instance

    Raises:
        ValueError: If experiment type not recognized
    """
    experiment_type = config.experiment

    if experiment_type == "tool_selection":
        return ToolSelectionExperiment(config)
    elif experiment_type == "planning":
        return PlanningExperiment(config)
    elif experiment_type == "timing_detection":
        return TimingDetectionExperiment(config)
    else:
        raise ValueError(f"Unknown experiment type: {experiment_type}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run agent benchmark experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run tool selection experiment
  python -m sage.benchmark.benchmark_agent --config config/tool_selection_exp.yaml

  # Run planning experiment with custom output
  python -m sage.benchmark.benchmark_agent \\
      --config config/planning_exp.yaml \\
      --output results/planning_results.json

  # Run timing detection with verbose output
  python -m sage.benchmark.benchmark_agent \\
      --config config/timing_detection_exp.yaml \\
      --verbose
        """,
    )

    parser.add_argument(
        "--config", type=str, required=True, help="Path to experiment configuration YAML file"
    )

    parser.add_argument("--output", type=str, help="Override output path for results (optional)")

    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    parser.add_argument(
        "--dry-run", action="store_true", help="Validate config without running experiment"
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Error: Config file not found: {config_path}")
            sys.exit(1)

        loader = ConfigLoader()
        config = loader.load_config(str(config_path))

        # Override from CLI args
        if args.output:
            config.report.path = args.output
        if args.verbose:
            config.verbose = getattr(config, "verbose", True)

        print(f"Loaded config: {config.experiment}")

        if args.dry_run:
            print("Config validation successful (dry-run mode)")
            print(f"  Experiment type: {config.experiment}")
            print(f"  Profile: {config.profile}")
            print(f"  Split: {config.split}")
            print(f"  Output: {config.report.path}")
            return 0

    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

    # Create experiment
    try:
        experiment = create_experiment(config)
        print(f"Created experiment: {experiment.__class__.__name__}")
    except Exception as e:
        print(f"Error creating experiment: {e}")
        sys.exit(1)

    # Run experiment
    try:
        print("\n" + "=" * 60)
        print("Starting experiment...")
        print("=" * 60 + "\n")

        experiment.prepare()
        result = experiment.run()
        experiment.finalize()

        print("\n" + "=" * 60)
        print("Experiment completed successfully!")
        print("=" * 60)
        print(f"Results saved to: {config.report.path}")
        print(f"Total samples: {result.metadata.get('total_samples', 0)}")
        print(f"Failed samples: {result.metadata.get('failed_samples', 0)}")

        return 0

    except KeyboardInterrupt:
        print("\n\nExperiment interrupted by user")
        return 130

    except Exception as e:
        print(f"\nError running experiment: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
