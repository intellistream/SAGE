#!/usr/bin/env python3
"""
Agent Training Method Comparison - One-Click Experiment Runner

Compare different training methods (Coreset Selection, Continual Learning)
and generate comparison charts automatically.

Usage:
    # Quick demo with simulated results (no GPU needed)
    python run_method_comparison.py --demo

    # Quick test with actual training (8GB GPU)
    python run_method_comparison.py --quick

    # Full comparison with all methods (24GB+ GPU)
    python run_method_comparison.py --full

    # Generate chart from existing results
    python run_method_comparison.py --chart-only --results ./comparison_results

Methods Compared:
    A: Baseline         - Standard SFT training
    B1: Coreset Loss    - Select high-loss samples
    B2: Coreset Diverse - Select diverse samples
    B3: Coreset Hybrid  - 60% loss + 40% diversity
    B4: Coreset Random  - Random selection (control)
    C: Continual        - Online continual learning with replay
    D: Combined         - Coreset + Continual Learning
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Compare Agent Training Methods",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--demo", action="store_true", help="Demo mode with simulated results (no GPU)"
    )
    parser.add_argument("--quick", action="store_true", help="Quick test with 3 methods (8GB GPU)")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Full comparison with all 7 methods (24GB+ GPU)",
    )
    parser.add_argument(
        "--chart-only",
        action="store_true",
        help="Only generate chart from existing results",
    )
    parser.add_argument(
        "--results", type=Path, default="./comparison_results", help="Results directory"
    )
    parser.add_argument(
        "--base-model",
        default="Qwen/Qwen2.5-1.5B-Instruct",
        help="Base model for training",
    )
    parser.add_argument("--show-plot", action="store_true", help="Display plot interactively")
    parser.add_argument(
        "--skip-training",
        action="store_true",
        help="Skip training, run evaluation only",
    )
    args = parser.parse_args()

    # Add SAGE to path if needed
    sage_root = Path(__file__).parent.parent.parent.parent
    if str(sage_root) not in sys.path:
        sys.path.insert(0, str(sage_root))

    from sage.benchmark.benchmark_agent.experiments.method_comparison import (
        MethodComparisonExperiment,
        MethodRegistry,
    )

    print("=" * 70)
    print("🔬 AGENT TRAINING METHOD COMPARISON")
    print("    目标: 难题4 - 高精度工具规划与调用 (95%+ accuracy)")
    print("=" * 70)

    if args.chart_only:
        # Load existing results and generate chart
        print(f"\nLoading results from: {args.results}")
        exp = MethodComparisonExperiment(output_dir=args.results)
        exp.load_results()
        chart_path = exp.generate_comparison_chart(show_plot=args.show_plot)
        print(f"\n✅ Chart generated: {chart_path}")
        return

    if args.demo:
        # Demo mode with simulated results
        print("\n📊 Running DEMO with simulated results...")
        print("   (No actual training - for testing the visualization)")
        methods = MethodRegistry.get_all_methods()
        exp = MethodComparisonExperiment(
            output_dir=args.results,
            methods=methods,
            dry_run=True,
        )
        exp.run_all_methods()
        chart_path = exp.generate_comparison_chart(show_plot=args.show_plot)
        print(f"\n✅ Demo complete! Chart: {chart_path}")

    elif args.quick:
        # Quick test
        print("\n⚡ Running QUICK comparison (3 methods)...")
        print(f"   Base model: {args.base_model}")
        methods = MethodRegistry.get_quick_methods()
        exp = MethodComparisonExperiment(
            output_dir=args.results,
            base_model=args.base_model,
            methods=methods,
            dry_run=False,
        )
        exp.run_all_methods(skip_training=args.skip_training)
        chart_path = exp.generate_comparison_chart(show_plot=args.show_plot)
        print(f"\n✅ Quick comparison complete! Chart: {chart_path}")

    elif args.full:
        # Full comparison
        print("\n🚀 Running FULL comparison (7 methods)...")
        print(f"   Base model: {args.base_model}")
        print("   ⚠️  This will take several hours and requires 24GB+ GPU")
        methods = MethodRegistry.get_all_methods()
        exp = MethodComparisonExperiment(
            output_dir=args.results,
            base_model=args.base_model,
            methods=methods,
            dry_run=False,
        )
        exp.run_all_methods(skip_training=args.skip_training)
        chart_path = exp.generate_comparison_chart(show_plot=args.show_plot)
        print(f"\n✅ Full comparison complete! Chart: {chart_path}")

    else:
        # Default: show help
        parser.print_help()
        print("\n" + "-" * 70)
        print("QUICK START:")
        print("  python run_method_comparison.py --demo    # See visualization (no GPU)")
        print("  python run_method_comparison.py --quick   # Quick test (8GB GPU)")
        print("  python run_method_comparison.py --full    # Full benchmark (24GB+ GPU)")


if __name__ == "__main__":
    main()
