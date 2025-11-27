#!/usr/bin/env python3
"""
End-to-end benchmark for Timing Detection (Challenge 1)

This script tests the complete timing judgment pipeline:
1. Loads timing judgment dataset
2. Runs different detector strategies
3. Computes evaluation metrics
4. Generates comparison visualizations

Output directory: .sage/benchmark/results/timing/

Usage:
    python run_timing_benchmark.py
    python run_timing_benchmark.py --max-samples 100 --verbose
    python run_timing_benchmark.py --detectors timing.rule_based timing.hybrid timing.embedding
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Setup paths
SCRIPT_DIR = Path(__file__).resolve().parent
BENCHMARK_AGENT_DIR = SCRIPT_DIR.parent.parent
BENCHMARK_ROOT = BENCHMARK_AGENT_DIR.parent.parent.parent  # sage-benchmark
sys.path.insert(0, str(BENCHMARK_ROOT / "src"))

# Import data paths module
try:
    from sage.benchmark.benchmark_agent.data_paths import get_runtime_paths

    runtime_paths = get_runtime_paths()
    DEFAULT_DATA_DIR = runtime_paths.timing_judgment_dir
    DEFAULT_OUTPUT_DIR = runtime_paths.timing_judgment_results
except ImportError:
    # Fallback for standalone execution
    SAGE_ROOT = BENCHMARK_ROOT.parent.parent
    DEFAULT_DATA_DIR = SAGE_ROOT / ".sage" / "benchmark" / "data" / "timing_judgment"
    DEFAULT_OUTPUT_DIR = SAGE_ROOT / ".sage" / "benchmark" / "results" / "timing"


@dataclass
class TimingResult:
    """Result from a single detector evaluation."""

    detector: str
    accuracy: float
    precision: float
    recall: float
    f1: float
    total_samples: int
    correct: int
    tool_accuracy: float
    no_tool_accuracy: float
    details: dict[str, Any] = field(default_factory=dict)


def load_timing_data(data_dir: Path, split: str = "test") -> list[dict]:
    """
    Load timing judgment data from JSONL files.

    Args:
        data_dir: Directory containing the data files
        split: Which split to load (train/dev/test)

    Returns:
        List of sample dictionaries
    """
    data_file = data_dir / f"{split}.jsonl"

    if not data_file.exists():
        print(f"Data file not found: {data_file}")
        print("Please run prepare_timing_data.py first:")
        print(f"  python scripts/prepare_timing_data.py --output {data_dir}")
        return []

    samples = []
    with open(data_file, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))

    return samples


def create_mock_message(sample: dict) -> Any:
    """Create a TimingMessage-like object from sample dict."""

    class MockMessage:
        def __init__(self, sample_id: str, message: str, context: dict, direct_answer: str = None):
            self.sample_id = sample_id
            self.message = message
            self.context = context
            self.direct_answer = direct_answer

    return MockMessage(
        sample_id=sample["sample_id"],
        message=sample["message"],
        context=sample.get("context", {}),
        direct_answer=sample.get("direct_answer"),
    )


def evaluate_detector(
    detector_name: str,
    samples: list[dict],
    max_samples: int | None = None,
    verbose: bool = False,
) -> TimingResult:
    """
    Evaluate a single detector on the dataset.

    Args:
        detector_name: Name of the detector strategy
        samples: List of sample dictionaries
        max_samples: Maximum number of samples to evaluate
        verbose: Whether to print progress

    Returns:
        TimingResult with metrics
    """
    from sage.benchmark.benchmark_agent import get_adapter_registry
    from sage.benchmark.benchmark_agent.evaluation import compute_metrics

    registry = get_adapter_registry()

    # Get detector
    try:
        detector = registry.get(detector_name)
    except ValueError as e:
        print(f"Error loading detector {detector_name}: {e}")
        return TimingResult(
            detector=detector_name,
            accuracy=0,
            precision=0,
            recall=0,
            f1=0,
            total_samples=0,
            correct=0,
            tool_accuracy=0,
            no_tool_accuracy=0,
            details={"error": str(e)},
        )

    # Evaluate
    predictions = []
    references = []

    eval_samples = samples[:max_samples] if max_samples else samples

    for idx, sample in enumerate(eval_samples):
        if verbose and (idx + 1) % 50 == 0:
            print(f"  Processing {idx + 1}/{len(eval_samples)}...")

        message = create_mock_message(sample)

        try:
            decision = detector.decide(message)
            pred = {
                "sample_id": sample["sample_id"],
                "should_call_tool": decision.should_call_tool,
                "confidence": decision.confidence,
                "reasoning": decision.reasoning,
            }
        except Exception as e:
            if verbose:
                print(f"  Error on sample {sample['sample_id']}: {e}")
            pred = {
                "sample_id": sample["sample_id"],
                "should_call_tool": False,
                "confidence": 0,
                "reasoning": f"Error: {e}",
            }

        predictions.append(pred)
        references.append(
            {
                "sample_id": sample["sample_id"],
                "should_call_tool": sample["should_call_tool"],
            }
        )

    # Compute metrics
    metrics = compute_metrics(
        task="timing_detection",
        predictions=predictions,
        references=references,
        metrics=["accuracy", "precision", "recall", "f1"],
    )

    # Extract accuracy details
    acc_details = metrics.get("accuracy_details", {})

    return TimingResult(
        detector=detector_name,
        accuracy=metrics.get("accuracy", 0),
        precision=metrics.get("precision", 0),
        recall=metrics.get("recall", 0),
        f1=metrics.get("f1", 0),
        total_samples=len(eval_samples),
        correct=acc_details.get("correct", int(metrics.get("accuracy", 0) * len(eval_samples))),
        tool_accuracy=acc_details.get("tool_accuracy", 0),
        no_tool_accuracy=acc_details.get("no_tool_accuracy", 0),
        details={"predictions": predictions, "references": references},
    )


def print_results(results: list[TimingResult], target_accuracy: float = 0.95):
    """Print results in a formatted table."""
    print("\n" + "=" * 80)
    print("TIMING DETECTION BENCHMARK RESULTS")
    print("=" * 80)
    print(f"Target Accuracy: {target_accuracy * 100:.1f}%")
    print("-" * 80)
    print(
        f"{'Detector':<25} {'Accuracy':>10} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Status':>10}"
    )
    print("-" * 80)

    for r in results:
        status = "✓ PASS" if r.accuracy >= target_accuracy else "✗ FAIL"
        print(
            f"{r.detector:<25} {r.accuracy * 100:>9.2f}% {r.precision * 100:>9.2f}% "
            f"{r.recall * 100:>9.2f}% {r.f1 * 100:>9.2f}% {status:>10}"
        )

    print("-" * 80)
    print(f"Samples evaluated: {results[0].total_samples if results else 0}")
    print("=" * 80)

    # Print per-class accuracy
    print("\nPer-Class Accuracy:")
    print("-" * 60)
    print(f"{'Detector':<25} {'Tool-Needed':>15} {'No-Tool':>15}")
    print("-" * 60)
    for r in results:
        print(
            f"{r.detector:<25} {r.tool_accuracy * 100:>14.2f}% {r.no_tool_accuracy * 100:>14.2f}%"
        )
    print("-" * 60)


def generate_visualization(results: list[TimingResult], output_dir: Path):
    """
    Generate comparison charts for detector performance.

    Args:
        results: List of TimingResult from each detector
        output_dir: Directory to save charts
    """
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("\nNote: matplotlib not available, skipping visualization")
        print("Install with: pip install matplotlib")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    # Chart 1: Overall metrics comparison
    fig, ax = plt.subplots(figsize=(12, 6))

    detectors = [r.detector for r in results]
    x = np.arange(len(detectors))
    width = 0.2

    metrics = {
        "Accuracy": [r.accuracy for r in results],
        "Precision": [r.precision for r in results],
        "Recall": [r.recall for r in results],
        "F1": [r.f1 for r in results],
    }

    colors = ["#2ecc71", "#3498db", "#e74c3c", "#9b59b6"]
    for i, (metric_name, values) in enumerate(metrics.items()):
        offset = width * (i - 1.5)
        bars = ax.bar(
            x + offset, [v * 100 for v in values], width, label=metric_name, color=colors[i]
        )
        # Add value labels on bars
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 1,
                f"{val * 100:.1f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    # Add target line
    ax.axhline(y=95, color="red", linestyle="--", linewidth=2, label="Target (95%)")

    ax.set_xlabel("Detector Strategy")
    ax.set_ylabel("Score (%)")
    ax.set_title("Timing Detection Benchmark - Strategy Comparison")
    ax.set_xticks(x)
    ax.set_xticklabels([d.replace("timing.", "") for d in detectors])
    ax.legend(loc="lower right")
    ax.set_ylim(0, 110)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    chart_path = output_dir / "timing_metrics_comparison.png"
    plt.savefig(chart_path, dpi=150)
    plt.close()
    print(f"\nSaved metrics comparison chart: {chart_path}")

    # Chart 2: Per-class accuracy
    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(len(detectors))
    width = 0.35

    tool_acc = [r.tool_accuracy * 100 for r in results]
    no_tool_acc = [r.no_tool_accuracy * 100 for r in results]

    bars1 = ax.bar(x - width / 2, tool_acc, width, label="Tool-Needed", color="#3498db")
    bars2 = ax.bar(x + width / 2, no_tool_acc, width, label="No-Tool-Needed", color="#2ecc71")

    # Add value labels
    for bar, val in zip(bars1, tool_acc):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,
            f"{val:.1f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    for bar, val in zip(bars2, no_tool_acc):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,
            f"{val:.1f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    ax.axhline(y=95, color="red", linestyle="--", linewidth=2, label="Target (95%)")

    ax.set_xlabel("Detector Strategy")
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Timing Detection - Per-Class Accuracy")
    ax.set_xticks(x)
    ax.set_xticklabels([d.replace("timing.", "") for d in detectors])
    ax.legend()
    ax.set_ylim(0, 110)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    chart_path = output_dir / "timing_per_class_accuracy.png"
    plt.savefig(chart_path, dpi=150)
    plt.close()
    print(f"Saved per-class accuracy chart: {chart_path}")

    # Chart 3: Radar chart
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"polar": True})

    categories = ["Accuracy", "Precision", "Recall", "F1", "Tool-Acc", "No-Tool-Acc"]
    num_vars = len(categories)

    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]  # Complete the loop

    colors = ["#3498db", "#2ecc71", "#e74c3c", "#9b59b6", "#f39c12"]

    for idx, r in enumerate(results):
        values = [
            r.accuracy * 100,
            r.precision * 100,
            r.recall * 100,
            r.f1 * 100,
            r.tool_accuracy * 100,
            r.no_tool_accuracy * 100,
        ]
        values += values[:1]

        ax.plot(
            angles,
            values,
            "o-",
            linewidth=2,
            label=r.detector.replace("timing.", ""),
            color=colors[idx % len(colors)],
        )
        ax.fill(angles, values, alpha=0.1, color=colors[idx % len(colors)])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)
    ax.set_ylim(0, 100)
    ax.set_title("Timing Detection - Strategy Comparison Radar", y=1.08)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.0))

    plt.tight_layout()
    chart_path = output_dir / "timing_radar_comparison.png"
    plt.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved radar comparison chart: {chart_path}")


def save_results_json(results: list[TimingResult], output_dir: Path):
    """Save results to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    results_data = {
        "timestamp": datetime.now().isoformat(),
        "task": "timing_detection",
        "target_accuracy": 0.95,
        "results": [
            {
                "detector": r.detector,
                "accuracy": r.accuracy,
                "precision": r.precision,
                "recall": r.recall,
                "f1": r.f1,
                "total_samples": r.total_samples,
                "correct": r.correct,
                "tool_accuracy": r.tool_accuracy,
                "no_tool_accuracy": r.no_tool_accuracy,
                "passed": r.accuracy >= 0.95,
            }
            for r in results
        ],
    }

    output_file = output_dir / "timing_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2, ensure_ascii=False)

    print(f"\nSaved results JSON: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="End-to-end test for Timing Detection")
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help=f"Directory containing timing judgment data (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help=f"Directory to save results and charts (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="test",
        choices=["train", "dev", "test"],
        help="Data split to evaluate on",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Maximum number of samples to evaluate",
    )
    parser.add_argument(
        "--detectors",
        nargs="+",
        default=[
            "timing.rule_based",
            "timing.llm_based",
            "timing.hybrid",
            "timing.embedding",
        ],
        help="Detector strategies to evaluate",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed progress",
    )
    parser.add_argument(
        "--no-viz",
        action="store_true",
        help="Skip visualization generation",
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip LLM-based strategies (faster, no GPU needed). Excludes timing.llm_based and timing.hybrid.",
    )

    args = parser.parse_args()

    # Filter out LLM strategies if --skip-llm is set
    # Note: timing.hybrid also uses LLM internally, so it should be skipped too
    LLM_STRATEGIES = {"timing.llm_based", "timing.hybrid"}
    if args.skip_llm:
        args.detectors = [d for d in args.detectors if d not in LLM_STRATEGIES]
        if not args.detectors:
            print(
                "Error: All detectors were filtered out by --skip-llm. Use --detectors to specify non-LLM detectors."
            )
            sys.exit(1)

    # Resolve paths - use .sage/benchmark/ by default
    data_dir = Path(args.data_dir) if args.data_dir else DEFAULT_DATA_DIR
    output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR

    print("=" * 60)
    print("SAGE Timing Detection Benchmark (Challenge 1)")
    print("=" * 60)
    print(f"Data directory: {data_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Split: {args.split}")
    print(f"Detectors: {', '.join(args.detectors)}")
    if args.skip_llm:
        print("  ⚠️  LLM strategies skipped (--skip-llm)")
    if args.max_samples:
        print(f"Max samples: {args.max_samples}")
    print()

    # Load data
    print("Loading timing judgment data...")
    samples = load_timing_data(data_dir, args.split)

    if not samples:
        print("\nNo data found. Generating synthetic data first...")
        # Try to run prepare_timing_data.py
        import subprocess

        prepare_script = SCRIPT_DIR / "prepare_timing_data.py"
        if prepare_script.exists():
            subprocess.run(
                [sys.executable, str(prepare_script), "--output", str(data_dir)],
                check=True,
            )
            samples = load_timing_data(data_dir, args.split)

    if not samples:
        print("ERROR: Could not load or generate data")
        sys.exit(1)

    print(f"Loaded {len(samples)} samples")

    # Count class distribution
    tool_count = sum(1 for s in samples if s["should_call_tool"])
    no_tool_count = len(samples) - tool_count
    print(f"  Tool-needed: {tool_count} ({tool_count / len(samples) * 100:.1f}%)")
    print(f"  No-tool: {no_tool_count} ({no_tool_count / len(samples) * 100:.1f}%)")

    # Evaluate each detector
    results = []
    for detector in args.detectors:
        print(f"\nEvaluating: {detector}")
        result = evaluate_detector(
            detector,
            samples,
            max_samples=args.max_samples,
            verbose=args.verbose,
        )
        results.append(result)
        print(f"  Accuracy: {result.accuracy * 100:.2f}%")

    # Print results
    print_results(results)

    # Save results
    save_results_json(results, output_dir)

    # Generate visualization
    if not args.no_viz:
        generate_visualization(results, output_dir)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed = sum(1 for r in results if r.accuracy >= 0.95)
    print(f"Detectors passing target (95%): {passed}/{len(results)}")

    best = max(results, key=lambda r: r.accuracy)
    print(f"Best detector: {best.detector} ({best.accuracy * 100:.2f}%)")

    if passed == 0:
        print("\n⚠ Note: No detector achieved the 95% target accuracy.")
        print("  This may be due to the synthetic data distribution or detector limitations.")
        print("  Consider tuning the rule patterns or using LLM-based detection.")

    # Print result locations
    print("\n" + "=" * 60)
    print("📁 RESULT LOCATIONS")
    print("=" * 60)
    print(f"  📄 Results JSON: {output_dir / 'timing_results.json'}")
    print(f"  📊 Charts:       {output_dir}/")
    print("=" * 60)

    return 0 if passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
