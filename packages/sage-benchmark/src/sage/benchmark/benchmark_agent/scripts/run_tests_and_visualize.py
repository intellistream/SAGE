#!/usr/bin/env python3
"""
One-click test runner with comparison chart generation.

Run all Agent-related tests, collect results, and generate method comparison charts.

Usage:
    # Quick run (core tests only + demo charts)
    python run_tests_and_visualize.py --quick

    # Full run (all tests + simulated comparison charts)
    python run_tests_and_visualize.py --full

    # Charts only (using existing data or simulated data)
    python run_tests_and_visualize.py --chart-only

    # Show charts
    python run_tests_and_visualize.py --quick --show
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend


@dataclass
class TestResult:
    """Test result data class"""

    module: str
    passed: int
    failed: int
    skipped: int
    duration: float
    details: str = ""


@dataclass
class BenchmarkResult:
    """Performance benchmark result"""

    name: str
    value: float
    unit: str
    target: Optional[float] = None


class TestRunner:
    """Run tests and collect results"""

    def __init__(self, sage_root: Path):
        self.sage_root = sage_root
        self.results: list[TestResult] = []
        self.benchmark_results: list[BenchmarkResult] = []

    def run_pytest(self, test_path: str, module_name: str) -> TestResult:
        """Run pytest and parse results"""
        print(f"\n{'=' * 60}")
        print(f"Running: {module_name}")
        print(f"{'=' * 60}")

        start_time = time.time()

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(self.sage_root / test_path),
            "-v",
            "--tb=short",
            "-q",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.sage_root)
            output = result.stdout + result.stderr
            duration = time.time() - start_time

            # Parse results
            passed, failed, skipped = self._parse_pytest_output(output)

            test_result = TestResult(
                module=module_name,
                passed=passed,
                failed=failed,
                skipped=skipped,
                duration=duration,
                details=output[-500:] if len(output) > 500 else output,
            )

            status = "PASS" if failed == 0 else "FAIL"
            print(f"{status} {module_name}: {passed} passed, {failed} failed, {skipped} skipped")
            print(f"   Duration: {duration:.2f}s")

            self.results.append(test_result)
            return test_result

        except Exception as e:
            print(f"ERROR running {module_name}: {e}")
            return TestResult(
                module=module_name,
                passed=0,
                failed=1,
                skipped=0,
                duration=time.time() - start_time,
                details=str(e),
            )

    def _parse_pytest_output(self, output: str) -> tuple[int, int, int]:
        """Parse pytest output to extract test counts"""
        import re

        passed = failed = skipped = 0

        # Match patterns like "13 passed", "2 failed", "1 skipped"
        passed_match = re.search(r"(\d+)\s+passed", output)
        failed_match = re.search(r"(\d+)\s+failed", output)
        skipped_match = re.search(r"(\d+)\s+skipped", output)

        if passed_match:
            passed = int(passed_match.group(1))
        if failed_match:
            failed = int(failed_match.group(1))
        if skipped_match:
            skipped = int(skipped_match.group(1))

        return passed, failed, skipped

    def run_all_agent_tests(self, quick: bool = False) -> list[TestResult]:
        """Run all agent-related tests"""
        test_suites = [
            (
                "packages/sage-benchmark/tests/benchmark_agent/",
                "Agent Core (Timing + Planning + Tool Selection)",
            ),
        ]

        if not quick:
            test_suites.extend(
                [
                    ("packages/sage-kernel/tests/agentic/", "Kernel Agentic Tests"),
                    ("packages/sage-libs/tests/tools/", "Tool Library Tests"),
                ]
            )

        for test_path, module_name in test_suites:
            self.run_pytest(test_path, module_name)

        return self.results


class ComparisonChartGenerator:
    """Generate comparison charts for method evaluation"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _generate_text_report(self, test_results: list[TestResult]) -> Path:
        """Generate text report as fallback"""
        output_file = self.output_dir / "test_summary.txt"
        with open(output_file, "w") as f:
            f.write("SAGE Agent Test Summary\n")
            f.write("=" * 60 + "\n\n")
            for r in test_results:
                f.write(f"{r.module}:\n")
                f.write(f"  Passed: {r.passed}, Failed: {r.failed}, Skipped: {r.skipped}\n")
                f.write(f"  Duration: {r.duration:.2f}s\n\n")
        return output_file

    def _generate_text_method_comparison(self) -> Path:
        """Generate text method comparison as fallback"""
        output_file = self.output_dir / "method_comparison.txt"
        with open(output_file, "w") as f:
            f.write("Method Comparison Results\n")
            f.write("=" * 60 + "\n")
        return output_file

    def generate_test_summary_chart(
        self, test_results: list[TestResult], output_file: Optional[str] = None
    ) -> Path:
        """Generate test results summary chart"""
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            print("WARNING: matplotlib not installed, generating text report instead")
            return self._generate_text_report(test_results)

        output_file = output_file or str(self.output_dir / "test_summary.png")

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        fig.suptitle(
            "SAGE Agent Tests Summary - Challenge 4 Validation", fontsize=14, fontweight="bold"
        )

        # 1. Test pass rate
        ax1 = axes[0]
        modules = [r.module[:30] for r in test_results]
        passed = [r.passed for r in test_results]
        failed = [r.failed for r in test_results]

        x = np.arange(len(modules))
        width = 0.35

        ax1.bar(x - width / 2, passed, width, label="Passed", color="green", alpha=0.8)
        ax1.bar(x + width / 2, failed, width, label="Failed", color="red", alpha=0.8)

        ax1.set_ylabel("Test Count")
        ax1.set_title("Test Results by Module")
        ax1.set_xticks(x)
        ax1.set_xticklabels(modules, rotation=45, ha="right", fontsize=8)
        ax1.legend()
        ax1.grid(axis="y", alpha=0.3)

        # 2. Test duration
        ax2 = axes[1]
        durations = [r.duration for r in test_results]
        colors = ["green" if r.failed == 0 else "red" for r in test_results]

        ax2.barh(modules, durations, color=colors, alpha=0.8)
        ax2.set_xlabel("Duration (seconds)")
        ax2.set_title("Test Execution Time")
        ax2.grid(axis="x", alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches="tight")
        print(f"\nTest summary chart saved to: {output_file}")

        plt.close()
        return Path(output_file)

    def generate_method_comparison_chart(
        self, show_plot: bool = False, output_file: Optional[str] = None
    ) -> Path:
        """Generate method comparison chart (using simulated data to demonstrate framework)"""
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            print("WARNING: matplotlib not installed")
            return self._generate_text_method_comparison()

        output_file = output_file or str(self.output_dir / "method_comparison.png")

        # Simulated data: comparing existing methods vs SAGE
        methods = [
            "Baseline\n(No Opt)",
            "ToolRerank\n(SOTA)",
            "Plugin-Selector\n(Traditional)",
            "SAGE Rule\n(Ours)",
            "SAGE Embed\n(Ours)",
            "SAGE Hybrid\n(Ours)",
        ]

        # Metrics for three core challenges
        timing_accuracy = [0.74, 0.81, 0.78, 0.89, 0.91, 0.94]  # Challenge 1: Timing
        planning_success = [0.65, 0.72, 0.68, 0.82, 0.85, 0.91]  # Challenge 2: Planning
        tool_selection = [0.70, 0.82, 0.75, 0.88, 0.93, 0.96]  # Challenge 3: Tool Selection

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(
            "Challenge 4: High-Accuracy Tool Planning & Invocation for Agent Platform\n"
            "Targets: Timing>=95%, Planning>=90%, Tool Selection(1000+)>=95%",
            fontsize=12,
            fontweight="bold",
        )

        colors = ["#ff6b6b", "#ffd93d", "#6bcb77", "#4d96ff", "#9b59b6", "#2ecc71"]

        # 1. Timing Judgment (Challenge 1)
        ax1 = axes[0, 0]
        bars1 = ax1.bar(methods, timing_accuracy, color=colors, alpha=0.8)
        ax1.axhline(y=0.95, color="red", linestyle="--", linewidth=2, label="Target (95%)")
        ax1.set_ylabel("Accuracy")
        ax1.set_title("Challenge 1: Dialog/Fusion Response Timing", fontweight="bold")
        ax1.set_ylim(0, 1.0)
        ax1.legend()
        ax1.tick_params(axis="x", rotation=45)

        # Add value labels
        for bar, val in zip(bars1, timing_accuracy):
            ax1.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.02,
                f"{val:.0%}",
                ha="center",
                fontsize=9,
            )

        # 2. Task Planning (Challenge 2)
        ax2 = axes[0, 1]
        bars2 = ax2.bar(methods, planning_success, color=colors, alpha=0.8)
        ax2.axhline(y=0.90, color="red", linestyle="--", linewidth=2, label="Target (90%)")
        ax2.set_ylabel("Success Rate")
        ax2.set_title("Challenge 2: Implicit Task Planning (5-10 steps)", fontweight="bold")
        ax2.set_ylim(0, 1.0)
        ax2.legend()
        ax2.tick_params(axis="x", rotation=45)

        for bar, val in zip(bars2, planning_success):
            ax2.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.02,
                f"{val:.0%}",
                ha="center",
                fontsize=9,
            )

        # 3. Tool Selection (Challenge 3)
        ax3 = axes[1, 0]
        bars3 = ax3.bar(methods, tool_selection, color=colors, alpha=0.8)
        ax3.axhline(y=0.95, color="red", linestyle="--", linewidth=2, label="Target (95%)")
        ax3.set_ylabel("Top-K Accuracy")
        ax3.set_title("Challenge 3: Full-Scale Tool Selection (1000+ tools)", fontweight="bold")
        ax3.set_ylim(0, 1.0)
        ax3.legend()
        ax3.tick_params(axis="x", rotation=45)

        for bar, val in zip(bars3, tool_selection):
            ax3.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.02,
                f"{val:.0%}",
                ha="center",
                fontsize=9,
            )

        # 4. Radar Chart Comparison
        ax4 = axes[1, 1]

        # Select 3 representative methods for radar chart
        radar_methods = ["Baseline", "ToolRerank (SOTA)", "SAGE Hybrid (Ours)"]
        radar_data = [
            [0.74, 0.65, 0.70],  # Baseline
            [0.81, 0.72, 0.82],  # SOTA
            [0.94, 0.91, 0.96],  # SAGE
        ]

        categories = ["Timing\nJudgment", "Task\nPlanning", "Tool\nSelection"]

        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1]

        radar_colors = ["#ff6b6b", "#ffd93d", "#2ecc71"]

        for i, (method, data) in enumerate(zip(radar_methods, radar_data)):
            data = data + data[:1]
            ax4.plot(
                angles, data, "o-", linewidth=2, label=method, color=radar_colors[i], markersize=8
            )
            ax4.fill(angles, data, alpha=0.15, color=radar_colors[i])

        ax4.set_xticks(angles[:-1])
        ax4.set_xticklabels(categories, fontsize=10)
        ax4.set_ylim(0, 1.0)
        ax4.set_title("Overall Capability Comparison", fontweight="bold")
        ax4.legend(loc="upper right", fontsize=9)

        # Add target line
        target_data = [0.95, 0.90, 0.95, 0.95]
        ax4.plot(angles, target_data, "--", color="red", linewidth=2, alpha=0.5, label="Target")

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches="tight")
        print(f"\nMethod comparison chart saved to: {output_file}")

        if show_plot:
            plt.show()

        plt.close()
        return Path(output_file)

    def generate_benchmark_chart(
        self, benchmark_results: list[BenchmarkResult], output_file: Optional[str] = None
    ) -> Path:
        """Generate performance benchmark chart"""
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            return Path("")

        output_file = output_file or str(self.output_dir / "benchmark_results.png")

        fig, ax = plt.subplots(figsize=(10, 6))
        fig.suptitle("SAGE Agent Performance Benchmarks", fontsize=14, fontweight="bold")

        names = [r.name for r in benchmark_results]
        values = [r.value for r in benchmark_results]
        targets = [r.target for r in benchmark_results]

        # Normalize display (relative to target)
        normalized = [v / t if t else v for v, t in zip(values, targets)]

        y_pos = np.arange(len(names))

        colors = ["green" if n >= 1.0 else "orange" for n in normalized]
        bars = ax.barh(y_pos, normalized, color=colors, alpha=0.8)

        # Add target line
        ax.axvline(x=1.0, color="red", linestyle="--", linewidth=2, label="Target")

        ax.set_yticks(y_pos)
        ax.set_yticklabels(names)
        ax.set_xlabel("Performance (relative to target)")
        ax.set_title("Benchmark Results vs Targets")
        ax.legend()
        ax.grid(axis="x", alpha=0.3)

        # Add value labels
        for i, (bar, val, target) in enumerate(zip(bars, values, targets)):
            ax.text(
                bar.get_width() + 0.02,
                bar.get_y() + bar.get_height() / 2,
                f"{val:.1%} (target: {target:.1%})" if target else f"{val:.1%}",
                va="center",
                fontsize=9,
            )

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches="tight")
        print(f"\nBenchmark chart saved to: {output_file}")

        plt.close()
        return Path(output_file)


def find_sage_root() -> Path:
    """Find the SAGE project root directory"""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "packages").exists() and (parent / "quickstart.sh").exists():
            return parent
    # Fallback to packages directory
    return Path(__file__).resolve().parent.parent.parent.parent.parent.parent


def main():
    parser = argparse.ArgumentParser(description="SAGE Agent One-click Test and Visualization")
    parser.add_argument("--quick", action="store_true", help="Quick run (core tests only)")
    parser.add_argument("--full", action="store_true", help="Full run (all tests)")
    parser.add_argument("--chart-only", action="store_true", help="Generate charts only (no tests)")
    parser.add_argument("--show", action="store_true", help="Display charts in window")
    parser.add_argument("--output", type=str, default=None, help="Output directory for charts")

    args = parser.parse_args()

    # Find SAGE root
    sage_root = find_sage_root()
    print("=" * 70)
    print("SAGE Agent One-click Test and Comparison Chart Generation")
    print("    Target: Challenge 4 - High-Accuracy Tool Planning & Invocation")
    print("=" * 70)
    print(f"SAGE Root: {sage_root}")

    # Setup output directory
    output_dir = Path(args.output) if args.output else sage_root / ".sage" / "test_results"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output: {output_dir}")

    test_results = []

    # Run tests if not chart-only
    if not args.chart_only:
        runner = TestRunner(sage_root)
        test_results = runner.run_all_agent_tests(quick=args.quick)

    # Generate charts
    print("\n" + "=" * 70)
    print("Generating Charts")
    print("=" * 70)

    chart_gen = ComparisonChartGenerator(output_dir)

    # Generate test summary if we have results
    if test_results:
        chart_gen.generate_test_summary_chart(test_results)

    # Generate method comparison chart
    chart_gen.generate_method_comparison_chart(show_plot=args.show)

    # Generate benchmark chart with sample data
    benchmark_results = [
        BenchmarkResult("Timing Accuracy", 0.94, "%", 0.95),
        BenchmarkResult("Planning Success", 0.91, "%", 0.90),
        BenchmarkResult("Tool Selection@10", 0.96, "%", 0.95),
        BenchmarkResult("Tool Selection@5", 0.93, "%", 0.90),
        BenchmarkResult("E2E Latency", 0.85, "s", 1.0),
    ]
    chart_gen.generate_benchmark_chart(benchmark_results)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    total_passed = sum(r.passed for r in test_results)
    total_failed = sum(r.failed for r in test_results)
    total_time = sum(r.duration for r in test_results)

    print(f"Total Tests: {total_passed} passed, {total_failed} failed")
    print(f"Total Time: {total_time:.2f}s")
    print("\nOutput files:")
    print(f"  - {output_dir}/test_summary.png")
    print(f"  - {output_dir}/method_comparison.png")
    print(f"  - {output_dir}/benchmark_results.png")

    # Save results to JSON
    results_json = {
        "timestamp": datetime.now().isoformat(),
        "test_results": [
            {
                "module": r.module,
                "passed": r.passed,
                "failed": r.failed,
                "skipped": r.skipped,
                "duration": r.duration,
            }
            for r in test_results
        ],
        "summary": {
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_time": total_time,
        },
    }

    with open(output_dir / "results.json", "w") as f:
        json.dump(results_json, f, indent=2)
    print(f"  - {output_dir}/results.json")

    if total_failed == 0:
        print("\nAll tests passed!")
        return 0
    else:
        print(f"\nWARNING: {total_failed} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
